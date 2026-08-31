"""Regression tests for the frozen source-line mapping."""

from __future__ import annotations

import re

import pytest

from researchforge.domain.models import MetricCode, PeriodBasis
from researchforge.domain.source_mapping import (
    SOURCE_MAPPING_VERSION,
    SOURCE_METRIC_MAPPINGS,
    MappingTransform,
    mapping_for,
)


def test_mapping_version_is_semantic() -> None:
    assert re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", SOURCE_MAPPING_VERSION)


def test_every_canonical_metric_has_exactly_one_mapping() -> None:
    mapped = [mapping.metric_code for mapping in SOURCE_METRIC_MAPPINGS]
    assert set(mapped) == set(MetricCode)
    assert len(mapped) == len(set(mapped))


@pytest.mark.parametrize(
    "metric",
    [
        MetricCode.ACCOUNTS_RECEIVABLE,
        MetricCode.INVENTORY,
        MetricCode.TOTAL_DEBT,
        MetricCode.CASH_AND_EQUIVALENTS,
    ],
)
def test_balance_metrics_use_instant_basis(metric: MetricCode) -> None:
    assert mapping_for(metric).normal_bases == (PeriodBasis.INSTANT,)


@pytest.mark.parametrize(
    "metric",
    [
        MetricCode.REVENUE,
        MetricCode.OPERATING_COST,
        MetricCode.NET_INCOME,
        MetricCode.GROSS_PROFIT,
        MetricCode.GROSS_MARGIN,
        MetricCode.OPERATING_CASH_FLOW,
        MetricCode.CAPEX,
    ],
)
def test_flow_metrics_allow_discrete_and_ytd(metric: MetricCode) -> None:
    assert mapping_for(metric).normal_bases == (
        PeriodBasis.DISCRETE,
        PeriodBasis.YTD,
    )


def test_reconciliation_fields_match_provider_documentation() -> None:
    assert mapping_for(MetricCode.REVENUE).tushare_fields == ("revenue",)
    assert mapping_for(MetricCode.OPERATING_COST).tushare_fields == ("oper_cost",)
    assert mapping_for(MetricCode.NET_INCOME).tushare_fields == ("n_income_attr_p",)
    assert mapping_for(MetricCode.OPERATING_CASH_FLOW).tushare_fields == ("n_cashflow_act",)
    assert mapping_for(MetricCode.ACCOUNTS_RECEIVABLE).tushare_fields == ("accounts_receiv",)
    assert mapping_for(MetricCode.INVENTORY).tushare_fields == ("inventories",)
    assert mapping_for(MetricCode.CAPEX).tushare_fields == ("c_pay_acq_const_fiolta",)


def test_total_debt_mapping_is_explicit_and_excludes_trade_payables() -> None:
    mapping = mapping_for(MetricCode.TOTAL_DEBT)
    assert mapping.transform is MappingTransform.SUM
    assert mapping.tushare_fields == (
        "st_borr",
        "st_bonds_payable",
        "non_cur_liab_due_1y",
        "lt_borr",
        "bond_payable",
        "lease_liab",
    )
    assert not {"notes_payable", "acct_payable", "oth_payable"} & set(mapping.tushare_fields)


def test_cash_equivalents_does_not_silently_use_monetary_funds() -> None:
    mapping = mapping_for(MetricCode.CASH_AND_EQUIVALENTS)
    assert mapping.tushare_fields == ("c_cash_equ_end_period",)
    assert "money_cap" not in mapping.tushare_fields


def test_mapping_objects_are_frozen() -> None:
    with pytest.raises(AttributeError):
        mapping_for(MetricCode.REVENUE).note = "changed"  # type: ignore[misc]
