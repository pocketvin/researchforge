"""FinanceBench adapter tests: frozen external labels never enter the Agent runtime."""

from __future__ import annotations

import json
from pathlib import Path

from researchforge.v2.benchmarks.financebench import (
    build_environment,
    load_or_build_environment,
    make_quality_case,
)
from researchforge.v2.quality import evaluate_quality
from researchforge.v2.storage import ResearchRepository
from tests.v2.test_foundation import synthetic_pdf


def benchmark_inputs() -> tuple[dict, dict]:
    question = {
        "financebench_id": "financebench_test_001",
        "doc_name": "SYNTHETIC_2025_10K",
        "question": "What was synthetic revenue?",
        "answer": "SECRET_GOLD_120",
        "justification": "SECRET_JUSTIFICATION_DO_NOT_LEAK",
        "evidence": [
            {
                "evidence_page_num": 0,
                "evidence_text": "Revenue 120",
                "evidence_text_full_page": (
                    "Metric 2025 2024 Revenue 120 100 Cash flow 20 30 Receivables 25 15 "
                    "Note 1 Values in USD millions. Cash flow fell as customer collection slowed."
                ),
            }
        ],
    }
    document = {
        "doc_name": "SYNTHETIC_2025_10K",
        "doc_type": "10k",
        "doc_period": 2025,
        "doc_link": "https://example.invalid/synthetic.pdf",
        "company": "Synthetic Benchmark Co",
    }
    return question, document


def test_financebench_runtime_environment_withholds_gold_labels(tmp_path: Path) -> None:
    question, document = benchmark_inputs()
    repository = ResearchRepository(tmp_path / "v2")
    environment = build_environment(repository, document=document, pdf_payload=synthetic_pdf())
    runtime_payload = json.dumps(environment, ensure_ascii=False)
    assert question["answer"] not in runtime_payload
    assert question["justification"] not in runtime_payload
    assert question["evidence"][0]["evidence_text_full_page"] not in runtime_payload
    assert environment["benchmark"]["gold_labels_in_runtime"] is False
    assert environment["facts"] == {}


def test_financebench_quality_case_keeps_gold_only_on_evaluation_side(tmp_path: Path) -> None:
    question, document = benchmark_inputs()
    repository = ResearchRepository(tmp_path / "v2")
    environment = build_environment(repository, document=document, pdf_payload=synthetic_pdf())
    case = make_quality_case(
        question=question,
        document=document,
        environment=environment,
        research_time="2026-09-11T00:00:00+00:00",
    )
    assert case.split == "development"
    assert case.required_findings[0].reference_answer == "SECRET_GOLD_120"
    assert case.required_evidence[0].alternatives[0].page_number == 1
    assert case.required_evidence[0].alternatives[0].match_mode == "page"
    assert case.reference_integrity == "provided"
    assert case.reference_reviewed_by is None


def test_financebench_full_page_reference_matches_a_substantial_observed_window(
    tmp_path: Path,
) -> None:
    question, document = benchmark_inputs()
    repository = ResearchRepository(tmp_path / "v2")
    environment = build_environment(repository, document=document, pdf_payload=synthetic_pdf())
    research_time = "2026-09-11T00:00:00+00:00"
    case = make_quality_case(
        question=question, document=document, environment=environment, research_time=research_time
    )
    source = next(iter(environment["documents"].values()))
    observed_text = question["evidence"][0]["evidence_text_full_page"][10:130]
    result = evaluate_quality(
        case,
        run={
            "run_id": "benchmark-run",
            "lifecycle_state": "succeeded",
            "request": {"research_question": case.question, "research_time": research_time},
        },
        environment={
            **environment,
            "company": environment["entity"],
            "corpus_hash": case.corpus_hash,
        },
        observed_evidence=[
            {
                "artifact_id": "view-benchmark",
                "document_hash": source["content_hash"],
                "page_number": 1,
                "text": observed_text,
            }
        ],
        report_hash=None,
    )
    assert result["eligible"] is True
    assert result["metrics"]["required_evidence_observation_recall"]["value"] == 1
    assert result["metrics"]["answer_correctness"]["value"] is None


def test_financebench_parsed_environment_is_cached_by_pdf_hash(tmp_path: Path) -> None:
    _question, document = benchmark_inputs()
    repository = ResearchRepository(tmp_path / "v2")
    payload = synthetic_pdf()
    first = load_or_build_environment(repository, document=document, pdf_payload=payload)
    second = load_or_build_environment(repository, document=document, pdf_payload=payload)
    assert first == second
    assert len(list((repository.root / "benchmark-document-cache").glob("*.json"))) == 1


def test_page_mode_requires_the_reviewed_page_not_merely_similar_text(tmp_path: Path) -> None:
    question, document = benchmark_inputs()
    repository = ResearchRepository(tmp_path / "v2")
    environment = build_environment(repository, document=document, pdf_payload=synthetic_pdf())
    research_time = "2026-09-11T00:00:00+00:00"
    case = make_quality_case(
        question=question, document=document, environment=environment, research_time=research_time
    )
    source = next(iter(environment["documents"].values()))
    result = evaluate_quality(
        case,
        run={
            "run_id": "benchmark-run",
            "lifecycle_state": "succeeded",
            "request": {"research_question": case.question, "research_time": research_time},
        },
        environment={
            **environment,
            "company": environment["entity"],
            "corpus_hash": case.corpus_hash,
        },
        observed_evidence=[
            {
                "artifact_id": "wrong-page",
                "document_hash": source["content_hash"],
                "page_number": 2,
                "text": question["evidence"][0]["evidence_text_full_page"],
            }
        ],
        report_hash=None,
    )
    assert result["metrics"]["required_evidence_observation_recall"]["value"] == 0


def test_known_financebench_label_conflict_is_marked_suspect(tmp_path: Path) -> None:
    question, document = benchmark_inputs()
    question = {**question, "financebench_id": "financebench_id_04672", "answer": "$8.70"}
    repository = ResearchRepository(tmp_path / "v2")
    environment = build_environment(repository, document=document, pdf_payload=synthetic_pdf())
    case = make_quality_case(
        question=question,
        document=document,
        environment=environment,
        research_time="2023-11-20T17:28:02+00:00",
    )
    assert case.reference_integrity == "suspect"
    assert "8,738" in case.reference_integrity_notes[0]
