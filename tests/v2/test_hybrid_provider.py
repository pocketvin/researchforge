"""Hybrid routing is deterministic and does not depend on live provider behavior."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from researchforge.budget import BudgetLedger
from researchforge.v2.contracts import ResearchRequest, WorkingState
from researchforge.v2.hybrid_provider import HybridResearchModel
from researchforge.v2.storage import ResearchRepository


class FakeCompletions:
    def __init__(self, model: str) -> None:
        self.model = model
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=20, completion_tokens=5),
            model=self.model,
        )


class FakeClient:
    def __init__(self, model: str) -> None:
        self.completions = FakeCompletions(model)
        self.chat = SimpleNamespace(completions=self.completions)


def build_model(tmp_path: Path) -> tuple[HybridResearchModel, FakeClient, FakeClient, FakeClient]:
    repository = ResearchRepository(tmp_path / "artifacts")
    request = ResearchRequest(
        company_query="Synthetic",
        market_hint="CN",
        requested_period_label="2025FY",
        research_question="Analyze the filing.",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="hybrid-route-test",
    )
    manifest, _ = repository.create(request, {})
    deepseek = FakeClient("deepseek-v4-flash")
    kimi = FakeClient("kimi-k3")
    qwen = FakeClient("qwen3-vl-plus")
    ledger = BudgetLedger(cap=Decimal("2"), state_path=tmp_path / "budget.json")
    model = HybridResearchModel(
        deepseek_client=deepseek,  # type: ignore[arg-type]
        kimi_client=kimi,  # type: ignore[arg-type]
        qwen_client=qwen,  # type: ignore[arg-type]
        ledger=ledger,
        repository=repository,
        run_id=manifest["run_id"],
        deepseek_model="deepseek-v4-flash",
        kimi_model="kimi-k3",
        qwen_research_model="qwen-plus",
        qwen_text_model="qwen-plus",
        qwen_fallback_synthesis_model="qwen3-max",
        qwen_vision_model="qwen3-vl-plus",
        remaining_seconds=lambda: 60.0,
    )
    return model, deepseek, kimi, qwen


def test_hybrid_routes_research_and_synthesis_to_deepseek_review_to_qwen(
    tmp_path: Path,
) -> None:
    model, deepseek, kimi, qwen = build_model(tmp_path)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_filing",
                "description": "search",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
                "strict": True,
            },
        }
    ]
    model._call(
        "policy",
        [{"role": "user", "content": "search"}],
        tools=tools,
        operation="agent_model",
    )
    assert len(deepseek.completions.calls) == 1
    assert deepseek.completions.calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert deepseek.completions.calls[0]["temperature"] == 0
    assert kimi.completions.calls == [] and qwen.completions.calls == []

    model._call(
        "policy",
        [{"role": "user", "content": "reflect"}],
        output_model=WorkingState,
        operation="state_reflection",
    )
    assert len(deepseek.completions.calls) == 2
    reflection_request = deepseek.completions.calls[-1]
    assert reflection_request["response_format"] == {"type": "json_object"}
    assert "JSON Schema" in reflection_request["messages"][0]["content"]
    assert kimi.completions.calls == []

    model._call(
        "policy",
        [{"role": "user", "content": "write"}],
        output_model=WorkingState,
        operation="synthesis",
    )
    assert len(deepseek.completions.calls) == 3
    assert deepseek.completions.calls[-1]["response_format"] == {"type": "json_object"}
    assert kimi.completions.calls == []

    model._call(
        "policy",
        [{"role": "user", "content": "review"}],
        output_model=WorkingState,
        operation="semantic_review",
    )
    assert len(qwen.completions.calls) == 1
    assert qwen.completions.calls[-1]["model"] == "qwen-plus"
    assert qwen.completions.calls[-1]["response_format"]["type"] == "json_schema"


def test_semantic_review_evidence_keeps_late_table_subtotal() -> None:
    text = "A" * 1700 + " Net cash provided by operating activities | $ | 265,009 " + "B" * 1000
    compact = HybridResearchModel._compact_review_evidence(
        {
            "artifact_id": "view_cash_flow",
            "document_id": "doc_filing",
            "source_kind": "table",
            "text": text,
        }
    )
    assert "Net cash provided by operating activities" in compact["text"]
    assert "265,009" in compact["text"]
    assert len(compact["text"]) == len(text)


def test_hybrid_routes_any_page_image_operation_to_qwen_vl(tmp_path: Path) -> None:
    model, deepseek, kimi, qwen = build_model(tmp_path)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "inspect",
                "description": "inspect",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        }
    ]
    model._call(
        "policy",
        [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
                    {"type": "text", "text": "inspect page"},
                ],
            }
        ],
        tools=tools,
        operation="agent_model",
    )
    assert len(qwen.completions.calls) == 1
    assert qwen.completions.calls[0]["model"] == "qwen3-vl-plus"
    assert deepseek.completions.calls == [] and kimi.completions.calls == []
    assert model.usage["calls_by_provider"] == {"deepseek": 0, "kimi": 0, "qwen": 1}


def test_hybrid_synthesis_strips_page_images_and_stays_on_deepseek(tmp_path: Path) -> None:
    model, deepseek, kimi, qwen = build_model(tmp_path)
    model._call(
        "policy",
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "The persisted page text contains the evidence."},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
                ],
            }
        ],
        output_model=WorkingState,
        operation="synthesis",
    )
    assert len(deepseek.completions.calls) == 1
    assert qwen.completions.calls == [] and kimi.completions.calls == []
    request = deepseek.completions.calls[0]
    content = request["messages"][1]["content"]
    assert isinstance(content, list)
    assert [item["type"] for item in content] == ["text"]


class FailingCompletions:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        raise self.error


class FailingClient:
    def __init__(self, error: Exception) -> None:
        self.completions = FailingCompletions(error)
        self.chat = SimpleNamespace(completions=self.completions)


def test_text_semantic_review_qwen_timeout_falls_back_without_fake_actual_cost(
    tmp_path: Path,
) -> None:
    repository = ResearchRepository(tmp_path / "artifacts-fallback")
    request = ResearchRequest(
        company_query="Synthetic",
        market_hint="CN",
        requested_period_label="2025FY",
        research_question="Analyze the filing.",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="hybrid-review-fallback-test",
    )
    manifest, _ = repository.create(request, {})
    deepseek = FakeClient("deepseek-v4-flash")
    kimi = FakeClient("kimi-k3")
    qwen = FailingClient(TimeoutError("synthetic qwen timeout"))
    ledger = BudgetLedger(cap=Decimal("2"), state_path=tmp_path / "budget-fallback.json")
    model = HybridResearchModel(
        deepseek_client=deepseek,  # type: ignore[arg-type]
        kimi_client=kimi,  # type: ignore[arg-type]
        qwen_client=qwen,  # type: ignore[arg-type]
        ledger=ledger,
        repository=repository,
        run_id=manifest["run_id"],
        deepseek_model="deepseek-v4-flash",
        kimi_model="kimi-k3",
        qwen_research_model="qwen-plus",
        qwen_text_model="qwen-plus",
        qwen_fallback_synthesis_model="qwen3-max",
        qwen_vision_model="qwen3-vl-plus",
        remaining_seconds=lambda: 90.0,
    )
    model._call(
        "policy",
        [{"role": "user", "content": "review"}],
        output_model=WorkingState,
        operation="semantic_review",
    )
    assert len(qwen.completions.calls) == 1
    assert len(deepseek.completions.calls) == 1
    assert model.review_metadata == {
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "independence": "reduced_same_provider",
        "fallback_used": True,
    }
    assert model.usage["provider_calls"] == 1
    assert model.usage["failed_provider_calls"] == 1
    assert model.usage["failed_calls_by_provider"] == {"qwen": 1}
    assert float(model.usage["unconfirmed_failed_cost_ceiling"]) > 0
    assert (
        0
        < float(model.usage["estimated_cost"])
        < float(model.usage["unconfirmed_failed_cost_ceiling"])
    )
    snapshot = ledger.snapshot()
    assert snapshot.reserved == 0
    events = repository.events(manifest["run_id"])
    assert any(event["event_type"] == "model_request_failed" for event in events)
    assert any(event["event_type"] == "semantic_review_provider_fallback" for event in events)


def test_image_semantic_review_failure_stays_fail_closed_without_text_fallback(
    tmp_path: Path,
) -> None:
    repository = ResearchRepository(tmp_path / "artifacts-image-fail")
    request = ResearchRequest(
        company_query="Synthetic",
        market_hint="CN",
        requested_period_label="2025FY",
        research_question="Analyze the filing image.",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="hybrid-image-review-fail-test",
    )
    manifest, _ = repository.create(request, {})
    deepseek = FakeClient("deepseek-v4-flash")
    qwen = FailingClient(TimeoutError("synthetic vision timeout"))
    ledger = BudgetLedger(cap=Decimal("2"), state_path=tmp_path / "budget-image-fail.json")
    model = HybridResearchModel(
        deepseek_client=deepseek,  # type: ignore[arg-type]
        kimi_client=FakeClient("kimi-k3"),  # type: ignore[arg-type]
        qwen_client=qwen,  # type: ignore[arg-type]
        ledger=ledger,
        repository=repository,
        run_id=manifest["run_id"],
        deepseek_model="deepseek-v4-flash",
        kimi_model="kimi-k3",
        qwen_research_model="qwen-plus",
        qwen_text_model="qwen-plus",
        qwen_fallback_synthesis_model="qwen3-max",
        qwen_vision_model="qwen3-vl-plus",
        remaining_seconds=lambda: 90.0,
    )
    import pytest

    with pytest.raises(TimeoutError, match="vision timeout"):
        model._call(
            "policy",
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
                        {"type": "text", "text": "review image"},
                    ],
                }
            ],
            output_model=WorkingState,
            operation="semantic_review",
        )
    assert len(qwen.completions.calls) == 1
    assert deepseek.completions.calls == []
    assert ledger.snapshot().reserved == 0
    assert model.usage["failed_provider_calls"] == 1
    assert model.usage["provider_calls"] == 0
    assert not any(
        event["event_type"] == "semantic_review_provider_fallback"
        for event in repository.events(manifest["run_id"])
    )


def test_hybrid_review_keeps_fallback_metadata_after_claimwise_review(
    tmp_path: Path,
) -> None:
    model, _deepseek, _kimi, _qwen = build_model(tmp_path)
    calls: list[str] = []

    def routed_call(*args: Any, **kwargs: Any) -> Any:
        output_model = kwargs["output_model"]
        calls.append(output_model.__name__)
        model._review_metadata = {
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "independence": "reduced_same_provider",
            "fallback_used": True,
            "strategy": "claim_wise_then_summary",
        }
        if output_model.__name__ == "ClaimReview":
            payload = '{"claim_id":"claim_one","verdict":"supported","reason":"Synthetic support."}'
        else:
            payload = '{"question_answered":true,"missing_material_topics":[]}'
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=payload))],
            model="deepseek-v4-flash",
        )

    model._call = routed_call  # type: ignore[method-assign]
    from researchforge.v2.contracts import ResearchReport

    report = ResearchReport.model_validate(
        {
            "title": "Synthetic report",
            "executive_summary": "Synthetic summary",
            "findings": [
                {
                    "claim_id": "claim_one",
                    "title": "Synthetic finding",
                    "text": "Synthetic text",
                    "kind": "observation",
                    "evidence_ids": ["view_one"],
                    "fact_ids": [],
                    "calculation_ids": [],
                    "numeric_assertions": [],
                    "confidence": "medium",
                    "uncertainty": "Synthetic only",
                }
            ],
            "sections": [{"title": "Section", "text": "Synthetic", "evidence_ids": ["view_one"]}],
            "limitations": ["Synthetic only"],
            "follow_up_questions": [],
        }
    )
    context = {
        "request": {"research_question": "Synthetic?"},
        "evidence": [{"artifact_id": "view_one", "text": "Synthetic evidence"}],
        "financial_facts": [],
        "calculations": [],
    }
    review = model.review(context, report)
    assert review.claims[0].claim_id == "claim_one"
    assert calls == ["ClaimReview", "ReviewSummary"]
    assert model.review_metadata == {
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "independence": "reduced_same_provider",
        "fallback_used": True,
        "strategy": "claim_wise_then_summary",
    }


def test_hybrid_product_review_is_claimwise_then_summary_on_qwen_plus(tmp_path: Path) -> None:
    model, deepseek, kimi, qwen = build_model(tmp_path)

    class ReviewCompletions:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []
            self.claim_index = 0

        def create(self, **kwargs: Any) -> Any:
            self.calls.append(kwargs)
            schema_name = kwargs["response_format"]["json_schema"]["name"]
            if schema_name == "ClaimReview":
                self.claim_index += 1
                content = (
                    '{"claim_id":"claim_'
                    + str(self.claim_index)
                    + '","verdict":"supported","reason":"Cited filing evidence supports it."}'
                )
            else:
                content = '{"question_answered":true,"missing_material_topics":[]}'
            return SimpleNamespace(
                usage=SimpleNamespace(prompt_tokens=20, completion_tokens=5),
                model="qwen-plus",
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            )

    review_completions = ReviewCompletions()
    qwen.completions = review_completions  # type: ignore[assignment]
    qwen.chat.completions = review_completions

    from researchforge.v2.contracts import ResearchReport

    report = ResearchReport.model_validate(
        {
            "direct_answer": "no",
            "title": "Synthetic report",
            "executive_summary": "No. Synthetic answer.",
            "findings": [
                {
                    "claim_id": f"claim_{index}",
                    "title": f"Finding {index}",
                    "text": f"Synthetic claim {index}.",
                    "kind": "observation",
                    "evidence_ids": [f"view_{index}"],
                    "fact_ids": [],
                    "calculation_ids": [],
                    "numeric_assertions": [],
                    "confidence": "medium",
                    "uncertainty": "Synthetic only",
                }
                for index in (1, 2)
            ],
            "sections": [{"title": "Section", "text": "Synthetic", "evidence_ids": ["view_1"]}],
            "limitations": ["Synthetic only"],
            "follow_up_questions": [],
        }
    )
    context = {
        "request": {"research_question": "Synthetic binary question?"},
        "evidence": [
            {"artifact_id": "view_1", "text": "Evidence one."},
            {"artifact_id": "view_2", "text": "Evidence two."},
        ],
        "financial_facts": [],
        "calculations": [],
    }
    review = model.review(context, report)
    assert [item.claim_id for item in review.claims] == ["claim_1", "claim_2"]
    assert review.question_answered is True
    assert [
        call["response_format"]["json_schema"]["name"] for call in review_completions.calls
    ] == ["ClaimReview", "ClaimReview", "ReviewSummary"]
    assert all(call["model"] == "qwen-plus" for call in review_completions.calls)
    claim_review_prompts = [call["messages"][0]["content"] for call in review_completions.calls[:2]]
    assert all(
        "不要要求这个局部 finding 单独承担全局分类结论" in prompt for prompt in claim_review_prompts
    )
    claim_payloads = [str(call["messages"][1]["content"]) for call in review_completions.calls[:2]]
    assert all("Synthetic binary question?" not in payload for payload in claim_payloads)
    summary_payload = str(review_completions.calls[-1]["messages"][1]["content"])
    assert "Synthetic binary question?" in summary_payload
    assert deepseek.completions.calls == [] and kimi.completions.calls == []
    assert model.review_metadata["strategy"] == "claim_wise_then_summary"
    assert model.review_metadata["fallback_used"] is False


def test_consumed_page_image_does_not_pin_future_agent_turns_to_vision(tmp_path: Path) -> None:
    model, _deepseek, _kimi, _qwen = build_model(tmp_path)
    image_message = {
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
            {"type": "text", "text": "This is a filing page."},
        ],
    }
    model.history = [image_message]
    provider, model_name, _client = model._route("agent_model", model.history)
    assert (provider, model_name) == ("qwen", "qwen3-vl-plus")

    model._prune_consumed_images()
    assert model._contains_image(model.history) is False
    provider, model_name, _client = model._route("agent_model", model.history)
    assert (provider, model_name) == ("deepseek", "deepseek-v4-flash")
    assert "此前回合已查看" in str(model.history[0]["content"])
    events = model.repository.events(model.run_id)
    assert any(event["event_type"] == "vision_context_consumed" for event in events)


class StatusFailure(RuntimeError):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"synthetic provider status {status_code}")
        self.status_code = status_code


def test_deepseek_402_locks_run_to_qwen_research_fallback_and_uses_distinct_review_model(
    tmp_path: Path,
) -> None:
    model, deepseek, kimi, qwen = build_model(tmp_path)
    failing = FailingCompletions(StatusFailure(402))
    deepseek.completions = failing  # type: ignore[assignment]
    deepseek.chat.completions = failing
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_filing",
                "description": "search",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                "strict": True,
            },
        }
    ]

    model._call(
        "policy",
        [{"role": "user", "content": "research"}],
        tools=tools,
        operation="agent_model",
    )
    assert len(failing.calls) == 1
    assert len(qwen.completions.calls) == 1
    assert qwen.completions.calls[-1]["model"] == "qwen-plus"
    assert model.usage["research_provider_fallback_used"] is True

    model._call(
        "policy",
        [{"role": "user", "content": "reflect"}],
        output_model=WorkingState,
        operation="state_reflection",
    )
    assert len(failing.calls) == 1
    assert qwen.completions.calls[-1]["model"] == "qwen3-max"

    model._call(
        "policy",
        [{"role": "user", "content": "write"}],
        output_model=WorkingState,
        operation="synthesis",
    )
    assert len(failing.calls) == 1
    assert qwen.completions.calls[-1]["model"] == "qwen3-max"

    model._call(
        "policy",
        [{"role": "user", "content": "review"}],
        output_model=WorkingState,
        operation="semantic_review",
    )
    assert qwen.completions.calls[-1]["model"] == "qwen-plus"
    assert model.review_metadata["independence"] == "different_model_from_synthesis_same_provider"
    assert model.review_metadata["research_provider_fallback_used"] is True
    assert kimi.completions.calls == []
    fallback_events = [
        event
        for event in model.repository.events(model.run_id)
        if event["event_type"] == "research_provider_fallback"
    ]
    assert len(fallback_events) == 1
    assert fallback_events[0]["data"]["status_code"] == 402
    assert fallback_events[0]["data"]["silent"] is False


def test_deepseek_400_is_not_hidden_by_qwen_fallback(tmp_path: Path) -> None:
    model, deepseek, _kimi, qwen = build_model(tmp_path)
    failing = FailingCompletions(StatusFailure(400))
    deepseek.completions = failing  # type: ignore[assignment]
    deepseek.chat.completions = failing
    with pytest.raises(StatusFailure, match="400"):
        model._call(
            "policy",
            [{"role": "user", "content": "bad request"}],
            output_model=WorkingState,
            operation="state_reflection",
        )
    assert len(failing.calls) == 1
    assert qwen.completions.calls == []
    assert model.usage.get("research_provider_fallback_used") is not True
    assert not any(
        event["event_type"] == "research_provider_fallback"
        for event in model.repository.events(model.run_id)
    )


def test_reflection_validation_error_retries_once_with_schema_feedback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, _deepseek, _kimi, _qwen = build_model(tmp_path)
    repaired = WorkingState(
        decision_summary="Repaired public state.",
        core_question_status="investigating",
        expected_value_of_more_research="medium",
    )
    responses = iter(
        [
            SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content='{"objectives":"not-a-list"}'))
                ]
            ),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content=repaired.model_dump_json()))
                ]
            ),
        ]
    )
    calls: list[list[dict[str, Any]]] = []

    def fake_call(
        _instructions: str,
        messages: list[dict[str, Any]],
        **_kwargs: Any,
    ) -> Any:
        calls.append(messages)
        return next(responses)

    monkeypatch.setattr(model, "_call", fake_call)
    result = model.reflect(
        {"request": {"research_question": "Analyze the filing."}, "catalog": {}},
        {"working": {}},
        [],
    )
    assert result.decision_summary == "Repaired public state."
    assert len(calls) == 2
    assert "WORKING_STATE_SCHEMA_INVALID" in str(calls[1][0]["content"])
    assert "objectives" in str(calls[1][0]["content"])
    events = model.repository.events(model.run_id, limit=100)
    assert any(event["event_type"] == "state_reflection_repair_requested" for event in events)
