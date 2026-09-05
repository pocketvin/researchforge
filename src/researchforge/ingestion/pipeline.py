"""Allowlisted, abstention-first ingestion of official A-share disclosures."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any, cast
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pypdf import PdfReader
from pypdf import __version__ as pypdf_version

from researchforge.ingestion.errors import IngestionAbstention
from researchforge.ingestion.extraction import (
    DeterministicFinancialFactExtractor,
    ExtractedFinancialCell,
    ExtractionBatch,
)
from researchforge.retrieval.fulltext import index_pdf_pages

JsonObject = dict[str, Any]
Clock = Callable[[], datetime]

OFFICIAL_DISCLOSURE_HOSTS = frozenset({"disc.static.szse.cn", "static.cninfo.com.cn"})
MAX_PDF_BYTES = 100_000_000


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _artifact_bytes(value: JsonObject) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _safe_child(root: Path, filename: str) -> Path:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", filename) is None:
        raise ValueError("unsafe artifact filename")
    resolved_root = root.resolve()
    candidate = (resolved_root / filename).resolve()
    if candidate.parent != resolved_root:
        raise ValueError("artifact path escapes its configured root")
    return candidate


def _validate_official_url(uri: str) -> None:
    parsed = urlparse(uri)
    if parsed.scheme != "https" or parsed.hostname not in OFFICIAL_DISCLOSURE_HOSTS:
        raise IngestionAbstention(
            "UNTRUSTED_SOURCE_URI",
            "acquisition",
            "Disclosure URL is not HTTPS on an allowlisted official host.",
        )


class _OfficialRedirectHandler(HTTPRedirectHandler):
    """Reject a redirect before urllib contacts a non-official host."""

    def redirect_request(
        self,
        req: Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        _validate_official_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@dataclass(frozen=True, slots=True)
class AcquiredDocument:
    """Verified immutable raw disclosure held outside Git."""

    path: Path
    retrieved_at: str
    content_hash: str
    byte_count: int

    def manifest_value(self) -> JsonObject:
        return {
            "retrieved_at": self.retrieved_at,
            "media_type": "application/pdf",
            "byte_count": self.byte_count,
            "content_hash": self.content_hash,
            "raw_payload_committed": False,
        }


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """Page-preserving PDF text used only as untrusted source data."""

    pages: tuple[str, ...]
    text_hash: str

    def manifest_value(self) -> JsonObject:
        return {
            "parser_name": "pypdf",
            "parser_version": pypdf_version,
            "page_count": len(self.pages),
            "page_boundaries_preserved": True,
            "text_hash": self.text_hash,
        }


class FilingRegistry:
    """Resolve exactly one pre-reviewed official filing record."""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        payload = cast(JsonObject, json.loads(self.path.read_text(encoding="utf-8")))
        if payload.get("schema_version") != "1.5.0":
            raise ValueError("filing registry must use schema_version 1.5.0")
        if payload.get("data_namespace") != "product":
            raise ValueError("filing registry must be isolated in the product namespace")
        records = payload.get("records")
        if not isinstance(records, list):
            raise ValueError("filing registry records must be an array")
        self._records = tuple(cast(JsonObject, item) for item in records)

    def discover(self, *, company_id: str, period_label: str) -> JsonObject:
        matches = [
            record
            for record in self._records
            if record["company"]["company_id"] == company_id
            and self.period_label(record["reporting_period"]) == period_label
        ]
        if len(matches) != 1:
            raise IngestionAbstention(
                "DISCLOSURE_NOT_UNAMBIGUOUS",
                "discovery",
                (
                    "Official disclosure registry must resolve exactly one record for "
                    f"{company_id}/{period_label}; found {len(matches)}."
                ),
            )
        record = matches[0]
        _validate_official_url(str(record["source_uri"]))
        return record

    @staticmethod
    def period_label(period: JsonObject) -> str:
        return f"{period['fiscal_year']}{period['fiscal_period']}"


class OfficialDocumentAcquirer:
    """Acquire and hash an allowlisted PDF without committing its raw bytes."""

    def __init__(self, *, clock: Clock = _utc_now, max_bytes: int = MAX_PDF_BYTES) -> None:
        self.clock = clock
        self.max_bytes = max_bytes
        self._opener = build_opener(_OfficialRedirectHandler())

    def acquire(
        self,
        record: JsonObject,
        *,
        raw_root: Path,
        source_file: Path | None = None,
    ) -> AcquiredDocument:
        uri = str(record["source_uri"])
        _validate_official_url(uri)
        raw_root.mkdir(parents=True, exist_ok=True)
        destination = _safe_child(raw_root, f"{record['record_id']}.pdf")

        retrieved_at: str
        if source_file is not None:
            payload = source_file.resolve().read_bytes()
            retrieved_at = str(record.get("reviewed_retrieved_at") or self.clock().isoformat())
        elif destination.is_file():
            payload = destination.read_bytes()
            retrieved_at = str(record.get("reviewed_retrieved_at") or self.clock().isoformat())
        else:
            request = Request(uri, headers={"User-Agent": "ResearchForge/1.7.3"})
            with self._opener.open(request, timeout=30) as response:
                _validate_official_url(str(response.geturl()))
                payload = response.read(self.max_bytes + 1)
            retrieved_at = self.clock().isoformat()

        actual_hash = _sha256(payload)
        actual_size = len(payload)
        abstention: IngestionAbstention | None = None
        if actual_size == 0 or actual_size > self.max_bytes:
            abstention = IngestionAbstention(
                "DISCLOSURE_SIZE_INVALID",
                "acquisition",
                f"Disclosure payload size {actual_size} is outside the allowed boundary.",
            )
        elif not payload.startswith(b"%PDF-"):
            abstention = IngestionAbstention(
                "DISCLOSURE_NOT_PDF",
                "acquisition",
                "Official disclosure payload does not have PDF magic bytes.",
            )
        elif record.get("expected_sha256") is not None and actual_hash != record["expected_sha256"]:
            abstention = IngestionAbstention(
                "DISCLOSURE_HASH_MISMATCH",
                "acquisition",
                "Official disclosure SHA-256 differs from the reviewed registry identity.",
            )
        elif (
            record.get("expected_byte_count") is not None
            and actual_size != record["expected_byte_count"]
        ):
            abstention = IngestionAbstention(
                "DISCLOSURE_SIZE_MISMATCH",
                "acquisition",
                "Official disclosure byte count differs from the reviewed registry identity.",
            )
        if abstention is not None:
            abstention.acquisition = {
                "retrieved_at": retrieved_at,
                "media_type": "application/pdf",
                "byte_count": max(actual_size, 1),
                "content_hash": actual_hash,
                "raw_payload_committed": False,
            }
            raise abstention

        if not destination.exists():
            temporary = destination.with_suffix(".pdf.partial")
            temporary.write_bytes(payload)
            temporary.replace(destination)
        return AcquiredDocument(destination, retrieved_at, actual_hash, actual_size)


class PagePreservingPdfParser:
    """Extract text without removing physical page boundaries."""

    def parse(self, document: AcquiredDocument) -> ParsedDocument:
        try:
            reader = PdfReader(document.path)
            pages = tuple(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise IngestionAbstention(
                "DISCLOSURE_PARSE_FAILED",
                "parsing",
                "The verified PDF could not be parsed into page-preserving text.",
            ) from exc
        text_hash = _sha256("\n\f\n".join(pages).encode("utf-8"))
        return ParsedDocument(pages=pages, text_hash=text_hash)


class ProductDisclosureIngestion:
    """Build one deterministic product data package or a schema-valid abstention."""

    def __init__(
        self,
        registry: FilingRegistry,
        *,
        acquirer: OfficialDocumentAcquirer | None = None,
        parser: PagePreservingPdfParser | None = None,
        extractor: DeterministicFinancialFactExtractor | None = None,
        clock: Clock = _utc_now,
    ) -> None:
        self.registry = registry
        self.acquirer = acquirer or OfficialDocumentAcquirer(clock=clock)
        self.parser = parser or PagePreservingPdfParser()
        self.extractor = extractor or DeterministicFinancialFactExtractor()
        self.clock = clock

    def run(
        self,
        *,
        company_id: str,
        period_label: str,
        raw_root: Path,
        package_root: Path,
        source_file: Path | None = None,
    ) -> JsonObject:
        record = self.registry.discover(company_id=company_id, period_label=period_label)
        discovery = self._discovery(record)
        acquisition: JsonObject | None = None
        parser_value: JsonObject | None = None
        extraction_value: JsonObject | None = None
        try:
            acquired = self.acquirer.acquire(
                record,
                raw_root=raw_root,
                source_file=source_file,
            )
            acquisition = acquired.manifest_value()
            parsed = self.parser.parse(acquired)
            parser_value = parsed.manifest_value()
            if (
                record.get("expected_page_count") is not None
                and len(parsed.pages) != record["expected_page_count"]
            ):
                raise IngestionAbstention(
                    "DISCLOSURE_PAGE_COUNT_MISMATCH",
                    "parsing",
                    "Parsed page count differs from the reviewed disclosure identity.",
                )
            artifacts, extraction = self._normalize(record, acquired, parsed)
            extraction_value = extraction.manifest_value()
        except IngestionAbstention as exc:
            acquisition = exc.acquisition or acquisition
            manifest = self._ingestion_manifest(
                record,
                discovery=discovery,
                acquisition=acquisition,
                parser_value=parser_value,
                extraction_value=extraction_value,
                status="abstained",
                outputs=[],
                abstentions=[exc.artifact()],
                package_hash=None,
            )
            self._write_single_manifest(package_root, manifest)
            return manifest

        artifact_hashes = {
            relative: _sha256(_artifact_bytes(payload)) for relative, payload in artifacts.items()
        }
        package_hash = _sha256(_canonical_bytes(artifact_hashes))
        outputs = [
            self._artifact_reference(relative, artifacts[relative], digest)
            for relative, digest in sorted(artifact_hashes.items())
        ]
        ingestion_manifest = self._ingestion_manifest(
            record,
            discovery=discovery,
            acquisition=acquisition,
            parser_value=parser_value,
            extraction_value=extraction_value,
            status="ready",
            outputs=outputs,
            abstentions=[],
            package_hash=package_hash,
        )
        package_manifest = self._package_manifest(
            record,
            artifacts,
            artifact_hashes,
            package_hash,
        )
        self._write_package(package_root, artifacts, ingestion_manifest, package_manifest)
        return ingestion_manifest

    def _normalize(
        self,
        record: JsonObject,
        acquired: AcquiredDocument,
        parsed: ParsedDocument,
    ) -> tuple[dict[str, JsonObject], ExtractionBatch]:
        extraction = self.extractor.extract(
            pages=parsed.pages,
            parser_text_hash=parsed.text_hash,
            reporting_period=record["reporting_period"],
        )
        source = self._source_document(record, acquired)
        artifacts: dict[str, JsonObject] = {
            f"source-documents/{source['document_id']}.json": source
        }
        for cell in extraction.cells:
            fact = self._financial_fact(record, acquired, cell)
            artifacts[f"financial-facts/{fact['fact_id']}.json"] = fact
            chunk = self._evidence_chunk(
                record,
                acquired,
                code=cell.metric_code,
                page=cell.page,
                section=f"Financial statement fact: {cell.row_label}",
                text=cell.evidence_text,
            )
            artifacts[f"evidence-chunks/{chunk['chunk_id']}.json"] = chunk
        for spec in self._counter_evidence(parsed):
            chunk = self._evidence_chunk(
                record,
                acquired,
                code=str(spec["chunk_code"]),
                page=int(spec["page"]),
                section=str(spec["section"]),
                text=str(spec["evidence_text"]),
            )
            artifacts[f"evidence-chunks/{chunk['chunk_id']}.json"] = chunk
        record_slug = str(record["record_id"]).replace("-", "_")
        for chunk in index_pdf_pages(
            source,
            parsed.pages,
            id_prefix=f"chunk_product_{record_slug}_fulltext",
            language="zh-CN",
            parser_version=f"pypdf-{pypdf_version}",
        ):
            artifacts[f"evidence-chunks/{chunk['chunk_id']}.json"] = chunk
        return artifacts, extraction

    def _source_document(self, record: JsonObject, acquired: AcquiredDocument) -> JsonObject:
        return {
            "schema_version": "1.4.0",
            "document_id": record["document_id"],
            "source_id": record["source_id"],
            "company": record["company"],
            "document_type": record["document_type"],
            "title": record["document_title"],
            "published_at": record["published_at"],
            "retrieved_at": acquired.retrieved_at,
            "available_from": record["published_at"],
            "source_uri": record["source_uri"],
            "content_hash": acquired.content_hash,
            "mime_type": "application/pdf",
            "language": "zh-CN",
            "reporting_period": record["reporting_period"],
            "license": {
                "license_id": None,
                "publication_mode": "derived_facts_and_short_excerpts",
                "raw_payload_committed": False,
                "notes": (
                    "Raw official filing is excluded. The product package contains only "
                    "normalized facts, short factual excerpts, locators, hashes and the link."
                ),
            },
            "parser_version": "1.0.0",
            "quality_flags": [
                "sha256_verified",
                "page_boundaries_preserved",
                "deterministic_cells_recovered",
                "raw_payload_excluded",
            ],
            "created_at": acquired.retrieved_at,
        }

    def _financial_fact(
        self,
        record: JsonObject,
        acquired: AcquiredDocument,
        cell: ExtractedFinancialCell,
    ) -> JsonObject:
        metric = cell.metric_code
        record_slug = str(record["record_id"]).replace("-", "_")
        return {
            "schema_version": "1.4.0",
            "fact_id": f"fact_product_{record_slug}_{metric}",
            "fact_kind": "reported",
            "company": record["company"],
            "metric_code": metric,
            "value": format(cell.normalized_value, "f"),
            "measurement_unit": "CURRENCY",
            "currency": "CNY",
            "canonical_scale": 1,
            "period": record["reporting_period"],
            "sign_convention": "natural_statement_value",
            "source": {
                "source_id": record["source_id"],
                "document_id": record["document_id"],
                "source_type": "official_filing",
                "published_at": record["published_at"],
                "retrieved_at": acquired.retrieved_at,
                "uri": record["source_uri"],
                "content_hash": acquired.content_hash,
                "license_id": None,
                "redistribution_allowed": False,
            },
            "source_locator": {
                "page": cell.page,
                "section": "财务报表",
                "table": cell.statement,
                "row_label": cell.row_label,
                "column_label": cell.column_label,
            },
            "formula_version": None,
            "source_fact_ids": [],
            "derivation": None,
            "availability": "available",
            "quality_flags": ["unit_normalized"],
            "created_at": acquired.retrieved_at,
        }

    def _evidence_chunk(
        self,
        record: JsonObject,
        acquired: AcquiredDocument,
        *,
        code: str,
        page: int,
        section: str,
        text: str,
    ) -> JsonObject:
        record_slug = str(record["record_id"]).replace("-", "_")
        return {
            "schema_version": "1.4.0",
            "chunk_id": f"chunk_product_{record_slug}_{code}",
            "document_id": record["document_id"],
            "company": record["company"],
            "reporting_period": record["reporting_period"],
            "document_type": record["evidence_document_type"],
            "published_at": record["published_at"],
            "retrieved_at": acquired.retrieved_at,
            "content_role": "untrusted_source",
            "section": section,
            "text": text,
            "text_hash": _sha256(text.encode("utf-8")),
            "source_uri": record["source_uri"],
            "locator": {
                "page_start": page,
                "page_end": page,
                "paragraph_start": None,
                "paragraph_end": None,
                "char_start": None,
                "char_end": None,
            },
            "language": "zh-CN",
            "parser_version": f"pypdf-{pypdf_version}",
            "quality_flags": ["text_native", "table_linearized"],
        }

    @staticmethod
    def _counter_evidence(parsed: ParsedDocument) -> list[JsonObject]:
        rules = (
            (
                "non_recurring_profit",
                "Counter evidence: non-recurring profit contribution",
                "归属于上市公司股东的扣除非经常性损益的净利润",
                5,
            ),
            (
                "unaudited_interim_report",
                "Counter evidence: audit status",
                "财务报告未经审计",
                1,
            ),
        )
        found: list[JsonObject] = []
        for code, section, phrase, max_lines in rules:
            matches: list[tuple[int, int, int, list[str]]] = []
            for page_number, page_text in enumerate(parsed.pages, start=1):
                lines = [line.strip() for line in page_text.splitlines() if line.strip()]
                for start in range(len(lines)):
                    for width in range(1, max_lines + 1):
                        window = " ".join(lines[start : start + width])
                        if phrase in _compact(window):
                            matches.append((width, page_number, start, lines))
                            break
            if matches:
                minimum_width = min(item[0] for item in matches)
                shortest = [item for item in matches if item[0] == minimum_width]
            else:
                shortest = []
            if len(shortest) == 1:
                width, page, start, lines = shortest[0]
                end = start + width
                if code == "non_recurring_profit":
                    while end < len(lines) and not re.search(
                        r"\d[\d,]*\.\d+", " ".join(lines[start:end])
                    ):
                        end += 1
                text = " ".join(lines[start:end])
                found.append(
                    {
                        "chunk_code": code,
                        "page": page,
                        "section": section,
                        "evidence_text": text,
                    }
                )
        return found

    def _discovery(self, record: JsonObject) -> JsonObject:
        return {
            "registry": record["registry"],
            "announcement_id": record["announcement_id"],
            "document_title": record["document_title"],
            "source_uri": record["source_uri"],
            "publication_time": record["published_at"],
            "discovered_at": self.clock().isoformat(),
        }

    def _ingestion_manifest(
        self,
        record: JsonObject,
        *,
        discovery: JsonObject,
        acquisition: JsonObject | None,
        parser_value: JsonObject | None,
        extraction_value: JsonObject | None,
        status: str,
        outputs: list[JsonObject],
        abstentions: list[JsonObject],
        package_hash: str | None,
    ) -> JsonObject:
        return {
            "schema_version": "1.5.0",
            "ingestion_id": record["ingestion_id"],
            "package_id": record["package_id"],
            "data_namespace": "product",
            "status": status,
            "company": record["company"],
            "reporting_period": record["reporting_period"],
            "discovery": discovery,
            "acquisition": acquisition,
            "parser": parser_value,
            "extraction": extraction_value,
            "outputs": outputs,
            "abstentions": abstentions,
            "created_at": self.clock().isoformat(),
            "package_hash": package_hash,
        }

    @staticmethod
    def _artifact_reference(
        relative: str,
        payload: JsonObject,
        digest: str,
    ) -> JsonObject:
        if relative.startswith("source-documents/"):
            kind = "source_document"
            identifier = str(payload["document_id"])
        elif relative.startswith("financial-facts/"):
            kind = "financial_fact"
            identifier = str(payload["fact_id"])
        else:
            kind = "evidence_chunk"
            identifier = str(payload["chunk_id"])
        return {
            "artifact_id": identifier,
            "artifact_kind": kind,
            "schema_version": str(payload["schema_version"]),
            "content_hash": digest,
            "path": relative,
        }

    @staticmethod
    def _package_manifest(
        record: JsonObject,
        artifacts: dict[str, JsonObject],
        artifact_hashes: dict[str, str],
        package_hash: str,
    ) -> JsonObject:
        sources = [value for key, value in artifacts.items() if key.startswith("source-documents/")]
        facts = [value for key, value in artifacts.items() if key.startswith("financial-facts/")]
        evidence = [value for key, value in artifacts.items() if key.startswith("evidence-chunks/")]
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
            "artifact_hashes": dict(sorted(artifact_hashes.items())),
            "ingestion_manifest": "ingestion-manifest.json",
        }

    @staticmethod
    def _write_single_manifest(package_root: Path, manifest: JsonObject) -> None:
        package_root.mkdir(parents=True, exist_ok=True)
        (package_root / "ingestion-manifest.json").write_bytes(_artifact_bytes(manifest))

    @staticmethod
    def _write_package(
        package_root: Path,
        artifacts: dict[str, JsonObject],
        ingestion_manifest: JsonObject,
        package_manifest: JsonObject,
    ) -> None:
        package_root.mkdir(parents=True, exist_ok=True)
        for relative, payload in artifacts.items():
            destination = package_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(_artifact_bytes(payload))
        (package_root / "ingestion-manifest.json").write_bytes(_artifact_bytes(ingestion_manifest))
        (package_root / "manifest.json").write_bytes(_artifact_bytes(package_manifest))
