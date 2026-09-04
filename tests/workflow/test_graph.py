"""LangGraph topology and conditional-route tests."""

from __future__ import annotations

from typing import Any

from researchforge.application.contracts import ResearchRunRequest
from researchforge.application.research import (
    DeterministicConclusionGenerator,
    ResearchLanguageDraft,
    StructuredOutputError,
)
from tests.runtime_helpers import assert_v14_schema, build_service, catl_request


def _input(request: ResearchRunRequest) -> dict[str, object]:
    payload = request.model_dump(mode="json")
    return {
        "input_kind": "research",
        "task_type": payload["task_type"],
        "research_question": payload["research_question"],
        "company_ids": payload["company_ids"],
        "requested_period_labels": payload["requested_period_labels"],
        "research_time": payload["research_time"],
    }


def test_happy_path_visits_all_ten_stages_in_order(tmp_path: object) -> None:
    from pathlib import Path

    service = build_service(Path(str(tmp_path)))
    outcome = service.workflow.run(
        "run_graph_happy",
        "trace_graph_happy",
        _input(catl_request()),
    )

    assert outcome.terminal_state == "succeeded"
    assert [event["stage"] for event in outcome.trace["stages"]] == list(
        service.workflow.stage_names
    )
    assert outcome.trace["stages"][6]["sanitized_summary"].endswith("not_found outcome.")
    assert_v14_schema(outcome.trace, "workflow-trace.schema.json")
    assert outcome.result is not None
    assert_v14_schema(outcome.result, "research-result.schema.json")


def test_missing_point_in_time_data_terminates_without_result(tmp_path: object) -> None:
    from pathlib import Path

    service = build_service(Path(str(tmp_path)))
    request = catl_request(research_time="2024-07-01T00:00:00+08:00")

    outcome = service.workflow.run(
        "run_graph_insufficient",
        "trace_graph_insufficient",
        _input(request),
    )

    assert outcome.terminal_state == "insufficient_data"
    assert outcome.result is None
    assert outcome.failure == {
        "code": "INSUFFICIENT_DATA",
        "message": (
            "Requested company/period facts are unavailable at the research cutoff: "
            "cn_300750/2024H1"
        ),
        "retryable": False,
    }
    assert [event["stage"] for event in outcome.trace["stages"]] == [
        "understanding_question",
        "planning",
        "loading_financial_data",
    ]
    assert_v14_schema(outcome.trace, "workflow-trace.schema.json")


class RepairSequenceGenerator:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0
        self.fallback = DeterministicConclusionGenerator()

    def generate(self, context: dict[str, Any]) -> ResearchLanguageDraft:
        self.calls += 1
        if self.calls <= self.failures:
            raise StructuredOutputError("invalid test output")
        return self.fallback.generate(context)


def test_output_repair_is_capped_at_one(tmp_path: object) -> None:
    from pathlib import Path

    service = build_service(Path(str(tmp_path)))
    generator = RepairSequenceGenerator(failures=1)
    service.workflow.conclusion_generator = generator

    outcome = service.workflow.run(
        "run_graph_repair",
        "trace_graph_repair",
        _input(catl_request()),
    )

    assert outcome.terminal_state == "succeeded"
    assert outcome.trace["repair_attempts"] == 1
    assert generator.calls == 2
    assert "structure-only repair" in outcome.trace["stages"][7]["sanitized_summary"]


def test_second_invalid_output_fails_without_result(tmp_path: object) -> None:
    from pathlib import Path

    service = build_service(Path(str(tmp_path)))
    generator = RepairSequenceGenerator(failures=2)
    service.workflow.conclusion_generator = generator

    outcome = service.workflow.run(
        "run_graph_double_invalid",
        "trace_graph_double_invalid",
        _input(catl_request()),
    )

    assert outcome.terminal_state == "failed"
    assert outcome.result is None
    assert outcome.trace["repair_attempts"] == 1
    assert outcome.failure is not None
    assert outcome.failure["code"] == "OUTPUT_SCHEMA_INVALID"
    assert generator.calls == 2
    assert_v14_schema(outcome.trace, "workflow-trace.schema.json")


def test_monotonic_timeout_stops_before_work_and_persists_valid_trace(
    tmp_path: object,
) -> None:
    from pathlib import Path

    service = build_service(Path(str(tmp_path)))
    outcome = service.workflow.run(
        "run_graph_timeout",
        "trace_graph_timeout",
        _input(catl_request()),
        timeout_seconds=0,
        monotonic=lambda: 100.0,
    )

    assert outcome.terminal_state == "timed_out"
    assert outcome.result is None
    assert outcome.failure is not None
    assert outcome.failure["code"] == "TIMED_OUT"
    assert outcome.trace["stages"][0]["failure_code"] == "TIMED_OUT"
    assert_v14_schema(outcome.trace, "workflow-trace.schema.json")


def test_checkpoint_is_loadable_by_a_new_service_instance(tmp_path: object) -> None:
    from pathlib import Path

    root = Path(str(tmp_path))
    first = build_service(root)
    first.workflow.run(
        "run_graph_durable",
        "trace_graph_durable",
        _input(catl_request()),
    )

    second = build_service(root)

    assert second.workflow.has_checkpoint("run_graph_durable") is True
    checkpoint_file = root / "checkpoints" / "langgraph-checkpoints.json"
    assert checkpoint_file.is_file()
    assert checkpoint_file.stat().st_mode & 0o777 == 0o600
