"""Deterministic statement-row extraction and calculations over verified native-text series."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import TypedDict

from researchforge.adapters.storage import payload_sha256
from researchforge.v2.contracts import Json, SeriesCalculateInput, SeriesExtractInput


class SeriesMetricDefinition(TypedDict):
    aliases: tuple[str, ...]
    sign: str


SERIES_METRICS: dict[str, SeriesMetricDefinition] = {
    "revenue": {
        "aliases": (
            "revenue",
            "revenues",
            "total net revenues",
            "net revenues",
            "sales",
            "营业收入",
            "营业总收入",
            "营收",
        ),
        "sign": "reported",
    },
    "capital_expenditures": {
        "aliases": (
            "capex",
            "capital expenditures",
            "capital expenditure",
            "purchases of property, plant and equipment",
            "purchases of property plant and equipment",
            "资本开支",
            "资本支出",
            "购建固定资产无形资产和其他长期资产支付的现金",
        ),
        "sign": "absolute",
    },
    "net_income": {
        "aliases": (
            "net income",
            "net profit",
            "net earnings",
            "净利润",
            "归母净利润",
        ),
        "sign": "reported",
    },
    "operating_cash_flow": {
        "aliases": (
            "net cash provided by operating activities",
            "net cash from operating activities",
            "operating cash flow",
            "经营活动产生的现金流量净额",
            "经营活动现金流量净额",
            "经营现金流",
        ),
        "sign": "reported",
    },
    "total_assets": {
        "aliases": ("total assets", "总资产", "资产总额"),
        "sign": "reported",
    },
    "fixed_assets": {
        "aliases": (
            "property, plant and equipment net",
            "property plant and equipment net",
            "fixed assets",
            "固定资产",
            "固定资产净额",
        ),
        "sign": "reported",
    },
    "accounts_receivable": {
        "aliases": ("accounts receivable", "trade receivables", "应收账款"),
        "sign": "reported",
    },
    "inventory": {
        "aliases": ("inventories", "inventory", "存货"),
        "sign": "reported",
    },
}

SERIES_FORMULAS = {
    "ratio_percent": (
        "For one requested matching fiscal period, numerator / denominator * 100. "
        "Operands must share company, currency and unit scale."
    ),
    "average_ratio_percent": (
        "For matching periods, numerator / denominator * 100 for each period, then arithmetic "
        "mean; operands must share company, currency, unit scale and period set."
    ),
    "flow_to_average_balance_percent": (
        "For one requested fiscal period, flow numerator / average(current, prior) balance * 100. "
        "Use for return metrics such as ROA when the numerator is net income and the balance is "
        "total assets. Operands must share company, currency and unit scale."
    ),
    "average_balance_to_flow_percent": (
        "For one requested fiscal period, average(current, prior) balance / period flow * 100. "
        "Use for capital-intensity measures such as average net PP&E / revenue or average total "
        "assets / revenue. Pass the balance series first and the flow series second."
    ),
    "average": "Arithmetic mean of one verified series over all its periods.",
    "sum": "Arithmetic sum of one verified series over all its periods.",
}

_YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
_NUMBER_RE = re.compile(r"\(?[-+]?\d[\d,]*(?:\.\d+)?\)?")


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value.casefold()).strip()


def _parse_number(token: str) -> Decimal:
    probe = token.strip()
    negative = probe.startswith("(") and probe.endswith(")")
    if negative:
        probe = probe[1:-1]
    probe = probe.replace(",", "")
    value = Decimal(probe)
    if not value.is_finite():
        raise ValueError("statement row contains a non-finite number")
    return -value if negative else value


def _unit_scale(lines: list[str]) -> tuple[int, str]:
    """Read only explicit statement unit headers; never infer scale from value magnitude."""
    head = " ".join(lines).casefold()
    scales = (
        ("billions", 1_000_000_000),
        ("millions", 1_000_000),
        ("thousands", 1_000),
    )
    for label, scale in scales:
        explicit_patterns = (
            rf"\b(?:amounts|dollars)\s+in\s+{label}\b",
            rf"\bin\s+{label}\b",
            # Common SEC presentation: `(Millions)` or
            # `(Millions, except per share amounts)`.
            rf"\(\s*{label}\b",
        )
        if any(re.search(pattern, head) for pattern in explicit_patterns):
            return scale, label
    chinese_unit = re.search(
        r"单位\s*[\uFF1A:]?\s*(?:人民币)?\s*(亿元|百万元|万元|千元|元)",
        " ".join(lines),
    )
    if chinese_unit:
        label = chinese_unit.group(1)
        scale = {
            "亿元": 100_000_000,
            "百万元": 1_000_000,
            "万元": 10_000,
            "千元": 1_000,
            "元": 1,
        }[label]
        return scale, label
    return 1, "units"


def _currency(page_text: str, document: Json) -> str | None:
    probe = page_text.casefold()
    if "hk$" in probe or "hong kong dollars" in probe:
        return "HKD"
    if "rmb" in probe or "renminbi" in probe or "人民币" in page_text:
        return "CNY"
    company = document.get("company", {})
    market = str(company.get("market") or company.get("country_code") or "").upper()
    if "$" in page_text and market == "US":
        return "USD"
    if market == "CN":
        return "CNY"
    if market == "HK":
        return "HKD"
    return None


def extract_statement_series(request: SeriesExtractInput, source: Json, document: Json) -> Json:
    source_kind = str(source.get("kind") or "")
    if source_kind not in {"page", "table"}:
        raise ValueError("statement series requires a native page or HTML table artifact")
    text = str(source.get("text") or "")
    if not text.strip():
        raise ValueError(
            "source has no native text; inspect the image but do not promote visual numbers"
        )
    definition = SERIES_METRICS[request.metric_code]
    row_norm = _norm(request.row_label)
    aliases = tuple(_norm(str(item)) for item in definition["aliases"])
    if not any(alias in row_norm or row_norm in alias for alias in aliases):
        raise ValueError("row label does not match the requested financial metric semantics")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    matches = [
        (index, line) for index, line in enumerate(lines) if _norm(line).startswith(row_norm)
    ]
    if len(matches) != 1:
        raise ValueError(f"row label must resolve uniquely on the page; candidates={len(matches)}")
    row_index, row_line = matches[0]
    # Remove only the leading row label. Numeric note references inside the label therefore never
    # become values, while numeric statement values remain available for deterministic parsing.
    prefix_match = re.match(re.escape(request.row_label), row_line, flags=re.IGNORECASE)
    if prefix_match is None:
        # Punctuation/spacing may normalize away. Use the normalized prefix length only when the
        # human-readable row still starts with all row-label words in order.
        words = [
            re.escape(word)
            for word in re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", request.row_label)
        ]
        pattern = r"^\s*" + r"[^A-Za-z0-9\u4e00-\u9fff]+".join(words)
        prefix_match = re.match(pattern, row_line, flags=re.IGNORECASE)
    if prefix_match is None:
        raise ValueError("could not isolate the requested row label from statement values")
    suffix = row_line[prefix_match.end() :]
    raw_tokens = _NUMBER_RE.findall(suffix)
    if not raw_tokens:
        raise ValueError("statement row contains no numeric values")

    header_index: int | None = None
    years: list[int] = []
    for index in range(row_index - 1, -1, -1):
        candidate_years = [int(value) for value in _YEAR_RE.findall(lines[index])]
        if len(candidate_years) == len(raw_tokens) and len(set(candidate_years)) == len(
            candidate_years
        ):
            header_index = index
            years = candidate_years
            break
    if header_index is None:
        raise ValueError("could not uniquely map statement values to fiscal-year headers")

    context_text = str(source.get("context_text") or "") if source_kind == "table" else ""
    context_lines = [line.strip() for line in context_text.splitlines() if line.strip()]
    # Unit/currency text can live either in the nearest HTML caption *or inside the table itself*.
    # Keep both bounded: enough nearest external context for captions, plus a small window around
    # the resolved fiscal-year header. Previously 20 context lines could consume the entire scan
    # budget and hide an explicit `(Dollars in thousands)` line in the table, incorrectly turning
    # a thousand-dollar series into unscaled units.
    statement_context = lines[max(0, header_index - 8) : min(len(lines), header_index + 9)]
    scale_lines = context_lines[-12:] + statement_context
    scale, scale_label = _unit_scale(scale_lines)
    currency = _currency("\n".join(scale_lines), document)
    sign_policy = str(definition["sign"])
    values: list[Json] = []
    for year, token in zip(years, raw_tokens, strict=True):
        try:
            parsed = _parse_number(token)
        except InvalidOperation as exc:
            raise ValueError("statement row contains an invalid decimal") from exc
        normalized = abs(parsed) if sign_policy == "absolute" else parsed
        values.append(
            {
                "fiscal_year": year,
                "fiscal_period": "FY",
                "period_label": f"{year}FY",
                "raw_token": token,
                "display_value": format(parsed, "f"),
                "normalized_value": format(normalized, "f"),
                "base_unit_value": format(normalized * Decimal(scale), "f"),
            }
        )

    excerpt = "\n".join(lines[header_index : row_index + 1])
    payload: Json = {
        "schema_version": "2.0.0",
        "metric_code": request.metric_code,
        "row_label": request.row_label,
        "sign_policy": sign_policy,
        "document_id": source["document_id"],
        "source_artifact_id": source["artifact_id"],
        "source_kind": source_kind,
        "page_id": source["artifact_id"] if source_kind == "page" else source.get("page_id"),
        "page_number": source.get("page_number"),
        "currency": currency,
        "measurement_unit": "CURRENCY",
        "canonical_scale": scale,
        "scale_label": scale_label,
        "values": values,
        "source_excerpt": excerpt,
        "verification_status": (
            "deterministic_native_page_text_row_and_header"
            if source_kind == "page"
            else "deterministic_native_html_table_row_header_and_context"
        ),
        "source_content_hash": document.get("content_hash"),
    }
    payload["series_id"] = "series_" + payload_sha256(payload)[:24]
    return payload


def calculate_series_metric(request: SeriesCalculateInput, series: dict[str, Json]) -> Json:
    if any(identifier not in series for identifier in request.series_ids):
        raise ValueError("series calculation requires run-owned verified series IDs")
    items = [series[identifier] for identifier in request.series_ids]
    if request.formula in {
        "ratio_percent",
        "average_ratio_percent",
        "flow_to_average_balance_percent",
        "average_balance_to_flow_percent",
    }:
        if len(items) != 2:
            raise ValueError(f"{request.formula} requires numerator and denominator series")
        numerator, denominator = items
        for key in ("document_id", "currency", "canonical_scale", "measurement_unit"):
            if numerator.get(key) != denominator.get(key):
                raise ValueError(f"incompatible series semantics: {key}")
        num_by_period = {
            item["period_label"]: Decimal(item["normalized_value"]) for item in numerator["values"]
        }
        den_by_period = {
            item["period_label"]: Decimal(item["normalized_value"])
            for item in denominator["values"]
        }
        common_periods = set(num_by_period) & set(den_by_period)
        if not common_periods:
            raise ValueError("ratio series must share at least one fiscal period")
        if request.formula in {
            "flow_to_average_balance_percent",
            "average_balance_to_flow_percent",
        }:
            if request.period_label is None:
                raise ValueError(f"{request.formula} requires period_label")
            flow_series, balance_series = (
                (numerator, denominator)
                if request.formula == "flow_to_average_balance_percent"
                else (denominator, numerator)
            )
            flow_value_item = next(
                (
                    item
                    for item in flow_series["values"]
                    if item["period_label"] == request.period_label
                ),
                None,
            )
            current_balance = next(
                (
                    item
                    for item in balance_series["values"]
                    if item["period_label"] == request.period_label
                ),
                None,
            )
            if flow_value_item is None or current_balance is None:
                raise ValueError("requested fiscal period must exist in flow and balance series")
            current_year = int(current_balance["fiscal_year"])
            fiscal_period = str(current_balance["fiscal_period"])
            prior_balance = next(
                (
                    item
                    for item in balance_series["values"]
                    if int(item["fiscal_year"]) == current_year - 1
                    and str(item["fiscal_period"]) == fiscal_period
                ),
                None,
            )
            if prior_balance is None:
                raise ValueError(
                    "average-balance calculation requires the immediately prior period"
                )
            flow_value = Decimal(flow_value_item["normalized_value"])
            current_value = Decimal(current_balance["normalized_value"])
            prior_value = Decimal(prior_balance["normalized_value"])
            average_balance = (current_value + prior_value) / Decimal(2)
            if average_balance <= 0:
                raise ValueError("average balance must be positive")
            if flow_value == 0:
                raise ValueError("flow value cannot be zero")
            exact = (
                flow_value / average_balance * Decimal(100)
                if request.formula == "flow_to_average_balance_percent"
                else average_balance / flow_value * Decimal(100)
            )
            quantizer = Decimal(1).scaleb(-request.round_decimals)
            rounded = exact.quantize(quantizer, rounding=ROUND_HALF_UP)
            result: Json = {
                "status": "valid",
                "value": format(rounded, "f"),
                "unrounded_value": format(exact, "f"),
                "measurement_unit": "PERCENT",
                "per_period": [
                    {
                        "period_label": request.period_label,
                        "value_percent": format(exact, "f"),
                        "flow_value": format(flow_value, "f"),
                        "average_balance": format(average_balance, "f"),
                    }
                ],
                "explanation": (
                    "Requested-period flow divided by average current/prior balance."
                    if request.formula == "flow_to_average_balance_percent"
                    else "Average current/prior balance divided by requested-period flow."
                ),
            }
        else:
            if request.formula == "average_ratio_percent" and set(num_by_period) != set(
                den_by_period
            ):
                raise ValueError("average ratio series must cover the same fiscal periods")
            if request.formula == "ratio_percent":
                if request.period_label is not None:
                    if request.period_label not in common_periods:
                        raise ValueError(
                            "requested ratio period is not present in both verified series"
                        )
                    selected_periods = [request.period_label]
                elif len(common_periods) == 1:
                    selected_periods = list(common_periods)
                else:
                    raise ValueError(
                        "ratio_percent requires period_label when multiple periods exist"
                    )
            else:
                if request.period_label is not None:
                    raise ValueError("average_ratio_percent does not accept a single period_label")
                selected_periods = sorted(common_periods, reverse=True)
            ratios: list[Json] = []
            exact_values: list[Decimal] = []
            for period in selected_periods:
                denominator_value = den_by_period[period]
                if denominator_value == 0:
                    raise ValueError("ratio denominator cannot be zero")
                ratio = num_by_period[period] / denominator_value * Decimal(100)
                exact_values.append(ratio)
                ratios.append({"period_label": period, "value_percent": format(ratio, "f")})
            exact = (
                exact_values[0]
                if request.formula == "ratio_percent"
                else sum(exact_values, Decimal(0)) / Decimal(len(exact_values))
            )
            quantizer = Decimal(1).scaleb(-request.round_decimals)
            rounded = exact.quantize(quantizer, rounding=ROUND_HALF_UP)
            result = {
                "status": "valid",
                "value": format(rounded, "f"),
                "unrounded_value": format(exact, "f"),
                "measurement_unit": "PERCENT",
                "per_period": ratios,
                "explanation": (
                    "Requested-period numerator/denominator percentage."
                    if request.formula == "ratio_percent"
                    else "Average of period-by-period numerator/denominator percentages."
                ),
            }
    else:
        if len(items) != 1:
            raise ValueError(f"{request.formula} requires exactly one series")
        values = [Decimal(item["normalized_value"]) for item in items[0]["values"]]
        if not values:
            raise ValueError("series contains no values")
        exact = sum(values, Decimal(0))
        if request.formula == "average":
            exact /= Decimal(len(values))
        quantizer = Decimal(1).scaleb(-request.round_decimals)
        rounded = exact.quantize(quantizer, rounding=ROUND_HALF_UP)
        result = {
            "status": "valid",
            "value": format(rounded, "f"),
            "unrounded_value": format(exact, "f"),
            "measurement_unit": items[0].get("measurement_unit"),
            "currency": items[0].get("currency"),
            "canonical_scale": items[0].get("canonical_scale"),
            "explanation": f"Deterministic {request.formula} over verified statement series.",
        }
    payload: Json = {
        "schema_version": "2.0.0",
        "formula_code": request.formula,
        "formula_version": "statement-series-1.0.0",
        "input_series_ids": request.series_ids,
        "round_decimals": request.round_decimals,
        "period_label": request.period_label,
        **result,
    }
    payload["calculation_id"] = "calc_" + payload_sha256(payload)[:24]
    return payload
