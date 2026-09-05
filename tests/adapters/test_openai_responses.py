"""No-network tests for the OpenAI Responses adapter."""

# ruff: noqa: RUF001 -- Chinese research prose is intentional test data.

from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from researchforge.adapters.openai_responses import OpenAIResponsesConclusionGenerator
from researchforge.application.budget import BudgetExceededError, BudgetLedger
from researchforge.application.research import GeneralResearchDraft


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


class FakeGeneralResponses(FakeResponses):
    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        output = {
            "executive_summary": (
                "公司当前经营表现稳定，但增长结构出现分化，需要同时关注现金质量与业务风险。"
            ),
            "findings": [
                {
                    "title": "核心业务仍是主要收入来源",
                    "text": "官方分部披露显示核心业务贡献了主要收入，业务集中度仍然较高。",
                    "evidence_ids": ["chunk_business"],
                    "fact_ids": ["fact_revenue"],
                    "claim_type": "observation",
                    "epistemic_status": "supported_inference",
                    "confidence": "high",
                    "direction": "neutral",
                },
                {
                    "title": "现金质量需要结合利润继续观察",
                    "text": "经营现金流与利润均可核验，但单一报告期不足以判断长期趋势。",
                    "evidence_ids": ["chunk_cash"],
                    "fact_ids": ["fact_ocf", "fact_profit"],
                    "claim_type": "earnings_quality",
                    "epistemic_status": "supported_inference",
                    "confidence": "medium",
                    "direction": "mixed",
                },
            ],
            "deep_analysis": [
                {
                    "title": "业绩与增长",
                    "text": "收入表现需要结合业务结构与管理层解释共同判断。",
                    "evidence_ids": ["chunk_business"],
                },
                {
                    "title": "盈利与现金流",
                    "text": "现金流与利润的关系是收益质量判断的主要约束。",
                    "evidence_ids": ["chunk_cash"],
                },
            ],
            "limitations": ["当前仅覆盖本次提供的官方披露证据。"],
            "suggested_follow_ups": [
                "增长来自哪些业务？",
                "毛利率发生了什么变化？",
                "主要风险是什么？",
                "管理层如何看未来？",
            ],
            "overall_judgment": "Mixed",
            "overall_judgment_rationale": "经营基础仍有支撑，但单期证据不足以确认增长持续性。",
        }
        return SimpleNamespace(
            output_text=json.dumps(output, ensure_ascii=False),
            usage=SimpleNamespace(input_tokens=300, output_tokens=200),
        )


class FailingResponses:
    def create(self, **kwargs: Any) -> Any:
        del kwargs
        raise ConnectionError("indeterminate transport failure")


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


def test_indeterminate_provider_failure_consumes_full_reservation() -> None:
    ledger = BudgetLedger()
    adapter = OpenAIResponsesConclusionGenerator(FailingResponses(), ledger)

    with pytest.raises(ConnectionError, match="indeterminate transport"):
        adapter.generate({"cash_conversion": "1.2"})

    snapshot = ledger.snapshot()
    assert snapshot.reserved == Decimal(0)
    assert snapshot.spent == adapter.worst_case_cost


def test_openai_adapter_validates_general_research_synthesis_contract() -> None:
    responses = FakeGeneralResponses()
    adapter = OpenAIResponsesConclusionGenerator(responses, BudgetLedger())

    draft = adapter.generate(
        {
            "response_contract": "general_research_v1_7",
            "selected_evidence": [
                {"chunk_id": "chunk_business"},
                {"chunk_id": "chunk_cash"},
            ],
            "counter_evidence": {"evidence_ids": ["chunk_counter"]},
            "financial_facts": [
                {"fact_id": "fact_revenue"},
                {"fact_id": "fact_ocf"},
                {"fact_id": "fact_profit"},
            ],
        }
    )

    assert isinstance(draft, GeneralResearchDraft)
    assert draft.executive_summary.startswith("公司当前经营表现稳定")
    assert draft.findings[0].claim_type == "observation"
    assert draft.findings[1].epistemic_status == "supported_inference"
    assert draft.overall_judgment_rationale.startswith("经营基础")
    call = responses.calls[0]
    assert call["text"]["format"]["name"] == "researchforge_general_research_draft"
    schema = call["text"]["format"]["schema"]
    assert "overall_judgment_rationale" in schema["properties"]
    assert "claim_type" in schema["$defs"]["GeneralFindingDraft"]["properties"]
    finding_props = schema["$defs"]["GeneralFindingDraft"]["properties"]
    analysis_props = schema["$defs"]["GeneralAnalysisSectionDraft"]["properties"]
    assert finding_props["evidence_ids"]["items"]["enum"] == [
        "chunk_business",
        "chunk_cash",
        "chunk_counter",
    ]
    assert analysis_props["evidence_ids"]["items"]["enum"] == [
        "chunk_business",
        "chunk_cash",
        "chunk_counter",
    ]
    assert finding_props["fact_ids"]["items"]["enum"] == ["fact_revenue", "fact_ocf", "fact_profit"]
