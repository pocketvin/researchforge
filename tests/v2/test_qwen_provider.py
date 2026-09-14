"""Qwen adapter tests are offline; live provider probes remain explicit manual evidence."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from researchforge.budget import BudgetLedger
from researchforge.v2.contracts import ResearchRequest, WorkingState
from researchforge.v2.provider import RESEARCH_POLICY, REVIEW_POLICY, SYNTHESIS_POLICY
from researchforge.v2.qwen_provider import (
    REFLECTION_POLICY,
    QwenChatResearchModel,
    _normalize_working_state_length_overflows,
)
from researchforge.v2.storage import ResearchRepository


def test_cash_flow_health_policies_require_multidimensional_mixed_judgment() -> None:
    assert "cash_flow_health_multidimensional_v1" in RESEARCH_POLICY
    assert "direct_answer 应使用 mixed" in RESEARCH_POLICY
    assert "票据背书/贴现" in RESEARCH_POLICY
    assert "cash_flow_health_multidimensional_v1" in REFLECTION_POLICY
    assert "整体现金状态" in REFLECTION_POLICY
    assert "CASH-FLOW HEALTH" in SYNTHESIS_POLICY
    assert "numeric_assertions only" in SYNTHESIS_POLICY
    assert "现金流健康/质量" in REVIEW_POLICY


def test_working_state_length_overflow_is_deterministically_bounded() -> None:
    payload = {
        "objectives": [
            {
                "objective_id": "obj_driver",
                "question": "What drove the change?",
                "priority": "required",
                "status": "answered",
                "evidence_ids": [],
                "conclusion": ("Management attributed the change to the merger. " * 80),
                "remaining_uncertainty": "",
            }
        ],
        "hypotheses": [],
        "open_questions": [],
        "decision_summary": "The objective is answered.",
        "core_question_status": "answerable",
        "expected_value_of_more_research": "low",
    }
    content = __import__("json").dumps(payload)
    try:
        WorkingState.model_validate_json(content)
    except __import__("pydantic").ValidationError as exc:
        normalized = _normalize_working_state_length_overflows(content, exc.errors())
    else:
        raise AssertionError("fixture must exceed the WorkingState conclusion limit")
    assert normalized is not None
    state, fields = normalized
    assert len(state.objectives[0].conclusion) <= 2400
    assert state.objectives[0].conclusion.endswith(".")
    assert fields[0]["loc"] == "objectives.0.conclusion"


def test_working_state_length_normalizer_does_not_repair_non_length_schema_errors() -> None:
    content = __import__("json").dumps(
        {
            "objectives": [],
            "hypotheses": [],
            "open_questions": [],
            "decision_summary": "ok",
            "core_question_status": "invalid-status",
            "expected_value_of_more_research": "low",
        }
    )
    try:
        WorkingState.model_validate_json(content)
    except __import__("pydantic").ValidationError as exc:
        assert _normalize_working_state_length_overflows(content, exc.errors()) is None
    else:
        raise AssertionError("fixture must contain a non-length schema error")


def test_driver_policies_anchor_explicit_management_bridge_and_keep_peripheral_items_supporting() -> (
    None
):
    assert "management bridge" in RESEARCH_POLICY
    assert "required driver objective" in RESEARCH_POLICY
    assert "report backbone" in SYNTHESIS_POLICY
    assert "secondary margin mechanics" in SYNTHESIS_POLICY
    assert "management bridge" in REFLECTION_POLICY
    assert "supporting objective / supporting context" in REFLECTION_POLICY
    assert "operating cash flow、OREO、equity、litigation" in REFLECTION_POLICY
    assert "expected_value_of_more_research=low" in REFLECTION_POLICY
    assert "operating cash flow、OREO、equity、litigation" in RESEARCH_POLICY
    assert "cash-flow, OREO, equity, litigation" in SYNTHESIS_POLICY


class FakeMessage:
    def __init__(self, *, tool_calls: list[Any] | None = None, content: str | None = None) -> None:
        self.tool_calls = tool_calls
        self.content = content

    def model_dump(self, *, exclude_none: bool = False) -> dict[str, Any]:
        output: dict[str, Any] = {"role": "assistant"}
        if self.content is not None or not exclude_none:
            output["content"] = self.content
        if self.tool_calls is not None or not exclude_none:
            output["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in self.tool_calls or []
            ]
        return output


class FakeCompletions:
    def __init__(self) -> None:
        self.calls = 0
        self.requests: list[dict[str, Any]] = []

    def create(self, **payload: Any) -> Any:
        self.calls += 1
        self.requests.append(payload)
        usage = SimpleNamespace(prompt_tokens=30, completion_tokens=5)
        if self.calls == 1:
            return SimpleNamespace(
                choices=[SimpleNamespace(message=FakeMessage(content=""))], usage=usage
            )
        function = SimpleNamespace(name="list_filings", arguments="{}")
        tool_call = SimpleNamespace(id="qwen_call_1", function=function)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=FakeMessage(tool_calls=[tool_call]))], usage=usage
        )


class FakeClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions())


def test_qwen_tool_contract_gets_one_controlled_repair(tmp_path: Path) -> None:
    repository = ResearchRepository(tmp_path / "artifacts")
    request = ResearchRequest(
        company_query="Synthetic",
        market_hint="CN",
        requested_period_label="2025FY",
        research_question="Read the filing.",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="qwen-provider-repair",
    )
    manifest, _ = repository.create(request, {})
    client = FakeClient()
    ledger = BudgetLedger(cap=Decimal("1"), state_path=tmp_path / "budget.json")
    model = QwenChatResearchModel(
        client,  # type: ignore[arg-type]
        ledger,
        repository,
        manifest["run_id"],
        model="qwen-plus",
        vision_model="qwen3-vl-plus",
        remaining_seconds=lambda: 30.0,
    )
    actions = model.next_action({"seed": True}, {"working": {}}, [])
    assert actions == [{"call_id": "qwen_call_1", "name": "list_filings", "arguments": {}}]
    for provider_request in client.chat.completions.requests:
        names = {tool["function"]["name"] for tool in provider_request["tools"]}
        assert "update_research_state" not in names
    assert client.chat.completions.calls == 2
    events = repository.events(manifest["run_id"])
    repairs = [event for event in events if event["event_type"] == "provider_contract_retry"]
    assert len(repairs) == 1
    assert model.usage["provider_calls"] == 2


class CompletionGateCompletions:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    def create(self, **payload: Any) -> Any:
        self.requests.append(payload)
        tools = payload["tools"]
        assert len(tools) == 1
        name = tools[0]["function"]["name"]
        function = SimpleNamespace(
            name=name,
            arguments=(
                '{"stop_reason":"sufficient_evidence","summary":"done",'
                '"evidence_ids":["view_test"],"remaining_uncertainties":[],'
                '"why_stop":"research contract complete"}'
            ),
        )
        tool_call = SimpleNamespace(id="qwen_gate_call", function=function)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=FakeMessage(tool_calls=[tool_call]))],
            usage=SimpleNamespace(prompt_tokens=25, completion_tokens=10),
            model="qwen-plus",
        )


def test_qwen_completion_gate_restricts_available_tool_without_choosing_arguments(
    tmp_path: Path,
) -> None:
    repository = ResearchRepository(tmp_path / "artifacts")
    request = ResearchRequest(
        company_query="Synthetic",
        market_hint="CN",
        requested_period_label="2025FY",
        research_question="Analyze the filing.",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="qwen-completion-gate",
    )
    manifest, _ = repository.create(request, {})
    completions = CompletionGateCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    model = QwenChatResearchModel(
        client,  # type: ignore[arg-type]
        BudgetLedger(cap=Decimal("1"), state_path=tmp_path / "budget.json"),
        repository,
        manifest["run_id"],
        model="qwen-plus",
        vision_model="qwen3-vl-plus",
        remaining_seconds=lambda: 30.0,
    )
    state = {"completeness": {"required_before_submit": ["submit_research"]}}
    action = model.next_action({"request": {}}, state, [])[0]
    assert action["name"] == "submit_research"
    assert action["arguments"]["why_stop"] == "research contract complete"
    names = [tool["function"]["name"] for tool in completions.requests[0]["tools"]]
    assert names == ["submit_research"]


def test_qwen_reflection_uses_strict_public_working_state_schema(tmp_path: Path) -> None:
    class ReflectionCompletions:
        def __init__(self) -> None:
            self.kwargs: dict[str, Any] = {}

        def create(self, **kwargs: Any) -> Any:
            self.kwargs = kwargs
            payload = {
                "hypotheses": [],
                "open_questions": [],
                "decision_summary": "No material issue is yet resolved.",
                "core_question_status": "investigating",
                "expected_value_of_more_research": "medium",
            }
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(message=FakeMessage(content=__import__("json").dumps(payload)))
                ],
                usage=SimpleNamespace(prompt_tokens=80, completion_tokens=30),
                model="qwen-plus",
            )

    class ReflectionClient:
        def __init__(self) -> None:
            self.completions = ReflectionCompletions()
            self.chat = SimpleNamespace(completions=self.completions)

    repository = ResearchRepository(tmp_path / "artifacts")
    req = ResearchRequest(
        company_query="Synthetic",
        market_hint="CN",
        requested_period_label="2025FY",
        research_question="Analyze the filing.",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="qwen-reflection-schema",
    )
    manifest, _ = repository.create(req, {})
    client = ReflectionClient()
    model = QwenChatResearchModel(
        client,  # type: ignore[arg-type]
        BudgetLedger(cap=Decimal("1"), state_path=tmp_path / "budget-reflect.json"),
        repository,
        manifest["run_id"],
        model="qwen-plus",
        vision_model="qwen3-vl-plus",
        remaining_seconds=lambda: 30.0,
    )
    reflected = model.reflect(
        {"request": {"research_question": "Analyze the filing."}, "catalog": {}},
        {"working": {}, "reference_registry": {"evidence": [], "facts": [], "calculations": []}},
        [],
    )
    assert reflected.core_question_status == "investigating"
    kwargs = client.completions.kwargs
    assert "tools" not in kwargs
    assert "tool_choice" not in kwargs
    assert kwargs["response_format"]["type"] == "json_schema"
    assert kwargs["response_format"]["json_schema"]["strict"] is True


def test_context_compaction_preserves_research_digest_without_repeating_it_normally(
    tmp_path: Path,
) -> None:
    repository = ResearchRepository(tmp_path / "artifacts")
    req = ResearchRequest(
        company_query="Synthetic",
        market_hint="CN",
        requested_period_label="2025FY",
        research_question="Analyze the filing.",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="qwen-compaction-memory",
    )
    manifest, _ = repository.create(req, {})
    model = QwenChatResearchModel(
        FakeClient(),  # type: ignore[arg-type]
        BudgetLedger(cap=Decimal("1"), state_path=tmp_path / "budget-compact.json"),
        repository,
        manifest["run_id"],
        model="qwen-plus",
        vision_model="qwen3-vl-plus",
        remaining_seconds=lambda: 30.0,
    )
    state = {
        "working": {"hypotheses": [], "open_questions": []},
        "research_evidence_digest": [
            {"call_id": "old_search", "name": "search_filing", "result": {"results": []}}
        ],
    }
    assert "research_evidence_digest" not in model._action_state_summary(state)
    model._compact({"request": {}, "catalog": {}}, state, [])
    compacted = __import__("json").loads(model.history[0]["content"])
    assert compacted["state"]["research_evidence_digest"][0]["call_id"] == "old_search"


def test_qwen_failed_request_releases_budget_and_separates_unknown_cost_ceiling(
    tmp_path: Path,
) -> None:
    class BrokenCompletions:
        def create(self, **kwargs: Any) -> Any:
            raise TimeoutError("synthetic provider timeout")

    repository = ResearchRepository(tmp_path / "artifacts-failure")
    request = ResearchRequest(
        company_query="Synthetic",
        market_hint="CN",
        requested_period_label="2025FY",
        research_question="Read the filing.",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="qwen-failed-cost-accounting",
    )
    manifest, _ = repository.create(request, {})
    ledger = BudgetLedger(cap=Decimal("1"), state_path=tmp_path / "budget-failure.json")
    model = QwenChatResearchModel(
        SimpleNamespace(chat=SimpleNamespace(completions=BrokenCompletions())),  # type: ignore[arg-type]
        ledger,
        repository,
        manifest["run_id"],
        model="qwen-plus",
        vision_model="qwen3-vl-plus",
        remaining_seconds=lambda: 30.0,
    )
    with pytest.raises(TimeoutError, match="provider timeout"):
        model._call(
            "policy",
            [{"role": "user", "content": "review"}],
            output_model=WorkingState,
            operation="semantic_review",
        )
    snapshot = ledger.snapshot()
    assert snapshot.spent == 0 and snapshot.reserved == 0
    assert model.usage["estimated_cost"] == 0.0
    assert model.usage["provider_calls"] == 0
    assert model.usage["failed_provider_calls"] == 1
    assert float(model.usage["unconfirmed_failed_cost_ceiling"]) > 0
    assert any(
        event["event_type"] == "model_request_failed"
        for event in repository.events(manifest["run_id"])
    )


def test_qwen_hides_submit_tool_while_completion_gate_is_closed(tmp_path: Path) -> None:
    class ClosedGateCompletions:
        def __init__(self) -> None:
            self.request: dict[str, Any] | None = None

        def create(self, **payload: Any) -> Any:
            self.request = payload
            names = [tool["function"]["name"] for tool in payload["tools"]]
            assert "submit_research" not in names
            assert "search_filing" in names
            function = SimpleNamespace(
                name="search_filing",
                arguments=(
                    '{"query":"cash flow","kind":"all","document_id":null,"offset":0,"limit":3}'
                ),
            )
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=FakeMessage(
                            tool_calls=[SimpleNamespace(id="closed_gate", function=function)]
                        )
                    )
                ],
                usage=SimpleNamespace(prompt_tokens=20, completion_tokens=5),
                model="qwen-plus",
            )

    repository = ResearchRepository(tmp_path / "artifacts-closed-gate")
    request = ResearchRequest(
        company_query="Synthetic",
        market_hint="CN",
        requested_period_label="2025FY",
        research_question="Read the filing.",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="qwen-closed-submit-gate",
    )
    manifest, _ = repository.create(request, {})
    completions = ClosedGateCompletions()
    model = QwenChatResearchModel(
        SimpleNamespace(chat=SimpleNamespace(completions=completions)),  # type: ignore[arg-type]
        BudgetLedger(cap=Decimal("1"), state_path=tmp_path / "budget-closed.json"),
        repository,
        manifest["run_id"],
        model="qwen-plus",
        vision_model="qwen3-vl-plus",
        remaining_seconds=lambda: 30.0,
    )
    state = {
        "completeness": {
            "required_before_submit": [],
            "required_objectives_open": 1,
            "high_priority_open_questions": 1,
        }
    }
    action = model.next_action({"request": {}}, state, [])[0]
    assert action["name"] == "search_filing"
    assert completions.request is not None
    names = [tool["function"]["name"] for tool in completions.request["tools"]]
    assert "submit_research" not in names
