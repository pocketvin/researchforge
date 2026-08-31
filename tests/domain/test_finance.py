"""Financial methodology regression tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from researchforge.domain.finance import (
    FORMULA_VERSION,
    absolute_change,
    cash_conversion,
    compare_fact_periods,
    derive_discrete_from_ytd,
    gross_margin,
    gross_profit,
    growth_rate,
    margin_change_pp,
    normalize_to_base_units,
    profit_cash_divergence,
    working_capital_change,
)
from researchforge.domain.models import (
    CalculationStatus,
    ComparisonKind,
    FactKind,
    FinancialFact,
    FiscalPeriod,
    MeasurementUnit,
    MetricCode,
    PeriodBasis,
    ReportingPeriod,
    RestatementStatus,
    StatementScope,
)

D = Decimal


def period(
    fiscal_period: FiscalPeriod,
    basis: PeriodBasis,
    *,
    year: int = 2024,
    scope: StatementScope = StatementScope.CONSOLIDATED,
    restatement: RestatementStatus = RestatementStatus.AS_REPORTED,
) -> ReportingPeriod:
    boundaries = {
        FiscalPeriod.Q1: (date(year, 1, 1), date(year, 3, 31)),
        FiscalPeriod.Q2: (date(year, 4, 1), date(year, 6, 30)),
        FiscalPeriod.H1: (date(year, 1, 1), date(year, 6, 30)),
        FiscalPeriod.Q3: (
            date(year, 7, 1) if basis is PeriodBasis.DISCRETE else date(year, 1, 1),
            date(year, 9, 30),
        ),
        FiscalPeriod.Q4: (date(year, 10, 1), date(year, 12, 31)),
        FiscalPeriod.FY: (date(year, 1, 1), date(year, 12, 31)),
    }
    start, end = boundaries[fiscal_period]
    return ReportingPeriod(
        period_start=start,
        period_end=end,
        fiscal_year=year,
        fiscal_period=fiscal_period,
        period_basis=basis,
        statement_scope=scope,
        restatement_status=restatement,
    )


def fact(
    fact_id: str,
    value: Decimal | None,
    reporting_period: ReportingPeriod,
    *,
    company_id: str = "company_catl",
    metric: MetricCode = MetricCode.REVENUE,
    currency: str | None = "CNY",
    unit: MeasurementUnit = MeasurementUnit.CURRENCY,
) -> FinancialFact:
    return FinancialFact(
        fact_id=fact_id,
        company_id=company_id,
        metric_code=metric,
        value=value,
        measurement_unit=unit,
        currency=currency,
        period=reporting_period,
    )


def test_normalize_to_base_units_uses_decimal() -> None:
    assert normalize_to_base_units(D("12.34"), 1_000_000) == D("12340000.00")


@pytest.mark.parametrize("scale", [0, -1])
def test_normalize_rejects_invalid_scale(scale: int) -> None:
    with pytest.raises(ValueError, match="positive"):
        normalize_to_base_units(D("1"), scale)


def test_normalize_rejects_binary_float() -> None:
    with pytest.raises(TypeError, match="Decimal"):
        normalize_to_base_units(1.2, 1)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("current", "comparison", "status", "value"),
    [
        (D("12"), D("10"), CalculationStatus.CALCULATED, D("2")),
        (D("-2"), D("-5"), CalculationStatus.CALCULATED, D("3")),
        (None, D("10"), CalculationStatus.UNAVAILABLE, None),
    ],
)
def test_absolute_change(
    current: Decimal | None,
    comparison: Decimal | None,
    status: CalculationStatus,
    value: Decimal | None,
) -> None:
    result = absolute_change(current, comparison)
    assert (result.status, result.value) == (status, value)


@pytest.mark.parametrize(
    ("current", "comparison", "status", "value"),
    [
        (D("120"), D("100"), CalculationStatus.CALCULATED, D("0.2")),
        (D("10"), D("0"), CalculationStatus.NOT_MEANINGFUL, None),
        (D("10"), D("-5"), CalculationStatus.NOT_MEANINGFUL, None),
        (None, D("5"), CalculationStatus.UNAVAILABLE, None),
    ],
)
def test_growth_positive_zero_negative_and_missing(
    current: Decimal | None,
    comparison: Decimal | None,
    status: CalculationStatus,
    value: Decimal | None,
) -> None:
    result = growth_rate(current, comparison)
    assert (result.status, result.value) == (status, value)


@pytest.mark.parametrize(
    ("revenue", "operating_cost", "status", "value"),
    [
        (D("100"), D("75"), CalculationStatus.CALCULATED, D("25")),
        (D("100"), D("110"), CalculationStatus.CALCULATED, D("-10")),
        (None, D("75"), CalculationStatus.UNAVAILABLE, None),
    ],
)
def test_gross_profit(
    revenue: Decimal | None,
    operating_cost: Decimal | None,
    status: CalculationStatus,
    value: Decimal | None,
) -> None:
    result = gross_profit(revenue, operating_cost)
    assert (result.status, result.value) == (status, value)


@pytest.mark.parametrize(
    ("gross_profit_value", "revenue", "status", "value"),
    [
        (D("25"), D("100"), CalculationStatus.CALCULATED, D("0.25")),
        (D("1"), D("0"), CalculationStatus.NOT_MEANINGFUL, None),
        (D("1"), D("-1"), CalculationStatus.NOT_MEANINGFUL, None),
        (None, D("1"), CalculationStatus.UNAVAILABLE, None),
    ],
)
def test_gross_margin(
    gross_profit_value: Decimal | None,
    revenue: Decimal | None,
    status: CalculationStatus,
    value: Decimal | None,
) -> None:
    result = gross_margin(gross_profit_value, revenue)
    assert (result.status, result.value) == (status, value)


def test_margin_change_is_percentage_points() -> None:
    result = margin_change_pp(D("0.28"), D("0.25"))
    assert result.status is CalculationStatus.CALCULATED
    assert result.value == D("3.00")
    assert result.measurement_unit is MeasurementUnit.PERCENT


@pytest.mark.parametrize(
    ("ocf", "income", "status", "value"),
    [
        (D("80"), D("100"), CalculationStatus.CALCULATED, D("0.8")),
        (D("80"), D("0"), CalculationStatus.NOT_MEANINGFUL, None),
        (D("80"), D("-1"), CalculationStatus.NOT_MEANINGFUL, None),
        (None, D("10"), CalculationStatus.UNAVAILABLE, None),
    ],
)
def test_cash_conversion(
    ocf: Decimal | None,
    income: Decimal | None,
    status: CalculationStatus,
    value: Decimal | None,
) -> None:
    result = cash_conversion(ocf, income)
    assert (result.status, result.value) == (status, value)


def test_working_capital_change_uses_ending_balances() -> None:
    result = working_capital_change(D("125"), D("100"))
    assert result.value == D("25")
    assert result.formula_code == "working_capital_change"


def test_profit_cash_divergence_all_three_rules() -> None:
    result = profit_cash_divergence(
        D("120"),
        D("-10"),
        comparison_net_income=D("100"),
        comparison_operating_cash_flow=D("20"),
    )
    assert result.value == D("1")
    assert "positive_profit_negative_ocf" in result.explanation
    assert "profit_growth_positive_ocf_growth_negative" in result.explanation
    assert "profit_improves_ocf_declines" in result.explanation


def test_profit_cash_divergence_can_be_clear() -> None:
    result = profit_cash_divergence(
        D("90"),
        D("30"),
        comparison_net_income=D("100"),
        comparison_operating_cash_flow=D("20"),
    )
    assert result.value == D("0")


def test_profit_cash_divergence_missing_is_unavailable() -> None:
    assert profit_cash_divergence(None, D("1")).status is CalculationStatus.UNAVAILABLE


def test_q1_discrete_equals_q1_ytd() -> None:
    q1 = fact("fact_q1", D("100"), period(FiscalPeriod.Q1, PeriodBasis.YTD))
    result = derive_discrete_from_ytd(q1, fact_id="fact_q1_discrete")

    assert result.status is CalculationStatus.CALCULATED
    assert result.fact is not None
    assert result.fact.value == D("100")
    assert result.fact.period.period_basis is PeriodBasis.DISCRETE
    assert result.fact.source_fact_ids == ("fact_q1",)


def test_h1_minus_q1_derives_q2() -> None:
    q1 = fact("fact_q1", D("100"), period(FiscalPeriod.Q1, PeriodBasis.YTD))
    h1 = fact("fact_h1", D("260"), period(FiscalPeriod.H1, PeriodBasis.YTD))
    result = derive_discrete_from_ytd(h1, q1, fact_id="fact_q2_discrete")

    assert result.fact is not None
    assert result.fact.value == D("160")
    assert result.fact.period.fiscal_period is FiscalPeriod.Q2
    assert result.fact.period.period_start == date(2024, 4, 1)
    assert result.fact.fact_kind is FactKind.DERIVED
    assert result.fact.formula_version == FORMULA_VERSION


def test_q3_minus_h1_derives_q3_discrete() -> None:
    h1 = fact("fact_h1", D("260"), period(FiscalPeriod.H1, PeriodBasis.YTD))
    q3 = fact("fact_q3", D("390"), period(FiscalPeriod.Q3, PeriodBasis.YTD))
    result = derive_discrete_from_ytd(q3, h1, fact_id="fact_q3_discrete")

    assert result.fact is not None
    assert result.fact.value == D("130")
    assert result.fact.period.period_start == date(2024, 7, 1)


def test_fy_minus_q3_derives_q4_discrete() -> None:
    q3 = fact("fact_q3", D("390"), period(FiscalPeriod.Q3, PeriodBasis.YTD))
    fy = fact("fact_fy", D("550"), period(FiscalPeriod.FY, PeriodBasis.YTD))
    result = derive_discrete_from_ytd(fy, q3, fact_id="fact_q4_discrete")

    assert result.fact is not None
    assert result.fact.value == D("160")
    assert result.fact.period.fiscal_period is FiscalPeriod.Q4


def test_ytd_derivation_marks_restatement_lineage() -> None:
    q1_period = period(
        FiscalPeriod.Q1,
        PeriodBasis.YTD,
        restatement=RestatementStatus.RESTATED,
    )
    h1_period = period(
        FiscalPeriod.H1,
        PeriodBasis.YTD,
        restatement=RestatementStatus.RESTATED,
    )
    result = derive_discrete_from_ytd(
        fact("fact_h1", D("250"), h1_period),
        fact("fact_q1", D("100"), q1_period),
        fact_id="fact_q2_restated",
    )

    assert result.fact is not None
    assert result.fact.period.restatement_status is RestatementStatus.DERIVED_FROM_RESTATED


@pytest.mark.parametrize(
    "prior_mutation",
    [
        {"company_id": "company_eve"},
        {"currency": "USD"},
        {
            "period": period(
                FiscalPeriod.Q1,
                PeriodBasis.YTD,
                scope=StatementScope.PARENT_COMPANY,
            )
        },
        {
            "period": period(
                FiscalPeriod.Q1,
                PeriodBasis.YTD,
                restatement=RestatementStatus.RESTATED,
            )
        },
    ],
)
def test_ytd_derivation_rejects_incompatible_facts(
    prior_mutation: dict[str, object],
) -> None:
    q1 = fact("fact_q1", D("100"), period(FiscalPeriod.Q1, PeriodBasis.YTD))
    h1 = fact("fact_h1", D("260"), period(FiscalPeriod.H1, PeriodBasis.YTD))
    result = derive_discrete_from_ytd(
        h1,
        replace(q1, **prior_mutation),  # type: ignore[arg-type]
        fact_id="fact_invalid",
    )

    assert result.status is CalculationStatus.UNRELIABLE
    assert result.fact is None


def test_ytd_derivation_rejects_instant_metric() -> None:
    inventory = fact(
        "fact_inventory",
        D("100"),
        period(FiscalPeriod.Q1, PeriodBasis.YTD),
        metric=MetricCode.INVENTORY,
    )
    result = derive_discrete_from_ytd(inventory, fact_id="fact_invalid")
    assert result.status is CalculationStatus.UNRELIABLE


def test_yoy_requires_equivalent_period_basis() -> None:
    current = fact("current", D("120"), period(FiscalPeriod.Q3, PeriodBasis.YTD))
    comparison = fact(
        "comparison",
        D("100"),
        period(FiscalPeriod.Q3, PeriodBasis.YTD, year=2023),
    )
    assert compare_fact_periods(current, comparison, ComparisonKind.YOY).comparable

    discrete = replace(
        comparison,
        period=period(FiscalPeriod.Q3, PeriodBasis.DISCRETE, year=2023),
    )
    assert not compare_fact_periods(current, discrete, ComparisonKind.YOY).comparable


def test_yoy_rejects_non_adjacent_fiscal_years() -> None:
    current = fact("current", D("120"), period(FiscalPeriod.Q3, PeriodBasis.YTD))
    two_year_gap = fact(
        "two_year_gap",
        D("90"),
        period(FiscalPeriod.Q3, PeriodBasis.YTD, year=2022),
    )

    result = compare_fact_periods(current, two_year_gap, ComparisonKind.YOY)

    assert not result.comparable
    assert result.explanation == "YoY periods or bases are not equivalent"


def test_qoq_rejects_ytd_and_accepts_consecutive_discrete_quarters() -> None:
    q2 = fact("q2", D("100"), period(FiscalPeriod.Q2, PeriodBasis.DISCRETE))
    q3 = fact("q3", D("120"), period(FiscalPeriod.Q3, PeriodBasis.DISCRETE))
    assert compare_fact_periods(q3, q2, ComparisonKind.QOQ).comparable

    q3_ytd = replace(q3, period=period(FiscalPeriod.Q3, PeriodBasis.YTD))
    assert not compare_fact_periods(q3_ytd, q2, ComparisonKind.QOQ).comparable


def test_peer_requires_aligned_period_and_currency() -> None:
    catl = fact("catl", D("100"), period(FiscalPeriod.Q3, PeriodBasis.YTD))
    eve = fact(
        "eve",
        D("80"),
        period(FiscalPeriod.Q3, PeriodBasis.YTD),
        company_id="company_eve",
    )
    assert compare_fact_periods(catl, eve, ComparisonKind.PEER).comparable

    eve_usd = replace(eve, currency="USD")
    assert not compare_fact_periods(catl, eve_usd, ComparisonKind.PEER).comparable


def test_peer_allows_each_company_latest_restatement_lineage() -> None:
    catl = fact("catl", D("100"), period(FiscalPeriod.H1, PeriodBasis.YTD))
    eve = fact(
        "eve",
        D("80"),
        period(
            FiscalPeriod.H1,
            PeriodBasis.YTD,
            restatement=RestatementStatus.RESTATED,
        ),
        company_id="company_eve",
    )

    result = compare_fact_periods(catl, eve, ComparisonKind.PEER)

    assert result.comparable
    assert "latest available lineage" in result.explanation
