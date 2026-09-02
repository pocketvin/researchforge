"""Run lifecycle, persistence, and idempotency tests."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pytest

from researchforge.adapters.storage import IdempotencyConflictError
from tests.runtime_helpers import assert_v14_schema, build_service, catl_request


def test_service_persists_schema_valid_bundle(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    submission = service.submit(catl_request())

    manifest = service.execute(submission.run_id)

    assert manifest["lifecycle_state"] == "succeeded"
    assert_v14_schema(manifest, "run-manifest.schema.json")
    result = service.get_result(submission.run_id)
    assert_v14_schema(result, "research-result.schema.json")
    assert_v14_schema(service.get_trace(submission.run_id), "workflow-trace.schema.json")
    assert service.get_evidence(submission.run_id)
    assert service.get_calculations(submission.run_id)
    assert result["monitoring_items"]
    assert all(claim["support_evidence_ids"] for claim in result["claims"])
    assert all(check["evidence_ids"] for check in result["mandatory_checks"] if check["fact_ids"])
    assert len(list((tmp_path / "objects").rglob("*.json"))) >= 8


def test_idempotent_submission_returns_original_run(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    request = catl_request()

    first = service.submit(request)
    second = service.submit(request)

    assert first.created is True
    assert second.created is False
    assert second.run_id == first.run_id


def test_idempotency_key_conflict_is_rejected(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    service.submit(catl_request(question="问题一"))

    with pytest.raises(IdempotencyConflictError):
        service.submit(catl_request(question="问题二"))


def test_queued_cancel_is_idempotent_and_schema_valid(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    submission = service.submit(catl_request())

    first = service.cancel(submission.run_id)
    second = service.cancel(submission.run_id)

    assert first == second
    assert first["lifecycle_state"] == "cancelled"
    assert_v14_schema(first, "run-manifest.schema.json")
    assert_v14_schema(service.get_trace(submission.run_id), "workflow-trace.schema.json")


class UnexpectedFailureGenerator:
    def generate(self, context: dict[str, Any]) -> None:
        del context
        raise RuntimeError("private adapter detail")


def test_unexpected_failure_has_retrievable_sanitized_trace(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    service.workflow.conclusion_generator = UnexpectedFailureGenerator()  # type: ignore[assignment]
    submission = service.submit(catl_request())

    manifest = service.execute(submission.run_id)
    trace = service.get_trace(submission.run_id)

    assert manifest["lifecycle_state"] == "failed"
    assert manifest["failure"]["code"] == "TOOL_FAILED"
    assert "private adapter detail" not in str(manifest)
    assert trace["terminal_state"] == "failed"
    assert trace["stages"][-1]["failure_code"] == "TOOL_FAILED"
    assert_v14_schema(manifest, "run-manifest.schema.json")
    assert_v14_schema(trace, "workflow-trace.schema.json")
    with pytest.raises(KeyError):
        service.get_result(submission.run_id)


class BlockingGenerator:
    def __init__(self, entered: threading.Event, release: threading.Event) -> None:
        self.entered = entered
        self.release = release

    def generate(self, context: dict[str, Any]) -> Any:
        self.entered.set()
        assert self.release.wait(timeout=5)
        from researchforge.application.research import DeterministicConclusionGenerator

        return DeterministicConclusionGenerator().generate(context)


def test_running_cancel_is_observed_after_active_node_returns(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    entered = threading.Event()
    release = threading.Event()
    service.workflow.conclusion_generator = BlockingGenerator(entered, release)
    submission = service.submit(catl_request())
    result: list[dict[str, Any]] = []

    worker = threading.Thread(target=lambda: result.append(service.execute(submission.run_id)))
    worker.start()
    assert entered.wait(timeout=5)
    cancellation_response = service.cancel(submission.run_id)
    assert cancellation_response["lifecycle_state"] == "running"
    release.set()
    worker.join(timeout=5)

    assert not worker.is_alive()
    assert result[0]["lifecycle_state"] == "cancelled"
    trace = service.get_trace(submission.run_id)
    assert trace["terminal_state"] == "cancelled"
    assert trace["stages"][-1]["status"] == "cancelled"
    assert_v14_schema(trace, "workflow-trace.schema.json")


def test_restart_recovers_completed_checkpoint_before_artifact_commit(tmp_path: Path) -> None:
    first = build_service(tmp_path)
    submission = first.submit(catl_request())
    manifest = first.get_manifest(submission.run_id)
    trace_id = f"trace_{submission.run_id}"
    running = {
        **manifest,
        "lifecycle_state": "running",
        "started_at": manifest["created_at"],
        "artifacts": {**manifest["artifacts"], "workflow_trace_id": trace_id},
    }
    first.repository.save_manifest(submission.run_id, running)
    first.workflow.run(submission.run_id, trace_id, running["input"])

    restarted = build_service(tmp_path)
    recovered = restarted.recover_interrupted_runs()

    assert recovered == [submission.run_id]
    recovered_manifest = restarted.get_manifest(submission.run_id)
    assert recovered_manifest["lifecycle_state"] == "succeeded"
    assert_v14_schema(recovered_manifest, "run-manifest.schema.json")
    assert_v14_schema(restarted.get_result(submission.run_id), "research-result.schema.json")
