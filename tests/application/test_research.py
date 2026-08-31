"""Framework-independent earnings-quality application tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from researchforge.adapters.fixtures import G0FixtureCatalog
from researchforge.api.app import DEFAULT_FIXTURE_ROOT
from researchforge.application.research import (
    DeterministicConclusionGenerator,
    EarningsQualityAnalyzer,
)
from tests.runtime_helpers import assert_v14_schema


def test_analyzer_uses_decimal_formulas_without_langgraph() -> None:
    loaded = G0FixtureCatalog(DEFAULT_FIXTURE_ROOT).load(
        ["cn_300750"],
        ["2024H1"],
        datetime.fromisoformat("2024-08-01T00:00:00+08:00"),
    )

    analysis = EarningsQualityAnalyzer().analyze(
        "run_unit_analysis",
        loaded,
        datetime(2026, 8, 31, tzinfo=UTC),
    )

    by_code = {item["formula_code"]: item for item in analysis.calculation_records}
    assert Decimal(by_code["cash_conversion"]["value"]) > Decimal("1.95")
    assert Decimal(by_code["gross_margin"]["value"]) > Decimal("0.26")
    assert by_code["profit_cash_divergence"]["value"] == "0"
    for calculation in analysis.calculation_records:
        assert_v14_schema(calculation, "calculation-record.schema.json")


def test_deterministic_conclusion_does_not_invent_sources() -> None:
    draft = DeterministicConclusionGenerator().generate(
        {
            "company": {"legal_name": "测试公司"},
            "period_label": "2024H1",
            "cash_conversion": "1.25",
            "gross_margin": "20.00%",
            "divergence_triggered": False,
        }
    )

    assert "1.25" in draft.executive_summary
    assert "20.00%" in draft.executive_summary
    assert all("http" not in limitation for limitation in draft.limitations)
