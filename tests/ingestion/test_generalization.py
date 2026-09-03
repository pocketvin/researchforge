"""General table semantics and three real product cases, not a new benchmark."""

# ruff: noqa: RUF001 -- native Chinese financial punctuation is intentional test input.

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from researchforge.adapters.fixtures import G0FixtureCatalog
from researchforge.adapters.storage import payload_sha256
from researchforge.api.app import DEFAULT_PRODUCT_ROOT, DEFAULT_SKILL_MANIFEST
from researchforge.application.contracts import ResearchRunRequest
from researchforge.application.service import ResearchRunService
from researchforge.ingestion.errors import IngestionAbstention
from researchforge.ingestion.extraction import DeterministicFinancialFactExtractor
from tests.runtime_helpers import assert_v14_schema


def _pages() -> tuple[str, ...]:
    return (
        "公司财务报表及附注的单位为：千元\n1、合并资产负债表\n"
        "资产 附注七 2024年6月30日 2023年12月31日\n"
        "应收账款 4 12,000 11,000\n存货 8 13,000 12,000",
        "2、合并利润表\n附注七\n截至2024年\n6月30日止\n6个月期间\n"
        "截至2023年\n6月30日止\n6个月期间\n(未经审计) (未经审计)\n"
        "一、营业收入 45 30,000 29,000\n减：营业成本 45 20,000 19,000\n"
        "归属于母公司所有者的净利润 10,000 9,000\n3、合并所有者权益变动表",
        "4、合并现金流量表\n附注七\n截至2024年\n6月30日止\n6个月期间\n"
        "截至2023年\n6月30日止\n6个月期间\n(未经审计) (未经审计)\n"
        "经营活动产生的现金流量净额 62 14,000 13,000\n5、公司资产负债表\n"
        "资产 附注十九 2024年6月30日 2023年12月31日\n应收账款 1 99,000 98,000",
    )


def _extract(pages: tuple[str, ...]) -> dict[str, Any]:
    period = {
        "fiscal_year": 2024,
        "fiscal_period": "H1",
        "period_end": "2024-06-30",
        "statement_scope": "consolidated",
    }
    batch = DeterministicFinancialFactExtractor().extract(
        pages=pages,
        parser_text_hash=hashlib.sha256("\n\f\n".join(pages).encode()).hexdigest(),
        reporting_period=period,
    )
    return {cell.metric_code: cell for cell in batch.cells}


def test_reusable_multiline_headers_global_unit_and_note_column() -> None:
    cells = _extract(_pages())
    assert str(cells["revenue"].normalized_value) == "30000000"
    assert cells["operating_cash_flow"].raw_value == "14,000"
    assert cells["accounts_receivable"].raw_value == "12,000"
    assert {cell.scale for cell in cells.values()} == {1000}


def test_reversed_period_columns_choose_current_not_first_number() -> None:
    pages = list(_pages())
    pages[0] = pages[0].replace("2024年6月30日 2023年12月31日", "2023年12月31日 2024年6月30日")
    cells = _extract(tuple(pages))
    assert cells["accounts_receivable"].raw_value == "11,000"


@pytest.mark.parametrize(
    ("old", "new", "code"),
    [
        ("应收账款 4 12,000 11,000", "应收账款 4 - 11,000", "METRIC_VALUE_MISSING"),
        ("应收账款 4 12,000 11,000", "应收账款 4 11,000", "VALUE_COLUMN_AMBIGUOUS"),
        (
            "2024年6月30日 2023年12月31日",
            "2024年6月30日 2024年6月30日",
            "REPORTING_COLUMN_UNRESOLVED",
        ),
        (
            "2024年6月30日 2023年12月31日",
            "2024年6月30日 2023年12月31日 2022年12月31日",
            "REPORTING_COLUMN_UNRESOLVED",
        ),
        ("公司财务报表及附注的单位为：千元", "单位不明", "STATEMENT_UNIT_UNRESOLVED"),
    ],
)
def test_ambiguous_layout_never_promotes_a_number(old: str, new: str, code: str) -> None:
    pages = tuple(page.replace(old, new) for page in _pages())
    with pytest.raises(IngestionAbstention) as caught:
        _extract(pages)
    assert caught.value.code == code


