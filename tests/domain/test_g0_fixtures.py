"""Regression tests over the frozen, public-safe G0 fixture package."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from researchforge.domain.finance import (
    cash_conversion,
    compare_fact_periods,
    derive_discrete_from_ytd,
    gross_margin,
    gross_profit,
    profit_cash_divergence,
)
from researchforge.domain.models import (
    CalculationStatus,
    ComparisonKind,
    FinancialFact,
    FiscalPeriod,
    MeasurementUnit,
    MetricCode,
    PeriodBasis,
    ReportingPeriod,
    RestatementStatus,
    StatementScope,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "data" / "fixtures" / "g0"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


FACTS = {
    fact["fact_id"]: fact
    for path in sorted((FIXTURE_DIR / "financial-facts").glob("*.json"))
    for fact in (load_json(path),)
}
MANIFEST = load_json(FIXTURE_DIR / "manifest.json")
GOLDEN = load_json(FIXTURE_DIR / "golden-cases.json")


def domain_fact(fact_id: str) -> FinancialFact:
    artifact = FACTS[fact_id]
    artifact_period = artifact["period"]
    return FinancialFact(
        fact_id=fact_id,
        company_id=artifact["company"]["company_id"],
        metric_code=MetricCode(artifact["metric_code"]),
        value=Decimal(artifact["value"]),
        measurement_unit=MeasurementUnit(artifact["measurement_unit"]),
        currency=artifact["currency"],
        period=ReportingPeriod(
            period_start=date.fromisoformat(artifact_period["period_start"]),
            period_end=date.fromisoformat(artifact_period["period_end"]),
            fiscal_year=artifact_period["fiscal_year"],
            fiscal_period=FiscalPeriod(artifact_period["fiscal_period"]),
            period_basis=PeriodBasis(artifact_period["period_basis"]),
            accounting_standard=artifact_period["accounting_standard"],
            statement_scope=StatementScope(artifact_period["statement_scope"]),
            restatement_status=RestatementStatus(artifact_period["restatement_status"]),
        ),
    )


def metric_facts(case: dict[str, Any]) -> dict[str, dict[str, FinancialFact]]:
    grouped: dict[str, dict[str, FinancialFact]] = {}
    for fact_id in case["fact_ids"]:
        fact = domain_fact(fact_id)
        grouped.setdefault(fact.company_id, {})[fact.metric_code.value] = fact
    return grouped


def assert_calculations(metrics: dict[str, FinancialFact], calculations: dict[str, str]) -> None:
    revenue = metrics["revenue"].value
    cost = metrics["operating_cost"].value
    income = metrics["net_income"].value
    ocf = metrics["operating_cash_flow"].value
    assert revenue is not None and cost is not None and income is not None and ocf is not None

    profit = gross_profit(revenue, cost)
    assert profit.status is CalculationStatus.CALCULATED
    margin = gross_margin(profit.value, revenue)
    conversion = cash_conversion(ocf, income)
    divergence = profit_cash_divergence(income, ocf)
    expected = {
        "gross_profit": profit.value,
        "gross_margin": margin.value,
        "cash_conversion": conversion.value,
        "profit_cash_divergence": divergence.value,
    }
    assert all(value is not None for value in expected.values())
    assert {key: Decimal(value) for key, value in calculations.items()} == expected


def test_g0_catalog_and_reconciliation_denominators_are_frozen() -> None:
    assert len(FACTS) == 48
    assert MANIFEST["source_document_count"] == 8
    assert MANIFEST["financial_fact_count"] == 48
    assert MANIFEST["reconciliation"]["semantic_complete_count"] == 48
    assert MANIFEST["reconciliation"]["visual_match_count"] == 48
    assert MANIFEST["reconciliation"]["unresolved_mismatch_count"] == 0
    assert MANIFEST["reconciliation"]["numeric_agreement_rate"] == "1.0"
    assert not list(FIXTURE_DIR.rglob("*.pdf"))


def test_owner_signoff_sample_is_exactly_twenty_and_representative() -> None:
    fact_ids = MANIFEST["owner_signoff"]["fact_ids"]
    sample = [FACTS[fact_id] for fact_id in fact_ids]

    assert len(fact_ids) == len(set(fact_ids)) == 20
    assert {fact["company"]["company_id"] for fact in sample} == {"cn_300750", "cn_300014"}
    assert {fact["metric_code"] for fact in sample} == {
        "accounts_receivable",
        "inventory",
        "revenue",
        "operating_cost",
        "net_income",
        "operating_cash_flow",
    }
    assert len({fact["source"]["document_id"] for fact in sample}) == 8


def test_three_golden_cases_recompute_through_production_formulas() -> None:
    cases = GOLDEN["cases"]
    assert len(cases) == 3
    for case in cases:
        grouped = metric_facts(case)
        if case["task_type"] == "company_research":
            assert_calculations(grouped[case["companies"][0]], case["calculations"])
        else:
            assert_calculations(grouped["cn_300750"], case["calculations"]["catl"])
            assert_calculations(grouped["cn_300014"], case["calculations"]["eve"])


def test_actual_ytd_derivation_preserves_or_rejects_restatement_lineage() -> None:
    catl_h1 = domain_fact("fact_g0_catl_2024h1_revenue")
    catl_q1 = domain_fact("fact_g0_catl_2024q1_revenue")
    catl_result = derive_discrete_from_ytd(
        catl_h1,
        catl_q1,
        fact_id="fact_golden_catl_2024q2_revenue",
    )
    assert catl_result.status is CalculationStatus.CALCULATED
    assert catl_result.fact is not None
    assert catl_result.fact.value == Decimal("86996055000.00")

    eve_h1 = domain_fact("fact_g0_eve_2024h1_corrected_revenue")
    eve_q1 = domain_fact("fact_g0_eve_2024q1_revenue")
    eve_result = derive_discrete_from_ytd(
        eve_h1,
        eve_q1,
        fact_id="fact_forbidden_mixed_lineage",
    )
    assert eve_result.status is CalculationStatus.UNRELIABLE
    assert eve_result.fact is None
    assert "restatement lineage" in eve_result.explanation


def test_peer_case_uses_aligned_periods_and_latest_available_lineages() -> None:
    catl = domain_fact("fact_g0_catl_2024h1_revenue")
    eve = domain_fact("fact_g0_eve_2024h1_corrected_revenue")

    comparison = compare_fact_periods(catl, eve, ComparisonKind.PEER)

    assert comparison.comparable
    assert "latest available lineage" in comparison.explanation


def test_golden_cases_obey_point_in_time_cutoff() -> None:
    for case in GOLDEN["cases"]:
        research_time = datetime.fromisoformat(case["research_time"])
        assert all(
            datetime.fromisoformat(FACTS[fact_id]["source"]["published_at"]) <= research_time
            for fact_id in case["fact_ids"]
        )
