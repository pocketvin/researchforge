"""Regression coverage for frozen cases where cash conversion is not meaningful."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from researchforge.application.contracts import ResearchRunRequest
from researchforge.application.service import ResearchRunService
from researchforge.domain.models import CalculationStatus
from tests.runtime_helpers import assert_v14_schema

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "data" / "fixtures" / "v1.5-contingency"
SKILL_MANIFEST = (
    ROOT / "skills" / "fundamental-research" / "versions" / "1.0.0" / "skill-version.json"
)


def test_nonpositive_income_records_not_meaningful_without_failing_run(
    tmp_path: Path,
) -> None:
    service = ResearchRunService.build(tmp_path, PACKAGE, SKILL_MANIFEST)
    request = ResearchRunRequest(
        task_type="filing_analysis",
        research_question="利润是否转化为高质量经营现金流?",
        company_ids=["cn_300438"],
        requested_period_labels=["2024FY"],
        research_time=datetime.fromisoformat("2025-04-25T00:00:00+08:00"),
        idempotency_key="test-nonpositive-income-2024fy",
    )

    submission = service.submit(
        request,
        run_kind="benchmark_evolution",
        case_id="case_evo_greatpower_2024fy",
        split="evolution",
    )
    manifest = service.execute(submission.run_id)

    assert manifest["lifecycle_state"] == "succeeded"
    conversion = next(
        item
        for item in service.repository.get_calculations(submission.run_id)
        if item["formula_code"] == "cash_conversion"
    )
    assert conversion["status"] == CalculationStatus.NOT_MEANINGFUL.value
    assert conversion["value"] is None
    result = service.get_result(submission.run_id)
    check = next(
        item for item in result["mandatory_checks"] if item["check_code"] == "cash_conversion"
    )
    assert check["status"] == "not_applicable"
    evaluation = service.verify(
        submission.run_id,
        case_id="case_evo_greatpower_2024fy",
        expected_calculations={"cash_conversion": None},
    )
    assert evaluation["failure_events"] == []
    assert evaluation["metrics"]["calculation_accuracy"] == 1.0
    assert evaluation["metrics"]["evidence_coverage"] == 1.0
    assert_v14_schema(manifest, "run-manifest.schema.json")
    assert_v14_schema(result, "research-result.schema.json")
    assert_v14_schema(evaluation, "evaluation-result.schema.json")
