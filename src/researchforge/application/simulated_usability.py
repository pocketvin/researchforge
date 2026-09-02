"""Three isolated, explicitly simulated AI usability sessions."""

from __future__ import annotations

import base64
import hashlib
import json
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from researchforge.adapters.evolution_storage import EvolutionArtifactRepository
from researchforge.adapters.openai_responses import (
    LUNA_INPUT_USD_PER_MILLION,
    LUNA_OUTPUT_USD_PER_MILLION,
    ResponsesResource,
    luna_worst_case_cost,
)
from researchforge.application.budget import BudgetLedger
from researchforge.application.evolution import MODEL_CONFIG

SIMULATION_CAP = Decimal("2.00")
SIMULATION_MAX_INPUT_TOKENS = 1_000_000
SIMULATION_MAX_OUTPUT_TOKENS = 2_000
SIMULATION_WORST_CASE = luna_worst_case_cost(
    SIMULATION_MAX_INPUT_TOKENS,
    SIMULATION_MAX_OUTPUT_TOKENS,
)
PERSONAS = (
    (
        "persona_buy_side_analyst",
        "Act as a time-constrained buy-side analyst checking whether the report "
        "supports a decision memo.",
    ),
    (
        "persona_financial_researcher",
        "Act as a financial researcher auditing claim, fact, calculation, evidence, "
        "and limitation links.",
    ),
    (
        "persona_engineering_hiring_manager",
        "Act as an engineering hiring manager assessing product clarity, traceability, "
        "and failure honesty.",
    ),
)


class SimulatedUsabilityBlocked(RuntimeError):
    """Raised before provider contact when bounded simulation prerequisites fail."""


