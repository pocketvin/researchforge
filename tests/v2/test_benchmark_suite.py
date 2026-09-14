"""Public benchmark suites are immutable development manifests, never hidden gold containers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from researchforge.v2.benchmarks.suite import (
    BenchmarkSuiteManifest,
    implementation_fingerprint,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = (
    PROJECT_ROOT
    / "docs"
    / "contracts"
    / "v2"
    / "benchmarks"
    / "financebench-public-development-10-v1.json"
)


def test_tracked_financebench_suite_is_public_development_and_contains_no_gold() -> None:
    raw = json.loads(SUITE_PATH.read_text())
    suite = BenchmarkSuiteManifest.model_validate(raw)
    assert suite.suite_id == "financebench-public-development-10-v1"
    assert suite.split == "development"
    assert suite.gold_fields_used_in_selection is False
    assert len(suite.cases) == 10
    assert len({case.company for case in suite.cases}) == 9
    assert len({case.financebench_id for case in suite.cases}) == 10
    assert set(suite.anchors) == {
        "financebench_id_03029",
        "financebench_id_07966",
        "financebench_id_00499",
    }
    serialized = json.dumps(raw).casefold()
    for forbidden in ('"answer"', '"justification"', '"evidence"'):
        assert forbidden not in serialized
    assert {case.stratum for case in suite.cases} == {
        "anchor",
        "extraction_metrics",
        "extraction_domain",
        "numerical_metrics",
        "logical_numeric",
        "num_or_logical",
        "margin_driver",
        "novel_10k",
    }


def test_suite_hash_detects_manifest_tampering() -> None:
    raw = json.loads(SUITE_PATH.read_text())
    raw["cases"][0]["question"] += " tampered"
    with pytest.raises(ValidationError, match="suite hash"):
        BenchmarkSuiteManifest.model_validate(raw)


def test_implementation_fingerprint_is_stable_for_same_tree() -> None:
    first = implementation_fingerprint(PROJECT_ROOT)
    second = implementation_fingerprint(PROJECT_ROOT)
    assert first == second
    assert len(first) == 64


def _synthetic_suite(source_sha256: str) -> BenchmarkSuiteManifest:
    from researchforge.v2.benchmarks.financebench import FINANCEBENCH_COMMIT, FINANCEBENCH_LICENSE
    from researchforge.v2.benchmarks.suite import finalize_suite

    return finalize_suite(
        {
            "schema_version": "2.0.0",
            "suite_id": "synthetic-public-development-suite",
            "benchmark_name": "FinanceBench open-source",
            "benchmark_commit": FINANCEBENCH_COMMIT,
            "benchmark_license": FINANCEBENCH_LICENSE,
            "split": "development",
            "selector_version": "test-v1",
            "seed": 1,
            "source_questions_sha256": source_sha256,
            "source_question_count": 1,
            "scope": "synthetic suite-runner test; no gold labels",
            "gold_fields_used_in_selection": False,
            "anchors": [],
            "cases": [
                {
                    "financebench_id": "financebench_synthetic_001",
                    "stratum": "synthetic",
                    "company": "Synthetic Co",
                    "doc_name": "SYNTHETIC_2025_10K",
                    "question_type": "metrics-generated",
                    "question_reasoning": "Information extraction",
                    "question": "What was revenue?",
                }
            ],
        }
    )


def test_suite_runner_can_initialize_without_provider_calls(tmp_path: Path) -> None:
    import hashlib
    import subprocess
    import sys

    source = tmp_path / "source" / "financebench_open_source.jsonl"
    source.parent.mkdir(parents=True)
    source.write_text('{"synthetic":true}\n')
    suite = _synthetic_suite(hashlib.sha256(source.read_bytes()).hexdigest())
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(suite.model_dump_json(indent=2) + "\n")
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_v2_financebench_suite.py",
            "--suite",
            str(suite_path),
            "--benchmark-root",
            str(tmp_path),
            "--max-new-runs",
            "0",
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["new_runs_started_this_invocation"] == 0
    assert result["pending"] == 1
    assert result["stopped_reason"] == "max_new_runs"
    execution = json.loads(Path(result["execution"]).read_text())
    assert execution["target_case_ids"] == ["financebench_synthetic_001"]
    assert execution["cases"][0]["status"] == "pending"
