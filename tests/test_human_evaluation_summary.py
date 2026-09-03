from __future__ import annotations

import copy
from typing import Any, cast

from scripts.summarize_human_evaluation import COMMON, SPECIFIC, summarize
from scripts.validate_contracts import ROOT, load_json


def completed_record(index: int, outcome: str = "independent_pass") -> dict[str, Any]:
    record = copy.deepcopy(
        load_json(ROOT / "examples/contracts/v1.5/final-human-evaluation-session.template.json")
    )
    record.update(
        {
            "session_id": f"test_session_{index}",
            "evidence_label": "REAL_HUMAN",
            "status": "completed",
            "study_started": True,
            "surface_order": "web_then_n8n" if index % 2 == 0 else "n8n_then_web",
            "started_at": "2026-09-04T09:00:00+08:00",
            "completed_at": "2026-09-04T09:30:00+08:00",
        }
    )
    record["consent"]["obtained"] = True
    for attempt in record["surface_attempts"]:
        attempt["attempt_status"] = "completed"
        attempt["run_id"] = f"run_{index:032x}"
        attempt["duration_seconds"] = 300
        attempt["common_outcomes"] = {metric: outcome for metric in COMMON}
        specific_key = f"{attempt['surface']}_outcomes"
        attempt[specific_key] = {metric: outcome for metric in SPECIFIC[attempt["surface"]]}
    return cast(dict[str, Any], record)


def test_six_balanced_independent_sessions_pass() -> None:
    result = summarize([completed_record(index) for index in range(6)])
    assert result["status"] == "PASS"
    assert result["human_user_value_validated"] is True
    assert result["overall_shared_rate"] == 1.0


def test_assistance_is_not_an_independent_pass() -> None:
    records = [completed_record(index) for index in range(6)]
    for record in records:
        record["surface_attempts"][0]["common_outcomes"] = {metric: "assisted" for metric in COMMON}
    result = summarize(records)
    assert result["status"] == "FAIL"
    assert result["human_user_value_validated"] is False
    assert result["overall_shared_rate"] == 0.5


def test_scheduled_templates_never_enter_the_denominator() -> None:
    template = load_json(
        ROOT / "examples/contracts/v1.5/final-human-evaluation-session.template.json"
    )
    result = summarize([template])
    assert result["status"] == "NOT_READY"
    assert result["eligible_participants"] == 0
    assert result["scheduled_templates_excluded"] == 1
