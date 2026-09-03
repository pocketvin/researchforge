"""Summarize final Web+n8n human records against the frozen Phase 6 rules."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.validate_contracts import ROOT, load_json, validate_instance

COMMON = (
    "successful_task_initiation",
    "conclusion_understanding",
    "key_financial_fact_discovery",
    "calculation_understanding",
    "evidence_discovery",
    "limitation_or_counter_evidence_discovery",
    "monitoring_discovery",
    "trust_boundary_understanding",
)
SPECIFIC = {
    "web": ("navigation", "information_hierarchy", "progressive_disclosure", "report_readability"),
    "n8n": (
        "workflow_entry_usability",
        "run_status_comprehension",
        "asynchronous_waiting_experience",
        "failure_path_comprehension",
        "perceived_automation_value",
    ),
}


def _rate(passes: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else passes / denominator


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    session_ids = [record["session_id"] for record in records]
    if len(session_ids) != len(set(session_ids)):
        raise ValueError("session_id values must be unique")
    eligible = [
        record
        for record in records
        if record["study_started"] is True and record["consent"]["obtained"] is True
    ]
    for record in eligible:
        if record["evidence_label"] != "REAL_HUMAN" or record["simulated"] is not False:
            raise ValueError("eligible sessions must be consented REAL_HUMAN records")
        surfaces = [attempt["surface"] for attempt in record["surface_attempts"]]
        if sorted(surfaces) != ["n8n", "web"]:
            raise ValueError("every eligible session must contain Web and n8n exactly once")

    participant_count = len(eligible)
    group_counts = Counter(record["surface_order"] for record in eligible)
    attempts = [attempt for record in eligible for attempt in record["surface_attempts"]]
    common_passes = {
        metric: sum(
            attempt["common_outcomes"][metric] == "independent_pass" for attempt in attempts
        )
        for metric in COMMON
    }
    common_denominator = participant_count * 2
    common_rates = {
        metric: _rate(count, common_denominator) for metric, count in common_passes.items()
    }
    all_common_passes = sum(common_passes.values())
    all_common_denominator = common_denominator * len(COMMON)

    surface_results: dict[str, Any] = {}
    for surface in ("web", "n8n"):
        surface_attempts = [attempt for attempt in attempts if attempt["surface"] == surface]
        specific_key = f"{surface}_outcomes"
        specific_passes = {
            metric: sum(
                attempt[specific_key][metric] == "independent_pass" for attempt in surface_attempts
            )
            for metric in SPECIFIC[surface]
        }
        surface_results[surface] = {
            "attempts": len(surface_attempts),
            "all_eight_shared_independent": sum(
                all(value == "independent_pass" for value in attempt["common_outcomes"].values())
                for attempt in surface_attempts
            ),
            "all_eight_shared_rate": _rate(
                sum(
                    all(
                        value == "independent_pass" for value in attempt["common_outcomes"].values()
                    )
                    for attempt in surface_attempts
                ),
                participant_count,
            ),
            "successful_task_initiation_rate": _rate(
                sum(
                    attempt["common_outcomes"]["successful_task_initiation"] == "independent_pass"
                    for attempt in surface_attempts
                ),
                participant_count,
            ),
            "trust_boundary_understanding_rate": _rate(
                sum(
                    attempt["common_outcomes"]["trust_boundary_understanding"] == "independent_pass"
                    for attempt in surface_attempts
                ),
                participant_count,
            ),
            "specific_rates": {
                metric: _rate(count, participant_count) for metric, count in specific_passes.items()
            },
        }

    checks = {
        "minimum_six_participants": participant_count >= 6,
        "balanced_groups": abs(group_counts["web_then_n8n"] - group_counts["n8n_then_web"]) <= 1,
        "overall_shared_at_least_80_percent": _rate(all_common_passes, all_common_denominator)
        >= 0.80,
        "each_shared_at_least_75_percent": all(rate >= 0.75 for rate in common_rates.values()),
        "each_surface_two_thirds_complete_all_shared": all(
            result["all_eight_shared_rate"] >= 2 / 3 for result in surface_results.values()
        ),
        "initiation_and_trust_each_surface_at_least_five_sixths": all(
            result[metric] >= 5 / 6
            for result in surface_results.values()
            for metric in (
                "successful_task_initiation_rate",
                "trust_boundary_understanding_rate",
            )
        ),
        "each_surface_specific_at_least_75_percent": all(
            rate >= 0.75
            for result in surface_results.values()
            for rate in result["specific_rates"].values()
        ),
    }
    ready = checks["minimum_six_participants"]
    passed = ready and all(checks.values())
    return {
        "protocol_version": "final-dual-surface-v1.0-frozen",
        "status": "PASS" if passed else "FAIL" if ready else "NOT_READY",
        "human_user_value_validated": passed,
        "eligible_participants": participant_count,
        "scheduled_templates_excluded": sum(not record["study_started"] for record in records),
        "withdrawn_after_start": sum(record["status"] == "withdrawn" for record in eligible),
        "group_counts": dict(group_counts),
        "overall_shared_rate": _rate(all_common_passes, all_common_denominator),
        "common_rates": common_rates,
        "surface_results": surface_results,
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", nargs="+", type=Path)
    args = parser.parse_args()
    schemas = {path.resolve(): load_json(path) for path in (ROOT / "schemas").glob("*/*.json")}
    schema_path = ROOT / "schemas/v1.5/final-human-evaluation-session.schema.json"
    records = []
    for path in args.records:
        record = load_json(path)
        validate_instance(record, schemas[schema_path], schema_path, schemas)
        records.append(record)
    print(json.dumps(summarize(records), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
