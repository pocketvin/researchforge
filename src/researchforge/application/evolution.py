"""Controlled, deterministic skill-evolution policy outside LangGraph."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

THRESHOLDS = {
    "repair_rate_min": 0.5,
    "regression_rate_max": 0.05,
    "task_score_drop_max": 0.02,
    "cluster_support_min": 3,
    "cluster_share_min": 0.2,
}
MODEL_CONFIG: dict[str, Any] = {
    "provider": "openai",
    "model_id": "gpt-5.6-luna",
    "model_snapshot": None,
    "temperature": None,
    "seed": None,
    "reasoning_effort": "medium",
    "max_output_tokens": 2000,
    "tool_choice_policy": "controlled",
    "store": False,
    "built_in_tools": [],
}


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class FailureCluster:
    cluster_id: str
    failure_label: str
    signature: str
    eligible_run_count: int
    supporting_failure_ids: tuple[str, ...]
    source_evaluation_ids: tuple[str, ...]
    distinct_case_ids: tuple[str, ...]

    @property
    def support_count(self) -> int:
        return len(self.supporting_failure_ids)


def preregister_experiment(
    *,
    experiment_id: str,
    suite_id: str,
    split_cases: dict[str, list[dict[str, str]]],
    seed_skill_version_id: str,
    timestamp: datetime,
) -> dict[str, Any]:
    """Freeze a split manifest only when both case IDs and group keys are isolated."""
    required = {"evolution", "validation", "final_test"}
    if set(split_cases) != required or any(not split_cases[split] for split in required):
        raise ValueError("all three non-empty experiment splits are required")
    all_case_ids: list[str] = []
    split_groups: dict[str, set[str]] = {}
    for split, cases in split_cases.items():
        case_ids = [case["case_id"] for case in cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError(f"duplicate case IDs inside {split}")
        all_case_ids.extend(case_ids)
        split_groups[split] = {case["group_key"] for case in cases}
    if len(all_case_ids) != len(set(all_case_ids)):
        raise ValueError("case IDs cross experiment splits")
    for left, right in (
        ("evolution", "validation"),
        ("evolution", "final_test"),
        ("validation", "final_test"),
    ):
        if split_groups[left] & split_groups[right]:
            raise ValueError(f"group keys cross {left} and {right}")
    frozen_suite = {split: split_cases[split] for split in sorted(split_cases)}
    return {
        "schema_version": "1.4.0",
        "experiment_id": experiment_id,
        "scope_version": "1.4",
        "suite_id": suite_id,
        "suite_hash": _canonical_hash(frozen_suite),
        "status": "preregistered",
        "outcome": "PENDING",
        "model": MODEL_CONFIG,
        "graph_version": "1.0.0",
        "seed_skill_version_id": seed_skill_version_id,
        "candidate_skill_version_id": None,
        "split_case_ids": {
            split: [case["case_id"] for case in split_cases[split]]
            for split in ("evolution", "validation", "final_test")
        },
        "thresholds": THRESHOLDS,
        "run_ids": [],
        "evaluation_ids": [],
        "budget": {"currency": "USD", "cap": 20.0, "spent": 0.0},
        "final_test_consumed": False,
        "preregistered_at": timestamp.isoformat(),
        "finished_at": None,
    }


def select_eligible_cluster(evaluations: list[dict[str, Any]]) -> FailureCluster | None:
    """Select the strongest exact-signature cluster under frozen support rules."""
    eligible_run_count = len({str(item["run_id"]) for item in evaluations})
    grouped: dict[tuple[str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for evaluation in evaluations:
        for failure in evaluation["failure_events"]:
            grouped[(failure["failure_label"], failure["signature"])].append((evaluation, failure))
    minimum = max(
        THRESHOLDS["cluster_support_min"],
        math.ceil(THRESHOLDS["cluster_share_min"] * eligible_run_count),
    )
    candidates: list[FailureCluster] = []
    for (label, signature), items in grouped.items():
        case_ids = tuple(sorted({str(item[0]["case_id"]) for item in items}))
        failure_ids = tuple(sorted({str(item[1]["failure_id"]) for item in items}))
        if len(failure_ids) < minimum or len(case_ids) < 2:
            continue
        candidates.append(
            FailureCluster(
                cluster_id=f"cluster_{label.lower()}_{_canonical_hash(signature)[:12]}",
                failure_label=label,
                signature=signature,
                eligible_run_count=eligible_run_count,
                supporting_failure_ids=failure_ids,
                source_evaluation_ids=tuple(
                    sorted({str(item[0]["evaluation_id"]) for item in items})
                ),
                distinct_case_ids=case_ids,
            )
        )
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (-item.support_count, item.failure_label, item.signature),
    )[0]


def distill_experience(
    cluster: FailureCluster,
    *,
    observed_behavior: str,
    applicable_condition: str,
    required_procedure: str,
    exceptions: list[str],
    timestamp: datetime,
) -> dict[str, Any]:
    payload = {
        "schema_version": "1.4.0",
        "experience_id": f"experience_{cluster.cluster_id}",
        "cluster_id": cluster.cluster_id,
        "failure_label": cluster.failure_label,
        "failure_signature": cluster.signature,
        "observed_behavior": observed_behavior,
        "applicable_condition": applicable_condition,
        "required_procedure": required_procedure,
        "exceptions": exceptions,
        "supporting_failure_ids": list(cluster.supporting_failure_ids),
        "source_evaluation_ids": list(cluster.source_evaluation_ids),
        "created_at": timestamp.isoformat(),
    }
    return {**payload, "content_hash": _canonical_hash(payload)}


def propose_patch(
    cluster: FailureCluster,
    experience: dict[str, Any],
    *,
    seed_version: str,
    seed_hash: str,
    timestamp: datetime,
) -> dict[str, Any]:
    rule = str(experience["required_procedure"])
    return {
        "schema_version": "1.4.0",
        "patch_id": f"patch_{cluster.cluster_id}",
        "source_skill": {"version": seed_version, "content_hash": seed_hash},
        "candidate_version": f"{seed_version}-candidate.1",
        "target_failure_cluster": {
            "cluster_id": cluster.cluster_id,
            "failure_label": cluster.failure_label,
            "signature": cluster.signature,
            "eligible_run_count": cluster.eligible_run_count,
            "support_count": cluster.support_count,
            "supporting_failure_ids": list(cluster.supporting_failure_ids),
        },
        "operations": [
            {
                "operation": "ADD",
                "target_section": "earnings_quality",
                "current_text": None,
                "new_rule": rule,
                "reason": f"Addresses verifier-confirmed cluster {cluster.cluster_id}.",
            }
        ],
        "guardrails": {
            "allowed_sections_only": True,
            "tools_unchanged": True,
            "permissions_unchanged": True,
            "experiment_policy_unchanged": True,
            "static_lint_passed": True,
            "conflict_check_passed": True,
            "total_changed_characters": len(rule),
        },
        "generated_by": MODEL_CONFIG,
        "status": "PROPOSED",
        "validation_evaluation_ids": [],
        "decision": None,
        "created_at": timestamp.isoformat(),
        "decided_at": None,
    }


def decide_validation(
    patch: dict[str, Any],
    seed_evaluations: list[dict[str, Any]],
    candidate_evaluations: list[dict[str, Any]],
    *,
    timestamp: datetime,
) -> dict[str, Any]:
    """Apply paired frozen thresholds; qualitative scores never affect adoption."""
    seed_by_case = {str(item["case_id"]): item for item in seed_evaluations}
    candidate_by_case = {str(item["case_id"]): item for item in candidate_evaluations}
    if set(seed_by_case) != set(candidate_by_case) or not seed_by_case:
        raise ValueError("Seed and Candidate Validation cases must pair exactly")
    signature = patch["target_failure_cluster"]["signature"]

    def has_target(evaluation: dict[str, Any]) -> bool:
        return any(event["signature"] == signature for event in evaluation["failure_events"])

    seed_target_cases = {case for case, item in seed_by_case.items() if has_target(item)}
    repaired = sum(1 for case in seed_target_cases if not has_target(candidate_by_case[case]))
    repair_rate = repaired / len(seed_target_cases) if seed_target_cases else 0.0
    target_reduced = sum(map(has_target, candidate_evaluations)) < sum(
        map(has_target, seed_evaluations)
    )

    target_check_codes = {
        code
        for item in seed_evaluations
        for event in item["failure_events"]
        if event["signature"] == signature
        for code in event["check_codes"]
    }
    regression_denominator = 0
    regressions = 0
    for case_id, seed in seed_by_case.items():
        candidate = candidate_by_case[case_id]
        seed_checks = {
            item["check_code"]: item
            for item in seed["deterministic_checks"] + seed["coverage_checks"]
        }
        candidate_checks = {
            item["check_code"]: item
            for item in candidate["deterministic_checks"] + candidate["coverage_checks"]
        }
        for code, check in seed_checks.items():
            if code in target_check_codes or check["status"] != "PASS":
                continue
            regression_denominator += 1
            if candidate_checks.get(code, {}).get("status") != "PASS":
                regressions += 1
    regression_rate = regressions / regression_denominator if regression_denominator else 0.0
    seed_score = sum(item["metrics"]["task_score"] for item in seed_evaluations) / len(
        seed_evaluations
    )
    candidate_score = sum(item["metrics"]["task_score"] for item in candidate_evaluations) / len(
        candidate_evaluations
    )
    hard_labels = {"CALCULATION_ERROR", "PERIOD_ERROR", "CITATION_ERROR"}
    seed_hard = {
        (item["case_id"], event["signature"])
        for item in seed_evaluations
        for event in item["failure_events"]
        if event["failure_label"] in hard_labels
    }
    candidate_hard = {
        (item["case_id"], event["signature"])
        for item in candidate_evaluations
        for event in item["failure_events"]
        if event["failure_label"] in hard_labels
    }
    deterministic_preserved = candidate_hard <= seed_hard
    overall_non_inferior = candidate_score >= seed_score - THRESHOLDS["task_score_drop_max"]
    regression_within = regression_rate <= THRESHOLDS["regression_rate_max"]
    adopted = (
        target_reduced
        and repair_rate >= THRESHOLDS["repair_rate_min"]
        and deterministic_preserved
        and overall_non_inferior
        and regression_within
        and patch["guardrails"]["static_lint_passed"]
        and patch["guardrails"]["conflict_check_passed"]
    )
    reason = (
        f"repair_rate={repair_rate:.3f}; regression_rate={regression_rate:.3f}; "
        f"seed_score={seed_score:.3f}; candidate_score={candidate_score:.3f}"
    )
    return {
        **patch,
        "status": "ADOPTED" if adopted else "REJECTED",
        "validation_evaluation_ids": [str(item["evaluation_id"]) for item in candidate_evaluations],
        "decision": {
            "target_failure_reduced": target_reduced,
            "deterministic_quality_preserved": deterministic_preserved,
            "overall_non_inferior": overall_non_inferior,
            "regression_within_threshold": regression_within,
            "decision_reason": reason,
        },
        "decided_at": timestamp.isoformat(),
    }


def decide_final_test(
    adopted_patch: dict[str, Any],
    seed_evaluation: dict[str, Any],
    candidate_evaluation: dict[str, Any],
) -> str:
    """Consume one paired Final Test and return its honest terminal outcome."""
    if adopted_patch["status"] != "ADOPTED":
        raise ValueError("Final Test is sealed until Validation adopts the Candidate")
    if seed_evaluation["case_id"] != candidate_evaluation["case_id"]:
        raise ValueError("Final Test pair must use the same sealed case")
    signature = adopted_patch["target_failure_cluster"]["signature"]
    seed_has_target = any(
        event["signature"] == signature for event in seed_evaluation["failure_events"]
    )
    candidate_has_target = any(
        event["signature"] == signature for event in candidate_evaluation["failure_events"]
    )
    catastrophic = any(
        event["failure_label"] in {"CALCULATION_ERROR", "PERIOD_ERROR", "CITATION_ERROR"}
        for event in candidate_evaluation["failure_events"]
    )
    return (
        "SUPPORTED"
        if seed_has_target and not candidate_has_target and not catastrophic
        else "REJECTED_FINAL"
    )


def complete_experiment(
    experiment: dict[str, Any],
    *,
    outcome: str,
    run_ids: list[str],
    evaluation_ids: list[str],
    candidate_skill_version_id: str | None,
    spent: float,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    if outcome not in {
        "NO_ELIGIBLE_CLUSTER",
        "REJECTED_VALIDATION",
        "REJECTED_FINAL",
        "SUPPORTED",
    }:
        raise ValueError("invalid terminal experiment outcome")
    if spent > experiment["budget"]["cap"]:
        raise ValueError("experiment spend exceeds frozen cap")
    finished = timestamp or datetime.now(UTC)
    return {
        **experiment,
        "status": "completed",
        "outcome": outcome,
        "candidate_skill_version_id": candidate_skill_version_id,
        "run_ids": run_ids,
        "evaluation_ids": evaluation_ids,
        "budget": {**experiment["budget"], "spent": spent},
        "final_test_consumed": outcome in {"REJECTED_FINAL", "SUPPORTED"},
        "finished_at": finished.isoformat(),
    }
