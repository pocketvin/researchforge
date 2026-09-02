"""Offline controls for the one permitted V1.5 contingency experiment."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from researchforge.adapters.evolution_storage import EvolutionArtifactRepository
from researchforge.adapters.openai_responses import luna_worst_case_cost
from researchforge.application.budget import BudgetLedger
from researchforge.application.contingency_experiment import (
    AUTHORIZATION_BASIS,
    CONTINGENCY_EXPERIMENT_CAP,
    ContingencyExperimentRunner,
    freeze_and_activate_contingency,
    freeze_final_contingency_outcome,
    preflight_contingency_experiment,
)
from researchforge.application.research import ConclusionGenerator
from tests.application.test_formal_experiment import synthetic_generator_factory

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "data" / "fixtures" / "v1.5-contingency"
SUITE = ROOT / "benchmark" / "suites" / "v1.5-contingency-preregistered.json"
SEED_ROOT = ROOT / "skills" / "fundamental-research" / "versions" / "1.0.0"
PRIMARY_ID = "experiment_primary_negative_test"
CONTINGENCY_ID = "experiment_contingency_test"
FIXED_TIME = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def save_terminal_primary(
    artifact_root: Path,
    *,
    outcome: str = "NO_ELIGIBLE_CLUSTER",
) -> EvolutionArtifactRepository:
    repository = EvolutionArtifactRepository(artifact_root)
    experiment = {
        "schema_version": "1.4.0",
        "experiment_id": PRIMARY_ID,
        "status": "completed",
        "outcome": outcome,
        "run_ids": ["run_1", "run_2"],
        "evaluation_ids": ["evaluation_1", "evaluation_2"],
        "candidate_skill_version_id": None,
        "final_test_consumed": False,
        "budget": {"currency": "USD", "cap": 9.0, "spent": 0.05},
        "finished_at": FIXED_TIME.isoformat(),
    }
    repository.save(PRIMARY_ID, "experiment", experiment)
    for kind in (
        "run-plan",
        "preflight",
        "budget-baseline",
        "base-evolution-evaluations",
        "seed-evolution-evaluations",
        "progress",
    ):
        repository.save(
            PRIMARY_ID,
            kind,
            {"schema_version": "1.4.0", "kind": kind, "experiment_id": PRIMARY_ID},
        )
    return repository


def test_activation_freezes_negative_result_once_and_is_idempotent(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    save_terminal_primary(artifact_root)

    first = freeze_and_activate_contingency(
        artifact_root=artifact_root,
        package_root=PACKAGE,
        primary_experiment_id=PRIMARY_ID,
        contingency_experiment_id=CONTINGENCY_ID,
        clock=lambda: FIXED_TIME,
    )
    second = freeze_and_activate_contingency(
        artifact_root=artifact_root,
        package_root=PACKAGE,
        primary_experiment_id=PRIMARY_ID,
        contingency_experiment_id=CONTINGENCY_ID,
        clock=lambda: datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
    )

    assert second == first
    assert first["negative_result_freeze"]["research_hypothesis_supported"] is False
    activation = first["activation"]
    assert activation["activation_count"] == 1
    assert activation["authorization_basis"] == AUTHORIZATION_BASIS
    assert activation["protocol_deviation"]["code"] == ("FROZEN_ACTIVATION_PREDICATE_TOO_NARROW")
    assert activation["protocol_deviation"]["data_or_threshold_changed"] is False


def test_supported_primary_cannot_activate_contingency(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    save_terminal_primary(artifact_root, outcome="SUPPORTED")

    with pytest.raises(ValueError, match="eligible unsupported outcome"):
        freeze_and_activate_contingency(
            artifact_root=artifact_root,
            package_root=PACKAGE,
            primary_experiment_id=PRIMARY_ID,
            contingency_experiment_id=CONTINGENCY_ID,
        )


def test_preflight_requires_private_truth_but_accepts_bound_activation(
    tmp_path: Path,
) -> None:
    artifact_root = tmp_path / "artifacts"
    save_terminal_primary(artifact_root)
    freeze_and_activate_contingency(
        artifact_root=artifact_root,
        package_root=PACKAGE,
        primary_experiment_id=PRIMARY_ID,
        contingency_experiment_id=CONTINGENCY_ID,
        clock=lambda: FIXED_TIME,
    )

    report = preflight_contingency_experiment(
        package_root=PACKAGE,
        private_ground_truth_root=tmp_path / "unavailable-private-truth",
        suite_path=SUITE,
        seed_manifest_path=SEED_ROOT / "skill-version.json",
        seed_content_path=SEED_ROOT / "SKILL.md",
        artifact_root=artifact_root,
        primary_experiment_id=PRIMARY_ID,
        contingency_experiment_id=CONTINGENCY_ID,
        ledger=BudgetLedger(state_path=artifact_root / "budget.json"),
        rotated_key_ready=True,
        calibration_ready=True,
        worst_case_request_cost=luna_worst_case_cost(8000, 4000),
    )

    assert report["status"] == "BLOCKED"
    assert report["provider_contacted"] is False
    assert report["activation_status"] == "ACTIVATED_ONCE"
    assert report["budget"]["contingency_cap"] == "6.00"
    assert sum("verifier-only ground truth mismatch" in item for item in report["blockers"]) == 24
    assert not any("activation" in item for item in report["blockers"])
    assert not any("overlaps" in item for item in report["blockers"])


def test_contingency_preregistration_pins_v15_scope_and_six_dollar_cap(
    tmp_path: Path,
) -> None:
    def factory(skill_content: str | None, ledger: BudgetLedger) -> ConclusionGenerator:
        return synthetic_generator_factory(skill_content, ledger)

    runner = ContingencyExperimentRunner(
        primary_experiment_id=PRIMARY_ID,
        experiment_id=CONTINGENCY_ID,
        package_root=PACKAGE,
        private_ground_truth_root=tmp_path / "private-truth",
        suite_path=SUITE,
        seed_manifest_path=SEED_ROOT / "skill-version.json",
        seed_content_path=SEED_ROOT / "SKILL.md",
        artifact_root=tmp_path / "artifacts",
        generator_factory=factory,
        ledger=BudgetLedger(state_path=tmp_path / "artifacts" / "budget.json"),
        worst_case_request_cost=Decimal("0.0064"),
        rotated_key_ready=True,
        calibration_ready=True,
        clock=lambda: FIXED_TIME,
    )

    experiment: dict[str, Any] = runner._preregister()

    assert experiment["scope_version"] == "1.5"
    assert Decimal(str(experiment["budget"]["cap"])) == CONTINGENCY_EXPERIMENT_CAP


def test_second_negative_result_freezes_honest_project_stopping_outcome(
    tmp_path: Path,
) -> None:
    artifact_root = tmp_path / "artifacts"
    repository = save_terminal_primary(artifact_root)
    freeze_and_activate_contingency(
        artifact_root=artifact_root,
        package_root=PACKAGE,
        primary_experiment_id=PRIMARY_ID,
        contingency_experiment_id=CONTINGENCY_ID,
        clock=lambda: FIXED_TIME,
    )
    repository.save(
        CONTINGENCY_ID,
        "experiment",
        {
            "schema_version": "1.4.0",
            "experiment_id": CONTINGENCY_ID,
            "scope_version": "1.5",
            "status": "completed",
            "outcome": "NO_ELIGIBLE_CLUSTER",
            "run_ids": ["run_v15_1", "run_v15_2"],
            "evaluation_ids": ["eval_v15_1", "eval_v15_2"],
            "candidate_skill_version_id": None,
            "final_test_consumed": False,
            "budget": {"currency": "USD", "cap": 6.0, "spent": 0.06},
            "finished_at": FIXED_TIME.isoformat(),
        },
    )
    for kind in (
        "run-plan",
        "preflight",
        "budget-baseline",
        "base-evolution-evaluations",
        "seed-evolution-evaluations",
        "progress",
    ):
        repository.save(
            CONTINGENCY_ID,
            kind,
            {"schema_version": "1.4.0", "kind": kind, "experiment_id": CONTINGENCY_ID},
        )

    first = freeze_final_contingency_outcome(
        artifact_root=artifact_root,
        primary_experiment_id=PRIMARY_ID,
        contingency_experiment_id=CONTINGENCY_ID,
        clock=lambda: FIXED_TIME,
    )
    second = freeze_final_contingency_outcome(
        artifact_root=artifact_root,
        primary_experiment_id=PRIMARY_ID,
        contingency_experiment_id=CONTINGENCY_ID,
        clock=lambda: datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
    )

    assert second == first
    outcome = first["project_research_outcome"]
    assert outcome["status"] == ("RESEARCH_HYPOTHESIS_UNSUPPORTED_AFTER_TWO_EXPERIMENTS")
    assert outcome["research_hypothesis_supported"] is False
    assert outcome["formal_experiment_count"] == 2
    assert outcome["final_test_consumed"] is False
    assert outcome["stopping_rule_applied"] is True
