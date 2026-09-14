"""Product-level request policy shared by every ResearchForge surface."""

from __future__ import annotations

import re


class UnsupportedCapabilityError(ValueError):
    """Raised before queueing a request outside the research-assistance boundary."""


_PROHIBITED_ADVICE_MARKERS = (
    "目标价",
    "股价预测",
    "买入建议",
    "卖出建议",
    "值不值得买",
    "该不该买",
    "该不该卖",
    "建议买入",
    "建议卖出",
    "投资建议",
    "推荐股票",
    "price target",
    "investment recommendation",
    "should i buy",
    "should i sell",
    "recommend buying",
    "recommend selling",
)


def enforce_research_question_policy(question: str) -> None:
    """Reject requests that cross into trading/advice rather than filing research."""
    lowered = question.casefold()
    if any(marker in lowered for marker in _PROHIBITED_ADVICE_MARKERS):
        raise UnsupportedCapabilityError(
            "ResearchForge provides research assistance, not investment advice, "
            "buy/sell recommendations, or price targets"
        )
    if re.search(r"\b(?:buy|sell)\s+(?:this|the)\s+(?:stock|share)\b", lowered):
        raise UnsupportedCapabilityError(
            "ResearchForge provides research assistance, not investment advice, "
            "buy/sell recommendations, or price targets"
        )
