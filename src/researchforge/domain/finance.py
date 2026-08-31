"""Deterministic Decimal financial formulas and period semantics."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from researchforge.domain.models import (
    CalculationResult,
    CalculationStatus,
    ComparabilityResult,
    ComparisonKind,
    DerivationResult,
    FactKind,
    FinancialFact,
    FiscalPeriod,
    MeasurementUnit,
    MetricCode,
    PeriodBasis,
    ReportingPeriod,
    RestatementStatus,
)

FORMULA_VERSION = "1.0.0"

FLOW_METRICS = {
    MetricCode.REVENUE,
    MetricCode.OPERATING_COST,
    MetricCode.NET_INCOME,
    MetricCode.GROSS_PROFIT,
    MetricCode.OPERATING_CASH_FLOW,
    MetricCode.CAPEX,
}


def _result(
    formula_code: str,
    status: CalculationStatus,
    explanation: str,
    *,
    value: Decimal | None = None,
    unit: MeasurementUnit | None = None,
) -> CalculationResult:
    return CalculationResult(
        formula_code=formula_code,
        status=status,
        value=value,
        measurement_unit=unit,
        explanation=explanation,
    )


def normalize_to_base_units(value: Decimal, reported_scale: int) -> Decimal:
    """Normalize a reported Decimal to base units without binary floating point."""
    if not isinstance(value, Decimal):
        raise TypeError("value must be Decimal")
    if reported_scale <= 0:
        raise ValueError("reported_scale must be positive")
    return value * Decimal(reported_scale)


def absolute_change(
    current: Decimal | None,
    comparison: Decimal | None,
    *,
    unit: MeasurementUnit = MeasurementUnit.CURRENCY,
) -> CalculationResult:
    """Return current minus comparison, or unavailable when either value is missing."""
    if current is None or comparison is None:
        return _result(
            "absolute_change",
            CalculationStatus.UNAVAILABLE,
            "Absolute change requires both current and comparison values.",
        )
    return _result(
        "absolute_change",
        CalculationStatus.CALCULATED,
        "Calculated as current minus comparison.",
        value=current - comparison,
        unit=unit,
    )


def growth_rate(current: Decimal | None, comparison: Decimal | None) -> CalculationResult:
    """Calculate standard growth only when the comparison base is positive."""
    if current is None or comparison is None:
        return _result(
            "growth_rate",
            CalculationStatus.UNAVAILABLE,
            "Growth requires both current and comparison values.",
        )
    if comparison <= 0:
        return _result(
            "growth_rate",
            CalculationStatus.NOT_MEANINGFUL,
            "Standard percentage growth is not meaningful from a zero or negative base.",
        )
    return _result(
        "growth_rate",
        CalculationStatus.CALCULATED,
        "Calculated as (current - comparison) / comparison.",
        value=(current - comparison) / comparison,
        unit=MeasurementUnit.RATIO,
    )


def gross_profit(revenue: Decimal | None, operating_cost: Decimal | None) -> CalculationResult:
    """Calculate revenue minus operating cost under a compatible scope and period."""
    if revenue is None or operating_cost is None:
        return _result(
            "gross_profit",
            CalculationStatus.UNAVAILABLE,
            "Gross profit requires revenue and operating cost.",
        )
    return _result(
        "gross_profit",
        CalculationStatus.CALCULATED,
        "Calculated as revenue minus operating cost.",
        value=revenue - operating_cost,
        unit=MeasurementUnit.CURRENCY,
    )


def gross_margin(gross_profit: Decimal | None, revenue: Decimal | None) -> CalculationResult:
    """Calculate gross profit divided by positive revenue."""
    if gross_profit is None or revenue is None:
        return _result(
            "gross_margin",
            CalculationStatus.UNAVAILABLE,
            "Gross margin requires gross profit and revenue.",
        )
    if revenue <= 0:
        return _result(
            "gross_margin",
            CalculationStatus.NOT_MEANINGFUL,
            "Gross margin is not meaningful when revenue is zero or negative.",
        )
    return _result(
        "gross_margin",
        CalculationStatus.CALCULATED,
        "Calculated as gross profit / revenue.",
        value=gross_profit / revenue,
        unit=MeasurementUnit.RATIO,
    )


def margin_change_pp(
    current_margin: Decimal | None,
    comparison_margin: Decimal | None,
) -> CalculationResult:
    """Return the change between decimal margins in percentage points."""
    if current_margin is None or comparison_margin is None:
        return _result(
            "margin_change_pp",
            CalculationStatus.UNAVAILABLE,
            "Margin change requires both current and comparison margins.",
        )
    return _result(
        "margin_change_pp",
        CalculationStatus.CALCULATED,
        "Calculated as (current margin - comparison margin) x 100.",
        value=(current_margin - comparison_margin) * Decimal(100),
        unit=MeasurementUnit.PERCENT,
    )


def cash_conversion(
    operating_cash_flow: Decimal | None,
    net_income: Decimal | None,
) -> CalculationResult:
    """Calculate OCF / net income only when net income is positive."""
    if operating_cash_flow is None or net_income is None:
        return _result(
            "cash_conversion",
            CalculationStatus.UNAVAILABLE,
            "Cash conversion requires operating cash flow and net income.",
        )
    if net_income <= 0:
        return _result(
            "cash_conversion",
            CalculationStatus.NOT_MEANINGFUL,
            "Cash conversion is not meaningful when net income is zero or negative.",
        )
    return _result(
        "cash_conversion",
        CalculationStatus.CALCULATED,
        "Calculated as operating cash flow / net income.",
        value=operating_cash_flow / net_income,
        unit=MeasurementUnit.RATIO,
    )


def working_capital_change(
    ending_balance: Decimal | None,
    comparison_ending_balance: Decimal | None,
) -> CalculationResult:
    """Calculate an instant working-capital balance change."""
    result = absolute_change(ending_balance, comparison_ending_balance)
    return CalculationResult(
        formula_code="working_capital_change",
        status=result.status,
        value=result.value,
        measurement_unit=result.measurement_unit,
        explanation=(
            "Calculated as ending balance minus comparison ending balance."
            if result.status is CalculationStatus.CALCULATED
            else "Working-capital change requires both ending balances."
        ),
    )


def profit_cash_divergence(
    current_net_income: Decimal | None,
    current_operating_cash_flow: Decimal | None,
    *,
    comparison_net_income: Decimal | None = None,
    comparison_operating_cash_flow: Decimal | None = None,
) -> CalculationResult:
    """Apply the three frozen profit/cash divergence signal rules."""
    if current_net_income is None or current_operating_cash_flow is None:
        return _result(
            "profit_cash_divergence",
            CalculationStatus.UNAVAILABLE,
            "Divergence requires current net income and operating cash flow.",
        )

    triggered_rules: list[str] = []
    if current_net_income > 0 and current_operating_cash_flow < 0:
        triggered_rules.append("positive_profit_negative_ocf")

    comparison_complete = (
        comparison_net_income is not None and comparison_operating_cash_flow is not None
    )
    if comparison_complete:
        assert comparison_net_income is not None
        assert comparison_operating_cash_flow is not None
        if comparison_net_income > 0 and comparison_operating_cash_flow > 0:
            profit_growth = (current_net_income - comparison_net_income) / comparison_net_income
            cash_growth = (
                current_operating_cash_flow - comparison_operating_cash_flow
            ) / comparison_operating_cash_flow
            if profit_growth > 0 and cash_growth < 0:
                triggered_rules.append("profit_growth_positive_ocf_growth_negative")
        if (
            current_net_income > comparison_net_income
            and current_operating_cash_flow < comparison_operating_cash_flow
        ):
            triggered_rules.append("profit_improves_ocf_declines")

    explanation = (
        "Triggered rules: " + ", ".join(triggered_rules) + ". Investigate; not causal proof."
        if triggered_rules
        else "No frozen profit/cash divergence rule was triggered."
    )
    return _result(
        "profit_cash_divergence",
        CalculationStatus.CALCULATED,
        explanation,
        value=Decimal(1 if triggered_rules else 0),
        unit=MeasurementUnit.COUNT,
    )


def _facts_are_ytd_compatible(current: FinancialFact, prior: FinancialFact) -> str | None:
    checks = (
        (current.company_id == prior.company_id, "company differs"),
        (current.metric_code == prior.metric_code, "metric differs"),
        (current.currency == prior.currency, "currency differs"),
        (
            current.period.accounting_standard == prior.period.accounting_standard,
            "accounting standard differs",
        ),
        (
            current.period.statement_scope == prior.period.statement_scope,
            "statement scope differs",
        ),
        (
            current.period.restatement_status == prior.period.restatement_status,
            "restatement lineage differs",
        ),
        (current.period.fiscal_year == prior.period.fiscal_year, "fiscal year differs"),
        (current.period.period_start == prior.period.period_start, "YTD start date differs"),
    )
    return next((reason for valid, reason in checks if not valid), None)


def derive_discrete_from_ytd(
    current: FinancialFact,
    prior: FinancialFact | None = None,
    *,
    fact_id: str,
) -> DerivationResult:
    """Derive Q1/Q2/Q3/Q4 discrete flow facts from compatible YTD facts."""
    if current.metric_code not in FLOW_METRICS:
        return DerivationResult(
            CalculationStatus.UNRELIABLE,
            None,
            "Only flow metrics may be derived from YTD values.",
        )
    if current.period.period_basis is not PeriodBasis.YTD:
        return DerivationResult(
            CalculationStatus.UNRELIABLE,
            None,
            "Current fact is not labeled YTD.",
        )
    if current.value is None:
        return DerivationResult(
            CalculationStatus.UNAVAILABLE,
            None,
            "Current YTD value is unavailable.",
        )

    source_ids: tuple[str, ...]
    if current.period.fiscal_period is FiscalPeriod.Q1:
        if prior is not None:
            return DerivationResult(
                CalculationStatus.UNRELIABLE,
                None,
                "Q1 discrete equals Q1 YTD and must not subtract a prior fact.",
            )
        value = current.value
        target_period = FiscalPeriod.Q1
        period_start = current.period.period_start
        source_ids = (current.fact_id,)
    else:
        if prior is None or prior.value is None:
            return DerivationResult(
                CalculationStatus.UNAVAILABLE,
                None,
                "A compatible prior YTD fact is required for this discrete quarter.",
            )
        if prior.period.period_basis is not PeriodBasis.YTD:
            return DerivationResult(
                CalculationStatus.UNRELIABLE,
                None,
                "Prior fact is not labeled YTD.",
            )
        incompatibility = _facts_are_ytd_compatible(current, prior)
        if incompatibility:
            return DerivationResult(
                CalculationStatus.UNRELIABLE,
                None,
                f"YTD facts are incompatible: {incompatibility}.",
            )
        expected_prior = {
            FiscalPeriod.H1: (FiscalPeriod.Q1, FiscalPeriod.Q2),
            FiscalPeriod.Q3: (FiscalPeriod.H1, FiscalPeriod.Q3),
            FiscalPeriod.FY: (FiscalPeriod.Q3, FiscalPeriod.Q4),
        }.get(current.period.fiscal_period)
        if expected_prior is None or prior.period.fiscal_period is not expected_prior[0]:
            return DerivationResult(
                CalculationStatus.UNRELIABLE,
                None,
                "YTD fiscal-period sequence is incompatible.",
            )
        value = current.value - prior.value
        target_period = expected_prior[1]
        period_start = prior.period.period_end + timedelta(days=1)
        source_ids = (current.fact_id, prior.fact_id)

    restatement = (
        RestatementStatus.DERIVED_FROM_RESTATED
        if current.period.restatement_status is RestatementStatus.RESTATED
        else RestatementStatus.AS_REPORTED
    )
    derived_period = ReportingPeriod(
        period_start=period_start,
        period_end=current.period.period_end,
        fiscal_year=current.period.fiscal_year,
        fiscal_period=target_period,
        period_basis=PeriodBasis.DISCRETE,
        accounting_standard=current.period.accounting_standard,
        statement_scope=current.period.statement_scope,
        restatement_status=restatement,
    )
    fact = FinancialFact(
        fact_id=fact_id,
        company_id=current.company_id,
        metric_code=current.metric_code,
        value=value,
        measurement_unit=current.measurement_unit,
        currency=current.currency,
        period=derived_period,
        fact_kind=FactKind.DERIVED,
        formula_version=FORMULA_VERSION,
        source_fact_ids=source_ids,
    )
    return DerivationResult(
        CalculationStatus.CALCULATED,
        fact,
        "Derived by subtracting compatible prior YTD value."
        if prior is not None
        else "Q1 discrete equals Q1 YTD.",
    )


def compare_fact_periods(
    current: FinancialFact,
    comparison: FinancialFact,
    kind: ComparisonKind,
) -> ComparabilityResult:
    """Check frozen period, metric, currency, scope, and restatement comparability."""
    shared_checks = (
        (current.metric_code == comparison.metric_code, "metric differs"),
        (current.currency == comparison.currency, "currency differs"),
        (
            current.period.accounting_standard == comparison.period.accounting_standard,
            "accounting standard differs",
        ),
        (
            current.period.statement_scope == comparison.period.statement_scope,
            "statement scope differs",
        ),
    )
    incompatibility = next((reason for valid, reason in shared_checks if not valid), None)
    if incompatibility:
        return ComparabilityResult(False, incompatibility)

    if kind is not ComparisonKind.PEER and current.company_id != comparison.company_id:
        return ComparabilityResult(False, "company differs for a non-peer comparison")
    if kind is ComparisonKind.PEER:
        aligned = (
            current.period.period_end == comparison.period.period_end
            and current.period.period_basis == comparison.period.period_basis
        )
        return ComparabilityResult(
            aligned,
            (
                "aligned peer periods using each company's latest available lineage"
                if aligned
                else "peer periods differ"
            ),
        )
    if current.period.restatement_status != comparison.period.restatement_status:
        return ComparabilityResult(False, "restatement lineage differs")
    if kind is ComparisonKind.YOY:
        equivalent = (
            current.period.fiscal_period == comparison.period.fiscal_period
            and current.period.period_basis == comparison.period.period_basis
            and current.period.fiscal_year == comparison.period.fiscal_year + 1
        )
        return ComparabilityResult(
            equivalent,
            "equivalent fiscal periods and bases"
            if equivalent
            else "YoY periods or bases are not equivalent",
        )

    quarter_order = {
        FiscalPeriod.Q1: 1,
        FiscalPeriod.Q2: 2,
        FiscalPeriod.Q3: 3,
        FiscalPeriod.Q4: 4,
    }
    current_order = quarter_order.get(current.period.fiscal_period)
    comparison_order = quarter_order.get(comparison.period.fiscal_period)
    consecutive = (
        current.period.period_basis is PeriodBasis.DISCRETE
        and comparison.period.period_basis is PeriodBasis.DISCRETE
        and current_order is not None
        and comparison_order is not None
        and (
            (
                current.period.fiscal_year == comparison.period.fiscal_year
                and current_order == comparison_order + 1
            )
            or (
                current.period.fiscal_year == comparison.period.fiscal_year + 1
                and current_order == 1
                and comparison_order == 4
            )
        )
    )
    return ComparabilityResult(
        consecutive,
        "consecutive discrete quarters"
        if consecutive
        else "QoQ requires consecutive discrete quarters",
    )
