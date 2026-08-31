"""Typed, framework-independent financial domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class PeriodBasis(StrEnum):
    """Financial statement period basis."""

    INSTANT = "instant"
    DISCRETE = "discrete"
    YTD = "ytd"
    TTM = "ttm"


class FiscalPeriod(StrEnum):
    """Canonical fiscal-period labels."""

    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"
    H1 = "H1"
    FY = "FY"
    TTM = "TTM"


class RestatementStatus(StrEnum):
    """Reported/restated lineage state."""

    AS_REPORTED = "as_reported"
    RESTATED = "restated"
    DERIVED_FROM_RESTATED = "derived_from_restated"


class StatementScope(StrEnum):
    """Financial statement consolidation scope."""

    CONSOLIDATED = "consolidated"
    PARENT_COMPANY = "parent_company"
    COMPANY_ONLY = "company_only"


class FactKind(StrEnum):
    """Whether a fact came directly from a source or a deterministic formula."""

    REPORTED = "reported"
    DERIVED = "derived"


class MetricCode(StrEnum):
    """V1.4 canonical financial metrics."""

    REVENUE = "revenue"
    OPERATING_COST = "operating_cost"
    NET_INCOME = "net_income"
    GROSS_PROFIT = "gross_profit"
    GROSS_MARGIN = "gross_margin"
    OPERATING_CASH_FLOW = "operating_cash_flow"
    ACCOUNTS_RECEIVABLE = "accounts_receivable"
    INVENTORY = "inventory"
    CAPEX = "capex"
    TOTAL_DEBT = "total_debt"
    CASH_AND_EQUIVALENTS = "cash_and_equivalents"


class MeasurementUnit(StrEnum):
    """Persisted measurement units."""

    CURRENCY = "CURRENCY"
    PERCENT = "PERCENT"
    RATIO = "RATIO"
    COUNT = "COUNT"


class CalculationStatus(StrEnum):
    """Deterministic calculation outcome."""

    CALCULATED = "calculated"
    NOT_MEANINGFUL = "not_meaningful"
    UNRELIABLE = "unreliable"
    UNAVAILABLE = "unavailable"


class ComparisonKind(StrEnum):
    """Supported period comparison types."""

    YOY = "yoy"
    QOQ = "qoq"
    PEER = "peer"


@dataclass(frozen=True, slots=True)
class ReportingPeriod:
    """Canonical financial reporting period."""

    period_start: date
    period_end: date
    fiscal_year: int
    fiscal_period: FiscalPeriod
    period_basis: PeriodBasis
    accounting_standard: str = "CAS"
    statement_scope: StatementScope = StatementScope.CONSOLIDATED
    restatement_status: RestatementStatus = RestatementStatus.AS_REPORTED

    def __post_init__(self) -> None:
        if self.period_start > self.period_end:
            raise ValueError("period_start must not be after period_end")
        if not 1900 <= self.fiscal_year <= 2200:
            raise ValueError("fiscal_year is outside the contract range")
        if not self.accounting_standard:
            raise ValueError("accounting_standard is required")


@dataclass(frozen=True, slots=True)
class FinancialFact:
    """Minimal deterministic view of a normalized financial fact."""

    fact_id: str
    company_id: str
    metric_code: MetricCode
    value: Decimal | None
    measurement_unit: MeasurementUnit
    currency: str | None
    period: ReportingPeriod
    fact_kind: FactKind = FactKind.REPORTED
    formula_version: str | None = None
    source_fact_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.fact_id or not self.company_id:
            raise ValueError("fact_id and company_id are required")
        if self.value is not None and not isinstance(self.value, Decimal):
            raise TypeError("financial fact values must use Decimal")
        if self.measurement_unit is MeasurementUnit.CURRENCY:
            if self.currency is None or len(self.currency) != 3 or not self.currency.isupper():
                raise ValueError("currency facts require a three-letter uppercase currency")
        elif self.currency is not None:
            raise ValueError("non-currency facts must not carry currency")
        if self.fact_kind is FactKind.DERIVED:
            if not self.formula_version or not self.source_fact_ids:
                raise ValueError("derived facts require formula_version and source_fact_ids")
        elif self.formula_version is not None or self.source_fact_ids:
            raise ValueError("reported facts cannot carry derivation metadata")


@dataclass(frozen=True, slots=True)
class CalculationResult:
    """Outcome of one deterministic calculation."""

    formula_code: str
    status: CalculationStatus
    value: Decimal | None
    measurement_unit: MeasurementUnit | None
    explanation: str

    def __post_init__(self) -> None:
        if self.status is CalculationStatus.CALCULATED and self.value is None:
            raise ValueError("calculated results require a value")
        if self.status is not CalculationStatus.CALCULATED and self.value is not None:
            raise ValueError("non-calculated results must not carry a value")
        if not self.explanation:
            raise ValueError("calculation explanation is required")


@dataclass(frozen=True, slots=True)
class DerivationResult:
    """Outcome of deriving one discrete quarter from YTD facts."""

    status: CalculationStatus
    fact: FinancialFact | None
    explanation: str

    def __post_init__(self) -> None:
        if self.status is CalculationStatus.CALCULATED and self.fact is None:
            raise ValueError("successful derivation requires a fact")
        if self.status is not CalculationStatus.CALCULATED and self.fact is not None:
            raise ValueError("failed derivation cannot carry a fact")


@dataclass(frozen=True, slots=True)
class ComparabilityResult:
    """Whether two facts may be compared under one frozen rule."""

    comparable: bool
    explanation: str
