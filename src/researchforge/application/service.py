"""Research-run lifecycle use case shared by CLI and FastAPI."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from researchforge.adapters.checkpoints import DurableJsonCheckpointSaver
from researchforge.adapters.fixtures import G0FixtureCatalog
from researchforge.adapters.storage import FileRunRepository
from researchforge.application.contracts import ResearchRunRequest, RunLinks, RunSubmission
from researchforge.application.research import (
    DeterministicConclusionGenerator,
    EarningsQualityAnalyzer,
)
from researchforge.application.verification import FinancialVerifier
from researchforge.persistence import DatabaseIndex
from researchforge.workflow.graph import (
    CHECKPOINT_SCHEMA_VERSION,
    GRAPH_VERSION,
    ResearchWorkflow,
)

TERMINAL_STATES = {"succeeded", "insufficient_data", "failed", "cancelled", "timed_out"}
PROMPT_TEXT = "ResearchForge bounded earnings-quality conclusion prompt v1.0.0"


def _default_clock() -> datetime:
    return datetime.now(UTC)


class UnsupportedCapabilityError(ValueError):
    """Raised before queueing a mode that is not yet in the G1 thin slice."""


class ResearchRunService:
    """Create, execute, inspect, and cancel one immutable research run."""

    def __init__(
        self,
        repository: FileRunRepository,
        fixture_catalog: G0FixtureCatalog,
        workflow: ResearchWorkflow,
        *,
        skill_version: str,
        skill_hash: str,
        verifier: FinancialVerifier | None = None,
        database_index: DatabaseIndex | None = None,
        clock: Callable[[], datetime] = _default_clock,
    ) -> None:
        self.repository = repository
        self.fixture_catalog = fixture_catalog
        self.workflow = workflow
        self.skill_version = skill_version
        self.skill_hash = skill_hash
        self.verifier = verifier or FinancialVerifier(clock=clock)
        self.database_index = database_index
        self.clock = clock

    @classmethod
    def build(
        cls,
        artifact_root: Path,
        fixture_root: Path,
        skill_manifest_path: Path,
        database_url: str | None = None,
    ) -> ResearchRunService:
        skill_manifest = json.loads(skill_manifest_path.read_text(encoding="utf-8"))
        skill_version = str(skill_manifest["version"])
        skill_hash = str(skill_manifest["content_hash"])
        catalog = G0FixtureCatalog(fixture_root)
        checkpointer = DurableJsonCheckpointSaver(
            artifact_root / "checkpoints" / "langgraph-checkpoints.json"
        )
        workflow = ResearchWorkflow(
            catalog.load,
            EarningsQualityAnalyzer(),
            DeterministicConclusionGenerator(),
            skill_version=skill_version,
            skill_hash=skill_hash,
            checkpointer=checkpointer,
        )
        database_index = (
            DatabaseIndex(database_url, artifact_root=artifact_root)
            if database_url is not None
            else None
        )
        if database_index is not None:
            database_index.mirror_skill(skill_manifest)
            database_index.mirror_sources(catalog.source_documents)
        return cls(
            FileRunRepository(artifact_root),
            catalog,
            workflow,
            skill_version=skill_version,
            skill_hash=skill_hash,
            database_index=database_index,
        )

    def _mirror(self, manifest: dict[str, Any]) -> None:
        if self.database_index is not None:
            self.database_index.mirror_run(
                manifest,
                self.repository.artifact_references(str(manifest["run_id"])),
            )

    def _manifest(self, request: ResearchRunRequest, run_id: str) -> dict[str, Any]:
        timestamp = self.clock().isoformat()
        package = self.fixture_catalog.manifest
        request_payload = request.model_dump(mode="json")
        return {
            "schema_version": "1.4.0",
            "run_id": run_id,
            "run_kind": "product",
            "case_id": None,
            "split": None,
            "lifecycle_state": "queued",
            "input": {
                "input_kind": "research",
                "task_type": request_payload["task_type"],
                "research_question": request_payload["research_question"],
                "company_ids": request_payload["company_ids"],
                "requested_period_labels": request_payload["requested_period_labels"],
                "research_time": request_payload["research_time"],
            },
            "configuration": {
                "model": {
                    "provider": "openai",
                    "model_id": "gpt-5.6-luna",
                    "model_snapshot": None,
                    "temperature": None,
                    "seed": None,
                    "reasoning_effort": "medium",
                    "max_output_tokens": 1000,
                    "tool_choice_policy": "controlled",
                    "store": False,
                    "built_in_tools": [],
                },
                "workflow": {
                    "engine": "langgraph",
                    "graph_version": GRAPH_VERSION,
                    "checkpoint_schema_version": CHECKPOINT_SCHEMA_VERSION,
                },
                "skill_version": self.skill_version,
                "skill_hash": self.skill_hash,
                "formula_version": "1.0.0",
                "prompt_hashes": {
                    "research_system": hashlib.sha256(PROMPT_TEXT.encode()).hexdigest()
                },
                "tool_versions": {
                    "financial_tools": "1.0.0",
                    "retrieval": "1.0.0",
                },
                "dataset_package_id": package["package_id"],
                "dataset_package_hash": package["package_hash"],
                "evidence_cutoff": request_payload["research_time"],
            },
            "limits": {
                "timeout_seconds": 300,
                "max_tool_calls": 30,
                "max_total_tokens": 12000,
                "max_estimated_cost": 0.02,
            },
            "attempt": 1,
            "idempotency_key": request.idempotency_key,
            "created_at": timestamp,
            "started_at": None,
            "finished_at": None,
            "artifacts": {
                "explicit_plan_id": None,
                "workflow_trace_id": None,
                "tool_record_ids": [],
                "result_id": None,
                "patch_id": None,
                "evaluation_id": None,
            },
            "usage": None,
            "failure": None,
        }

    def submit(self, request: ResearchRunRequest) -> RunSubmission:
        if (
            request.task_type in {"company_research", "risk_detection"}
            and len(request.requested_period_labels) < 2
        ):
            raise UnsupportedCapabilityError(
                f"{request.task_type} requires at least two comparable periods"
            )
        if request.task_type == "thesis_investigation":
            lowered = request.research_question.casefold()
            prohibited = ("目标价", "股价预测", "买入", "卖出", "price target", "buy or sell")
            if any(term in lowered for term in prohibited):
                raise UnsupportedCapabilityError(
                    "thesis_investigation refuses price predictions and investment advice"
                )
        run_id = f"run_{uuid.uuid4().hex}"
        manifest, created = self.repository.create_or_get(
            request.model_dump(mode="json"),
            run_id,
            self._manifest(request, run_id),
        )
        existing_id = str(manifest["run_id"])
        self._mirror(manifest)
        return RunSubmission(
            run_id=existing_id,
            lifecycle_state=str(manifest["lifecycle_state"]),
            created=created,
            links=RunLinks(
                status=f"/v1/research-runs/{existing_id}",
                result=f"/v1/research-runs/{existing_id}/result",
                trace=f"/v1/research-runs/{existing_id}/trace",
            ),
        )

    def execute(self, run_id: str) -> dict[str, Any]:
        manifest = self.repository.get_manifest(run_id)
        if manifest["lifecycle_state"] in TERMINAL_STATES:
            return manifest
        if self.repository.is_cancel_requested(run_id):
            return self.cancel(run_id)

        resume = manifest["lifecycle_state"] == "running"
        started_at = manifest["started_at"] or self.clock().isoformat()
        trace_id = f"trace_{run_id}"
        manifest = {
            **manifest,
            "lifecycle_state": "running",
            "started_at": started_at,
            "artifacts": {**manifest["artifacts"], "workflow_trace_id": trace_id},
        }
        self.repository.save_manifest(run_id, manifest)
        self._mirror(manifest)
        try:
            outcome = self.workflow.run(
                run_id,
                trace_id,
                manifest["input"],
                resume=resume,
                should_cancel=lambda: self.repository.is_cancel_requested(run_id),
                timeout_seconds=float(manifest["limits"]["timeout_seconds"]),
            )
        except Exception as exc:
            outcome = self.workflow.failed_outcome(run_id, trace_id, manifest["input"], exc)

        self.repository.save_trace(run_id, outcome.trace)
        self.repository.save_plan(
            run_id,
            {"plan_id": f"plan_{run_id}", "run_id": run_id, "steps": outcome.plan},
        )
        self.repository.save_calculations(run_id, outcome.calculations)
        finished_at = self.clock().isoformat()
        artifacts = {
            **manifest["artifacts"],
            "explicit_plan_id": f"plan_{run_id}",
            "result_id": None,
        }
        if outcome.result is not None:
            self.repository.save_result(run_id, outcome.result)
            artifacts["result_id"] = outcome.result["result_id"]
        manifest = {
            **manifest,
            "lifecycle_state": outcome.terminal_state,
            "finished_at": finished_at,
            "artifacts": artifacts,
            "usage": outcome.trace["usage"],
            "failure": outcome.failure,
        }
        self.repository.save_manifest(run_id, manifest)
        self._mirror(manifest)
        return manifest

    def recover_interrupted_runs(self) -> list[str]:
        """Resume every persisted running run after a single-process restart."""
        recovered: list[str] = []
        for run_id in self.repository.list_run_ids():
            if self.repository.get_manifest(run_id)["lifecycle_state"] == "running":
                self.execute(run_id)
                recovered.append(run_id)
        return recovered

    def get_manifest(self, run_id: str) -> dict[str, Any]:
        return self.repository.get_manifest(run_id)

    def get_result(self, run_id: str) -> dict[str, Any]:
        return self.repository.get_result(run_id)

    def get_trace(self, run_id: str) -> dict[str, Any]:
        return self.repository.get_trace(run_id)

    def get_evaluation(self, run_id: str) -> dict[str, Any]:
        return self.repository.get_evaluation(run_id)

    def get_facts(self, run_id: str) -> list[dict[str, Any]]:
        """Resolve the point-in-time facts used by a persisted research run."""
        manifest = self.repository.get_manifest(run_id)
        loaded = self.fixture_catalog.load(
            manifest["input"]["company_ids"],
            manifest["input"]["requested_period_labels"],
            datetime.fromisoformat(manifest["input"]["research_time"]),
        )
        return list(loaded.facts)

    def verify(
        self,
        run_id: str,
        *,
        case_id: str,
        expected_calculations: dict[str, str],
    ) -> dict[str, Any]:
        """Evaluate one completed run against controlled deterministic ground truth."""
        manifest = self.repository.get_manifest(run_id)
        if manifest["lifecycle_state"] != "succeeded":
            raise ValueError("only a succeeded research run can be verified")
        research_time = datetime.fromisoformat(manifest["input"]["research_time"])
        loaded = self.fixture_catalog.load(
            manifest["input"]["company_ids"],
            manifest["input"]["requested_period_labels"],
            research_time,
        )
        evaluation = self.verifier.evaluate(
            case_id=case_id,
            manifest=manifest,
            result=self.repository.get_result(run_id),
            trace=self.repository.get_trace(run_id),
            calculations=self.repository.get_calculations(run_id),
            loaded=loaded,
            expected_calculations=expected_calculations,
        )
        self.repository.save_evaluation(run_id, evaluation)
        manifest = {
            **manifest,
            "artifacts": {
                **manifest["artifacts"],
                "evaluation_id": evaluation["evaluation_id"],
            },
        }
        self.repository.save_manifest(run_id, manifest)
        if self.database_index is not None:
            self.database_index.mirror_evaluation(evaluation)
        self._mirror(manifest)
        return evaluation

    def cancel(self, run_id: str) -> dict[str, Any]:
        manifest = self.repository.get_manifest(run_id)
        if manifest["lifecycle_state"] in TERMINAL_STATES:
            return manifest
        self.repository.request_cancel(run_id)
        if manifest["lifecycle_state"] == "running":
            return manifest
        timestamp = self.clock().isoformat()
        trace_id = manifest["artifacts"]["workflow_trace_id"] or f"trace_{run_id}"
        trace_base = {
            "schema_version": "1.4.0",
            "trace_id": trace_id,
            "run_id": run_id,
            "engine": "langgraph",
            "graph_version": GRAPH_VERSION,
            "checkpoint_schema_version": CHECKPOINT_SCHEMA_VERSION,
            "started_at": manifest["started_at"] or timestamp,
            "finished_at": timestamp,
            "terminal_state": "cancelled",
            "stages": [
                {
                    "sequence": 1,
                    "stage": "understanding_question",
                    "node_version": "1.0.0",
                    "status": "cancelled",
                    "started_at": timestamp,
                    "finished_at": timestamp,
                    "input_artifact_ids": [f"request_{run_id}"],
                    "output_artifact_ids": [],
                    "tool_record_ids": [],
                    "sanitized_summary": "Run cancelled before further tools executed.",
                    "failure_code": "CANCELLED_BY_USER",
                }
            ],
            "repair_attempts": 0,
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "latency_ms": 0,
                "tool_calls": 0,
                "estimated_cost": 0,
                "cost_currency": "USD",
            },
        }
        trace = {
            **trace_base,
            "trace_hash": hashlib.sha256(
                json.dumps(trace_base, sort_keys=True).encode("utf-8")
            ).hexdigest(),
        }
        self.repository.save_trace(run_id, trace)
        failure = {
            "code": "CANCELLED_BY_USER",
            "message": "The run was cancelled by the user.",
            "retryable": False,
        }
        manifest = {
            **manifest,
            "lifecycle_state": "cancelled",
            "finished_at": timestamp,
            "artifacts": {**manifest["artifacts"], "workflow_trace_id": trace_id},
            "usage": trace["usage"],
            "failure": failure,
        }
        self.repository.save_manifest(run_id, manifest)
        self._mirror(manifest)
        return manifest
