"""Benchmark semantic assessor contracts remain report-bound and explicitly uncalibrated."""

from __future__ import annotations

import pytest

from researchforge.v2.benchmarks.semantic_assessor import (
    AtomicClaimAssessment,
    SemanticAssessmentDraft,
    annotations_from_draft,
    assessor_independence_label,
    build_payload,
    product_runtime_model_roles,
)
from researchforge.v2.quality import FindingRequirement, QualityCase, RequirementAssessment


def quality_case() -> QualityCase:
    return QualityCase(
        case_id="external:test",
        split="validation",
        question="What is the answer?",
        company_id="company_test",
        research_time="2026-01-01T00:00:00+00:00",
        corpus_hash="abc",
        reference_author="external benchmark",
        required_findings=[
            FindingRequirement(
                requirement_id="gold_answer",
                description="Answer the benchmark question correctly.",
                reference_answer="42",
            )
        ],
    )


def report() -> dict:
    return {
        "title": "Test report",
        "executive_summary": "The answer is 42.",
        "findings": [
            {
                "claim_id": "claim_1",
                "title": "Answer",
                "text": "The filing states 42.",
                "kind": "observation",
                "evidence_ids": ["view_1"],
                "uncertainty": "",
            }
        ],
        "limitations": [],
    }


def draft() -> SemanticAssessmentDraft:
    return SemanticAssessmentDraft(
        requirement_assessments=[
            RequirementAssessment(
                requirement_id="gold_answer",
                report_claim_ids=["claim_1"],
                verdict="covered",
                reason="The report gives the reference answer.",
            )
        ],
        atomic_claim_assessments=[
            AtomicClaimAssessment(
                report_claim_id="claim_1",
                atomic_claim="The filing states 42.",
                correctness="correct",
                citation_support="supported",
                reason="The cited filing excerpt states 42.",
            )
        ],
        premature_stop=False,
        unnecessary_continuation=True,
        notes=["Synthetic evaluator test."],
    )


def test_annotations_are_derived_from_detailed_assessment_not_model_counts() -> None:
    annotations = annotations_from_draft(
        quality_case(),
        report_hash="report_hash",
        report=report(),
        draft=draft(),
        assessor_id="test-assessor",
        assessor_version="test-v1",
    )
    assert annotations.assessment_kind == "uncalibrated_model"
    assert annotations.assessed_atomic_claims == 1
    assert annotations.correct_atomic_claims == 1
    assert annotations.supported_cited_claims == 1
    assert annotations.claims_with_valid_support == 1
    assert annotations.premature_stop is False
    assert annotations.unnecessary_continuation is True
    assert any("not ground truth" in note for note in annotations.notes)


def test_assessor_must_cover_every_report_finding_and_reference_requirement() -> None:
    incomplete = draft().model_copy(update={"atomic_claim_assessments": []})
    with pytest.raises(ValueError, match="every report finding"):
        annotations_from_draft(
            quality_case(),
            report_hash="report_hash",
            report=report(),
            draft=incomplete,
            assessor_id="test-assessor",
            assessor_version="test-v1",
        )
    wrong_requirement = draft().model_copy(
        update={
            "requirement_assessments": [
                RequirementAssessment(
                    requirement_id="not_gold",
                    report_claim_ids=["claim_1"],
                    verdict="covered",
                    reason="wrong requirement",
                )
            ]
        }
    )
    with pytest.raises(ValueError, match="every reference requirement"):
        annotations_from_draft(
            quality_case(),
            report_hash="report_hash",
            report=report(),
            draft=wrong_requirement,
            assessor_id="test-assessor",
            assessor_version="test-v1",
        )


def test_assessor_payload_contains_report_citations_and_reference_but_no_hidden_state() -> None:
    payload = build_payload(
        quality_case(),
        report=report(),
        observed_evidence=[
            {
                "artifact_id": "view_1",
                "page_number": 7,
                "source_kind": "page",
                "text": "The filing value is 42.",
            }
        ],
        trajectory={"agent_turns": 2},
    )
    finding = payload["report"]["findings"][0]
    assert finding["cited_evidence"][0]["text"] == "The filing value is 42."
    assert payload["reference_requirements"][0]["reference_answer"] == "42"
    assert "working_state" not in payload
    assert "messages" not in payload


def test_structured_assessor_repairs_schema_once_without_changing_judge() -> None:
    from types import SimpleNamespace

    from researchforge.v2.benchmarks.semantic_assessor import (
        FindingAssessmentDraft,
        _structured_call,
    )

    invalid = '{"report_claim_id":"claim_1","atomic_claims":[],"unexpected":true}'
    valid = FindingAssessmentDraft(
        report_claim_id="claim_1",
        atomic_claim_assessments=[
            AtomicClaimAssessment(
                report_claim_id="claim_1",
                atomic_claim="The filing states 42.",
                correctness="correct",
                citation_support="supported",
                reason="The cited evidence states 42.",
            )
        ],
        notes=[],
    ).model_dump_json()

    class FakeCompletions:
        def __init__(self) -> None:
            self.calls = 0
            self.messages: list[list[dict]] = []

        def create(self, **kwargs: object) -> SimpleNamespace:
            self.calls += 1
            self.messages.append(kwargs["messages"])  # type: ignore[index]
            content = invalid if self.calls == 1 else valid
            return SimpleNamespace(
                model="same-judge-model",
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
            )

    completions = FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    parsed, metadata = _structured_call(
        client,  # type: ignore[arg-type]
        model="same-judge-model",
        policy="Return strict JSON.",
        payload={"finding": "test"},
        output_model=FindingAssessmentDraft,
        schema_name="FindingAssessmentDraftTest",
        timeout_seconds=5,
        temperature=0,
    )
    assert parsed.report_claim_id == "claim_1"
    assert completions.calls == 2
    assert metadata["protocol_repair_attempts"] == 1
    assert metadata["input_tokens"] == 20
    assert metadata["output_tokens"] == 10
    repair_message = completions.messages[1][-1]["content"]
    assert "schema_repair" in str(repair_message)


