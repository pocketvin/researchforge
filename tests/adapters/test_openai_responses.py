"""No-network tests for the OpenAI Responses adapter."""

from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from researchforge.adapters.openai_responses import OpenAIResponsesConclusionGenerator
from researchforge.application.budget import BudgetExceededError, BudgetLedger


class FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        output = {
            "executive_summary": "仅使用提供的确定性上下文。",
            "earnings_quality_text": "现金转化比来自已计算结果。",
            "gross_margin_text": "毛利率来自已计算结果。",
            "limitations": ["冻结事实范围有限。"],
            "reported_check_codes": [
                "operating_cash_flow",
                "cash_conversion",
                "profit_cash_divergence",
            ],
        }
        return SimpleNamespace(
            output_text=json.dumps(output, ensure_ascii=False),
            usage=SimpleNamespace(input_tokens=100, output_tokens=50),
        )


def test_openai_adapter_forces_store_false_schema_and_no_tools() -> None:
    responses = FakeResponses()
    ledger = BudgetLedger()
    adapter = OpenAIResponsesConclusionGenerator(responses, ledger)

    draft = adapter.generate({"cash_conversion": "1.2"})

    assert draft.executive_summary
    call = responses.calls[0]
    assert call["model"] == "gpt-5.6-luna"
    assert call["store"] is False
    assert call["tools"] == []
    assert call["reasoning"] == {"effort": "medium"}
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["strict"] is True
    assert ledger.snapshot().spent > Decimal(0)


def test_budget_guard_stops_before_provider_contact() -> None:
    responses = FakeResponses()
    adapter = OpenAIResponsesConclusionGenerator(
        responses,
        BudgetLedger(Decimal("0.000001")),
    )

    with pytest.raises(BudgetExceededError):
        adapter.generate({"cash_conversion": "1.2"})

    assert responses.calls == []
