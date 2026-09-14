"""Synthetic sanity checks for the measurement instrument, not quality claims."""

from __future__ import annotations

from researchforge.v2.quality import (
    QualityCase,
    SemanticAnnotations,
    evaluate_quality,
    summarize_quality_results,
)


def quality_inputs() -> tuple[QualityCase, dict, dict, list[dict]]:
    case = QualityCase.model_validate(
        {
            "case_id": "synthetic-quality-instrument-001",
            "split": "synthetic_sanity",
            "question": "Why did cash flow fall?",
            "company_id": "test_issuer",
            "research_time": "2025-12-31T00:00:00+00:00",
            "corpus_hash": "corpus-a",
            "reference_author": "synthetic test fixture",
            "numeric_references": [
                {
                    "metric_code": "revenue",
                    "fiscal_year": 2025,
                    "fiscal_period": "H1",
                    "period_basis": "ytd",
                    "currency": "CNY",
                    "value": "100",
                    "source_document_hash": "document-a",
                    "source_locator": "P2, row Revenue",
                }
            ],
            "required_evidence": [
                {
                    "requirement_id": "collections-explanation",
                    "description": "Collections explanation",
                    "alternatives": [
                        {
                            "document_hash": "document-a",
                            "page_number": 2,
                            "required_text": "Cash flow fell as collections slowed.",
                        }
                    ],
                }
            ],
            "required_findings": [
                {
                    "requirement_id": "cash-flow-change",
                    "description": "State the cash-flow direction.",
                },
                {
                    "requirement_id": "collection-effect",
                    "description": "Explain the collection effect.",
                },
            ],
        }
    )
    run = {
        "run_id": "synthetic-run",
        "lifecycle_state": "succeeded",
        "request": {"research_question": case.question, "research_time": case.research_time},
    }
    environment = {
        "company": {"company_id": case.company_id},
        "corpus_hash": case.corpus_hash,
        "facts": [
            {
                "fact_id": "fact-a",
                "metric_code": "revenue",
                "value": "100",
                "currency": "CNY",
                "period": {"fiscal_year": 2025, "fiscal_period": "H1", "period_basis": "ytd"},
                "source": {"content_hash": "document-a"},
            }
        ],
    }
    observations = [
        {
            "artifact_id": "view-a",
            "document_hash": "document-a",
            "page_number": 2,
            "text": "Cash flow fell as collections slowed.",
        }
    ]
    return case, run, environment, observations


def synthetic_report() -> dict:
    return {
        "findings": [
            {"claim_id": "claim_cash", "text": "Cash flow fell."},
            {"claim_id": "claim_collection", "text": "Collections slowed."},
        ]
    }


def test_reference_metrics_do_not_invent_semantic_or_stop_scores() -> None:
    case, run, environment, observations = quality_inputs()
    result = evaluate_quality(
        case,
        run=run,
        environment=environment,
        observed_evidence=observations,
        report_hash="report-a",
    )
    assert result["eligible"] is True
    assert result["metrics"]["reference_fact_recovery_accuracy"]["value"] == 1
    assert result["metrics"]["required_evidence_observation_recall"]["value"] == 1
    assert result["metrics"]["answer_correctness"]["value"] is None
    assert result["metrics"]["stop_quality"]["value"] is None
    assert result["overall_score"] is None
    assert result["suitable_for_product_quality_claim"] is False


def test_wrong_unit_period_and_partial_evidence_are_not_counted_as_correct() -> None:
    case, run, environment, observations = quality_inputs()
    environment["facts"][0]["period"]["period_basis"] = "discrete"
    observations[0]["text"] = "Cash flow fell."
    result = evaluate_quality(
        case,
        run=run,
        environment=environment,
        observed_evidence=observations,
        report_hash="report-a",
    )
    assert result["metrics"]["reference_fact_recovery_accuracy"]["value"] == 0
    assert result["metrics"]["required_evidence_observation_recall"]["value"] == 0


def test_changed_corpus_is_ineligible_not_a_low_quality_system_score() -> None:
    case, run, environment, observations = quality_inputs()
    environment["corpus_hash"] = "different-corpus"
    result = evaluate_quality(
        case, run=run, environment=environment, observed_evidence=observations, report_hash=None
    )
    assert result["eligible"] is False
    assert result["metrics"] == {}


def test_independent_annotations_keep_denominators_and_assessor_identity() -> None:
    case, run, environment, observations = quality_inputs()
    annotations = SemanticAnnotations.model_validate(
        {
            "report_hash": "report-a",
            "assessor_id": "synthetic-assessor",
            "assessor_version": "test-only",
            "assessment_kind": "human",
            "requirement_assessments": [
                {
                    "requirement_id": "cash-flow-change",
                    "report_claim_ids": ["claim_cash"],
                    "verdict": "covered",
                    "reason": "Synthetic assessor mapping.",
                }
            ],
            "assessed_report_claim_ids": ["claim_cash", "claim_collection"],
            "assessed_atomic_claims": 2,
            "correct_atomic_claims": 1,
            "assessed_cited_claims": 2,
            "supported_cited_claims": 1,
            "claims_requiring_citations": 2,
            "claims_with_valid_support": 1,
            "premature_stop": True,
            "unnecessary_continuation": False,
        }
    )
    result = evaluate_quality(
        case,
        run=run,
        environment=environment,
        observed_evidence=observations,
        report_hash="report-a",
        report=synthetic_report(),
        annotations=annotations,
    )
    assert result["metrics"]["reference_finding_coverage"] == {
        "value": 0.5,
        "numerator": 1,
        "denominator": 2,
        "status": "measured",
    }
    assert result["metrics"]["stop_quality"]["premature_stop"] is True
    assert result["suitable_for_product_quality_claim"] is False
    mismatch = evaluate_quality(
        case,
        run=run,
        environment=environment,
        observed_evidence=observations,
        report_hash="report-b",
        report=synthetic_report(),
        annotations=annotations,
    )
    assert mismatch["eligible"] is False


