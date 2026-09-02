"""Controlled activation and execution of the single sealed V1.5 contingency."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from researchforge.adapters.evolution_storage import EvolutionArtifactRepository
from researchforge.application.budget import BudgetLedger
from researchforge.application.formal_experiment import (
    FormalExperimentRunner,
    _canonical_hash,
    _load_json,
    _sha256,
    formal_run_plan,
)

CONTINGENCY_EXPERIMENT_CAP = Decimal("6.00")
PRIMARY_EXPERIMENT_ID = "experiment_primary_v1_4_001"
CONTINGENCY_EXPERIMENT_ID = "experiment_contingency_v1_5_001"
NEGATIVE_OUTCOMES = {
    "NO_ELIGIBLE_CLUSTER",
    "REJECTED_VALIDATION",
    "REJECTED_FINAL",
}
TERMINAL_OUTCOMES = {*NEGATIVE_OUTCOMES, "SUPPORTED"}
AUTHORIZATION_BASIS = "V1.4_SCOPE_ANY_UNSUPPORTED_PRIMARY"
FROZEN_PACKAGE_PREDICATE = "PRIMARY_VALIDATION_REJECTS_CANDIDATE"
NEGATIVE_ARTIFACT_KINDS = (
    "experiment",
    "run-plan",
    "preflight",
    "budget-baseline",
    "base-evolution-evaluations",
    "seed-evolution-evaluations",
    "progress",
)
CONTINGENCY_TERMINAL_REQUIRED_KINDS = (
    "experiment",
    "run-plan",
    "preflight",
    "budget-baseline",
    "base-evolution-evaluations",
    "seed-evolution-evaluations",
    "progress",
)
CONTINGENCY_TERMINAL_OPTIONAL_KINDS = (
    "technical-retries",
    "failure-cluster",
    "experience",
    "patch",
    "candidate-skill",
    "seed-validation-evaluations",
    "candidate-validation-evaluations",
    "validation-decision",
    "final-test-consumption",
    "seed-final_test-evaluations",
    "candidate-final_test-evaluations",
)


def _now() -> datetime:
    return datetime.now(UTC)


def _primary_negative_core(
    repository: EvolutionArtifactRepository,
    primary_experiment_id: str,
) -> dict[str, Any]:
    experiment = repository.get(primary_experiment_id, "experiment")
    if experiment.get("status") != "completed":
        raise ValueError("primary experiment is not terminal")
    outcome = str(experiment.get("outcome"))
    if outcome not in NEGATIVE_OUTCOMES:
        raise ValueError("primary experiment is not an eligible unsupported outcome")
    artifacts = {
        kind: repository.get(primary_experiment_id, kind) for kind in NEGATIVE_ARTIFACT_KINDS
    }
    return {
        "schema_version": "1.4.0",
        "primary_experiment_id": primary_experiment_id,
        "status": "FROZEN_NEGATIVE_RESULT",
        "outcome": outcome,
        "research_hypothesis_supported": False,
        "run_count": len(experiment["run_ids"]),
        "evaluation_count": len(experiment["evaluation_ids"]),
        "candidate_skill_version_id": experiment["candidate_skill_version_id"],
        "final_test_consumed": experiment["final_test_consumed"],
        "budget": experiment["budget"],
        "finished_at": experiment["finished_at"],
        "artifact_hashes": {
            kind: _canonical_hash(payload) for kind, payload in sorted(artifacts.items())
        },
    }


def freeze_and_activate_contingency(
    *,
    artifact_root: Path,
    package_root: Path,
    primary_experiment_id: str = PRIMARY_EXPERIMENT_ID,
    contingency_experiment_id: str = CONTINGENCY_EXPERIMENT_ID,
    clock: Callable[[], datetime] = _now,
) -> dict[str, Any]:
    """Freeze the unsupported primary result and authorize exactly one V1.5 runtime."""
    repository = EvolutionArtifactRepository(artifact_root)
    core = _primary_negative_core(repository, primary_experiment_id)
    negative_result_hash = _canonical_hash(core)
    try:
        existing_freeze = repository.get(primary_experiment_id, "negative-result-freeze")
        created_at = str(existing_freeze["created_at"])
    except KeyError:
        existing_freeze = None
        created_at = clock().isoformat()
    freeze = {
        **core,
        "negative_result_hash": negative_result_hash,
        "created_at": created_at,
    }
    if existing_freeze is not None and existing_freeze != freeze:
        raise ValueError("existing primary negative-result freeze differs from current artifacts")
    repository.save(primary_experiment_id, "negative-result-freeze", freeze)

    manifest = _load_json(package_root.resolve() / "manifest.json")
    if manifest.get("evidence_status") != "FROZEN_CONTINGENCY_SEALED":
        raise ValueError("contingency package is not frozen and sealed")
    if manifest.get("formal_run_authorized") is not False:
        raise ValueError("frozen contingency manifest authorization changed")
    if manifest.get("contingency_activation_authorized") is not False:
        raise ValueError("frozen contingency activation flag changed")
    if manifest.get("sealed_until") != FROZEN_PACKAGE_PREDICATE:
        raise ValueError("frozen contingency activation predicate changed")
    activation_core = {
        "schema_version": "1.4.0",
        "contingency_experiment_id": contingency_experiment_id,
        "status": "ACTIVATED_ONCE",
        "authorization_basis": AUTHORIZATION_BASIS,
        "primary_experiment_id": primary_experiment_id,
        "primary_outcome": core["outcome"],
        "primary_negative_result_hash": negative_result_hash,
        "contingency_package_id": manifest["package_id"],
        "contingency_package_hash": manifest["package_hash"],
        "activation_count": 1,
        "protocol_deviation": {
            "code": "FROZEN_ACTIVATION_PREDICATE_TOO_NARROW",
            "frozen_package_predicate": FROZEN_PACKAGE_PREDICATE,
            "applied_scope_rule": AUTHORIZATION_BASIS,
            "data_or_threshold_changed": False,
            "explanation": (
                "The controlling V1.4 scope requires the one disjoint contingency after any "
                "unsupported primary result; the frozen package field named only Validation "
                "rejection. The package, companies, cases, truth, model, graph, and thresholds "
                "remain unchanged."
            ),
        },
    }
    try:
        existing_activation = repository.get(contingency_experiment_id, "activation")
        activated_at = str(existing_activation["activated_at"])
    except KeyError:
        existing_activation = None
        activated_at = clock().isoformat()
    activation = {
        **activation_core,
        "activation_hash": _canonical_hash(activation_core),
        "activated_at": activated_at,
    }
    if existing_activation is not None and existing_activation != activation:
        raise ValueError("contingency was already activated with different evidence")
    repository.save(contingency_experiment_id, "activation", activation)
    return {"negative_result_freeze": freeze, "activation": activation}


def preflight_contingency_experiment(
    *,
    package_root: Path,
    private_ground_truth_root: Path,
    suite_path: Path,
    seed_manifest_path: Path,
    seed_content_path: Path,
    artifact_root: Path,
    primary_experiment_id: str,
    contingency_experiment_id: str,
    ledger: BudgetLedger,
    rotated_key_ready: bool,
    calibration_ready: bool,
    worst_case_request_cost: Decimal,
) -> dict[str, Any]:
    """Validate the sealed package and runtime activation without provider contact."""
    package_root = package_root.resolve()
    private_ground_truth_root = private_ground_truth_root.resolve()
    suite_path = suite_path.resolve()
    project_root = package_root.parents[2]
    manifest = _load_json(package_root / "manifest.json")
    blockers: list[str] = []
    if manifest.get("evidence_status") != "FROZEN_CONTINGENCY_SEALED":
        blockers.append("contingency package is not frozen and sealed")
    if manifest.get("formal_run_authorized") is not False:
        blockers.append("frozen contingency formal authorization changed")
    if manifest.get("contingency_activation_authorized") is not False:
        blockers.append("frozen contingency activation flag changed")
    if manifest.get("sealed_until") != FROZEN_PACKAGE_PREDICATE:
        blockers.append("frozen contingency activation predicate changed")
    if not rotated_key_ready:
        blockers.append("rotated local OpenAI key is not confirmed ready")
    if not calibration_ready:
        blockers.append("pinned OpenAI calibration has not passed")

    repository = EvolutionArtifactRepository(artifact_root)
    try:
        freeze = repository.get(primary_experiment_id, "negative-result-freeze")
        current_core = _primary_negative_core(repository, primary_experiment_id)
        current_hash = _canonical_hash(current_core)
        if freeze.get("negative_result_hash") != current_hash:
            blockers.append("primary negative-result freeze hash differs from current artifacts")
    except (KeyError, ValueError):
        freeze = {}
        current_hash = None
        blockers.append("eligible frozen primary negative result is missing")
    try:
        activation = repository.get(contingency_experiment_id, "activation")
    except KeyError:
        activation = {}
        blockers.append("one-time contingency activation record is missing")
    if activation:
        if activation.get("status") != "ACTIVATED_ONCE":
            blockers.append("contingency activation status changed")
        if activation.get("activation_count") != 1:
            blockers.append("contingency activation count must remain one")
        if activation.get("authorization_basis") != AUTHORIZATION_BASIS:
            blockers.append("contingency authorization basis changed")
        if activation.get("primary_negative_result_hash") != current_hash:
            blockers.append("contingency activation does not bind the frozen primary result")
        if activation.get("contingency_package_hash") != manifest.get("package_hash"):
            blockers.append("contingency activation does not bind the frozen package")

    public_hashes = manifest.get("public_artifact_hashes", {})
    if not isinstance(public_hashes, dict) or len(public_hashes) != 216:
        blockers.append("contingency public artifact hash catalog must contain 216 artifacts")
    else:
        for relative, expected_hash in public_hashes.items():
            path = (project_root / str(relative)).resolve()
            if project_root not in path.parents or not path.is_file():
                blockers.append(f"contingency public artifact is missing: {relative}")
                continue
            if _sha256(path) != expected_hash:
                blockers.append(f"contingency public artifact hash mismatch: {relative}")

    cases = {
        case["case_id"]: case
        for path in sorted((package_root / "cases").glob("*.json"))
        for case in (_load_json(path),)
    }
    if len(cases) != 24:
        blockers.append("contingency package must contain exactly 24 cases")
    if any(case.get("package_hash") != manifest.get("package_hash") for case in cases.values()):
        blockers.append("contingency case package hashes differ from its manifest")
    primary_groups = {
        str(_load_json(path).get("group_key"))
        for path in (project_root / "data" / "fixtures" / "v1.4-primary" / "cases").glob("*.json")
    }
    if primary_groups & {str(case.get("group_key")) for case in cases.values()}:
        blockers.append("contingency company group overlaps the primary experiment")

    truth_hashes = manifest.get("ground_truth_hashes", {})
    if not isinstance(truth_hashes, dict) or set(truth_hashes) != set(cases):
        blockers.append("contingency ground-truth hash catalog differs from cases")
    else:
        for case_id, expected_hash in truth_hashes.items():
            truth_path = private_ground_truth_root / f"ground_truth_{case_id}.json"
            if not truth_path.is_file() or _sha256(truth_path) != expected_hash:
                blockers.append(f"contingency verifier-only ground truth mismatch: {case_id}")

    if not suite_path.is_file() or manifest.get("preregistered_suite_hash") != _sha256(suite_path):
        blockers.append("contingency preregistered suite hash differs from its manifest")
    sources = {
        source["document_id"]: source
        for path in sorted((package_root / "source-documents").glob("*.json"))
        for source in (_load_json(path),)
    }
    facts = {
        fact["fact_id"]: fact
        for path in sorted((package_root / "financial-facts").glob("*.json"))
        for fact in (_load_json(path),)
    }
    chunks = {
        chunk["chunk_id"]: chunk
        for path in sorted((package_root / "evidence-chunks").glob("*.json"))
        for chunk in (_load_json(path),)
    }
    if suite_path.is_file() and isinstance(truth_hashes, dict):
        data_hashes = {
            **{f"source:{key}": _canonical_hash(value) for key, value in sources.items()},
            **{f"fact:{key}": _canonical_hash(value) for key, value in facts.items()},
            **{f"chunk:{key}": _canonical_hash(value) for key, value in chunks.items()},
            **{
                f"ground_truth:{key}": value
                for key, value in cast(dict[str, str], truth_hashes).items()
            },
            "preregistered_suite": _sha256(suite_path),
        }
        if _canonical_hash(data_hashes) != manifest.get("package_hash"):
            blockers.append("contingency package hash does not match frozen inputs")

    seed_manifest = _load_json(seed_manifest_path)
    if _sha256(seed_content_path) != seed_manifest.get("content_hash"):
        blockers.append("Seed Skill content hash differs from its manifest")
    if seed_manifest.get("status") != "seed":
        blockers.append("Seed Skill manifest is not frozen as seed")

    plan = formal_run_plan()
    maximum_requests = int(plan["maximum_provider_requests_with_one_repair_per_run"])
    experiment_worst_case = worst_case_request_cost * maximum_requests
    snapshot = ledger.snapshot()
    if experiment_worst_case > CONTINGENCY_EXPERIMENT_CAP:
        blockers.append("contingency worst-case requests exceed the USD 6 cap")
    if snapshot.spent + snapshot.reserved + experiment_worst_case > snapshot.cap:
        blockers.append("contingency worst-case requests exceed aggregate project budget")
    return {
        "schema_version": "1.4.0",
        "status": "PASS" if not blockers else "BLOCKED",
        "provider_contacted": False,
        "experiment_id": contingency_experiment_id,
        "package_id": manifest.get("package_id"),
        "package_hash": manifest.get("package_hash"),
        "primary_negative_result_hash": current_hash,
        "case_count": len(cases),
        "private_ground_truth_hash_count": len(truth_hashes),
        "rotated_key_ready": rotated_key_ready,
        "activation_status": activation.get("status"),
        "budget": {
            "aggregate_cap": format(snapshot.cap, "f"),
            "aggregate_spent": format(snapshot.spent, "f"),
            "aggregate_reserved": format(snapshot.reserved, "f"),
            "contingency_cap": format(CONTINGENCY_EXPERIMENT_CAP, "f"),
            "worst_case_request_cost": format(worst_case_request_cost, "f"),
            "experiment_worst_case": format(experiment_worst_case, "f"),
        },
        "run_plan": plan,
        "blockers": blockers,
    }


def freeze_final_contingency_outcome(
    *,
    artifact_root: Path,
    primary_experiment_id: str = PRIMARY_EXPERIMENT_ID,
    contingency_experiment_id: str = CONTINGENCY_EXPERIMENT_ID,
    clock: Callable[[], datetime] = _now,
) -> dict[str, Any]:
    """Freeze the second formal result and its honest project research conclusion."""
    repository = EvolutionArtifactRepository(artifact_root)
    primary_freeze = repository.get(primary_experiment_id, "negative-result-freeze")
    experiment = repository.get(contingency_experiment_id, "experiment")
    outcome = str(experiment.get("outcome"))
    if experiment.get("status") != "completed" or outcome not in TERMINAL_OUTCOMES:
        raise ValueError("contingency experiment is not terminal")

    artifacts = {
        kind: repository.get(contingency_experiment_id, kind)
        for kind in CONTINGENCY_TERMINAL_REQUIRED_KINDS
    }
    for kind in CONTINGENCY_TERMINAL_OPTIONAL_KINDS:
        try:
            artifacts[kind] = repository.get(contingency_experiment_id, kind)
        except KeyError:
            continue
    core = {
        "schema_version": "1.4.0",
        "contingency_experiment_id": contingency_experiment_id,
        "scope_version": "1.5",
        "status": "FROZEN_TERMINAL_RESULT",
        "outcome": outcome,
        "research_hypothesis_supported": outcome == "SUPPORTED",
        "run_count": len(experiment["run_ids"]),
        "evaluation_count": len(experiment["evaluation_ids"]),
        "candidate_skill_version_id": experiment["candidate_skill_version_id"],
        "final_test_consumed": experiment["final_test_consumed"],
        "budget": experiment["budget"],
        "finished_at": experiment["finished_at"],
        "primary_experiment_id": primary_experiment_id,
        "primary_outcome": primary_freeze["outcome"],
        "primary_negative_result_hash": primary_freeze["negative_result_hash"],
        "artifact_hashes": {
            kind: _canonical_hash(payload) for kind, payload in sorted(artifacts.items())
        },
    }
    terminal_result_hash = _canonical_hash(core)
    try:
        existing = repository.get(contingency_experiment_id, "terminal-result-freeze")
        created_at = str(existing["created_at"])
    except KeyError:
        existing = None
        created_at = clock().isoformat()
    terminal_freeze = {
        **core,
        "terminal_result_hash": terminal_result_hash,
        "created_at": created_at,
    }
    if existing is not None and existing != terminal_freeze:
        raise ValueError("existing contingency terminal freeze differs from current artifacts")
    repository.save(contingency_experiment_id, "terminal-result-freeze", terminal_freeze)

    project_status = (
        "RESEARCH_HYPOTHESIS_SUPPORTED_BY_CONTINGENCY"
        if outcome == "SUPPORTED"
        else "RESEARCH_HYPOTHESIS_UNSUPPORTED_AFTER_TWO_EXPERIMENTS"
    )
    conclusion_core = {
        "schema_version": "1.4.0",
        "status": project_status,
        "formal_experiment_count": 2,
        "research_hypothesis_supported": outcome == "SUPPORTED",
        "primary": {
            "experiment_id": primary_experiment_id,
            "outcome": primary_freeze["outcome"],
            "result_hash": primary_freeze["negative_result_hash"],
        },
        "contingency": {
            "experiment_id": contingency_experiment_id,
            "outcome": outcome,
            "result_hash": terminal_result_hash,
        },
        "final_test_consumed": bool(experiment["final_test_consumed"]),
        "stopping_rule_applied": True,
        "claim_boundary": (
            "Engineering delivery may complete, but the research hypothesis is unsupported and "
            "no further formal experiment is authorized."
            if outcome != "SUPPORTED"
            else "The contingency met the pre-registered research-support gates."
        ),
    }
    try:
        existing_conclusion = repository.get(contingency_experiment_id, "project-research-outcome")
        concluded_at = str(existing_conclusion["concluded_at"])
    except KeyError:
        existing_conclusion = None
        concluded_at = clock().isoformat()
    conclusion = {
        **conclusion_core,
        "outcome_hash": _canonical_hash(conclusion_core),
        "concluded_at": concluded_at,
    }
    if existing_conclusion is not None and existing_conclusion != conclusion:
        raise ValueError("existing project research outcome differs from current artifacts")
    repository.save(contingency_experiment_id, "project-research-outcome", conclusion)
    return {
        "terminal_result_freeze": terminal_freeze,
        "project_research_outcome": conclusion,
    }


class ContingencyExperimentRunner(FormalExperimentRunner):
    """Reuse the frozen formal workflow for the sole activated V1.5 package."""

    def __init__(
        self,
        *,
        primary_experiment_id: str = PRIMARY_EXPERIMENT_ID,
        **kwargs: Any,
    ) -> None:
        self.primary_experiment_id = primary_experiment_id
        super().__init__(
            **kwargs,
            experiment_cap=CONTINGENCY_EXPERIMENT_CAP,
            scope_version="1.5",
        )

    def preflight(self) -> dict[str, Any]:
        report = preflight_contingency_experiment(
            package_root=self.package_root,
            private_ground_truth_root=self.private_ground_truth_root,
            suite_path=self.suite_path,
            seed_manifest_path=self.seed_manifest_path,
            seed_content_path=self.seed_content_path,
            artifact_root=self.artifact_root,
            primary_experiment_id=self.primary_experiment_id,
            contingency_experiment_id=self.experiment_id,
            ledger=self.ledger,
            rotated_key_ready=self.rotated_key_ready,
            calibration_ready=self.calibration_ready,
            worst_case_request_cost=self.worst_case_request_cost,
        )
        self.evolution_repository.save(self.experiment_id, "preflight", report)
        self.evolution_repository.save(self.experiment_id, "run-plan", formal_run_plan())
        return report

    def run(self) -> dict[str, Any]:
        experiment = super().run()
        if experiment["status"] == "completed":
            freeze_final_contingency_outcome(
                artifact_root=self.artifact_root,
                primary_experiment_id=self.primary_experiment_id,
                contingency_experiment_id=self.experiment_id,
                clock=self.clock,
            )
        return experiment


__all__ = [
    "AUTHORIZATION_BASIS",
    "CONTINGENCY_EXPERIMENT_CAP",
    "CONTINGENCY_EXPERIMENT_ID",
    "ContingencyExperimentRunner",
    "freeze_and_activate_contingency",
    "freeze_final_contingency_outcome",
    "preflight_contingency_experiment",
]
