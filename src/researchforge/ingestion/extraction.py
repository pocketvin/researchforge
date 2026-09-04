"""Deterministic extraction of the six bounded financial statement metrics."""

# ruff: noqa: RUF001 -- Chinese financial punctuation and Unicode minus signs are inputs.

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, cast

from researchforge.ingestion.errors import IngestionAbstention

JsonObject = dict[str, Any]
MetricCode = Literal[
    "revenue",
    "operating_cost",
    "net_income",
    "operating_cash_flow",
    "accounts_receivable",
    "inventory",
]
StatementName = Literal["合并资产负债表", "合并利润表", "合并现金流量表"]

EXTRACTOR_NAME = "researchforge_deterministic_financial_statement"
EXTRACTOR_VERSION = "1.1.0"

_NUMBER_PATTERN = re.compile(
    r"(?<![\d,])(?:[（(]\s*)?[+\-−－]?(?:\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\.\d+)?(?:\s*[）)])?(?![\d,])"
)
_UNIT_PATTERN = re.compile(r"单位[：:]?(?:人民币)?(百万元|万元|千元|元)(?:币种[：:]?人民币)?")
_GLOBAL_UNIT_PATTERN = re.compile(
    r"(?:本)?公司财务报表及附注的单位为[：:](?:人民币)?(百万元|万元|千元|元)"
)
_HEADER_LABEL_PATTERN = re.compile(
    r"截至\d{4}年\d{1,2}月\d{1,2}日止\d{1,2}个月期间"
    r"|\d{4}年\d{1,2}月\d{1,2}日"
    r"|\d{4}年(?:半年度|1[—\-至][369]月|第一季度|前三季度)"
    r"|\d{4}年度|\d{4}年"
    r"|期末余额|期初余额|本报告期末|上年度末|本期发生额|上期发生额"
    r"|本报告期|上年同期|本期金额|上期金额|本年累计数|上年累计数"
)
_CELL_PATTERN = re.compile(_NUMBER_PATTERN.pattern + r"|(?<!\S)[—–-](?!\S)")
_ENUMERATION_PATTERN = re.compile(
    r"^(?:(?:[（(]?[一二三四五六七八九十]+[）)、.．])|(?:[（(]?\d+[）)、.．]))\s*"
)
_PARENTHETICAL_PATTERN = re.compile(r"（[^）]*）|\([^)]*\)")
_STATEMENT_TITLES = (
    "合并资产负债表",
    "母公司资产负债表",
    "合并利润表",
    "母公司利润表",
    "合并现金流量表",
    "母公司现金流量表",
    "公司资产负债表",
    "公司利润表",
    "公司现金流量表",
    "合并所有者权益变动表",
    "母公司所有者权益变动表",
    "公司所有者权益变动表",
)
_TARGET_STATEMENTS = frozenset({"合并资产负债表", "合并利润表", "合并现金流量表"})
_UNIT_SCALES: dict[str, int] = {"元": 1, "千元": 1_000, "万元": 10_000, "百万元": 1_000_000}


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_hash(value: JsonObject) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    """One allowed metric and its statement-specific exact row aliases."""

    metric_code: MetricCode
    statement: StatementName
    row_aliases: tuple[str, ...]


METRIC_DEFINITIONS: tuple[MetricDefinition, ...] = (
    MetricDefinition("revenue", "合并利润表", ("营业收入",)),
    MetricDefinition("operating_cost", "合并利润表", ("营业成本",)),
    MetricDefinition(
        "net_income",
        "合并利润表",
        (
            "归属于母公司股东的净利润",
            "归属于母公司所有者的净利润",
            "归属于上市公司股东的净利润",
        ),
    ),
    MetricDefinition(
        "operating_cash_flow",
        "合并现金流量表",
        ("经营活动产生的现金流量净额",),
    ),
    MetricDefinition("accounts_receivable", "合并资产负债表", ("应收账款",)),
    MetricDefinition("inventory", "合并资产负债表", ("存货",)),
)