@pytest.mark.parametrize("slug", ["catl-2024h1", "catl-2024fy", "byd-2024h1"])
def test_same_backend_verifies_each_real_filing(tmp_path: Path, slug: str) -> None:
    ingestion = json.loads((DEFAULT_PRODUCT_ROOT / slug / "ingestion-manifest.json").read_text())
    service = ResearchRunService.build(
        tmp_path, DEFAULT_PRODUCT_ROOT, DEFAULT_SKILL_MANIFEST, data_namespace="product"
    )
    company = ingestion["company"]["company_id"]
    period = ingestion["reporting_period"]
    label = f"{period['fiscal_year']}{period['fiscal_period']}"
    request = ResearchRunRequest(
        task_type="filing_analysis",
        company_ids=[company],
        requested_period_labels=[label],
        research_question=f"{label}利润是否转化为经营现金流？",
        research_time=datetime.fromisoformat("2026-09-03T00:00:00+08:00"),
        idempotency_key=f"generalization-{slug}",
    )
    run_id = service.submit(request).run_id
    assert service.execute(run_id)["lifecycle_state"] == "succeeded"
    assert len(service.get_facts(run_id)) == 6
    assert {f["source"]["document_id"] for f in service.get_facts(run_id)} == {
        f"doc_product_{slug.replace('-', '_')}"
    }
    result = service.get_result(run_id)
    assert_v14_schema(result, "research-result.schema.json")
    assert len(service.get_calculations(run_id)) == 4
    assert len(service.get_trace(run_id)["stages"]) == 10
    assert result["monitoring_items"] and result["limitations"]
    evaluation = service.verify(
        run_id, case_id=f"product_{slug.replace('-', '_')}", expected_calculations={}
    )
    assert evaluation["failure_events"] == []
    assert evaluation["metrics"]["calculation_accuracy"] == 1
    if period["fiscal_period"] == "FY":
        assert "未经审计" not in json.dumps(result, ensure_ascii=False)


def test_product_index_rejects_path_escape(tmp_path: Path) -> None:
    index = json.loads((DEFAULT_PRODUCT_ROOT / "manifest.json").read_text())
    index["packages"][0]["path"] = "../fixtures"
    index["package_hash"] = payload_sha256(index["packages"])
    (tmp_path / "manifest.json").write_text(json.dumps(index))
    with pytest.raises(ValueError, match="unsafe product package path"):
        G0FixtureCatalog(tmp_path, expected_namespace="product")


def test_stale_ready_package_cannot_serve_after_abstention(tmp_path: Path) -> None:
    root = tmp_path / "package"
    shutil.copytree(DEFAULT_PRODUCT_ROOT / "catl-2024h1", root)
    manifest = json.loads((root / "ingestion-manifest.json").read_text())
    manifest["status"] = "abstained"
    (root / "ingestion-manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="stale artifacts refused"):
        G0FixtureCatalog(root, expected_namespace="product")


def test_product_fact_tampering_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "package"
    shutil.copytree(DEFAULT_PRODUCT_ROOT / "catl-2024h1", root)
    path = next((root / "financial-facts").glob("*.json"))
    fact = json.loads(path.read_text())
    fact["value"] = "1.00"
    path.write_text(json.dumps(fact))
    with pytest.raises(ValueError, match="artifact hashes"):
        G0FixtureCatalog(root, expected_namespace="product")


def test_cli_default_output_is_selected_filing_not_initial_slice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from researchforge.cli import main
    from researchforge.ingestion import ProductDisclosureIngestion

    captured: list[Path] = []

    def run(self: ProductDisclosureIngestion, **kwargs: Any) -> dict[str, Any]:
        del self
        captured.append(kwargs["package_root"])
        return {"status": "ready"}

    monkeypatch.setattr(ProductDisclosureIngestion, "run", run)
    main(["ingest-disclosure", "--company", "cn_002594", "--period", "2024H1"])
    assert captured == [DEFAULT_PRODUCT_ROOT / "byd-2024h1"]
