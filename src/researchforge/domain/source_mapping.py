"""Versioned source-line mappings for the V1.4 financial domain.

The official row labels are the authoritative extraction target. Tushare field
names are retained only for optional, local reconciliation during G0; Tushare is
not a runtime or redistribution source for V1.4.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from researchforge.domain.models import MetricCode, PeriodBasis

SOURCE_MAPPING_VERSION = "1.0.0"


class StatementCode(StrEnum):
    """Canonical statement containing a source line."""

    INCOME = "income_statement"
    BALANCE = "balance_sheet"
    CASH_FLOW = "cash_flow_statement"


class MappingTransform(StrEnum):
    """Frozen transformation from mapped source lines to a canonical metric."""

    DIRECT = "direct"
    DIFFERENCE = "difference"
    RATIO = "ratio"
    SUM = "sum"


@dataclass(frozen=True, slots=True)
class SourceMetricMapping:
    """One immutable canonical metric mapping."""

    metric_code: MetricCode
    statements: tuple[StatementCode, ...]
    official_row_labels: tuple[str, ...]
    tushare_endpoint: str | None
    tushare_fields: tuple[str, ...]
    normal_bases: tuple[PeriodBasis, ...]
    transform: MappingTransform
    sign_convention: str
    note: str

    def __post_init__(self) -> None:
        if not self.statements or not self.official_row_labels or not self.normal_bases:
            raise ValueError("source mappings require statements, labels, and period bases")
        if self.tushare_endpoint is None and self.tushare_fields:
            raise ValueError("Tushare fields require an endpoint")
        if not self.note:
            raise ValueError("source mapping note is required")


SOURCE_METRIC_MAPPINGS: tuple[SourceMetricMapping, ...] = (
    SourceMetricMapping(
        metric_code=MetricCode.REVENUE,
        statements=(StatementCode.INCOME,),
        official_row_labels=("营业收入",),
        tushare_endpoint="income",
        tushare_fields=("revenue",),
        normal_bases=(PeriodBasis.DISCRETE, PeriodBasis.YTD),
        transform=MappingTransform.DIRECT,
        sign_convention="natural_statement_value",
        note="Use consolidated operating revenue, not operating total revenue.",
    ),
    SourceMetricMapping(
        metric_code=MetricCode.OPERATING_COST,
        statements=(StatementCode.INCOME,),
        official_row_labels=("营业成本",),
        tushare_endpoint="income",
        tushare_fields=("oper_cost",),
        normal_bases=(PeriodBasis.DISCRETE, PeriodBasis.YTD),
        transform=MappingTransform.DIRECT,
        sign_convention="natural_statement_value",
        note="Use operating cost under the same consolidated scope and period as revenue.",
    ),
    SourceMetricMapping(
        metric_code=MetricCode.NET_INCOME,
        statements=(StatementCode.INCOME,),
        official_row_labels=("归属于上市公司股东的净利润", "归属于母公司股东的净利润"),
        tushare_endpoint="income",
        tushare_fields=("n_income_attr_p",),
        normal_bases=(PeriodBasis.DISCRETE, PeriodBasis.YTD),
        transform=MappingTransform.DIRECT,
        sign_convention="natural_statement_value",
        note="V1.4 selects attributable net income for the consolidated comparison scope.",
    ),
    SourceMetricMapping(
        metric_code=MetricCode.GROSS_PROFIT,
        statements=(StatementCode.INCOME,),
        official_row_labels=("营业收入", "营业成本"),
        tushare_endpoint="income",
        tushare_fields=("revenue", "oper_cost"),
        normal_bases=(PeriodBasis.DISCRETE, PeriodBasis.YTD),
        transform=MappingTransform.DIFFERENCE,
        sign_convention="natural_statement_value",
        note="Derive as revenue minus operating cost under the same scope and period.",
    ),
    SourceMetricMapping(
        metric_code=MetricCode.GROSS_MARGIN,
        statements=(StatementCode.INCOME,),
        official_row_labels=("营业收入", "营业成本"),
        tushare_endpoint="income",
        tushare_fields=("revenue", "oper_cost"),
        normal_bases=(PeriodBasis.DISCRETE, PeriodBasis.YTD),
        transform=MappingTransform.RATIO,
        sign_convention="positive_ratio",
        note="Derive gross profit first, then divide by positive revenue.",
    ),
    SourceMetricMapping(
        metric_code=MetricCode.OPERATING_CASH_FLOW,
        statements=(StatementCode.CASH_FLOW,),
        official_row_labels=("经营活动产生的现金流量净额",),
        tushare_endpoint="cashflow",
        tushare_fields=("n_cashflow_act",),
        normal_bases=(PeriodBasis.DISCRETE, PeriodBasis.YTD),
        transform=MappingTransform.DIRECT,
        sign_convention="natural_statement_value",
        note="Use the consolidated statement net operating cash-flow line.",
    ),
    SourceMetricMapping(
        metric_code=MetricCode.ACCOUNTS_RECEIVABLE,
        statements=(StatementCode.BALANCE,),
        official_row_labels=("应收账款",),
        tushare_endpoint="balancesheet",
        tushare_fields=("accounts_receiv",),
        normal_bases=(PeriodBasis.INSTANT,),
        transform=MappingTransform.DIRECT,
        sign_convention="natural_statement_value",
        note=(
            "Do not substitute notes receivable or combined receivables without a mapping revision."
        ),
    ),
    SourceMetricMapping(
        metric_code=MetricCode.INVENTORY,
        statements=(StatementCode.BALANCE,),
        official_row_labels=("存货",),
        tushare_endpoint="balancesheet",
        tushare_fields=("inventories",),
        normal_bases=(PeriodBasis.INSTANT,),
        transform=MappingTransform.DIRECT,
        sign_convention="natural_statement_value",
        note="Use the reported consolidated inventory balance.",
    ),
    SourceMetricMapping(
        metric_code=MetricCode.CAPEX,
        statements=(StatementCode.CASH_FLOW,),
        official_row_labels=("购建固定资产、无形资产和其他长期资产支付的现金",),
        tushare_endpoint="cashflow",
        tushare_fields=("c_pay_acq_const_fiolta",),
        normal_bases=(PeriodBasis.DISCRETE, PeriodBasis.YTD),
        transform=MappingTransform.DIRECT,
        sign_convention="positive_outflow_magnitude",
        note=(
            "This is a cash-flow proxy and is not accrual additions to property, plant, and "
            "equipment."
        ),
    ),
    SourceMetricMapping(
        metric_code=MetricCode.TOTAL_DEBT,
        statements=(StatementCode.BALANCE,),
        official_row_labels=(
            "短期借款",
            "应付短期债券",
            "一年内到期的非流动负债",
            "长期借款",
            "应付债券",
            "租赁负债",
        ),
        tushare_endpoint="balancesheet",
        tushare_fields=(
            "st_borr",
            "st_bonds_payable",
            "non_cur_liab_due_1y",
            "lt_borr",
            "bond_payable",
            "lease_liab",
        ),
        normal_bases=(PeriodBasis.INSTANT,),
        transform=MappingTransform.SUM,
        sign_convention="natural_statement_value",
        note=(
            "Frozen interest-bearing debt sum; absent line items remain missing/zero only when the "
            "filing explicitly omits or reports zero, never by silent coercion."
        ),
    ),
    SourceMetricMapping(
        metric_code=MetricCode.CASH_AND_EQUIVALENTS,
        statements=(StatementCode.CASH_FLOW,),
        official_row_labels=("期末现金及现金等价物余额",),
        tushare_endpoint="cashflow",
        tushare_fields=("c_cash_equ_end_period",),
        normal_bases=(PeriodBasis.INSTANT,),
        transform=MappingTransform.DIRECT,
        sign_convention="natural_statement_value",
        note="Do not substitute balance-sheet monetary funds without a mapping revision.",
    ),
)


def mapping_for(metric_code: MetricCode) -> SourceMetricMapping:
    """Return the single frozen mapping for a canonical metric."""
    matches = tuple(
        mapping for mapping in SOURCE_METRIC_MAPPINGS if mapping.metric_code is metric_code
    )
    if len(matches) != 1:
        raise LookupError(f"expected exactly one source mapping for {metric_code.value}")
    return matches[0]
