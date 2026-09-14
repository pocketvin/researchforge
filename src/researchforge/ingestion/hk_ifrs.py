"""Deterministic HKEX IFRS statement extraction shared by the V2 runtime."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from researchforge.ingestion.errors import IngestionAbstention

_NUMBER_RE = re.compile(r"\(?-?\d[\d,]*(?:\.\d+)?\)?")
_UNIT_RE = re.compile(
    r"(?P<currency>RMB|CNY|HKD|HK\$|USD|US\$)[\u2019']?\s*(?P<scale>Million|Thousand|Billion)",
    re.IGNORECASE,
)
_SCALE = {"thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000}
_CURRENCY = {
    "RMB": "CNY",
    "CNY": "CNY",
    "HKD": "HKD",
    "HK$": "HKD",
    "USD": "USD",
    "US$": "USD",
}


@dataclass(frozen=True, slots=True)
class HkExtractedCell:
    metric_code: str
    page: int
    statement: str
    row_label: str
    raw_line: str
    reported_value: Decimal
    normalized_value: Decimal
    currency: str
    scale: int


@dataclass(frozen=True, slots=True)
class _StatementPage:
    page: int
    title: str
    lines: tuple[str, ...]
    currency: str
    scale: int


class HkIfrsExtractor:
    """Recover the six bounded canonical metrics from native-text HKEX filing pages."""

    def extract(self, pages: tuple[str, ...]) -> tuple[HkExtractedCell, ...]:
        income_page = self._find_statement_page(
            pages,
            "Consolidated Income Statement",
            required_markers=("Cost of revenues", "Equity holders of the Company"),
        )
        position_page = self._find_statement_page(
            pages,
            "Consolidated Statement of Financial Position",
            required_markers=("Accounts receivable", "Inventories"),
        )
        cash_page = self._find_statement_page(
            pages,
            "Consolidated Statement of Cash Flows",
            required_markers=("Net cash flows generated from operating activities",),
        )

        cells = (
            self._revenue_cell(income_page),
            self._row_cell(income_page, "operating_cost", ("Cost of revenues", "Cost of revenue")),
            self._row_cell(
                income_page,
                "net_income",
                (
                    "Equity holders of the Company",
                    "Owners of the Company",
                    "Equity holders of the parent",
                    "Owners of the parent",
                ),
            ),
            self._row_cell(
                cash_page,
                "operating_cash_flow",
                (
                    "Net cash flows generated from operating activities",
                    "Net cash generated from operating activities",
                    "Net cash from operating activities",
                ),
            ),
            self._row_cell(
                position_page,
                "accounts_receivable",
                ("Accounts receivable", "Trade receivables"),
            ),
            self._row_cell(position_page, "inventory", ("Inventories", "Inventory")),
        )
        if len({cell.metric_code for cell in cells}) != 6:
            raise IngestionAbstention(
                "SIX_METRIC_SET_INCOMPLETE",
                "verification",
                "HKEX extraction did not recover exactly the six-metric contract.",
            )
        return cells

    def _find_statement_page(
        self,
        pages: tuple[str, ...],
        title: str,
        *,
        required_markers: tuple[str, ...],
    ) -> _StatementPage:
        matches: list[_StatementPage] = []
        for page_number, text in enumerate(pages, start=1):
            lines = tuple(line.strip() for line in text.splitlines() if line.strip())
            if not any(self._norm(line) == self._norm(title) for line in lines):
                continue
            normalized_lines = tuple(self._norm(line) for line in lines)
            if not all(
                any(self._norm(marker) in line for line in normalized_lines)
                for marker in required_markers
            ):
                continue
            unit = self._resolve_unit(lines)
            if unit is None:
                continue
            matches.append(
                _StatementPage(
                    page=page_number,
                    title=title,
                    lines=lines,
                    currency=unit[0],
                    scale=unit[1],
                )
            )
        if len(matches) != 1:
            raise IngestionAbstention(
                "HK_STATEMENT_UNRESOLVED",
                "parsing",
                f"Expected exactly one native-text {title!r} page; found {len(matches)}.",
            )
        return matches[0]

    @staticmethod
    def _resolve_unit(lines: tuple[str, ...]) -> tuple[str, int] | None:
        for line in lines[:15]:
            match = _UNIT_RE.search(line)
            if match is None:
                continue
            raw_currency = match.group("currency").upper()
            return _CURRENCY[raw_currency], _SCALE[match.group("scale").lower()]
        return None

    @staticmethod
    def _norm(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.casefold())

    def _row_cell(
        self,
        statement: _StatementPage,
        metric: str,
        aliases: tuple[str, ...],
    ) -> HkExtractedCell:
        matches = [
            line
            for line in statement.lines
            if any(self._norm(line).startswith(self._norm(alias)) for alias in aliases)
            and len(_NUMBER_RE.findall(line)) >= 2
        ]
        if len(matches) != 1:
            raise IngestionAbstention(
                "HK_METRIC_AMBIGUOUS",
                "normalization",
                f"Expected one {metric} row in {statement.title}; found {len(matches)}.",
            )
        return self._cell_from_line(statement, metric, matches[0])

    def _revenue_cell(self, statement: _StatementPage) -> HkExtractedCell:
        direct = [
            line
            for line in statement.lines
            if self._norm(line).startswith("revenue") and len(_NUMBER_RE.findall(line)) >= 2
        ]
        if len(direct) == 1:
            return self._cell_from_line(statement, "revenue", direct[0])

        revenue_indexes = [
            index
            for index, line in enumerate(statement.lines)
            if self._norm(line) in {"revenue", "revenues"}
        ]
        if len(revenue_indexes) != 1:
            raise IngestionAbstention(
                "HK_REVENUE_UNRESOLVED", "normalization", "Revenue statement row is ambiguous."
            )
        candidates: list[str] = []
        for line in statement.lines[revenue_indexes[0] + 1 :]:
            if self._norm(line).startswith("costofrevenue"):
                break
            if len(_NUMBER_RE.findall(line)) >= 2:
                candidates.append(line)
        if not candidates:
            raise IngestionAbstention(
                "HK_REVENUE_UNRESOLVED", "normalization", "Revenue total row was not found."
            )
        return self._cell_from_line(statement, "revenue", candidates[-1])

    def _cell_from_line(
        self,
        statement: _StatementPage,
        metric: str,
        line: str,
    ) -> HkExtractedCell:
        tokens = _NUMBER_RE.findall(line)
        if len(tokens) < 2:
            raise IngestionAbstention(
                "HK_NUMERIC_CELL_MISSING", "normalization", f"No comparative values in {line!r}."
            )
        current = self._parse_number(tokens[-2])
        if metric == "operating_cost":
            current = abs(current)
        return HkExtractedCell(
            metric_code=metric,
            page=statement.page,
            statement=statement.title,
            row_label=self._row_label(line),
            raw_line=line,
            reported_value=current,
            normalized_value=current * statement.scale,
            currency=statement.currency,
            scale=statement.scale,
        )

    @staticmethod
    def _parse_number(token: str) -> Decimal:
        stripped = token.replace(",", "").strip()
        negative = stripped.startswith("(") and stripped.endswith(")")
        value = Decimal(stripped.strip("()"))
        return -value if negative else value

    @staticmethod
    def _row_label(line: str) -> str:
        match = _NUMBER_RE.search(line)
        return line[: match.start()].strip() if match is not None else line.strip()
