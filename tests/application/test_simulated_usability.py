"""No-network tests for the isolated simulated-usability executor."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from researchforge.application.budget import BudgetLedger
from researchforge.application.simulated_usability import (
    SimulatedUsabilityBlocked,
    SimulatedUsabilityRunner,
)
from tests.runtime_helpers import assert_v14_schema

PNG = b"\x89PNG\r\n\x1a\nsynthetic-test-image"


class FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        session = len(self.calls)
        return SimpleNamespace(
            id=f"response_{session}",
            output_text=json.dumps(
                {
                    "located_key_change": True,
                    "located_supporting_evidence": True,
                    "located_counter_evidence_or_limitation": True,
                    "located_monitoring_item": True,
                    "usefulness_score": 3 if session == 3 else 4,
                    "auditability_score": 4,
                    "findings": [
                        "The trace is auditable.",
                        "Dissent retained: the frozen evidence scope limits generalization.",
                    ],
                }
            ),
            usage=SimpleNamespace(input_tokens=1_000, output_tokens=200),
        )


def bundle() -> dict[str, Any]:
    return {
        "manifest": {"run_id": "run_simulation_source", "lifecycle_state": "succeeded"},
        "result": {"run_id": "run_simulation_source", "claims": []},
        "trace": {"run_id": "run_simulation_source", "stages": [{}] * 10},
        "facts": [{"fact_id": "fact_1"}],
    }


def runner(
    tmp_path: Path,
    responses: FakeResponses,
    *,
    key_ready: bool,
) -> SimulatedUsabilityRunner:
    screenshots = {}
    for kind in ("research", "skill_lab"):
        path = tmp_path / f"{kind}.png"
        path.write_bytes(PNG)
        screenshots[kind] = path
    return SimulatedUsabilityRunner(
        batch_id="simulated_usability_v1_4_test",
        run_bundle=bundle(),
        screenshots=screenshots,
        artifact_root=tmp_path / "artifacts",
        ledger=BudgetLedger(state_path=tmp_path / "budget.json"),
        rotated_key_ready=key_ready,
        responses_factory=lambda: responses,
        clock=lambda: datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
    )


def test_preflight_blocks_before_provider_when_rotated_key_is_absent(tmp_path: Path) -> None:
    responses = FakeResponses()
    simulation = runner(tmp_path, responses, key_ready=False)

    report = simulation.preflight()

    assert report["status"] == "BLOCKED"
    assert report["provider_contacted"] is False
    assert "rotated local OpenAI key is not confirmed ready" in report["blockers"]
    with pytest.raises(SimulatedUsabilityBlocked):
        simulation.run()
    assert responses.calls == []


def test_three_sessions_are_isolated_labeled_schema_valid_and_idempotent(
    tmp_path: Path,
) -> None:
    responses = FakeResponses()
    simulation = runner(tmp_path, responses, key_ready=True)

    batch = simulation.run()
    repeated = simulation.run()

    assert batch == repeated
    assert batch["status"] == "PASS"
    assert batch["evidence_label"] == "SIMULATED"
    assert batch["human_user_value_validated"] is False
    assert batch["high_score_session_count"] == 2
    assert len(responses.calls) == 3
    assert all(call["store"] is False and call["tools"] == [] for call in responses.calls)
    assert all(call["input"][0]["role"] == "user" for call in responses.calls)
    assert all("prior session" not in json.dumps(call["input"]) for call in responses.calls)
    for session_number in range(1, 4):
        evaluation = simulation.repository.get(
            "simulated_usability_v1_4_test", f"session-{session_number}"
        )
        assert evaluation["evidence_label"] == "SIMULATED"
        assert evaluation["human_user_value_validated"] is False
        assert_v14_schema(evaluation, "simulated-usability-evaluation.schema.json")