@dataclass(frozen=True, slots=True)
class StatementLine:
    """A physical-page line with inherited table semantics."""

    page: int
    line_number: int
    text: str
    statement: StatementName
    unit_label: str | None
    scale: int | None
    column_label: str | None
    column_index: int = 0
    has_note_column: bool = False


@dataclass(frozen=True, slots=True)
class ExtractedFinancialCell:
    """A deterministically recoverable statement cell before fact promotion."""

    metric_code: MetricCode
    statement: StatementName
    page: int
    line_start: int
    line_end: int
    row_label: str
    column_label: str
    raw_value: str
    reported_value: Decimal
    unit_label: str
    scale: int
    normalized_value: Decimal
    evidence_text: str
    page_text_hash: str
    recovery_hash: str

    def manifest_value(self) -> JsonObject:
        return {
            "metric_code": self.metric_code,
            "statement": self.statement,
            "page": self.page,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "row_label": self.row_label,
            "column_label": self.column_label,
            "raw_value": self.raw_value,
            "reported_value": format(self.reported_value, "f"),
            "unit_label": self.unit_label,
            "scale": self.scale,
            "normalized_value": format(self.normalized_value, "f"),
            "evidence_text": self.evidence_text,
            "evidence_text_hash": _sha256_text(self.evidence_text),
            "page_text_hash": self.page_text_hash,
            "recovery_hash": self.recovery_hash,
        }


@dataclass(frozen=True, slots=True)
class ExtractionBatch:
    """The complete all-or-nothing six-metric extraction result."""

    cells: tuple[ExtractedFinancialCell, ...]
    parser_text_hash: str

    def manifest_value(self) -> JsonObject:
        return {
            "schema_version": "1.5.0",
            "extractor_name": EXTRACTOR_NAME,
            "extractor_version": EXTRACTOR_VERSION,
            "method": "deterministic_pdf_text_recovery",
            "numerical_truth_source": "verified_pdf",
            "llm_used": False,
            "ambiguity_policy": "abstain_entire_package",
            "target_metrics": [definition.metric_code for definition in METRIC_DEFINITIONS],
            "promoted_metric_count": len(self.cells),
            "parser_text_hash": self.parser_text_hash,
            "recoveries": [cell.manifest_value() for cell in self.cells],
        }