def test_assessor_independence_uses_actual_fallback_model_roles() -> None:
    run = {
        "usage": {
            "research_provider_fallback_used": True,
            "models": {
                "research": "deepseek-v4-flash",
                "reflection": "deepseek-v4-flash",
                "synthesis": "deepseek-v4-flash",
                "research_fallback": "qwen-plus",
                "synthesis_after_research_fallback": "qwen3-max",
                "semantic_review": "qwen-plus",
                "vision": "qwen3-vl-plus",
            },
        }
    }
    roles = product_runtime_model_roles(run)
    assert roles == {
        "research": "qwen-plus",
        "reflection": "qwen3-max",
        "synthesis": "qwen3-max",
        "semantic_review": "qwen-plus",
        "vision": "qwen3-vl-plus",
        "research_provider_fallback_used": True,
    }

    independence, observed_roles = assessor_independence_label(
        run,
        assessor_provider="qwen",
        assessor_model="qwen3-max",
    )
    assert independence == "same_model_as_product_synthesis"
    assert observed_roles == roles

    independence, _ = assessor_independence_label(
        run,
        assessor_provider="qwen",
        assessor_model="qwen-plus",
    )
    assert independence == "same_model_as_product_semantic_review"

    independence, _ = assessor_independence_label(
        run,
        assessor_provider="kimi",
        assessor_model="kimi-k3",
    )
    assert independence == "different_provider_from_product_runtime"


def test_assessor_independence_marks_same_provider_different_model_on_primary_run() -> None:
    run = {
        "usage": {
            "research_provider_fallback_used": False,
            "models": {
                "research": "deepseek-v4-flash",
                "reflection": "deepseek-v4-flash",
                "synthesis": "deepseek-v4-flash",
                "semantic_review": "qwen-plus",
                "vision": "qwen3-vl-plus",
            },
        }
    }
    independence, roles = assessor_independence_label(
        run,
        assessor_provider="qwen",
        assessor_model="qwen3-max",
    )
    assert independence == "different_model_same_provider"
    assert roles["synthesis"] == "deepseek-v4-flash"
    assert roles["semantic_review"] == "qwen-plus"

    independence, _ = assessor_independence_label(
        run,
        assessor_provider="deepseek",
        assessor_model="deepseek-v4-flash",
    )
    assert independence == "same_model_as_product_synthesis"


def test_finding_evidence_compaction_keeps_relevant_tail_instead_of_blind_head() -> None:
    from researchforge.v2.benchmarks.semantic_assessor import _compact_finding

    long_prefix = "Operating activities detail " * 80
    evidence = (
        long_prefix
        + "\nCash flows from investing activities:\n"
        + "Capital expenditures (116) (131) (155)\n"
        + "Other investing activities 6 (6) 3"
    )
    compact = _compact_finding(
        {
            "claim_id": "claim_capex",
            "title": "Activision capex ratio",
            "text": (
                "FY2019 capital expenditures were 116 million, FY2018 131 million and "
                "FY2017 155 million."
            ),
            "kind": "observation",
            "uncertainty": "",
            "cited_evidence": [{"evidence_id": "view_capex", "text": evidence}],
        },
        evidence_chars=650,
    )
    assert "Capital expenditures (116) (131) (155)" in compact["cited_evidence"][0]["text"]
    assert len(compact["cited_evidence"][0]["text"]) <= 650


def test_reference_page_compaction_uses_question_to_keep_relevant_financial_line() -> None:
    from researchforge.v2.benchmarks.semantic_assessor import _reference_payload
    from researchforge.v2.quality import EvidenceAlternative, EvidenceRequirement

    long_prefix = "Operating activities detail " * 80
    case = quality_case().model_copy(
        update={
            "question": "What is the capex amount from the cash flow statement?",
            "required_evidence": [
                EvidenceRequirement(
                    requirement_id="gold_page",
                    description="Observe the annotated cash-flow evidence page.",
                    alternatives=[
                        EvidenceAlternative(
                            document_hash="d" * 64,
                            page_number=73,
                            match_mode="page",
                            required_text=(
                                long_prefix
                                + "\nCash flows from investing activities:\n"
                                + "Capital expenditures (116) (131) (155)\n"
                            ),
                        )
                    ],
                )
            ],
        }
    )
    payload = _reference_payload(case, evidence_text_limit=650)
    text = payload["reference_evidence"][0]["alternatives"][0]["required_text"]
    assert "Capital expenditures (116) (131) (155)" in text
    assert len(text) <= 650
