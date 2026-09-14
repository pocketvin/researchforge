from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_quality_summary_cli_skips_non_assessment_json(tmp_path: Path) -> None:
    assessment = {
        "schema_version": "2.0.0",
        "case_id": "case-a",
        "eligible": True,
        "suitable_for_product_quality_claim": False,
        "metrics": {
            "required_evidence_observation_recall": {
                "value": 1.0,
                "numerator": 1,
                "denominator": 1,
                "status": "measured",
            },
            "reference_answer_scalar_presence": {
                "value": 1.0,
                "numerator": 1,
                "denominator": 1,
                "status": "measured",
            },
        },
        "trajectory": {"agent_turns": 2, "provider_calls": 4, "total_tokens": 1000},
    }
    (tmp_path / "case.json").write_text(json.dumps(assessment), encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps({"benchmark": "not assessment"}))
    output = tmp_path / "summary.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/summarize_v2_quality.py",
            str(tmp_path),
            "--output",
            str(output),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    summary = json.loads(output.read_text())
    assert summary["eligible_cases"] == 1
    assert summary["metrics"]["required_evidence_observation_recall"]["value"] == 1
    assert summary["metrics"]["reference_answer_scalar_presence"]["value"] == 1
    assert summary["trajectory"]["agent_turns"]["median"] == 2
    assert summary["overall_score"] is None
