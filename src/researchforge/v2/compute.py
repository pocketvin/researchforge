"""Financial meaning remains local; models supply source IDs, never raw
operands."""

from __future__ import annotations

from decimal import Decimal

from researchforge.adapters.storage import payload_sha256
from researchforge.domain.finance import (
    absolute_change,
    cash_conversion,
    gross_margin,
    gross_profit,
    growth_rate,
)
from researchforge.v2.contracts import CalculateInput, Json

FORMULAS = {
    ("growth_rate"): (
        "(current - comparison) / comparison; identical metric and "
        "comparable fiscal periods; positive base only"
    ),
    "absolute_change": "current - comparison; identical metric and comparable fiscal periods",
    "gross_profit": "revenue - operating_cost; identical fiscal period and scope",
    "gross_margin": "(revenue - operating_cost) / revenue; identical fiscal period and scope",
    ("cash_conversion"): (
        "operating_cash_flow / net_income; identical fiscal period and "
        "scope; positive net income only"
    ),
}


def calculate(request: CalculateInput, facts: dict[str, Json]) -> Json:
    if any(identifier not in facts for identifier in request.fact_ids):
        raise ValueError("calculation requires existing run-owned verified fact IDs")
    left, right = (facts[identifier] for identifier in request.fact_ids)
    for key in ("currency", "measurement_unit"):
        if left[key] != right[key]:
            raise ValueError(f"incompatible {key}")
    if left["company"]["company_id"] != right["company"]["company_id"]:
        raise ValueError("cross-company arithmetic is not enabled")
    lp, rp = left["period"], right["period"]
    for key in ("accounting_standard", "statement_scope", "restatement_status", "period_basis"):
        if lp.get(key) != rp.get(key):
            raise ValueError(f"incompatible period semantics: {key}")
    comparison = request.formula in {"growth_rate", "absolute_change"}
    if comparison:
        if left["metric_code"] != right["metric_code"]:
            raise ValueError("change calculations require the same metric")
        if lp.get("fiscal_period") != rp.get("fiscal_period"):
            raise ValueError("different fiscal periods cannot be compared by this formula")
        if (
            not lp.get("period_end")
            or not rp.get("period_end")
            or lp["period_end"] <= rp["period_end"]
        ):
            raise ValueError("current period must follow the comparison period")
    elif any(
        lp.get(key) != rp.get(key)
        for key in ("period_start", "period_end", "fiscal_year", "fiscal_period")
    ):
        raise ValueError("ratio operands must use the same reporting period")
    a, b = Decimal(left["value"]), Decimal(right["value"])
    if not a.is_finite() or not b.is_finite():
        raise ValueError("non-finite financial operand")
    if request.formula in {"gross_profit", "gross_margin"}:
        if (left["metric_code"], right["metric_code"]) != ("revenue", "operating_cost"):
            raise ValueError("supply revenue then operating_cost")
        result = (
            gross_profit(a, b) if request.formula == ("gross_profit") else gross_margin(a - b, a)
        )
    elif request.formula == "cash_conversion":
        if (left["metric_code"], right["metric_code"]) != ("operating_cash_flow", "net_income"):
            raise ValueError("supply operating_cash_flow then net_income")
        result = cash_conversion(a, b)
    elif request.formula == "growth_rate":
        result = growth_rate(a, b)
    else:
        result = absolute_change(a, b)
    payload = {
        "schema_version": "2.0.0",
        "formula_code": request.formula,
        "formula_version": "v2-wrapper-1/domain-1.0.0",
        "input_fact_ids": request.fact_ids,
        "input_values": [left["value"], right["value"]],
        "period": lp,
        "comparison_period": rp if comparison else None,
        "currency": left["currency"],
        "status": result.status.value,
        "value": format(result.value, "f") if result.value is not None else None,
        "measurement_unit": result.measurement_unit.value if result.measurement_unit else None,
        "explanation": result.explanation,
    }
    payload["calculation_id"] = "calc_" + payload_sha256(payload)[:24]
    return payload