class DeterministicFinancialFactExtractor:
    """Recover exactly six metrics from native PDF text, or abstain."""

    def extract(
        self,
        *,
        pages: tuple[str, ...],
        parser_text_hash: str,
        reporting_period: JsonObject,
    ) -> ExtractionBatch:
        if not pages or not any(_compact(page) for page in pages):
            raise IngestionAbstention(
                "TEXT_LAYER_REQUIRED",
                "parsing",
                "The verified filing has no usable native text layer; OCR is outside scope.",
            )
        if reporting_period.get("statement_scope") != "consolidated":
            raise IngestionAbstention(
                "STATEMENT_SCOPE_UNSUPPORTED",
                "normalization",
                "The bounded extractor only promotes consolidated financial statements.",
            )

        lines = self._statement_lines(pages, reporting_period)
        cells = tuple(
            self._extract_metric(definition, lines, pages) for definition in METRIC_DEFINITIONS
        )
        if {cell.metric_code for cell in cells} != {
            definition.metric_code for definition in METRIC_DEFINITIONS
        }:
            raise IngestionAbstention(
                "SIX_METRIC_SET_INCOMPLETE",
                "verification",
                "The promoted metric set is not exactly the six-metric extraction contract.",
            )
        return ExtractionBatch(cells=cells, parser_text_hash=parser_text_hash)

    def _statement_lines(
        self,
        pages: tuple[str, ...],
        reporting_period: JsonObject,
    ) -> tuple[StatementLine, ...]:
        active_statement: StatementName | None = None
        active_unit: str | None = None
        active_scale: int | None = None
        active_column: str | None = None
        column_index = 0
        has_note_column = False
        global_unit: str | None = None
        output: list[StatementLine] = []

        for page_number, page_text in enumerate(pages, start=1):
            page_lines = page_text.splitlines()
            for line_number, raw_line in enumerate(page_lines, start=1):
                text = raw_line.strip()
                if not text:
                    continue
                compact = _compact(text)
                global_match = _GLOBAL_UNIT_PATTERN.fullmatch(compact)
                if global_match is not None:
                    unit = global_match.group(1)
                    if global_unit is not None and global_unit != unit:
                        raise IngestionAbstention(
                            "STATEMENT_UNIT_AMBIGUOUS",
                            "normalization",
                            "Conflicting financial-report-wide unit declarations.",
                        )
                    global_unit = unit
                    continue
                statement_title = self._statement_title(compact)
                if statement_title is not None:
                    active_statement = (
                        cast(StatementName, statement_title)
                        if statement_title in _TARGET_STATEMENTS
                        else None
                    )
                    active_unit = global_unit
                    active_scale = _UNIT_SCALES[global_unit] if global_unit else None
                    active_column = None
                    column_index = 0
                    has_note_column = False
                    continue
                if active_statement is None:
                    continue

                unit = self._unit(compact)
                if unit is not None:
                    if active_unit is not None and active_unit != unit:
                        raise IngestionAbstention(
                            "STATEMENT_UNIT_AMBIGUOUS",
                            "normalization",
                            f"{active_statement} contains conflicting unit declarations.",
                        )
                    active_unit = unit
                    active_scale = _UNIT_SCALES[unit]
                    continue

                if re.match(r"^(?:项目|(?:资产|负债|股东权益)?附注)", compact):
                    header = self._header_text(page_lines, line_number - 1)
                    columns = self._current_columns(header, active_statement, reporting_period)
                    if columns is None:
                        raise IngestionAbstention(
                            "REPORTING_COLUMN_UNRESOLVED",
                            "normalization",
                            (
                                f"Could not resolve the current-period column in "
                                f"{active_statement} on physical page {page_number}."
                            ),
                        )
                    active_column, column_index, has_note_column = columns
                    continue

                output.append(
                    StatementLine(
                        page=page_number,
                        line_number=line_number,
                        text=text,
                        statement=active_statement,
                        unit_label=active_unit,
                        scale=active_scale,
                        column_label=active_column,
                        column_index=column_index,
                        has_note_column=has_note_column,
                    )
                )
        return tuple(output)

    @staticmethod
    def _statement_title(compact: str) -> str | None:
        for title in _STATEMENT_TITLES:
            if re.fullmatch(rf"(?:\d+[、.．])?{title}", compact):
                return title
        return None

    @staticmethod
    def _unit(compact: str) -> str | None:
        match = _UNIT_PATTERN.fullmatch(compact)
        return match.group(1) if match is not None else None

    @staticmethod
    def _header_text(lines: list[str], start: int) -> str:
        """Join only adjacent header fragments, never a financial data row."""
        parts = [lines[start]]
        for line in lines[start + 1 : start + 20]:
            compact = _compact(line)
            if not compact:
                continue
            if re.match(r"^(?:截至|\d{1,4}(?:年|月|个月)|[（(](?:未经审计|经审计))", compact):
                parts.append(line)
            else:
                break
        return _compact(" ".join(parts))

    @staticmethod
    def _current_columns(
        compact: str,
        statement: StatementName,
        reporting_period: JsonObject,
    ) -> tuple[str, int, bool] | None:
        year = int(reporting_period["fiscal_year"])
        if statement == "合并资产负债表":
            end = str(reporting_period["period_end"])
            end_year, end_month, end_day = (int(value) for value in end.split("-"))
            aliases = (
                f"{end_year}年{end_month}月{end_day}日",
                "期末余额",
                "本报告期末",
            )
        else:
            period = str(reporting_period["fiscal_period"])
            specific: tuple[str, ...]
            if period == "H1":
                specific = (
                    f"截至{year}年6月30日止6个月期间",
                    f"{year}年半年度",
                    f"{year}年1—6月",
                    f"{year}年1-6月",
                    f"{year}年1至6月",
                )
            elif period == "FY":
                specific = (f"{year}年度", f"{year}年")
            elif period == "Q1":
                specific = (f"{year}年1—3月", f"{year}年1-3月", f"{year}年第一季度")
            elif period == "Q3":
                specific = (f"{year}年1—9月", f"{year}年1-9月", f"{year}年前三季度")
            else:
                specific = ()
            aliases = (*specific, "本期发生额", "本报告期", "本期金额", "本年累计数")
        labels = _HEADER_LABEL_PATTERN.findall(compact)
        matches = [index for index, label in enumerate(labels) if label in aliases]
        if len(labels) != 2 or len(matches) != 1:
            return None
        index = matches[0]
        return labels[index], index, "附注" in compact

    def _extract_metric(
        self,
        definition: MetricDefinition,
        lines: tuple[StatementLine, ...],
        pages: tuple[str, ...],
    ) -> ExtractedFinancialCell:
        statement_lines = [line for line in lines if line.statement == definition.statement]
        candidates: list[ExtractedFinancialCell] = []
        for index, first in enumerate(statement_lines):
            first_text = self._strip_enumeration(first.text)
            first_token = _CELL_PATTERN.search(first_text)
            prefix = self._normalize_row_label(
                first_text[: first_token.start()] if first_token else first_text
            )
            if not prefix or not any(alias.startswith(prefix) for alias in definition.row_aliases):
                continue
            combined_lines: list[StatementLine] = []
            for current in statement_lines[index : index + 5]:
                if current.page != first.page:
                    break
                combined_lines.append(current)
                combined_text = " ".join(item.text for item in combined_lines)
                stripped = self._strip_enumeration(combined_text)
                number_matches = list(_CELL_PATTERN.finditer(stripped))
                if len(number_matches) < 2:
                    continue
                first_number = number_matches[0]
                row_label = self._normalize_row_label(stripped[: first_number.start()])
                if row_label not in definition.row_aliases:
                    break
                tokens = [match.group(0).strip() for match in number_matches]
                if (
                    first.has_note_column
                    and len(tokens) == 3
                    and re.fullmatch(r"\d{1,3}", tokens[0])
                ):
                    tokens = tokens[1:]
                elif (
                    first.has_note_column
                    and len(tokens) == 2
                    and re.fullmatch(r"\d{1,3}", tokens[0])
                ):
                    raise IngestionAbstention(
                        "VALUE_COLUMN_AMBIGUOUS",
                        "normalization",
                        "A small integer may be a note reference rather than a value.",
                    )
                if len(tokens) != 2:
                    raise IngestionAbstention(
                        "VALUE_COLUMN_AMBIGUOUS",
                        "normalization",
                        f"{definition.metric_code} does not have two resolved value columns.",
                    )
                raw_value = tokens[first.column_index]
                if raw_value in {"-", "—", "–"}:
                    raise IngestionAbstention(
                        "METRIC_VALUE_MISSING",
                        "normalization",
                        f"{definition.metric_code} has no reported current-period value.",
                    )
                candidates.append(
                    self._promote_candidate(
                        definition=definition,
                        first=first,
                        last=combined_lines[-1],
                        row_label=row_label,
                        raw_value=raw_value,
                        evidence_text=combined_text,
                        page_text=pages[first.page - 1],
                    )
                )
                break

        unique = {candidate.recovery_hash: candidate for candidate in candidates}
        if not unique:
            raise IngestionAbstention(
                "METRIC_ROW_NOT_FOUND",
                "normalization",
                f"No unambiguous {definition.metric_code} row was found in {definition.statement}.",
            )
        if len(unique) != 1:
            pages_found = sorted({candidate.page for candidate in unique.values()})
            raise IngestionAbstention(
                "METRIC_ROW_AMBIGUOUS",
                "normalization",
                (
                    f"{definition.metric_code} matched {len(unique)} recoveries on physical "
                    f"pages {pages_found}."
                ),
            )
        return next(iter(unique.values()))

    @staticmethod
    def _strip_enumeration(text: str) -> str:
        current = text.strip()
        while True:
            updated = _ENUMERATION_PATTERN.sub("", current, count=1)
            if updated == current:
                return current
            current = updated.lstrip()

    @classmethod
    def _normalize_row_label(cls, label: str) -> str:
        compact = _compact(label)
        compact = cls._strip_enumeration(compact)
        compact = re.sub(r"^(?:其中|减|加)[：:]", "", compact)
        compact = _PARENTHETICAL_PATTERN.sub("", compact)
        return compact.strip("：:")

    def _promote_candidate(
        self,
        *,
        definition: MetricDefinition,
        first: StatementLine,
        last: StatementLine,
        row_label: str,
        raw_value: str,
        evidence_text: str,
        page_text: str,
    ) -> ExtractedFinancialCell:
        if first.unit_label is None or first.scale is None:
            raise IngestionAbstention(
                "STATEMENT_UNIT_UNRESOLVED",
                "normalization",
                f"No unit was resolved before the {definition.metric_code} row.",
            )
        if first.column_label is None:
            raise IngestionAbstention(
                "REPORTING_COLUMN_UNRESOLVED",
                "normalization",
                f"No current-period column was resolved before the {definition.metric_code} row.",
            )
        if any(
            line.unit_label != first.unit_label
            or line.scale != first.scale
            or line.column_label != first.column_label
            or line.column_index != first.column_index
            or line.has_note_column != first.has_note_column
            for line in (first, last)
        ):
            raise IngestionAbstention(
                "ROW_CONTEXT_AMBIGUOUS",
                "normalization",
                f"The {definition.metric_code} row crosses incompatible table context.",
            )
        reported = self._parse_decimal(raw_value)
        normalized = reported * Decimal(first.scale)
        if _compact(evidence_text) not in _compact(page_text):
            raise IngestionAbstention(
                "PROVENANCE_RECOVERY_FAILED",
                "verification",
                f"The {definition.metric_code} evidence cannot be recovered from its source page.",
            )
        page_hash = _sha256_text(page_text)
        recovery_material: JsonObject = {
            "metric_code": definition.metric_code,
            "statement": definition.statement,
            "page": first.page,
            "line_start": first.line_number,
            "line_end": last.line_number,
            "row_label": row_label,
            "column_label": first.column_label,
            "raw_value": raw_value.strip(),
            "reported_value": format(reported, "f"),
            "unit_label": first.unit_label,
            "scale": first.scale,
            "normalized_value": format(normalized, "f"),
            "evidence_text_hash": _sha256_text(evidence_text),
            "page_text_hash": page_hash,
        }
        return ExtractedFinancialCell(
            metric_code=definition.metric_code,
            statement=definition.statement,
            page=first.page,
            line_start=first.line_number,
            line_end=last.line_number,
            row_label=row_label,
            column_label=first.column_label,
            raw_value=raw_value.strip(),
            reported_value=reported,
            unit_label=first.unit_label,
            scale=first.scale,
            normalized_value=normalized,
            evidence_text=evidence_text,
            page_text_hash=page_hash,
            recovery_hash=_canonical_hash(recovery_material),
        )

    @staticmethod
    def _parse_decimal(raw_value: str) -> Decimal:
        compact = re.sub(r"\s+", "", raw_value)
        negative_parentheses = compact.startswith(("(", "（")) and compact.endswith((")", "）"))
        compact = compact.strip("()（）").replace(",", "")
        compact = compact.replace("−", "-").replace("－", "-")
        try:
            value = Decimal(compact)
        except InvalidOperation as exc:
            raise IngestionAbstention(
                "NUMERIC_TOKEN_INVALID",
                "normalization",
                f"Could not parse statement number {raw_value!r} deterministically.",
            ) from exc
        return -value if negative_parentheses else value
