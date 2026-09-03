"""V1.5 real-disclosure ingestion, abstention, and namespace isolation tests."""

# ruff: noqa: RUF001 -- fixtures intentionally preserve Chinese disclosure punctuation.

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from researchforge.adapters.fixtures import G0FixtureCatalog
from researchforge.api.app import DEFAULT_FIXTURE_ROOT, PROJECT_ROOT
from researchforge.ingestion import FilingRegistry, ProductDisclosureIngestion
from researchforge.ingestion.extraction import DeterministicFinancialFactExtractor
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
    """Build a CI-safe native-text statement without prefilled fact metadata."""

    registry_payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    record = registry_payload["records"][0]
    pages = (
        (
            "四、主要会计数据和财务指标\n"
            "归属于上市公司股东的扣除\n"
            "非经常性损益的净利润（万\n"
            "元）\n"
            "2,005,394.11 1,755,299.67 14.25%"
        ),
        (
            "1、合并资产负债表\n"
            "单位：万元\n"
            "项目 期末余额 期初余额\n"
            "应收账款 5,809,947.60 6,402,053.34\n"
            "存货 4,805,067.62 4,543,389.01\n"
            "2、母公司资产负债表"
        ),
        (
            "3、合并利润表\n"
            "单位：万元\n"
            "项目 2024 年半年度 2023 年半年度\n"
            "一、营业总收入 16,676,683.36 18,924,604.13\n"
            "其中：营业收入 16,676,683.36 18,924,604.13\n"
            "其中：营业成本 12,251,784.88 14,830,593.41\n"
            "1.归属于母公司股东的净利润\n"
            "（净亏损以“—”号填列） 2,286,498.74 2,071,726.45\n"
            "4、母公司利润表\n"
            "单位：万元\n"
            "项目 2024 年半年度 2023 年半年度\n"
            "营业收入 1.00 2.00"
        ),
        "5、合并现金流量表\n单位：万元",
        (
            "项目 2024 年半年度 2023 年半年度\n"
            "经营活动产生的现金流量净额 4,470,895.46 3,707,036.98\n"
            "6、母公司现金流量表"
        ),
        "一、审计报告\n公司半年度财务报告未经审计。",
    )
    page_count = len(pages)

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
    assert first["extraction"]["llm_used"] is False
    assert first["extraction"]["numerical_truth_source"] == "verified_pdf"
    assert first["extraction"]["promoted_metric_count"] == 6
    assert len(first["extraction"]["recoveries"]) == 6
    recoveries = {item["metric_code"]: item for item in first["extraction"]["recoveries"]}
    for recovery in recoveries.values():
        assert Decimal(recovery["reported_value"]) * recovery["scale"] == Decimal(
            recovery["normalized_value"]
        )
    assert recoveries["net_income"]["line_end"] > recoveries["net_income"]["line_start"]
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


def test_missing_statement_row_abstains_without_emitting_facts(tmp_path: Path) -> None:
    registry_path, source_pdf, parser, _, _ = _portable_inputs(tmp_path)
    pages = list(parser.pages)
    pages[1] = pages[1].replace("应收账款 5,809,947.60 6,402,053.34\n", "")
    parser = _PortableTestParser(tuple(pages))
    package_root = tmp_path / "abstained-package"

    manifest = _pipeline(registry_path, parser=parser).run(
        company_id="cn_300750",
        period_label="2024H1",
        raw_root=tmp_path / "raw",
        package_root=package_root,
        source_file=source_pdf,
    )

    assert manifest["status"] == "abstained"
    assert manifest["abstentions"][0]["code"] == "METRIC_ROW_NOT_FOUND"
    assert not (package_root / "financial-facts").exists()
    _validate(manifest, "ingestion-manifest.schema.json", v15=True)


def test_ambiguous_current_period_header_abstains(tmp_path: Path) -> None:
    registry_path, source_pdf, parser, _, _ = _portable_inputs(tmp_path)
    pages = list(parser.pages)
    pages[2] = pages[2].replace(
        "项目 2024 年半年度 2023 年半年度",
        "项目 2023 年半年度 2022 年半年度",
    )
    manifest = _pipeline(
        registry_path,
        parser=_PortableTestParser(tuple(pages)),
    ).run(
        company_id="cn_300750",
        period_label="2024H1",
        raw_root=tmp_path / "raw",
        package_root=tmp_path / "ambiguous-period",
        source_file=source_pdf,
    )

    assert manifest["status"] == "abstained"
    assert manifest["abstentions"][0]["code"] == "REPORTING_COLUMN_UNRESOLVED"


def test_duplicate_metric_row_abstains(tmp_path: Path) -> None:
    registry_path, source_pdf, parser, _, _ = _portable_inputs(tmp_path)
    pages = list(parser.pages)
    pages[2] = pages[2].replace(
        "其中：营业收入 16,676,683.36 18,924,604.13",
        ("其中：营业收入 16,676,683.36 18,924,604.13\n其中：营业收入 16,000,000.00 18,000,000.00"),
    )
    manifest = _pipeline(
        registry_path,
        parser=_PortableTestParser(tuple(pages)),
    ).run(
        company_id="cn_300750",
        period_label="2024H1",
        raw_root=tmp_path / "raw",
        package_root=tmp_path / "duplicate-row",
        source_file=source_pdf,
    )

    assert manifest["status"] == "abstained"
    assert manifest["abstentions"][0]["code"] == "METRIC_ROW_AMBIGUOUS"


def test_conflicting_statement_unit_abstains(tmp_path: Path) -> None:
    registry_path, source_pdf, parser, _, _ = _portable_inputs(tmp_path)
    pages = list(parser.pages)
    pages[1] = pages[1].replace("单位：万元", "单位：万元\n单位：元", 1)
    manifest = _pipeline(
        registry_path,
        parser=_PortableTestParser(tuple(pages)),
    ).run(
        company_id="cn_300750",
        period_label="2024H1",
        raw_root=tmp_path / "raw",
        package_root=tmp_path / "conflicting-unit",
        source_file=source_pdf,
    )

    assert manifest["status"] == "abstained"
    assert manifest["abstentions"][0]["code"] == "STATEMENT_UNIT_AMBIGUOUS"


def test_missing_native_text_layer_abstains_without_ocr(tmp_path: Path) -> None:
    registry_path, source_pdf, parser, _, page_count = _portable_inputs(tmp_path)
    parser = _PortableTestParser(tuple("" for _ in range(page_count)))
    manifest = _pipeline(registry_path, parser=parser).run(
        company_id="cn_300750",
        period_label="2024H1",
        raw_root=tmp_path / "raw",
        package_root=tmp_path / "no-text",
        source_file=source_pdf,
    )

    assert manifest["status"] == "abstained"
    assert manifest["abstentions"][0]["code"] == "TEXT_LAYER_REQUIRED"
    assert manifest["extraction"] is None


def test_registry_contains_identity_not_prefilled_numbers_or_locators() -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    serialized = json.dumps(payload, ensure_ascii=False)
    for forbidden in ("fact_specs", "reported_value", "page", "evidence_text"):
        assert f'"{forbidden}"' not in serialized


def test_numeric_token_normalization_handles_zero_and_negative_notation() -> None:
    parse = DeterministicFinancialFactExtractor._parse_decimal

    assert parse("0.00") == Decimal("0.00")
    assert parse("-1,234.50") == Decimal("-1234.50")
    assert parse("（1,234.50）") == Decimal("-1234.50")


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
