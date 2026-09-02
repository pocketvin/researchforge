"""V1.5 real-disclosure ingestion, abstention, and namespace isolation tests."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from researchforge.adapters.fixtures import G0FixtureCatalog
from researchforge.api.app import DEFAULT_FIXTURE_ROOT, PROJECT_ROOT
from researchforge.ingestion import FilingRegistry, ProductDisclosureIngestion
from scripts.validate_contracts import (
    ACTIVE_PRODUCT_SCHEMA_DIR,
    SCHEMA_DIR,
    load_json,
    validate_instance,
)

REGISTRY = PROJECT_ROOT / "data" / "product" / "filing-catalog.json"
SOURCE_PDF = PROJECT_ROOT / "data" / "raw" / "g0" / "catl-2024h1.pdf"
FIXED_TIME = datetime.fromisoformat("2026-09-02T18:00:00+08:00")


def _pipeline(registry: Path = REGISTRY) -> ProductDisclosureIngestion:
    return ProductDisclosureIngestion(FilingRegistry(registry), clock=lambda: FIXED_TIME)


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
    pipeline = _pipeline()

    first = pipeline.run(
        company_id="cn_300750",
        period_label="2024H1",
        raw_root=tmp_path / "raw",
        package_root=package_root,
        source_file=SOURCE_PDF,
    )
    second = pipeline.run(
        company_id="cn_300750",
        period_label="2024H1",
        raw_root=tmp_path / "raw",
        package_root=package_root,
    )

    assert first["status"] == "ready"
    assert first["data_namespace"] == "product"
    assert first["acquisition"]["content_hash"] == (
        "2a690cb2471c1f0d4539d909a9f068c03710a838ddd35313175790169e85eab1"
    )
    assert first["parser"]["page_count"] == 174
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
    registry_payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    registry_payload["records"][0]["fact_specs"][0]["evidence_text"] = "应收账款 9,999,999.99"
    registry_path = tmp_path / "filing-catalog.json"
    registry_path.write_text(json.dumps(registry_payload, ensure_ascii=False), encoding="utf-8")
    package_root = tmp_path / "abstained-package"

    manifest = _pipeline(registry_path).run(
        company_id="cn_300750",
        period_label="2024H1",
        raw_root=tmp_path / "raw",
        package_root=package_root,
        source_file=SOURCE_PDF,
    )

    assert manifest["status"] == "abstained"
    assert manifest["abstentions"][0]["code"] == "REVIEWED_CELL_NOT_FOUND"
    assert not (package_root / "financial-facts").exists()
    _validate(manifest, "ingestion-manifest.schema.json", v15=True)


def test_hash_mismatch_abstains_before_parsing(tmp_path: Path) -> None:
    registry_payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    registry_payload["records"][0]["expected_sha256"] = "0" * 64
    registry_path = tmp_path / "filing-catalog.json"
    registry_path.write_text(json.dumps(registry_payload, ensure_ascii=False), encoding="utf-8")

    manifest = _pipeline(registry_path).run(
        company_id="cn_300750",
        period_label="2024H1",
        raw_root=tmp_path / "raw",
        package_root=tmp_path / "abstained-package",
        source_file=SOURCE_PDF,
    )

    assert manifest["status"] == "abstained"
    assert manifest["abstentions"][0]["code"] == "DISCLOSURE_HASH_MISMATCH"
    assert manifest["parser"] is None
    _validate(manifest, "ingestion-manifest.schema.json", v15=True)


def test_namespace_expectation_refuses_fixture_product_fallback(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="fallback refused"):
        G0FixtureCatalog(DEFAULT_FIXTURE_ROOT, expected_namespace="product")

    package_root = tmp_path / "product-package"
    _pipeline().run(
        company_id="cn_300750",
        period_label="2024H1",
        raw_root=tmp_path / "raw",
        package_root=package_root,
        source_file=SOURCE_PDF,
    )
    with pytest.raises(ValueError, match="fallback refused"):
        G0FixtureCatalog(package_root, expected_namespace="fixture")
