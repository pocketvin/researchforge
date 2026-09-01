"""One bounded provider calibration before any formal benchmark run."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

from researchforge.adapters.evolution_storage import EvolutionArtifactRepository
from researchforge.application.budget import BudgetLedger
from researchforge.application.evolution import MODEL_CONFIG
from researchforge.application.research import ConclusionDraft

CALIBRATION_ID = "calibration_v1_4_001"
CALIBRATION_CAP = Decimal("1.00")
REQUIRED_CHECK_CODES = {
    "operating_cash_flow",
    "accounts_receivable",
    "inventory",
    "cash_conversion",
    "profit_cash_divergence",
    "one_off_contribution",
    "counter_evidence",
}
CALIBRATION_CONTEXT: dict[str, Any] = {
    "evidence_class": "SYNTHETIC_CALIBRATION_ONLY_NOT_RESEARCH_EVIDENCE",
    "question": "Check whether the supplied synthetic profit is supported by cash conversion.",
    "facts": {
        "net_income": "100.00",
        "operating_cash_flow": "120.00",
        "accounts_receivable": "40.00",
        "inventory": "30.00",
    },
    "precomputed_calculations": {
        "cash_conversion": "1.20",
        "profit_cash_divergence": "0",
        "one_off_contribution": "unavailable",
    },
    "counter_evidence": {
        "performed": True,
        "result": "not_found",
        "summary": "No additional item exists inside this synthetic calibration payload.",
    },
    "required_check_codes": sorted(REQUIRED_CHECK_CODES),
    "constraints": [
        "Do not add facts, calculations, sources, companies, or investment advice.",
        "Explicitly address every required_check_code and report exactly those codes.",
    ],
}


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


CALIBRATION_CONTEXT_HASH = _canonical_hash(CALIBRATION_CONTEXT)


class CalibrationBlocked(RuntimeError):
    """Raised before provider contact when calibration prerequisites fail."""


class CalibrationGenerator(Protocol):
    """Narrow provider generator surface used by the calibration runner."""

    @property
    def prompt_hashes(self) -> dict[str, str]: ...

    @property
    def worst_case_cost(self) -> Decimal: ...

    @property
    def usage(self) -> dict[str, int | float | str]: ...

    def begin_run(self) -> None: ...

    def generate(self, context: dict[str, Any]) -> ConclusionDraft: ...


GeneratorFactory = Callable[[BudgetLedger], CalibrationGenerator]


def calibration_artifact_passed(artifact_root: Path) -> bool:
    """Return true only for the pinned, successful, synthetic calibration artifact."""
    try:
        artifact = EvolutionArtifactRepository(artifact_root).get(CALIBRATION_ID, "calibration")
    except KeyError:
        return False
    return bool(
        artifact.get("status") == "PASS"
        and artifact.get("evidence_class") == "SYNTHETIC_CALIBRATION_ONLY_NOT_RESEARCH_EVIDENCE"
        and artifact.get("context_hash") == CALIBRATION_CONTEXT_HASH
        and artifact.get("model") == MODEL_CONFIG
        and artifact.get("provider_contacted") is True
    )


class OpenAICalibrationRunner:
    """Calibrate exactly one synthetic request and persist auditable evidence."""

    def __init__(
        self,
        *,
        artifact_root: Path,
        ledger: BudgetLedger,
        rotated_key_ready: bool,
        generator_factory: GeneratorFactory | None,
        worst_case_cost: Decimal,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.artifact_root = artifact_root.resolve()
        self.ledger = ledger
        self.rotated_key_ready = rotated_key_ready
        self.generator_factory = generator_factory
        self.worst_case_cost = worst_case_cost
        self.clock = clock or (lambda: datetime.now(UTC))
        self.repository = EvolutionArtifactRepository(self.artifact_root)

    def preflight(self) -> dict[str, Any]:
        """Check key and budget boundaries without constructing a provider client."""
        blockers: list[str] = []
        if not self.rotated_key_ready:
            blockers.append("rotated local OpenAI key is not confirmed ready")
        if self.generator_factory is None and self.rotated_key_ready:
            blockers.append("calibration generator factory is unavailable")
        snapshot = self.ledger.snapshot()
        if self.worst_case_cost > CALIBRATION_CAP:
            blockers.append("calibration request exceeds the USD 1 calibration cap")
        if snapshot.spent + snapshot.reserved + self.worst_case_cost > snapshot.cap:
            blockers.append("calibration request exceeds the aggregate project budget")
        return {
            "schema_version": "1.4.0",
            "calibration_id": CALIBRATION_ID,
            "status": "PASS" if not blockers else "BLOCKED",
            "evidence_class": "SYNTHETIC_CALIBRATION_ONLY_NOT_RESEARCH_EVIDENCE",
            "provider_contacted": False,
            "context_hash": CALIBRATION_CONTEXT_HASH,
            "model": MODEL_CONFIG,
            "budget": {
                "aggregate_cap": format(snapshot.cap, "f"),
                "aggregate_spent": format(snapshot.spent, "f"),
                "calibration_cap": format(CALIBRATION_CAP, "f"),
                "request_worst_case": format(self.worst_case_cost, "f"),
            },
            "blockers": blockers,
        }

    def run(self) -> dict[str, Any]:
        """Run once or return the existing immutable successful calibration."""
        preflight = self.preflight()
        self.repository.save(CALIBRATION_ID, "preflight", preflight)
        if preflight["status"] != "PASS":
            raise CalibrationBlocked("; ".join(preflight["blockers"]))
        try:
            existing = self.repository.get(CALIBRATION_ID, "calibration")
            if not calibration_artifact_passed(self.artifact_root):
                raise CalibrationBlocked("existing calibration artifact is not valid")
            return existing
        except KeyError:
            pass
        if self.generator_factory is None:
            raise CalibrationBlocked("calibration generator factory is unavailable")
        generator = self.generator_factory(self.ledger)
        if generator.worst_case_cost != self.worst_case_cost:
            raise CalibrationBlocked("calibration generator cost boundary changed")
        generator.begin_run()
        draft = generator.generate(CALIBRATION_CONTEXT)
        reported = set(draft.reported_check_codes or [])
        if reported != REQUIRED_CHECK_CODES:
            raise RuntimeError("calibration output did not explicitly cover every required check")
        snapshot = self.ledger.snapshot()
        artifact = {
            "schema_version": "1.4.0",
            "calibration_id": CALIBRATION_ID,
            "status": "PASS",
            "evidence_class": "SYNTHETIC_CALIBRATION_ONLY_NOT_RESEARCH_EVIDENCE",
            "provider_contacted": True,
            "context_hash": CALIBRATION_CONTEXT_HASH,
            "output_hash": _canonical_hash(draft.model_dump(mode="json")),
            "model": MODEL_CONFIG,
            "prompt_hashes": generator.prompt_hashes,
            "usage": generator.usage,
            "aggregate_spent_after": format(snapshot.spent, "f"),
            "research_hypothesis_supported": False,
            "created_at": self.clock().isoformat(),
        }
        self.repository.save(CALIBRATION_ID, "calibration", artifact)
        return artifact
