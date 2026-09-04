"""Deterministic HKEX IFRS annual-report ingestion for ResearchForge."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from urllib.request import Request, urlopen

from pypdf import PdfReader
from pypdf import __version__ as pypdf_version

from researchforge.ingestion.discovery import DiscoveredFiling
from researchforge.ingestion.errors import IngestionAbstention
from researchforge.retrieval.fulltext import index_pdf_pages

JsonObject = dict[str, Any]

_HEADERS = {"User-Agent": "Mozilla/5.0 ResearchForge/1.6", "Accept": "application/pdf,*/*"}
_NUMBER_RE = re.compile(r"\(?-?\d[\d,]*(?:\.\d+)?\)?")
_UNIT_RE = re.compile(
    r"(?P<currency>RMB|CNY|HKD|HK\$|USD|US\$)[\u2019']?\s*(?P<scale>Million|Thousand|Billion)",
    re.IGNORECASE,
)
_SCALE = {"thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000}
_CURRENCY = {"RMB": "CNY", "CNY": "CNY", "HKD": "HKD", "HK$": "HKD", "USD": "USD", "US$": "USD"}


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


class HkIfrsProductIngestion:
    """Recover the six bounded metrics from a native-text HKEX annual-report PDF."""

    def run(self, filing: DiscoveredFiling, *, package_root: Path) -> JsonObject:
        if filing.document_type != "annual_report":
            raise IngestionAbstention(
                "HK_PERIOD_UNSUPPORTED",
                "normalization",
                "HKEX live research currently supports annual reports only.",
            )
        payload = self._fetch(filing.source_uri)
        raw_path = package_root.parent.parent / "raw" / f"{filing.filing_id}.pdf"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        if not raw_path.exists():
            raw_path.write_bytes(payload)
        pages = tuple(page.extract_text() or "" for page in PdfReader(raw_path).pages)
        if not any(page.strip() for page in pages):
            raise IngestionAbstention(
                "TEXT_LAYER_REQUIRED",
                "parsing",
                "The HKEX filing has no usable native text layer; OCR is outside scope.",
            )
        cells = self._extract(pages)
        retrieved_at = datetime.now(UTC).isoformat()
        source_hash = hashlib.sha256(payload).hexdigest()
        artifacts = self._artifacts(
            filing,
            cells,
            pages=pages,
            source_hash=source_hash,
            retrieved_at=retrieved_at,
        )
        hashes = {path: self._hash_json(value) for path, value in artifacts.items()}
        package_hash = hashlib.sha256(self._canonical(hashes)).hexdigest()
        ingestion = self._ingestion_manifest(
            filing,
            cells,
            package_hash=package_hash,
            source_hash=source_hash,
            byte_count=len(payload),
            page_count=len(pages),
            retrieved_at=retrieved_at,
        )
        manifest = self._package_manifest(filing, artifacts, hashes, package_hash)
        self._write(package_root, artifacts, ingestion, manifest)
        return ingestion

    @staticmethod
    def _fetch(url: str) -> bytes:
        with urlopen(Request(url, headers=_HEADERS), timeout=45) as response:
            payload = cast(bytes, response.read())
        if not payload.startswith(b"%PDF"):
            raise IngestionAbstention(
                "NON_PDF_PAYLOAD", "acquisition", "HKEX source did not return a PDF payload."
            )
        return payload

    def _extract(self, pages: tuple[str, ...]) -> tuple[HkExtractedCell, ...]:
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

    @dataclass(frozen=True, slots=True)
    class _StatementPage:
        page: int
        title: str
        lines: tuple[str, ...]
        currency: str
        scale: int

    def _find_statement_page(
        self,
        pages: tuple[str, ...],
        title: str,
        *,
        required_markers: tuple[str, ...],
    ) -> _StatementPage:
        matches: list[HkIfrsProductIngestion._StatementPage] = []
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
                self._StatementPage(
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
            currency = _CURRENCY[raw_currency]
            scale = _SCALE[match.group("scale").lower()]
            return currency, scale
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
        start = revenue_indexes[0] + 1
        candidates: list[str] = []
        for line in statement.lines[start:]:
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
        stripped = stripped.strip("()")
        value = Decimal(stripped)
        return -value if negative else value

    @staticmethod
    def _row_label(line: str) -> str:
        match = _NUMBER_RE.search(line)
        return line[: match.start()].strip() if match is not None else line.strip()

    def _artifacts(
        self,
        filing: DiscoveredFiling,
        cells: tuple[HkExtractedCell, ...],
        *,
        pages: tuple[str, ...],
        source_hash: str,
        retrieved_at: str,
    ) -> dict[str, JsonObject]:
        record = filing.dynamic_record()
        source = self._source_document(
            filing, record, source_hash=source_hash, retrieved_at=retrieved_at
        )
        artifacts: dict[str, JsonObject] = {
            f"source-documents/{source['document_id']}.json": source
        }
        for cell in cells:
            fact = self._fact(
                filing, record, cell, source_hash=source_hash, retrieved_at=retrieved_at
            )
            evidence = self._evidence(filing, record, cell, retrieved_at=retrieved_at)
            artifacts[f"financial-facts/{fact['fact_id']}.json"] = fact
            artifacts[f"evidence-chunks/{evidence['chunk_id']}.json"] = evidence
        slug = str(record["record_id"]).replace("-", "_")
        for chunk in index_pdf_pages(
            source,
            pages,
            id_prefix=f"chunk_product_{slug}_fulltext",
            language="en-US",
            parser_version=f"pypdf-{pypdf_version}",
        ):
            artifacts[f"evidence-chunks/{chunk['chunk_id']}.json"] = chunk
        return artifacts

    @staticmethod
    def _source_document(
        filing: DiscoveredFiling,
        record: JsonObject,
        *,
        source_hash: str,
        retrieved_at: str,
    ) -> JsonObject:
        return {
            "schema_version": "1.4.0",
            "document_id": record["document_id"],
            "source_id": record["source_id"],
            "company": filing.company.artifact_value(),
            "document_type": filing.document_type,
            "title": filing.title,
            "published_at": filing.published_at,
            "retrieved_at": retrieved_at,
            "available_from": filing.published_at,
            "source_uri": filing.source_uri,
            "content_hash": source_hash,
            "mime_type": "application/pdf",
            "language": "en-US",
            "reporting_period": filing.reporting_period,
            "license": {
                "license_id": None,
                "publication_mode": "derived_facts_and_short_excerpts",
                "raw_payload_committed": False,
                "notes": "HKEX filing is referenced by URL and hash; raw PDF stays outside Git.",
            },
            "parser_version": f"pypdf-{pypdf_version}",
            "quality_flags": ["official_hkex_source", "native_pdf_text", "raw_payload_excluded"],
            "created_at": retrieved_at,
        }

    @staticmethod
    def _fact(
        filing: DiscoveredFiling,
        record: JsonObject,
        cell: HkExtractedCell,
        *,
        source_hash: str,
        retrieved_at: str,
    ) -> JsonObject:
        slug = str(record["record_id"]).replace("-", "_")
        return {
            "schema_version": "1.4.0",
            "fact_id": f"fact_product_{slug}_{cell.metric_code}",
            "fact_kind": "reported",
            "company": filing.company.artifact_value(),
            "metric_code": cell.metric_code,
            "value": format(cell.normalized_value, "f"),
            "measurement_unit": "CURRENCY",
            "currency": cell.currency,
            "canonical_scale": 1,
            "period": filing.reporting_period,
            "sign_convention": "natural_statement_value",
            "source": {
                "source_id": record["source_id"],
                "document_id": record["document_id"],
                "source_type": "official_filing",
                "published_at": filing.published_at,
                "retrieved_at": retrieved_at,
                "uri": filing.source_uri,
                "content_hash": source_hash,
                "license_id": None,
                "redistribution_allowed": False,
            },
            "source_locator": {
                "page": cell.page,
                "section": "Financial statements",
                "table": cell.statement,
                "row_label": cell.row_label,
                "column_label": str(filing.reporting_period["fiscal_year"]),
            },
            "formula_version": None,
            "source_fact_ids": [],
            "derivation": None,
            "availability": "available",
            "quality_flags": ["unit_normalized", "native_pdf_text"],
            "created_at": retrieved_at,
        }

    @staticmethod
    def _evidence(
        filing: DiscoveredFiling,
        record: JsonObject,
        cell: HkExtractedCell,
        *,
        retrieved_at: str,
    ) -> JsonObject:
        slug = str(record["record_id"]).replace("-", "_")
        return {
            "schema_version": "1.4.0",
            "chunk_id": f"chunk_product_{slug}_{cell.metric_code}",
            "document_id": record["document_id"],
            "company": filing.company.artifact_value(),
            "reporting_period": filing.reporting_period,
            "document_type": filing.evidence_document_type,
            "published_at": filing.published_at,
            "retrieved_at": retrieved_at,
            "content_role": "untrusted_source",
            "section": f"Financial statement fact: {cell.row_label}",
            "text": cell.raw_line,
            "text_hash": hashlib.sha256(cell.raw_line.encode()).hexdigest(),
            "source_uri": filing.source_uri,
            "locator": {
                "page_start": cell.page,
                "page_end": cell.page,
                "paragraph_start": None,
                "paragraph_end": None,
                "char_start": None,
                "char_end": None,
            },
            "language": "en-US",
            "parser_version": f"pypdf-{pypdf_version}",
            "quality_flags": ["native_pdf_text", "table_linearized"],
        }

    @staticmethod
    def _ingestion_manifest(
        filing: DiscoveredFiling,
        cells: tuple[HkExtractedCell, ...],
        *,
        package_hash: str,
        source_hash: str,
        byte_count: int,
        page_count: int,
        retrieved_at: str,
    ) -> JsonObject:
        record = filing.dynamic_record()
        return {
            "schema_version": "1.5.0",
            "ingestion_id": record["ingestion_id"],
            "package_id": record["package_id"],
            "data_namespace": "product",
            "status": "ready",
            "company": filing.company.artifact_value(),
            "reporting_period": filing.reporting_period,
            "discovery": {
                "registry": "HKEX",
                "announcement_id": filing.filing_id,
                "document_title": filing.title,
                "source_uri": filing.source_uri,
                "publication_time": filing.published_at,
                "discovered_at": retrieved_at,
            },
            "acquisition": {
                "retrieved_at": retrieved_at,
                "media_type": "application/pdf",
                "byte_count": byte_count,
                "content_hash": source_hash,
                "raw_payload_committed": False,
            },
            "parser": {
                "parser_name": "pypdf",
                "parser_version": pypdf_version,
                "page_count": page_count,
                "native_text_required": True,
            },
            "extraction": {
                "schema_version": "1.5.0",
                "extractor_name": "researchforge_hk_ifrs",
                "extractor_version": "1.0.0",
                "method": "deterministic_pdf_text_recovery",
                "numerical_truth_source": "verified_hkex_pdf",
                "llm_used": False,
                "target_metrics": [cell.metric_code for cell in cells],
                "promoted_metric_count": len(cells),
                "recoveries": [
                    {
                        "metric_code": cell.metric_code,
                        "page": cell.page,
                        "statement": cell.statement,
                        "row_label": cell.row_label,
                        "reported_value": format(cell.reported_value, "f"),
                        "scale": cell.scale,
                        "normalized_value": format(cell.normalized_value, "f"),
                    }
                    for cell in cells
                ],
            },
            "outputs": [],
            "abstentions": [],
            "created_at": retrieved_at,
            "package_hash": package_hash,
        }

    @staticmethod
    def _package_manifest(
        filing: DiscoveredFiling,
        artifacts: dict[str, JsonObject],
        hashes: dict[str, str],
        package_hash: str,
    ) -> JsonObject:
        record = filing.dynamic_record()
        sources = [v for k, v in artifacts.items() if k.startswith("source-documents/")]
        facts = [v for k, v in artifacts.items() if k.startswith("financial-facts/")]
        evidence = [v for k, v in artifacts.items() if k.startswith("evidence-chunks/")]
        return {
            "schema_version": "1.5.0",
            "package_id": record["package_id"],
            "package_hash": package_hash,
            "data_namespace": "product",
            "status": "ready",
            "source_document_count": len(sources),
            "financial_fact_count": len(facts),
            "evidence_chunk_count": len(evidence),
            "source_document_ids": sorted(item["document_id"] for item in sources),
            "financial_fact_ids": sorted(item["fact_id"] for item in facts),
            "evidence_chunk_ids": sorted(item["chunk_id"] for item in evidence),
            "artifact_hashes": dict(sorted(hashes.items())),
            "ingestion_manifest": "ingestion-manifest.json",
        }

    @staticmethod
    def _canonical(value: Any) -> bytes:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()

    @classmethod
    def _hash_json(cls, value: JsonObject) -> str:
        return hashlib.sha256(cls._pretty(value)).hexdigest()

    @staticmethod
    def _pretty(value: Any) -> bytes:
        return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()

    @classmethod
    def _write(
        cls,
        package_root: Path,
        artifacts: dict[str, JsonObject],
        ingestion: JsonObject,
        manifest: JsonObject,
    ) -> None:
        package_root.mkdir(parents=True, exist_ok=True)
        for relative, payload in artifacts.items():
            destination = package_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(cls._pretty(payload))
        (package_root / "ingestion-manifest.json").write_bytes(cls._pretty(ingestion))
        (package_root / "manifest.json").write_bytes(cls._pretty(manifest))