class SimulatedAssessment(BaseModel):
    """Strict model-authored observations; pass/fail is computed locally."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    located_key_change: bool
    located_supporting_evidence: bool
    located_counter_evidence_or_limitation: bool
    located_monitoring_item: bool
    usefulness_score: int = Field(ge=1, le=5)
    auditability_score: int = Field(ge=1, le=5)
    findings: list[str] = Field(min_length=1, max_length=30)


class ResponsesFactory(Protocol):
    """Lazily construct the SDK resource only after preflight passes."""

    def __call__(self) -> ResponsesResource: ...


def _now() -> datetime:
    return datetime.now(UTC)


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _actual_cost(input_tokens: int, output_tokens: int) -> Decimal:
    return (
        Decimal(input_tokens) * LUNA_INPUT_USD_PER_MILLION
        + Decimal(output_tokens) * LUNA_OUTPUT_USD_PER_MILLION
    ) / Decimal(1_000_000)


class SimulatedUsabilityRunner:
    """Run exactly three fresh Responses calls over the same persisted evidence."""

    def __init__(
        self,
        *,
        batch_id: str,
        run_bundle: dict[str, Any],
        screenshots: Mapping[str, Path],
        artifact_root: Path,
        ledger: BudgetLedger,
        rotated_key_ready: bool,
        responses_factory: ResponsesFactory | None,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self.batch_id = batch_id
        self.run_bundle = run_bundle
        self.screenshots = {kind: path.resolve() for kind, path in screenshots.items()}
        self.artifact_root = artifact_root.resolve()
        self.ledger = ledger
        self.rotated_key_ready = rotated_key_ready
        self.responses_factory = responses_factory
        self.clock = clock
        self.repository = EvolutionArtifactRepository(self.artifact_root)

    def _ui_evidence(self) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for kind, path in sorted(self.screenshots.items()):
            evidence.append(
                {
                    "screen_kind": kind,
                    "content_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "media_type": "image/png",
                    "description": {
                        "research": (
                            "Research page with task controls, persisted result, financial facts, "
                            "claim-to-evidence links, calculations, monitoring triggers, "
                            "counter-evidence, limitations, and trace."
                        ),
                        "skill_lab": (
                            "Skill Lab page with experiment status, failure cluster, Experience, "
                            "Skill Diff, validation decision, and sealed Final Test state."
                        ),
                    }[kind],
                }
            )
        return evidence

    def preflight(self) -> dict[str, Any]:
        """Validate evidence, isolation, and maximum spend without provider contact."""
        blockers: list[str] = []
        required_bundle = {
            "manifest",
            "result",
            "trace",
            "facts",
            "evidence",
            "calculations",
        }
        if set(self.run_bundle) != required_bundle:
            blockers.append(
                "run bundle must contain manifest, result, trace, facts, evidence, and "
                "calculations only"
            )
        manifest = self.run_bundle.get("manifest", {})
        result = self.run_bundle.get("result", {})
        trace = self.run_bundle.get("trace", {})
        run_id = manifest.get("run_id") if isinstance(manifest, dict) else None
        if not isinstance(run_id, str) or manifest.get("lifecycle_state") != "succeeded":
            blockers.append("simulation requires one persisted succeeded run")
        if not isinstance(result, dict) or result.get("run_id") != run_id:
            blockers.append("result does not resolve to the persisted run")
        if not isinstance(trace, dict) or trace.get("run_id") != run_id:
            blockers.append("trace does not resolve to the persisted run")
        if not isinstance(self.run_bundle.get("facts"), list):
            blockers.append("facts must be a persisted JSON array")
        if not isinstance(self.run_bundle.get("evidence"), list):
            blockers.append("evidence must be a persisted JSON array")
        if not isinstance(self.run_bundle.get("calculations"), list):
            blockers.append("calculations must be a persisted JSON array")
        if set(self.screenshots) != {"research", "skill_lab"}:
            blockers.append("research and skill_lab screenshots are both required")
        else:
            for kind, path in self.screenshots.items():
                if not path.is_file() or path.suffix.lower() != ".png":
                    blockers.append(f"{kind} screenshot is missing or is not PNG")
                elif path.stat().st_size > 5_000_000:
                    blockers.append(f"{kind} screenshot exceeds the 5 MB bound")
                elif not path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
                    blockers.append(f"{kind} screenshot does not contain a PNG signature")
        if not self.rotated_key_ready:
            blockers.append("rotated local OpenAI key is not confirmed ready")
        if self.responses_factory is None and self.rotated_key_ready:
            blockers.append("Responses client factory is unavailable")

        maximum_batch_cost = SIMULATION_WORST_CASE * len(PERSONAS)
        snapshot = self.ledger.snapshot()
        if maximum_batch_cost > SIMULATION_CAP:
            blockers.append("simulation worst-case cost exceeds the USD 2 simulation cap")
        if snapshot.spent + snapshot.reserved + maximum_batch_cost > snapshot.cap:
            blockers.append("simulation worst-case cost exceeds the aggregate project budget")
        shared_input = {
            "run_bundle": self.run_bundle,
            "ui_evidence": self._ui_evidence()
            if not any("screenshot" in b for b in blockers)
            else [],
        }
        return {
            "schema_version": "1.4.0",
            "batch_id": self.batch_id,
            "status": "PASS" if not blockers else "BLOCKED",
            "evidence_label": "SIMULATED",
            "provider_contacted": False,
            "run_id": run_id,
            "session_count": 3,
            "shared_input_hash": _canonical_hash(shared_input),
            "fresh_context_per_session": True,
            "prior_session_outputs_included": False,
            "human_user_value_validated": False,
            "budget": {
                "aggregate_cap": format(snapshot.cap, "f"),
                "aggregate_spent": format(snapshot.spent, "f"),
                "simulation_cap": format(SIMULATION_CAP, "f"),
                "per_session_worst_case": format(SIMULATION_WORST_CASE, "f"),
                "batch_worst_case": format(maximum_batch_cost, "f"),
            },
            "blockers": blockers,
        }

    @staticmethod
    def _instructions(persona_instruction: str) -> str:
        return (
            "This is an AI-simulated usability inspection, not a real user study and not an "
            "investment recommendation. Use only the supplied persisted artifacts and UI images. "
            "Do not use outside knowledge or infer missing facts. Retain dissent, factual errors, "
            "usability blockers, and unknowns in findings. "
            + persona_instruction
            + " Locate the key reported change, its supporting evidence, one counter-evidence item "
            "or limitation, and one monitoring item. Score presentation usefulness and "
            "auditability."
        )

    def _input(self, persona_id: str, persona_instruction: str) -> list[dict[str, Any]]:
        shared = {
            "evidence_label": "SIMULATED",
            "persona_id": persona_id,
            "run_bundle": self.run_bundle,
            "ui_evidence": self._ui_evidence(),
        }
        content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": json.dumps(shared, ensure_ascii=False, sort_keys=True),
            }
        ]
        for path in self.screenshots.values():
            encoded = base64.b64encode(path.read_bytes()).decode()
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{encoded}",
                    "detail": "high",
                }
            )
        return [{"role": "user", "content": content}]

    def _evaluate(
        self,
        responses: ResponsesResource,
        *,
        session_number: int,
        persona_id: str,
        persona_instruction: str,
        run_id: str,
        shared_input_hash: str,
    ) -> dict[str, Any]:
        context_kind = f"session-{session_number}-context"
        evaluation_kind = f"session-{session_number}"
        try:
            context = self.repository.get(self.batch_id, context_kind)
            evaluation = self.repository.get(self.batch_id, evaluation_kind)
            if (
                context.get("shared_input_hash") == shared_input_hash
                and evaluation.get("persona_id") == persona_id
                and evaluation.get("run_id") == run_id
            ):
                return evaluation
            raise SimulatedUsabilityBlocked("persisted simulation context changed")
        except KeyError:
            pass

        reservation_id = self.ledger.reserve(SIMULATION_WORST_CASE)
        started = time.perf_counter()
        try:
            response = responses.create(
                model="gpt-5.6-luna",
                instructions=self._instructions(persona_instruction),
                input=self._input(persona_id, persona_instruction),
                reasoning={"effort": "medium"},
                max_output_tokens=SIMULATION_MAX_OUTPUT_TOKENS,
                store=False,
                tools=[],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "researchforge_simulated_usability_assessment",
                        "strict": True,
                        "schema": SimulatedAssessment.model_json_schema(),
                    }
                },
            )
            input_tokens = int(response.usage.input_tokens)
            output_tokens = int(response.usage.output_tokens)
            actual_cost = _actual_cost(input_tokens, output_tokens)
            if actual_cost > SIMULATION_WORST_CASE:
                raise RuntimeError("actual simulation cost exceeded its worst-case reservation")
            self.ledger.complete(reservation_id, actual_cost)
        except Exception:
            # Treat an indeterminate transport outcome as fully spent rather than
            # undercounting a request that may already have reached the provider.
            self.ledger.complete(reservation_id, SIMULATION_WORST_CASE)
            raise
        try:
            assessment = SimulatedAssessment.model_validate_json(cast(str, response.output_text))
        except ValidationError as exc:
            raise RuntimeError("simulated usability output failed validation") from exc
        elapsed_ms = max(0, int((time.perf_counter() - started) * 1000))
        located_all = all(
            (
                assessment.located_key_change,
                assessment.located_supporting_evidence,
                assessment.located_counter_evidence_or_limitation,
                assessment.located_monitoring_item,
            )
        )
        evaluation = {
            "schema_version": "1.4.0",
            "evaluation_id": f"{self.batch_id}_session_{session_number}",
            "evidence_label": "SIMULATED",
            "session_number": session_number,
            "persona_id": persona_id,
            "run_id": run_id,
            "model": {**MODEL_CONFIG, "max_output_tokens": SIMULATION_MAX_OUTPUT_TOKENS},
            **assessment.model_dump(mode="json"),
            "passed": located_all,
            "human_user_value_validated": False,
            "created_at": self.clock().isoformat(),
        }
        self.repository.save(
            self.batch_id,
            context_kind,
            {
                "schema_version": "1.4.0",
                "evidence_label": "SIMULATED",
                "session_number": session_number,
                "shared_input_hash": shared_input_hash,
                "fresh_context": True,
                "prior_session_outputs_included": False,
                "store": False,
                "provider_response_id": getattr(response, "id", None),
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "estimated_cost": format(actual_cost, "f"),
                    "currency": "USD",
                    "latency_ms": elapsed_ms,
                },
            },
        )
        self.repository.save(self.batch_id, evaluation_kind, evaluation)
        return evaluation

    def run(self) -> dict[str, Any]:
        """Run or idempotently resume the bounded three-session batch."""
        preflight = self.preflight()
        self.repository.save(self.batch_id, "preflight", preflight)
        if preflight["status"] != "PASS":
            raise SimulatedUsabilityBlocked("; ".join(preflight["blockers"]))
        try:
            existing = self.repository.get(self.batch_id, "batch")
            if existing.get("shared_input_hash") != preflight["shared_input_hash"]:
                raise SimulatedUsabilityBlocked("completed simulation input changed")
            return existing
        except KeyError:
            pass
        if self.responses_factory is None:
            raise SimulatedUsabilityBlocked("Responses client factory is unavailable")
        responses = self.responses_factory()
        run_id = str(preflight["run_id"])
        evaluations = [
            self._evaluate(
                responses,
                session_number=index,
                persona_id=persona_id,
                persona_instruction=instruction,
                run_id=run_id,
                shared_input_hash=str(preflight["shared_input_hash"]),
            )
            for index, (persona_id, instruction) in enumerate(PERSONAS, start=1)
        ]
        high_score_count = sum(
            evaluation["usefulness_score"] >= 4 and evaluation["auditability_score"] >= 4
            for evaluation in evaluations
        )
        passed = all(evaluation["passed"] for evaluation in evaluations) and high_score_count >= 2
        snapshot = self.ledger.snapshot()
        batch = {
            "schema_version": "1.4.0",
            "batch_id": self.batch_id,
            "status": "PASS" if passed else "FAIL",
            "evidence_label": "SIMULATED",
            "run_id": run_id,
            "session_count": 3,
            "shared_input_hash": preflight["shared_input_hash"],
            "fresh_context_per_session": True,
            "prior_session_outputs_included": False,
            "high_score_session_count": high_score_count,
            "evaluation_ids": [evaluation["evaluation_id"] for evaluation in evaluations],
            "human_user_value_validated": False,
            "disclosure": (
                "AI-simulated presentation and navigation evidence only; real-user value and "
                "market demand remain unvalidated."
            ),
            "aggregate_spent_after": format(snapshot.spent, "f"),
            "completed_at": self.clock().isoformat(),
        }
        self.repository.save(self.batch_id, "batch", batch)
        return batch
