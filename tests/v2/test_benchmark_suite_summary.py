from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from researchforge.v2.benchmarks.suite import (
    BenchmarkSuiteExecution,
    BenchmarkSuiteManifest,
    SuiteCaseExecution,
)
from researchforge.v2.benchmarks.suite_summary import summarize_suite_execution

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SUITE_PATH = (
    PROJECT_ROOT
    / "docs"
    / "contracts"
    / "v2"
    / "benchmarks"
    / "financebench-public-development-10-v1.json"
)


def _assessment(case_id: str, evidence_value: int, independence: str) -> dict:
    return {
        "schema_version": "2.0.0",
        "case_id": f"financebench:{case_id}",
        "eligible": True,
        "suitable_for_product_quality_claim": False,
        "metrics": {
            "required_evidence_observation_recall": {
                "status": "measured",
                "value": float(evidence_value),
                "numerator": evidence_value,
                "denominator": 1,
            },
            "reference_answer_scalar_presence": {
                "status": "not_measured",
                "value": None,
                "numerator": 0,
                "denominator": 0,
            },
        },
        "trajectory": {
            "agent_turns": 2,
            "tool_results": 2,
            "counter_searches": 0,
            "provider_calls": 7,
            "total_tokens": 33000,
        },
        "benchmark_assessor": {"independence": independence},
    }


def test_suite_summary_is_stratified_and_never_emits_composite_score() -> None:
    suite = BenchmarkSuiteManifest.model_validate_json(SUITE_PATH.read_text())
    cases = suite.cases[:2]
    execution = BenchmarkSuiteExecution(
        execution_id="exec-test",
        suite_id=suite.suite_id,
        suite_hash=suite.suite_hash,
        implementation_hash="a" * 64,
        git_head="b" * 40,
        git_dirty=True,
        started_at=datetime.now(UTC),
        stopped_reason="completed",
        new_runs_started=2,
        estimated_cost_usd=0.02,
        max_new_runs=2,
        max_estimated_cost_usd=0.2,
        target_case_ids=[case.financebench_id for case in cases],
        cases=[
            SuiteCaseExecution(
                financebench_id=case.financebench_id,
                stratum=case.stratum,
                company=case.company,
                status="succeeded",
                run_id=f"run_{index}",
                lifecycle_state="succeeded",
            )
            for index, case in enumerate(cases)
        ],
    )
    assessments = {
        cases[0].financebench_id: _assessment(
            cases[0].financebench_id, 1, "same_model_as_product_synthesis"
        ),
        cases[1].financebench_id: _assessment(
            cases[1].financebench_id, 0, "different_provider_from_product_runtime"
        ),
    }
    summary = summarize_suite_execution(suite, execution, assessments)
    assert summary["split"] == "development"
    assert summary["public_development_suite"] is True
    assert summary["overall_score"] is None
    assert summary["overall"]["overall_score"] is None
    assert summary["overall"]["metrics"]["required_evidence_observation_recall"]["value"] == 0.5
    assert summary["coverage"]["assessment_cases"] == 2
    assert summary["coverage"]["status_counts"] == {"succeeded": 2}
    assert summary["assessor_independence_counts"] == {
        "different_provider_from_product_runtime": 1,
        "same_model_as_product_synthesis": 1,
    }
    assert "anchor" in summary["by_stratum"]
