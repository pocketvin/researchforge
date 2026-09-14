"""Deterministic provenance checks for percentages mentioned in public research artifacts."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Literal, TypedDict

from researchforge.v2.contracts import Json

# Do not consume a hyphen that belongs to a lexical comparator such as ``sub-20%``. Starting the
# match at ``20`` lets the prefix classifier recover ``sub-`` as comparison semantics instead of
# incorrectly treating the threshold as negative twenty percent. Native filing-table text keeps
# cell separators, so ``18.3 | %`` is the same reported percentage as ``18.3%``. Parenthesized
# table values such as ``(46.9) | %`` retain accounting-negative semantics.
_PERCENT_RE = re.compile(
    r"(?<![A-Za-z0-9_.])(?P<open>\()?(?P<number>[-+]?\d[\d,]*(?:\.\d+)?)"
    # Native HTML cell expansion can place a separator *inside* accounting parentheses,
    # e.g. ``(5.7 | )%``. Accept a bounded cell separator on either side of the close paren so
    # filing-reported negative percentages are not mistaken for model-derived arithmetic.
    r"(?:\s*\|\s*)?(?P<close>\))?(?:\s*\|\s*)?\s*%"
)
_TABLE_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9])(?P<open>\()?(?P<number>[-+]?\d[\d,]*(?:\.\d+)?)(?P<close>\))?"
    r"(?![A-Za-z0-9])"
)
_APPROX_PREFIX_RE = re.compile(
    r"(?:约|大约|大致|接近|近似|左右|around|about|approximately|approx\.?|roughly)\s*$",
    re.IGNORECASE,
)
_LT_PREFIX_RE = re.compile(
    r"(?:<|低于|少于|小于|less\s+than|below|under|sub-)\s*$",
    re.IGNORECASE,
)
_LTE_PREFIX_RE = re.compile(
    r"(?:<=|≤|不超过|至多|at\s+most|no\s+more\s+than)\s*$",
    re.IGNORECASE,
)
_GT_PREFIX_RE = re.compile(
    r"(?:>|高于|多于|大于|more\s+than|above|over)\s*$",
    re.IGNORECASE,
)
_GTE_PREFIX_RE = re.compile(
    r"(?:>=|≥|不少于|至少|at\s+least|no\s+less\s+than)\s*$",
    re.IGNORECASE,
)
_DECREASE_PREFIX_RE = re.compile(
    r"(?:down(?:\s+by)?|decreased(?:\s+by)?|declined(?:\s+by)?|fell(?:\s+by)?|"
    r"dropped(?:\s+by)?|下降|减少|降低|下跌)\s*$",
    re.IGNORECASE,
)
_DECREASE_SUFFIX_RE = re.compile(
    # Bind suffix direction to the percentage's own short label (``21% Softseed EBIT decline``),
    # but never cross clause punctuation or another numeric amount (``4.28%, primarily related
    # to a 46 bp decrease``). Crossing either boundary can silently flip an unrelated percentage.
    r"^[^.!?;,%0-9]{0,40}(?:decline|decrease|drop|fall|下降|减少|降低|下跌)\b",
    re.IGNORECASE,
)

PercentageSemantic = Literal["exact", "approximate", "comparison"]
ComparisonRelation = Literal["lt", "lte", "gt", "gte"]


class PercentageMention(TypedDict):
    raw: str
    value: Decimal
    decimal_places: int
    semantic: PercentageSemantic
    relation: ComparisonRelation | None


def _decimal(value: object) -> Decimal | None:
    try:
        parsed = Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _comparison_relation(prefix: str) -> ComparisonRelation | None:
    # Test the longer/non-strict variants first so ``<=`` is not classified as ``<``.
    for relation, pattern in (
        ("lte", _LTE_PREFIX_RE),
        ("gte", _GTE_PREFIX_RE),
        ("lt", _LT_PREFIX_RE),
        ("gt", _GT_PREFIX_RE),
    ):
        if pattern.search(prefix):
            return relation  # type: ignore[return-value]
    return None


def percentage_mentions(text: str) -> list[PercentageMention]:
    mentions: list[PercentageMention] = []
    for match in _PERCENT_RE.finditer(text):
        token = match.group("number")
        value = _decimal(token)
        if value is None:
            continue
        if match.group("open") and match.group("close") and value > 0:
            value = -value
        normalized = token.replace(",", "")
        decimals = len(normalized.rsplit(".", 1)[1]) if "." in normalized else 0
        prefix = text[max(0, match.start() - 36) : match.start()]
        suffix = text[match.end() : match.end() + 48]
        if value > 0 and (_DECREASE_PREFIX_RE.search(prefix) or _DECREASE_SUFFIX_RE.search(suffix)):
            value = -value
        relation = _comparison_relation(prefix)
        if relation is not None:
            semantic: PercentageSemantic = "comparison"
        elif _APPROX_PREFIX_RE.search(prefix):
            semantic = "approximate"
        else:
            semantic = "exact"
        mentions.append(
            {
                "raw": match.group(0),
                "value": value,
                "decimal_places": decimals,
                "semantic": semantic,
                "relation": relation,
            }
        )
    return mentions


def reported_percentage_values(text: str) -> list[Decimal]:
    """Recover exact/approximate percentages explicitly reported by filing text.

    Comparison thresholds are intentionally excluded from the bare numeric pool. ``below 20%``
    does not prove an exact 20% observation; its relation is checked separately. PDF table
    extraction sometimes prints the percent sign only on selected rows while a dedicated table
    header states ``(Percent of ...)`` or ``Percent Change in Net Sales``. In those narrow,
    percent-only table contexts, nearby numeric cells are treated as reported percentages without
    performing financial arithmetic. Rows containing a currency marker are excluded from this
    fallback so a dollar change cannot accidentally authorize an identically-valued percentage.
    """
    values = [
        mention["value"]
        for mention in percentage_mentions(text)
        if mention["semantic"] != "comparison"
    ]
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    header_indexes = [
        index
        for index, line in enumerate(lines)
        if (
            "percent of" in line.casefold()
            or "percentage of" in line.casefold()
            or "percent change in net sales" in line.casefold()
        )
    ]
    for header_index in header_indexes:
        for line in lines[header_index + 1 : header_index + 12]:
            if "$" in line:
                continue
            for match in _TABLE_NUMBER_RE.finditer(line):
                token = match.group("number")
                value = _decimal(token)
                if value is None:
                    continue
                if match.group("open") and match.group("close") and value > 0:
                    value = -value
                # Exclude fiscal years and obviously non-percentage magnitudes. The surrounding
                # table header, not this bound, provides the percentage semantics.
                if value == value.to_integral_value() and Decimal(1900) <= value <= Decimal(2100):
                    continue
                if abs(value) <= Decimal(1000):
                    values.append(value)
    return values


def reported_comparison_mentions(text: str) -> list[PercentageMention]:
    return [mention for mention in percentage_mentions(text) if mention["semantic"] == "comparison"]


def calculation_percentage_values(calculations: list[Json]) -> list[Decimal]:
    values: list[Decimal] = []
    for calculation in calculations:
        if calculation.get("measurement_unit") != "PERCENT":
            continue
        for key in ("value", "unrounded_value"):
            value = _decimal(calculation.get(key))
            if value is not None:
                values.append(value)
        per_period = calculation.get("per_period", [])
        if isinstance(per_period, list):
            for item in per_period:
                if not isinstance(item, dict):
                    continue
                value = _decimal(item.get("value_percent"))
                if value is not None:
                    values.append(value)
    return values


def fact_percentage_values(facts: list[Json]) -> list[Decimal]:
    values: list[Decimal] = []
    for fact in facts:
        if fact.get("measurement_unit") != "PERCENT":
            continue
        value = _decimal(fact.get("value"))
        if value is not None:
            values.append(value)
    return values


def _same_display_value(mention: PercentageMention, candidate: Decimal) -> bool:
    quantizer = Decimal(1).scaleb(-mention["decimal_places"])
    try:
        return candidate.quantize(quantizer, rounding=ROUND_HALF_UP) == mention["value"]
    except InvalidOperation:
        return False


def percentage_supported(
    mention: PercentageMention,
    candidates: list[Decimal],
    reported_comparisons: list[PercentageMention] | None = None,
) -> bool:
    if mention["semantic"] == "comparison":
        # A comparison threshold carries meaning beyond the observed ratio itself. A 19.76%
        # calculation can support ``约20%`` after display rounding, but it does not establish that
        # ``sub-20%`` is a meaningful threshold. Comparison claims therefore require the same
        # relation to be directly present in cited filing evidence.
        return any(
            reported["relation"] == mention["relation"]
            and _same_display_value(mention, reported["value"])
            for reported in reported_comparisons or []
        )
    return any(_same_display_value(mention, candidate) for candidate in candidates)


def unsupported_percentages(
    text: str,
    *,
    calculations: list[Json],
    facts: list[Json],
    evidence: list[Json],
) -> list[str]:
    candidates = calculation_percentage_values(calculations)
    candidates.extend(fact_percentage_values(facts))
    comparisons: list[PercentageMention] = []
    for item in evidence:
        source_text = str(item.get("text", ""))
        candidates.extend(reported_percentage_values(source_text))
        comparisons.extend(reported_comparison_mentions(source_text))
    return [
        mention["raw"]
        for mention in percentage_mentions(text)
        if not percentage_supported(mention, candidates, comparisons)
    ]
