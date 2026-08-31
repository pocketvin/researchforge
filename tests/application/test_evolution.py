"""Synthetic policy fixtures for controlled Evolution decisions.

These tests prove the algorithm only. They are not a formal benchmark run and
must never be cited as a V1.4 SUPPORTED research result.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from researchforge.application.evolution import (
    complete_experiment,
    decide_final_test,
    decide_validation,
    distill_experience,
    preregister_experiment,
    propose_patch,
    select_eligible_cluster,
)
from tests.runtime_helpers import assert_v14_schema

NOW = datetime(2026, 9, 1, tzinfo=UTC)
HASH = "7" * 64
SIGNATURE = "coverage_cash_conversion_missing"


def _evaluation(
    evaluation_id: str,
    run_id: str,
    case_id: str,
    *,
    target_failure: bool,
    candidate: bool = False,
) -> dict[str, Any]:
    target_check: dict[str, Any] = {
        "check_code": "coverage_cash_conversion",
        "status": "FAIL" if target_failure else "PASS",
        "expected": "cash conversion check present",
        "observed": "missing" if target_failure else "present",
        "fact_ids": [],
        "evidence_ids": [],
    }
    deterministic = {
        "check_code": "calculation_cash_conversion",
        "status": "PASS",
        "expected": "deterministic value",
        "observed": "deterministic value",
        "fact_ids": [],
        "evidence_ids": [],
    }
    failures = (
        [
            {
                "failure_id": f"failure_{evaluation_id}",
                "failure_label": "CRITICAL_OMISSION",
                "signature": SIGNATURE,
                "severity": "major",
                "check_codes": ["coverage_cash_conversion"],
                "description": "Cash conversion coverage was omitted.",
            }
        ]
        if target_failure
        else []
    )
    score = 0.75 if target_failure else 1.0
    return {
        "schema_version": "1.4.0",
        "evaluation_id": evaluation_id,
        "run_id": run_id,
        "case_id": case_id,
        "skill_version": "1.0.0-candidate.1" if candidate else "1.0.0",
        "skill_hash": HASH,
        "verifier_version": "1.0.0",
        "ground_truth_hash": HASH,
        "deterministic_checks": [deterministic],
        "coverage_checks": [target_check],
        "qualitative_checks": [],
        "failure_events": failures,
        "metrics": {
            "task_score": score,
            "calculation_accuracy": 1.0,
            "evidence_coverage": 0.0 if target_failure else 1.0,
            "critical_omission_rate": 1.0 if target_failure else 0.0,
            "citation_accuracy": 1.0,
        },
        "created_at": NOW.isoformat(),
    }


def _adopted_patch() -> dict[str, Any]:
    evolution = [
        _evaluation("eval_evo_1", "run_evo_1", "case_evo_a", target_failure=True),
        _evaluation("eval_evo_2", "run_evo_2", "case_evo_b", target_failure=True),
        _evaluation("eval_evo_3", "run_evo_3", "case_evo_a_repeat", target_failure=True),
    ]
    cluster = select_eligible_cluster(evolution)
    assert cluster is not None
    experience = distill_experience(
        cluster,
        observed_behavior="The report omitted a meaningful cash-conversion check.",
        applicable_condition="Positive net income and available operating cash flow.",
        required_procedure=(
            "When net income is positive and operating cash flow is available, calculate and "
            "record cash conversion before making a material earnings-quality claim."
        ),
        exceptions=["Mark unavailable when the denominator is non-positive."],
        timestamp=NOW,
    )
    patch = propose_patch(
        cluster,
        experience,
        seed_version="1.0.0",
        seed_hash=HASH,
        timestamp=NOW,
    )
    seed_validation = [
        _evaluation("eval_seed_val_a", "run_seed_val_a", "case_val_a", target_failure=True),
        _evaluation("eval_seed_val_b", "run_seed_val_b", "case_val_b", target_failure=True),
    ]
    candidate_validation = [
        _evaluation(
            "eval_candidate_val_a",
            "run_candidate_val_a",
            "case_val_a",
            target_failure=False,
            candidate=True,
        ),
        _evaluation(
            "eval_candidate_val_b",
            "run_candidate_val_b",
            "case_val_b",
            target_failure=False,
            candidate=True,
        ),
    ]
    adopted = decide_validation(patch, seed_validation, candidate_validation, timestamp=NOW)
    assert_v14_schema(experience, "experience.schema.json")
    assert_v14_schema(adopted, "skill-patch.schema.json")
    return adopted


def test_exact_cluster_requires_three_failures_across_two_cases() -> None:
    one_case_repeats = [
        _evaluation(f"eval_{index}", f"run_{index}", "case_same", target_failure=True)
        for index in range(3)
    ]
    assert select_eligible_cluster(one_case_repeats) is None

    two_cases = [
        _evaluation("eval_a", "run_a", "case_a", target_failure=True),
        _evaluation("eval_b", "run_b", "case_b", target_failure=True),
        _evaluation("eval_c", "run_c", "case_a_repeat", target_failure=True),
    ]
    cluster = select_eligible_cluster(two_cases)

    assert cluster is not None
    assert cluster.support_count == 3


def test_synthetic_validation_adopts_only_threshold_passing_patch() -> None:
    adopted = _adopted_patch()

    assert adopted["status"] == "ADOPTED"
    assert adopted["decision"] == {
        "target_failure_reduced": True,
        "deterministic_quality_preserved": True,
        "overall_non_inferior": True,
        "regression_within_threshold": True,
        "decision_reason": (
            "repair_rate=1.000; regression_rate=0.000; seed_score=0.750; candidate_score=1.000"
        ),
    }


def test_final_test_is_sealed_until_adoption_and_consumed_once() -> None:
    proposed = {**_adopted_patch(), "status": "PROPOSED"}
    seed = _evaluation("eval_seed_final", "run_seed_final", "case_final", target_failure=True)
    candidate = _evaluation(
        "eval_candidate_final",
        "run_candidate_final",
        "case_final",
        target_failure=False,
        candidate=True,
    )

    with pytest.raises(ValueError, match="sealed"):
        decide_final_test(proposed, seed, candidate)

    adopted = _adopted_patch()
    assert decide_final_test(adopted, seed, candidate) == "SUPPORTED"


def test_preregister_and_complete_synthetic_policy_fixture() -> None:
    experiment = preregister_experiment(
        experiment_id="experiment_synthetic_policy_fixture",
        suite_id="suite_synthetic_policy_fixture",
        split_cases={
            "evolution": [{"case_id": "case_evo", "group_key": "company_a"}],
            "validation": [{"case_id": "case_val", "group_key": "company_b"}],
            "final_test": [{"case_id": "case_final", "group_key": "company_c"}],
        },
        seed_skill_version_id="skill_fundamental_1_0_0",
        timestamp=NOW,
    )
    completed = complete_experiment(
        experiment,
        outcome="SUPPORTED",
        run_ids=["run_synthetic_evo", "run_synthetic_val", "run_synthetic_final"],
        evaluation_ids=["eval_synthetic_evo", "eval_synthetic_val", "eval_synthetic_final"],
        candidate_skill_version_id="skill_fundamental_1_0_0_candidate_1",
        spent=0.0,
        timestamp=NOW,
    )

    assert_v14_schema(experiment, "evolution-experiment.schema.json")
    assert_v14_schema(completed, "evolution-experiment.schema.json")
    assert completed["final_test_consumed"] is True


def test_preregistration_rejects_group_leakage() -> None:
    with pytest.raises(ValueError, match="group keys cross"):
        preregister_experiment(
            experiment_id="experiment_leaky",
            suite_id="suite_leaky",
            split_cases={
                "evolution": [{"case_id": "case_evo", "group_key": "company_same"}],
                "validation": [{"case_id": "case_val", "group_key": "company_same"}],
                "final_test": [{"case_id": "case_final", "group_key": "company_other"}],
            },
            seed_skill_version_id="skill_fundamental_1_0_0",
            timestamp=NOW,
        )
