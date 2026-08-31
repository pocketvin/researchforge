"""Fixed deterministic and coverage Verifier fixtures."""

from __future__ import annotations

import copy
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from researchforge.application.research import LoadedResearchData
from researchforge.application.verification import FinancialVerifier
from tests.runtime_helpers import assert_v14_schema, build_service, catl_request

EXPECTED_CATL_2024H1 = {
    "cash_conversion": "1.955345691552841179348299138",
    "gross_margin": "0.2653344423755971583069020985",
    "gross_profit": "44248984800.00",
    "profit_cash_divergence": "0",
}


def _bundle(
    tmp_path: Path,
) -> tuple[
    FinancialVerifier,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    LoadedResearchData,
]:
    service = build_service(tmp_path)
    request = catl_request()
    submission = service.submit(request)
    manifest = service.execute(submission.run_id)
    result = service.get_result(submission.run_id)
    trace = service.get_trace(submission.run_id)
    calculations = service.repository.get_calculations(submission.run_id)
    loaded = service.fixture_catalog.load(
        request.company_ids,
        request.requested_period_labels,
        request.research_time,
    )
    return FinancialVerifier(), manifest, result, trace, calculations, loaded


def _evaluate(
    verifier: FinancialVerifier,
    manifest: dict[str, Any],
    result: dict[str, Any],
    trace: dict[str, Any],
    calculations: list[dict[str, Any]],
    loaded: LoadedResearchData,
) -> dict[str, Any]:
    return verifier.evaluate(
        case_id="golden_g0_catl_2024h1_runtime",
        manifest=manifest,
        result=result,
        trace=trace,
        calculations=calculations,
        loaded=loaded,
        expected_calculations=EXPECTED_CATL_2024H1,
    )


def test_verifier_passes_the_fixed_happy_fixture(tmp_path: Path) -> None:
    evaluation = _evaluate(*_bundle(tmp_path))

    assert evaluation["failure_events"] == []
    assert evaluation["metrics"] == {
        "task_score": 1.0,
        "calculation_accuracy": 1.0,
        "evidence_coverage": 1.0,
        "critical_omission_rate": 0.0,
        "citation_accuracy": 1.0,
    }
    assert_v14_schema(evaluation, "evaluation-result.schema.json")


@pytest.mark.parametrize(
    ("mutation", "expected_label", "expected_check"),
    [
        ("calculation", "CALCULATION_ERROR", "calculation_cash_conversion"),
        ("coverage", "CRITICAL_OMISSION", "coverage_inventory"),
        ("citation", "CITATION_ERROR", "citation_existence"),
        ("cutoff", "PERIOD_ERROR", "point_in_time_validity"),
    ],
)
def test_verifier_detects_each_fixed_failure_signature(
    tmp_path: Path,
    mutation: str,
    expected_label: str,
    expected_check: str,
) -> None:
    verifier, manifest, result, trace, calculations, loaded = _bundle(tmp_path)
    result = copy.deepcopy(result)
    calculations = copy.deepcopy(calculations)
    if mutation == "calculation":
        target = next(item for item in calculations if item["formula_code"] == "cash_conversion")
        target["value"] = "999"
    elif mutation == "coverage":
        result["mandatory_checks"] = [
            item for item in result["mandatory_checks"] if item["check_code"] != "inventory"
        ]
    elif mutation == "citation":
        result["claims"][0]["fact_ids"].append("fact_missing_in_fixture")
    elif mutation == "cutoff":
        result["evidence_cutoff"] = datetime.fromisoformat("2024-01-01T00:00:00+08:00").isoformat()

    evaluation = _evaluate(verifier, manifest, result, trace, calculations, loaded)
    matching = [
        event
        for event in evaluation["failure_events"]
        if event["failure_label"] == expected_label and expected_check in event["check_codes"]
    ]

    assert len(matching) == 1
    assert_v14_schema(evaluation, "evaluation-result.schema.json")


def test_one_off_contribution_is_explicitly_unavailable_not_omitted(
    tmp_path: Path,
) -> None:
    _, _, result, _, _, _ = _bundle(tmp_path)
    check = next(
        item for item in result["mandatory_checks"] if item["check_code"] == "one_off_contribution"
    )

    assert check["status"] == "unavailable"
    assert "未作推断" in check["finding"]
    assert any("一次性损益" in limitation for limitation in result["limitations"])


def test_service_persists_evaluation_and_links_manifest(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    submission = service.submit(catl_request())
    service.execute(submission.run_id)

    evaluation = service.verify(
        submission.run_id,
        case_id="golden_g0_catl_2024h1_service",
        expected_calculations=EXPECTED_CATL_2024H1,
    )
    manifest = service.get_manifest(submission.run_id)

    assert manifest["artifacts"]["evaluation_id"] == evaluation["evaluation_id"]
    assert service.get_evaluation(submission.run_id) == evaluation
    assert_v14_schema(manifest, "run-manifest.schema.json")
    assert_v14_schema(evaluation, "evaluation-result.schema.json")
