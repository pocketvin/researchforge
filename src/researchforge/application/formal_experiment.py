"""Controlled V1.4 Base/Seed/Candidate experiment execution outside LangGraph."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol, cast

from researchforge.adapters.checkpoints import DurableJsonCheckpointSaver
from researchforge.adapters.evolution_storage import EvolutionArtifactRepository
from researchforge.adapters.fixtures import G0FixtureCatalog
from researchforge.adapters.storage import FileRunRepository
from researchforge.application.budget import BudgetLedger
from researchforge.application.contracts import ResearchRunRequest
from researchforge.application.evolution import (
    MODEL_CONFIG,
    complete_experiment,
    decide_final_test_batch,
    decide_validation,
    distill_experience,
    preregister_experiment,
    propose_patch,
    select_eligible_cluster,
)
from researchforge.application.research import (
    ConclusionGenerator,
    EarningsQualityAnalyzer,
)
from researchforge.application.service import ResearchRunService
from researchforge.application.verification import FinancialVerifier
from researchforge.workflow.graph import ResearchWorkflow

FORMAL_REPEATS = 3
PRIMARY_EXPERIMENT_CAP = Decimal("9.00")
BASE_VERSION = "0.0.0"
BASE_HASH = hashlib.sha256(b"").hexdigest()


class FormalExperimentBlocked(RuntimeError):
    """Raised before provider contact when a frozen precondition is absent."""


class GeneratorFactory(Protocol):
    """Build one condition-pinned conclusion adapter."""

    def __call__(
        self,
        skill_content: str | None,
        ledger: BudgetLedger,
    ) -> ConclusionGenerator: ...


@dataclass(frozen=True, slots=True)
class SkillCondition:
    """Immutable skill identity and trusted procedure supplied to one condition."""

    name: str
    version: str
    content_hash: str
    content: str | None
    version_id: str | None


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return cast(dict[str, Any], value)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


def formal_run_plan() -> dict[str, Any]:
    """Return fixed denominators before any formal request is sent."""
    phases = {
        "evolution": {
            "case_count": 12,
            "conditions": ["base", "seed"],
            "repeats": FORMAL_REPEATS,
            "run_count": 72,
        },
        "validation": {
            "case_count": 6,
            "conditions": ["seed", "candidate"],
            "repeats": FORMAL_REPEATS,
            "run_count": 36,
        },
        "final_test": {
            "case_count": 6,
            "conditions": ["seed", "candidate"],
            "repeats": FORMAL_REPEATS,
            "run_count": 36,
        },
    }
    return {
        "schema_version": "1.4.0",
        "repeats_per_case_condition": FORMAL_REPEATS,
        "phases": phases,
        "maximum_formal_runs": 144,
        "maximum_provider_requests_with_one_repair_per_run": 288,
        "final_test_policy": "sealed_until_validation_adoption_then_consumed_once",
    }


def preflight_primary_experiment(
    *,
    package_root: Path,
    private_ground_truth_root: Path,
    seed_manifest_path: Path,
    seed_content_path: Path,
    ledger: BudgetLedger,
    rotated_key_ready: bool,
    worst_case_request_cost: Decimal,
) -> dict[str, Any]:
    """Validate package, truth hashes, skill, key readiness, and worst-case budget."""
    package_root = package_root.resolve()
    project_root = package_root.parents[2]
    manifest = _load_json(package_root / "manifest.json")
    blockers: list[str] = []
    if manifest.get("evidence_status") != "SIGNED":
        blockers.append("primary package owner signoff is not SIGNED")
    if manifest.get("formal_run_authorized") is not True:
        blockers.append("primary package formal_run_authorized is not true")
    if manifest.get("owner_signoff", {}).get("status") != "signed":
        blockers.append("primary package owner_signoff status is not signed")
    if not rotated_key_ready:
        blockers.append("rotated local OpenAI key is not confirmed ready")

    public_hashes = manifest.get("public_artifact_hashes", {})
    if not isinstance(public_hashes, dict) or len(public_hashes) != 216:
        blockers.append("public artifact hash catalog must contain 216 artifacts")
    else:
        for relative, expected_hash in public_hashes.items():
            path = (project_root / str(relative)).resolve()
            if project_root not in path.parents or not path.is_file():
                blockers.append(f"public artifact is missing or escapes project: {relative}")
                continue
            if _sha256(path) != expected_hash:
                blockers.append(f"public artifact hash mismatch: {relative}")

    cases = {
        case["case_id"]: case
        for path in sorted((package_root / "cases").glob("*.json"))
        for case in (_load_json(path),)
    }
    if len(cases) != 24:
        blockers.append("primary package must contain exactly 24 cases")
    if any(case.get("package_hash") != manifest.get("package_hash") for case in cases.values()):
        blockers.append("case package hashes differ from the primary manifest")

    truth_hashes = manifest.get("ground_truth_hashes", {})
    if not isinstance(truth_hashes, dict) or set(truth_hashes) != set(cases):
        blockers.append("ground-truth hash catalog differs from case catalog")
    else:
        for case_id, expected_hash in truth_hashes.items():
            truth_path = private_ground_truth_root / f"ground_truth_{case_id}.json"
            if not truth_path.is_file() or _sha256(truth_path) != expected_hash:
                blockers.append(f"verifier-only ground truth hash mismatch: {case_id}")

    suite_path = project_root / "benchmark" / "suites" / "v1.4-primary-preregistered.json"
    if not suite_path.is_file():
        blockers.append("pre-registered primary suite is missing")
    else:
        suite_hash = _sha256(suite_path)
        if manifest.get("preregistered_suite_hash") != suite_hash:
            blockers.append("pre-registered suite hash differs from primary manifest")
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
        data_hashes = {
            **{f"source:{key}": _canonical_hash(value) for key, value in sources.items()},
            **{f"fact:{key}": _canonical_hash(value) for key, value in facts.items()},
            **{f"chunk:{key}": _canonical_hash(value) for key, value in chunks.items()},
            **{
                f"ground_truth:{key}": value
                for key, value in cast(dict[str, str], truth_hashes).items()
            },
            "preregistered_suite": suite_hash,
        }
        if _canonical_hash(data_hashes) != manifest.get("package_hash"):
            blockers.append("primary package hash does not match its frozen inputs")

    seed_manifest = _load_json(seed_manifest_path)
    if _sha256(seed_content_path) != seed_manifest.get("content_hash"):
        blockers.append("Seed Skill content hash differs from its manifest")
    if seed_manifest.get("status") != "seed":
        blockers.append("Seed Skill manifest is not frozen as seed")

    plan = formal_run_plan()
    maximum_provider_requests = int(plan["maximum_provider_requests_with_one_repair_per_run"])
    experiment_worst_case = worst_case_request_cost * maximum_provider_requests
    snapshot = ledger.snapshot()
    if experiment_worst_case > PRIMARY_EXPERIMENT_CAP:
        blockers.append("formal experiment worst-case requests exceed the USD 9 primary cap")
    if snapshot.spent + snapshot.reserved + experiment_worst_case > snapshot.cap:
        blockers.append("formal experiment worst-case requests exceed aggregate project budget")

    return {
        "schema_version": "1.4.0",
        "status": "PASS" if not blockers else "BLOCKED",
        "provider_contacted": False,
        "package_id": manifest.get("package_id"),
        "package_hash": manifest.get("package_hash"),
        "case_count": len(cases),
        "private_ground_truth_hash_count": len(truth_hashes),
        "rotated_key_ready": rotated_key_ready,
        "budget": {
            "aggregate_cap": format(snapshot.cap, "f"),
            "aggregate_spent": format(snapshot.spent, "f"),
            "aggregate_reserved": format(snapshot.reserved, "f"),
            "primary_cap": format(PRIMARY_EXPERIMENT_CAP, "f"),
            "worst_case_request_cost": format(worst_case_request_cost, "f"),
            "experiment_worst_case": format(experiment_worst_case, "f"),
        },
        "run_plan": plan,
        "blockers": blockers,
    }


class FormalExperimentRunner:
    """Run the pre-registered experiment with no open-ended self-modification."""

    def __init__(
        self,
        *,
        experiment_id: str,
        package_root: Path,
        private_ground_truth_root: Path,
        suite_path: Path,
        seed_manifest_path: Path,
        seed_content_path: Path,
        artifact_root: Path,
        generator_factory: GeneratorFactory,
        ledger: BudgetLedger,
        worst_case_request_cost: Decimal,
        rotated_key_ready: bool,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self.experiment_id = experiment_id
        self.package_root = package_root.resolve()
        self.private_ground_truth_root = private_ground_truth_root.resolve()
        self.suite_path = suite_path.resolve()
        self.seed_manifest_path = seed_manifest_path.resolve()
        self.seed_content_path = seed_content_path.resolve()
        self.artifact_root = artifact_root.resolve()
        self.generator_factory = generator_factory
        self.ledger = ledger
        self.worst_case_request_cost = worst_case_request_cost
        self.rotated_key_ready = rotated_key_ready
        self.clock = clock
        self.evolution_repository = EvolutionArtifactRepository(self.artifact_root)
        self.run_repository = FileRunRepository(self.artifact_root)
        self.catalog = G0FixtureCatalog(self.package_root)
        self.package_manifest = _load_json(self.package_root / "manifest.json")
        self.suite = _load_json(self.suite_path)
        self.cases = {
            case["case_id"]: case
            for path in sorted((self.package_root / "cases").glob("*.json"))
            for case in (_load_json(path),)
        }

    def preflight(self) -> dict[str, Any]:
        report = preflight_primary_experiment(
            package_root=self.package_root,
            private_ground_truth_root=self.private_ground_truth_root,
            seed_manifest_path=self.seed_manifest_path,
            seed_content_path=self.seed_content_path,
            ledger=self.ledger,
            rotated_key_ready=self.rotated_key_ready,
            worst_case_request_cost=self.worst_case_request_cost,
        )
        self.evolution_repository.save(self.experiment_id, "preflight", report)
        self.evolution_repository.save(self.experiment_id, "run-plan", formal_run_plan())
        return report

    def _preregister(self) -> dict[str, Any]:
        try:
            existing = self.evolution_repository.get(self.experiment_id)
            timestamp = datetime.fromisoformat(existing["preregistered_at"])
        except KeyError:
            existing = None
            timestamp = self.clock()
        expected = preregister_experiment(
            experiment_id=self.experiment_id,
            suite_id=str(self.suite["suite_id"]),
            split_cases=cast(dict[str, list[dict[str, str]]], self.suite["splits"]),
            seed_skill_version_id="skill_fundamental_1_0_0",
            timestamp=timestamp,
        )
        if existing is None:
            experiment = expected
            self.evolution_repository.save(self.experiment_id, "experiment", experiment)
        else:
            experiment = existing
            immutable_keys = (
                "experiment_id",
                "scope_version",
                "suite_id",
                "suite_hash",
                "model",
                "graph_version",
                "seed_skill_version_id",
                "split_case_ids",
                "thresholds",
            )
            if any(experiment[key] != expected[key] for key in immutable_keys):
                raise FormalExperimentBlocked("existing experiment preregistration changed")
        if Decimal(str(experiment["budget"]["cap"])) != PRIMARY_EXPERIMENT_CAP:
            raise FormalExperimentBlocked("existing experiment does not retain the USD 9 cap")
        return experiment

    def _truth(self, case: dict[str, Any], *, allow_final: bool) -> dict[str, Any]:
        if case["split"] == "final_test" and not allow_final:
            raise FormalExperimentBlocked("Final Test ground truth remains sealed")
        reference = case["verifier_ground_truth_ref"]
        path = self.private_ground_truth_root / f"{reference['artifact_id']}.json"
        if _sha256(path) != reference["artifact_hash"]:
            raise FormalExperimentBlocked(f"ground truth hash mismatch: {case['case_id']}")
        return _load_json(path)

    def _service(self, condition: SkillCondition, checkpoint_key: str) -> ResearchRunService:
        generator = self.generator_factory(condition.content, self.ledger)
        prompt_hashes = getattr(generator, "prompt_hashes", None)
        if not isinstance(prompt_hashes, dict):
            prompt_hashes = {
                "research_wrapper": hashlib.sha256(
                    b"synthetic-or-non-provider-conclusion-generator"
                ).hexdigest()
            }
        workflow = ResearchWorkflow(
            self.catalog.load,
            EarningsQualityAnalyzer(),
            generator,
            skill_version=condition.version,
            skill_hash=condition.content_hash,
            checkpointer=DurableJsonCheckpointSaver(
                self.artifact_root
                / "checkpoints"
                / "formal"
                / condition.name
                / f"{checkpoint_key}.json"
            ),
            clock=self.clock,
        )
        return ResearchRunService(
            self.run_repository,
            self.catalog,
            workflow,
            skill_version=condition.version,
            skill_hash=condition.content_hash,
            verifier=FinancialVerifier(clock=self.clock),
            model_config=MODEL_CONFIG,
            prompt_hashes=cast(dict[str, str], prompt_hashes),
            clock=self.clock,
        )

    @staticmethod
    def _period_label(case: dict[str, Any]) -> str:
        period = case["target_periods"][0]
        return f"{period['fiscal_year']}{period['fiscal_period']}"

    def _run_condition(
        self,
        *,
        split: str,
        condition: SkillCondition,
        allow_final: bool,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        evaluations: list[dict[str, Any]] = []
        run_ids: list[str] = []
        run_kind = {
            "evolution": "benchmark_evolution",
            "validation": "benchmark_validation",
            "final_test": "benchmark_final_test",
        }[split]
        case_ids = [str(item["case_id"]) for item in self.suite["splits"][split]]
        for case_id in case_ids:
            case = self.cases[case_id]
            truth = self._truth(case, allow_final=allow_final)
            for repeat in range(1, FORMAL_REPEATS + 1):
                service = self._service(condition, f"{case_id}-repeat-{repeat}")
                request = ResearchRunRequest(
                    task_type="filing_analysis",
                    research_question=case["research_question"],
                    company_ids=[case["company"]["company_id"]],
                    requested_period_labels=[self._period_label(case)],
                    research_time=datetime.fromisoformat(case["research_time"]),
                    idempotency_key=(
                        f"formal:{self.experiment_id}:{split}:{condition.name}:"
                        f"{case_id}:repeat-{repeat}"
                    ),
                )
                submission = service.submit(
                    request,
                    run_kind=run_kind,
                    case_id=case_id,
                    split=split,
                )
                manifest = service.execute(submission.run_id)
                if manifest["lifecycle_state"] != "succeeded":
                    raise FormalExperimentBlocked(
                        f"technical run did not succeed: {submission.run_id} "
                        f"({manifest['lifecycle_state']})"
                    )
                if manifest["artifacts"]["evaluation_id"] is None:
                    evaluation = service.verify(
                        submission.run_id,
                        case_id=case_id,
                        expected_calculations=cast(dict[str, str], truth["expected_calculations"]),
                        ground_truth_hash=case["verifier_ground_truth_ref"]["artifact_hash"],
                    )
                else:
                    evaluation = service.get_evaluation(submission.run_id)
                run_ids.append(submission.run_id)
                evaluations.append(evaluation)
        self.evolution_repository.save(
            self.experiment_id,
            f"{condition.name}-{split}-evaluations",
            {
                "schema_version": "1.4.0",
                "condition": condition.name,
                "split": split,
                "repeat_count": FORMAL_REPEATS,
                "evaluations": evaluations,
            },
        )
        return evaluations, run_ids

    @staticmethod
    def _experience_text(signature: str) -> tuple[str, str, str, list[str]]:
        check_code = signature.split(":", 1)[0].removeprefix("coverage_")
        procedures = {
            "operating_cash_flow": "Record operating cash flow before judging profit quality.",
            "accounts_receivable": "Record the supplied accounts-receivable balance.",
            "inventory": "Record the supplied inventory balance.",
            "cash_conversion": (
                "When net income is positive and operating cash flow is available, record the "
                "deterministic cash-conversion result before making a material conclusion."
            ),
            "profit_cash_divergence": "Record the deterministic profit/cash divergence status.",
            "one_off_contribution": (
                "Record one-off contribution as unavailable when the frozen facts do not supply it."
            ),
            "counter_evidence": "Record whether the bounded counter-evidence search was performed.",
        }
        procedure = procedures.get(check_code)
        if procedure is None:
            raise FormalExperimentBlocked(f"unsupported Evolution target: {check_code}")
        return (
            f"Valid reports repeatedly omitted the required {check_code} status.",
            "The check is required by the frozen earnings-quality procedure.",
            procedure,
            ["Do not invent unavailable facts or evidence."],
        )

    def _candidate(
        self,
        seed: SkillCondition,
        cluster: Any,
    ) -> tuple[SkillCondition, dict[str, Any], dict[str, Any], dict[str, Any]]:
        observed, condition, procedure, exceptions = self._experience_text(cluster.signature)
        timestamp = self.clock()
        experience = distill_experience(
            cluster,
            observed_behavior=observed,
            applicable_condition=condition,
            required_procedure=procedure,
            exceptions=exceptions,
            timestamp=timestamp,
        )
        patch = propose_patch(
            cluster,
            experience,
            seed_version=seed.version,
            seed_hash=seed.content_hash,
            timestamp=timestamp,
        )
        assert seed.content is not None
        content = seed.content.rstrip() + "\n\n## Candidate Reinforcement\n\n" + procedure + "\n"
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        version = str(patch["candidate_version"])
        version_id = "skill_fundamental_1_0_0_candidate_1"
        content_path = (
            self.artifact_root / "evolution" / self.experiment_id / "candidate-skill" / "SKILL.md"
        )
        content_path.parent.mkdir(parents=True, exist_ok=True)
        if content_path.exists() and content_path.read_text(encoding="utf-8") != content:
            raise FormalExperimentBlocked("candidate content changed after freezing")
        content_path.write_text(content, encoding="utf-8")
        skill_version = {
            "schema_version": "1.4.0",
            "skill_version_id": version_id,
            "skill_name": "fundamental-research",
            "version": version,
            "content_hash": content_hash,
            "parent_version_id": seed.version_id,
            "source_patch_id": patch["patch_id"],
            "status": "candidate",
            "content_path": str(content_path),
            "created_at": timestamp.isoformat(),
            "activated_at": None,
        }
        candidate = SkillCondition("candidate", version, content_hash, content, version_id)
        return candidate, experience, patch, skill_version

    def _save_progress(self, phase: str, run_ids: list[str], evaluation_ids: list[str]) -> None:
        snapshot = self.ledger.snapshot()
        self.evolution_repository.save(
            self.experiment_id,
            "progress",
            {
                "schema_version": "1.4.0",
                "phase": phase,
                "run_ids": run_ids,
                "evaluation_ids": evaluation_ids,
                "budget": {
                    "cap": format(snapshot.cap, "f"),
                    "spent": format(snapshot.spent, "f"),
                    "reserved": format(snapshot.reserved, "f"),
                },
                "updated_at": self.clock().isoformat(),
            },
        )

    def _experiment_spent(self, baseline: Decimal) -> float:
        spent = self.ledger.snapshot().spent - baseline
        if spent < 0 or spent > PRIMARY_EXPERIMENT_CAP:
            raise FormalExperimentBlocked("primary experiment spend is outside its USD 9 cap")
        return float(spent)

    def run(self) -> dict[str, Any]:
        """Execute or idempotently resume all allowed phases through terminal outcome."""
        experiment = self._preregister()
        if experiment["status"] == "completed":
            return experiment
        preflight = self.preflight()
        if preflight["status"] != "PASS":
            raise FormalExperimentBlocked("; ".join(preflight["blockers"]))

        try:
            budget_baseline = self.evolution_repository.get(self.experiment_id, "budget-baseline")
        except KeyError:
            if experiment["status"] == "running":
                raise FormalExperimentBlocked(
                    "running experiment has no durable budget baseline"
                ) from None
            budget_baseline = {
                "schema_version": "1.4.0",
                "currency": "USD",
                "aggregate_spent_before": format(self.ledger.snapshot().spent, "f"),
                "created_at": self.clock().isoformat(),
            }
            self.evolution_repository.save(self.experiment_id, "budget-baseline", budget_baseline)
        start_spend = Decimal(str(budget_baseline["aggregate_spent_before"]))
        if self.ledger.snapshot().spent < start_spend:
            raise FormalExperimentBlocked("aggregate budget spend fell below frozen baseline")
        experiment = {**experiment, "status": "running"}
        self.evolution_repository.save(self.experiment_id, "experiment", experiment)
        seed_manifest = _load_json(self.seed_manifest_path)
        seed_content = self.seed_content_path.read_text(encoding="utf-8")
        base = SkillCondition("base", BASE_VERSION, BASE_HASH, None, None)
        seed = SkillCondition(
            "seed",
            str(seed_manifest["version"]),
            str(seed_manifest["content_hash"]),
            seed_content,
            str(seed_manifest["skill_version_id"]),
        )
        all_runs: list[str] = []
        all_evaluations: list[str] = []

        base_evolution, base_run_ids = self._run_condition(
            split="evolution", condition=base, allow_final=False
        )
        seed_evolution, seed_run_ids = self._run_condition(
            split="evolution", condition=seed, allow_final=False
        )
        all_runs.extend([*base_run_ids, *seed_run_ids])
        all_evaluations.extend(
            evaluation["evaluation_id"] for evaluation in [*base_evolution, *seed_evolution]
        )
        self._save_progress("evolution_complete", all_runs, all_evaluations)

        cluster = select_eligible_cluster(seed_evolution)
        if cluster is None:
            completed = complete_experiment(
                experiment,
                outcome="NO_ELIGIBLE_CLUSTER",
                run_ids=all_runs,
                evaluation_ids=all_evaluations,
                candidate_skill_version_id=None,
                spent=self._experiment_spent(start_spend),
                timestamp=self.clock(),
            )
            self.evolution_repository.save(self.experiment_id, "experiment", completed)
            return completed

        self.evolution_repository.save(
            self.experiment_id,
            "failure-cluster",
            {
                "schema_version": "1.4.0",
                "cluster_id": cluster.cluster_id,
                "failure_label": cluster.failure_label,
                "signature": cluster.signature,
                "eligible_run_count": cluster.eligible_run_count,
                "support_count": cluster.support_count,
                "supporting_failure_ids": list(cluster.supporting_failure_ids),
                "source_evaluation_ids": list(cluster.source_evaluation_ids),
                "distinct_case_ids": list(cluster.distinct_case_ids),
            },
        )
        candidate, experience, patch, skill_version = self._candidate(seed, cluster)
        self.evolution_repository.save(self.experiment_id, "experience", experience)
        self.evolution_repository.save(self.experiment_id, "patch", patch)
        self.evolution_repository.save(self.experiment_id, "candidate-skill", skill_version)

        seed_validation, seed_validation_runs = self._run_condition(
            split="validation", condition=seed, allow_final=False
        )
        candidate_validation, candidate_validation_runs = self._run_condition(
            split="validation", condition=candidate, allow_final=False
        )
        all_runs.extend([*seed_validation_runs, *candidate_validation_runs])
        all_evaluations.extend(
            evaluation["evaluation_id"] for evaluation in [*seed_validation, *candidate_validation]
        )
        patch = decide_validation(
            patch,
            seed_validation,
            candidate_validation,
            timestamp=self.clock(),
        )
        self.evolution_repository.save(self.experiment_id, "patch", patch)
        self.evolution_repository.save(
            self.experiment_id,
            "validation-decision",
            {
                "schema_version": "1.4.0",
                "status": patch["status"],
                "decision": patch["decision"],
                "seed_evaluation_ids": [item["evaluation_id"] for item in seed_validation],
                "candidate_evaluation_ids": [
                    item["evaluation_id"] for item in candidate_validation
                ],
            },
        )
        self._save_progress("validation_complete", all_runs, all_evaluations)
        if patch["status"] != "ADOPTED":
            completed = complete_experiment(
                experiment,
                outcome="REJECTED_VALIDATION",
                run_ids=all_runs,
                evaluation_ids=all_evaluations,
                candidate_skill_version_id=candidate.version_id,
                spent=self._experiment_spent(start_spend),
                timestamp=self.clock(),
            )
            self.evolution_repository.save(self.experiment_id, "experiment", completed)
            return completed

        try:
            consumption = self.evolution_repository.get(
                self.experiment_id, "final-test-consumption"
            )
        except KeyError:
            consumption = {
                "schema_version": "1.4.0",
                "status": "UNSEALED_ONCE",
                "package_hash": self.package_manifest["package_hash"],
                "candidate_skill_hash": candidate.content_hash,
                "started_at": self.clock().isoformat(),
            }
            self.evolution_repository.save(
                self.experiment_id, "final-test-consumption", consumption
            )
        if consumption["candidate_skill_hash"] != candidate.content_hash:
            raise FormalExperimentBlocked("Final Test was already unsealed for another Candidate")

        seed_final, seed_final_runs = self._run_condition(
            split="final_test", condition=seed, allow_final=True
        )
        candidate_final, candidate_final_runs = self._run_condition(
            split="final_test", condition=candidate, allow_final=True
        )
        all_runs.extend([*seed_final_runs, *candidate_final_runs])
        all_evaluations.extend(
            evaluation["evaluation_id"] for evaluation in [*seed_final, *candidate_final]
        )
        outcome = decide_final_test_batch(
            patch,
            seed_final,
            candidate_final,
            timestamp=self.clock(),
        )
        completed = complete_experiment(
            experiment,
            outcome=outcome,
            run_ids=all_runs,
            evaluation_ids=all_evaluations,
            candidate_skill_version_id=candidate.version_id,
            spent=self._experiment_spent(start_spend),
            timestamp=self.clock(),
        )
        self.evolution_repository.save(self.experiment_id, "experiment", completed)
        self._save_progress("final_test_complete", all_runs, all_evaluations)
        return completed
