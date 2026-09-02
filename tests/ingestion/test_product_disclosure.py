"""V1.5 real-disclosure ingestion, abstention, and namespace isolation tests."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from researchforge.adapters.fixtures import G0FixtureCatalog
from researchforge.api.app import DEFAULT_FIXTURE_ROOT, PROJECT_ROOT
from researchforge.ingestion import FilingRegistry, ProductDisclosureIngestion
from researchforge.ingestion.pipeline import (
    AcquiredDocument,
    PagePreservingPdfParser,
    ParsedDocument,
)
from scripts.validate_contracts import (
    ACTIVE_PRODUCT_SCHEMA_DIR,
    SCHEMA_DIR,
    load_json,
    validate_instance,
)

REGISTRY = PROJECT_ROOT / "data" / "product" / "filing-catalog.json"
FIXED_TIME = datetime.fromisoformat("2026-09-02T18:00:00+08:00")


class _PortableTestParser(PagePreservingPdfParser):
    """Return page-preserving reviewed text without committing the real filing PDF."""

    def __init__(self, pages: tuple[str, ...]) -> None:
        self.pages = pages

    def parse(self, document: AcquiredDocument) -> ParsedDocument:
        assert document.path.is_file()
        joined = "\n\f\n".join(self.pages).encode("utf-8")
        return ParsedDocument(
            pages=self.pages,
            text_hash=hashlib.sha256(joined).hexdigest(),
        )


def _pipeline(
    registry: Path = REGISTRY,
    *,
    parser: PagePreservingPdfParser | None = None,
) -> ProductDisclosureIngestion:
    return ProductDisclosureIngestion(
        FilingRegistry(registry),
        parser=parser,
        clock=lambda: FIXED_TIME,
    )


def _portable_inputs(
    tmp_path: Path,
) -> tuple[Path, Path, _PortableTestParser, str, int]:
    """Build a CI-safe acquisition fixture from the public reviewed text cells."""

    registry_payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    record = registry_payload["records"][0]
    specs = [*record["fact_specs"], *record["counter_evidence_specs"]]
    page_count = max(int(spec["page"]) for spec in specs)
    pages = [""] * page_count
    for spec in specs:
        page_index = int(spec["page"]) - 1
        pages[page_index] = f"{pages[page_index]}\n{spec['evidence_text']}"

    payload = b"%PDF-1.4\n% ResearchForge portable acquisition fixture\n%%EOF\n"
    digest = hashlib.sha256(payload).hexdigest()
    source_path = tmp_path / "portable-source.pdf"
    source_path.write_bytes(payload)
    record["expected_sha256"] = digest
    record["expected_byte_count"] = len(payload)
    record["expected_page_count"] = page_count
    registry_path = tmp_path / "filing-catalog.json"
    registry_path.write_text(json.dumps(registry_payload, ensure_ascii=False), encoding="utf-8")
    return registry_path, source_path, _PortableTestParser(tuple(pages)), digest, page_count


def _validate(payload: dict[str, Any], schema_name: str, *, v15: bool = False) -> None:
    schema_dirs = (SCHEMA_DIR, ACTIVE_PRODUCT_SCHEMA_DIR)
    schemas = {
        path.resolve(): load_json(path)
        for directory in schema_dirs
        for path in directory.glob("*.schema.json")
    }
    directory = ACTIVE_PRODUCT_SCHEMA_DIR if v15 else SCHEMA_DIR
    schema_path = (directory / schema_name).resolve()
    validate_instance(payload, schemas[schema_path], schema_path, schemas)


def test_builds_ready_real_product_package_and_reloads_it(tmp_path: Path) -> None:
    package_root = tmp_path / "product-package"
    registry_path, source_pdf, parser, digest, page_count = _portable_inputs(tmp_path)
    pipeline = _pipeline(registry_path, parser=parser)

    first = pipeline.run(
        company_id="cn_300750",
        period_label="2024H1",
        raw_root=tmp_path / "raw",
        package_root=package_root,
        source_file=source_pdf,
    )
    second = pipeline.run(
        company_id="cn_300750",
        period_label="2024H1",
        raw_root=tmp_path / "raw",
        package_root=package_root,
    )

    assert first["status"] == "ready"
    assert first["data_namespace"] == "product"
    assert first["acquisition"]["content_hash"] == digest
    assert first["parser"]["page_count"] == page_count
    assert first["package_hash"] == second["package_hash"]
    _validate(first, "ingestion-manifest.schema.json", v15=True)

    source = load_json(next((package_root / "source-documents").glob("*.json")))
    _validate(source, "source-document.schema.json")
    for path in (package_root / "financial-facts").glob("*.json"):
        _validate(load_json(path), "financial-fact.schema.json")
    for path in (package_root / "evidence-chunks").glob("*.json"):
        _validate(load_json(path), "evidence-chunk.schema.json")

    catalog = G0FixtureCatalog(package_root, expected_namespace="product")
    loaded = catalog.load(
        ["cn_300750"],
        ["2024H1"],
        datetime.fromisoformat("2026-09-02T18:00:00+08:00"),
    )
    values = {fact["metric_code"]: fact["value"] for fact in loaded.facts}
    assert values["net_income"] == "22864987400.00"
    assert values["operating_cash_flow"] == "44708954600.00"
    assert len(loaded.evidence_chunks) == 8
    assert any(
        chunk["section"] == "Counter evidence: audit status" for chunk in loaded.evidence_chunks
    )


def test_reviewed_cell_mismatch_abstains_without_emitting_facts(tmp_path: Path) -> None:
    registry_path, source_pdf, parser, _, _ = _portable_inputs(tmp_path)
    registry_payload = json.loads(registry_path.read_text(encoding="utf-8"))
    registry_payload["records"][0]["fact_specs"][0]["evidence_text"] = "应收账款 9,999,999.99"
    registry_path.write_text(json.dumps(registry_payload, ensure_ascii=False), encoding="utf-8")
    package_root = tmp_path / "abstained-package"

    manifest = _pipeline(registry_path, parser=parser).run(
        company_id="cn_300750",
        period_label="2024H1",
        raw_root=tmp_path / "raw",
        package_root=package_root,
        source_file=source_pdf,
    )

    assert manifest["status"] == "abstained"
    assert manifest["abstentions"][0]["code"] == "REVIEWED_CELL_NOT_FOUND"
    assert not (package_root / "financial-facts").exists()
    _validate(manifest, "ingestion-manifest.schema.json", v15=True)


def test_hash_mismatch_abstains_before_parsing(tmp_path: Path) -> None:
    registry_path, source_pdf, parser, _, _ = _portable_inputs(tmp_path)
    registry_payload = json.loads(registry_path.read_text(encoding="utf-8"))
    registry_payload["records"][0]["expected_sha256"] = "0" * 64
    registry_path.write_text(json.dumps(registry_payload, ensure_ascii=False), encoding="utf-8")

    manifest = _pipeline(registry_path, parser=parser).run(
        company_id="cn_300750",
        period_label="2024H1",
        raw_root=tmp_path / "raw",
        package_root=tmp_path / "abstained-package",
        source_file=source_pdf,
    )

    assert manifest["status"] == "abstained"
    assert manifest["abstentions"][0]["code"] == "DISCLOSURE_HASH_MISMATCH"
    assert manifest["parser"] is None
    _validate(manifest, "ingestion-manifest.schema.json", v15=True)


def test_namespace_expectation_refuses_fixture_product_fallback(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="fallback refused"):
        G0FixtureCatalog(DEFAULT_FIXTURE_ROOT, expected_namespace="product")

    package_root = tmp_path / "product-package"
    registry_path, source_pdf, parser, _, _ = _portable_inputs(tmp_path)
    _pipeline(registry_path, parser=parser).run(
        company_id="cn_300750",
        period_label="2024H1",
        raw_root=tmp_path / "raw",
        package_root=package_root,
        source_file=source_pdf,
    )
    with pytest.raises(ValueError, match="fallback refused"):
        G0FixtureCatalog(package_root, expected_namespace="fixture")