def test_real_environment_fact_mapping_shape_is_supported() -> None:
    case, run, environment, observations = quality_inputs()
    environment["facts"] = {"fact-a": environment["facts"][0]}
    result = evaluate_quality(
        case, run=run, environment=environment, observed_evidence=observations, report_hash=None
    )
    assert result["metrics"]["reference_fact_recovery_accuracy"]["value"] == 1


def test_annotations_cannot_confuse_reference_requirements_with_report_claim_ids() -> None:
    case, run, environment, observations = quality_inputs()
    annotations = SemanticAnnotations.model_validate(
        {
            "report_hash": "report-a",
            "assessor_id": "synthetic-assessor",
            "assessor_version": "test-only",
            "assessment_kind": "human",
            "requirement_assessments": [
                {
                    "requirement_id": "cash-flow-change",
                    "report_claim_ids": ["not-a-real-claim"],
                    "verdict": "covered",
                    "reason": "Intentionally invalid mapping.",
                }
            ],
            "assessed_report_claim_ids": [],
            "assessed_atomic_claims": 0,
            "correct_atomic_claims": 0,
            "assessed_cited_claims": 0,
            "supported_cited_claims": 0,
            "claims_requiring_citations": 0,
            "claims_with_valid_support": 0,
        }
    )
    result = evaluate_quality(
        case,
        run=run,
        environment=environment,
        observed_evidence=observations,
        report_hash="report-a",
        report=synthetic_report(),
        annotations=annotations,
    )
    assert result["eligible"] is False
    assert "semantic_annotations_reference_unknown_report_claims" in result["errors"]


def test_suite_summary_keeps_denominators_confidence_intervals_and_no_overall_score() -> None:
    case, run, environment, observations = quality_inputs()
    first = evaluate_quality(
        case,
        run=run,
        environment=environment,
        observed_evidence=observations,
        report_hash=None,
        events=[
            {"event_type": "agent_turn", "name": "research"},
            {"event_type": "tool_result", "name": "search_counter_evidence"},
        ],
    )
    second = evaluate_quality(
        case,
        run=run,
        environment=environment,
        observed_evidence=[],
        report_hash=None,
        events=[
            {"event_type": "agent_turn", "name": "research"},
            {"event_type": "agent_turn", "name": "research"},
        ],
    )
    summary = summarize_quality_results([first, second])
    evidence = summary["metrics"]["required_evidence_observation_recall"]
    assert evidence["numerator"] == 1 and evidence["denominator"] == 2
    assert 0 <= evidence["wilson_95"]["low"] <= evidence["wilson_95"]["high"] <= 1
    assert summary["trajectory"]["agent_turns"]["median"] == 1.5
    assert summary["overall_score"] is None


def test_equivalent_utc_timestamp_serializations_are_the_same_cutoff() -> None:
    case, run, environment, observations = quality_inputs()
    run["request"]["research_time"] = "2025-12-31T00:00:00Z"
    result = evaluate_quality(
        case, run=run, environment=environment, observed_evidence=observations, report_hash=None
    )
    assert result["eligible"] is True


def test_scalar_reference_presence_is_measured_but_not_called_answer_correctness() -> None:
    case, run, environment, observations = quality_inputs()
    case.required_findings[0].reference_answer = "$1,577.00"
    report = {
        "findings": [{"claim_id": "claim_cash"}],
        "executive_summary": "The answer is 1,577 USD millions; another figure is 1,373.",
    }
    result = evaluate_quality(
        case,
        run=run,
        environment=environment,
        observed_evidence=observations,
        report_hash="report-a",
        report=report,
    )
    assert result["metrics"]["reference_answer_scalar_presence"]["value"] == 1
    assert result["metrics"]["answer_correctness"]["value"] is None


def test_scalar_presence_keeps_percent_and_plain_number_semantics_distinct() -> None:
    case, run, environment, observations = quality_inputs()
    case.required_findings[0].reference_answer = "1.9%"
    report = {
        "findings": [],
        "executive_summary": "The report mentions 1.9 million, not 1.9 percent.",
    }
    result = evaluate_quality(
        case,
        run=run,
        environment=environment,
        observed_evidence=observations,
        report_hash="report-a",
        report=report,
    )
    assert result["metrics"]["reference_answer_scalar_presence"]["value"] == 0


def test_suspect_reference_keeps_evidence_metrics_but_disables_gold_scalar_measurement() -> None:
    case, run, environment, observations = quality_inputs()
    case.reference_integrity = "suspect"
    case.reference_integrity_notes = ["Synthetic gold conflicts with reviewed source."]
    case.required_findings[0].reference_answer = "$100"
    result = evaluate_quality(
        case,
        run=run,
        environment=environment,
        observed_evidence=observations,
        report_hash="report-a",
        report={"findings": [], "executive_summary": "The value is $100."},
    )
    assert result["eligible"] is True
    assert result["metrics"]["required_evidence_observation_recall"]["value"] == 1
    assert result["metrics"]["reference_answer_scalar_presence"]["value"] is None
    assert (
        result["metrics"]["reference_answer_scalar_presence"]["reason"]
        == "reference_integrity_suspect"
    )
    assert result["suitable_for_product_quality_claim"] is False
