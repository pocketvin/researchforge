"""Choice-only held-out review UI stays blind and requires no authored human rubric."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from researchforge.adapters.storage import payload_sha256
from researchforge.v2.benchmarks.heldout import (
    HeldOutAcceptanceAttempt,
    HeldOutDocument,
    HeldOutHumanJudgment,
    HeldOutRuntimeCase,
    HeldOutSuiteSeal,
)
from researchforge.v2.benchmarks.human_review import (
    CandidateResultRef,
    HumanJudgmentFile,
    build_review_package,
    render_review_html,
    summarize_human_acceptance,
)
from scripts.summarize_v2_heldout_review import _complete_attempt


def _opaque(value: str) -> str:
    return hashlib.sha256(("researchforge-heldout-v2:" + value).encode()).hexdigest()


def _seal(case_id: str, review_mode: str) -> HeldOutSuiteSeal:
    return HeldOutSuiteSeal(
        suite_id="private-choice-only-v2",
        frozen_at=datetime(2026, 9, 12, tzinfo=UTC),
        review_mode=review_mode,
        bundle_hash="a" * 64,
        runtime_manifest_hash="b" * 64,
        source_manifest_hash="c" * 64,
        case_count=1,
        company_count=1,
        stratum_counts={"direct_extraction": 1},
        opaque_case_hashes=[_opaque(case_id)],
        opaque_company_hashes=[_opaque("new-issuer")],
        development_suite_hashes=["d" * 64],
        development_exclusion_hashes=["e" * 64],
        development_exposure_hashes=["f" * 64],
    )


def _runtime(case_id: str) -> HeldOutRuntimeCase:
    document_hash = "f" * 64
    return HeldOutRuntimeCase(
        case_id=case_id,
        stratum="direct_extraction",
        company_group_key="new-issuer",
        company_query="New Issuer",
        company_id="new-issuer-id",
        market_hint="US",
        requested_period_label="2025FY",
        research_question="What was FY2025 revenue?",
        research_time="2026-02-01T00:00:00+00:00",
        corpus_hash=payload_sha256([document_hash]),
        documents=[
            HeldOutDocument(
                document_id="doc_1",
                title="Frozen filing",
                relative_path="sources/source.pdf",
                content_hash=document_hash,
                source_uri="https://example.invalid/source.pdf",
                published_at="2026-01-15T00:00:00+00:00",
                document_type="annual_report",
                reporting_period={"fiscal_year": 2025, "fiscal_period": "FY"},
            )
        ],
    )


def _write_results(tmp_path: Path, case_id: str) -> list[CandidateResultRef]:
    v1_path = tmp_path / "baseline.json"
    v2_path = tmp_path / "candidate.json"
    v1_path.write_text(
        json.dumps(
            {
                "executive_summary": "Revenue was 100 million.",
                "claims": [{"text": "Reported revenue was 100 million."}],
                "analysis_sections": [{"title": "Revenue", "text": "The filing reports 100."}],
                "limitations": ["No external sources."],
                "overall_judgment": {"label": "Supported"},
            }
        )
    )
    v2_path.write_text(
        json.dumps(
            {
                "report": {
                    "title": "Revenue research",
                    "direct_answer": "not_applicable",
                    "executive_summary": "FY2025 revenue was 100 million.",
                    "findings": [{"title": "Revenue", "text": "Reported revenue was 100 million."}],
                    "sections": [{"title": "Source", "text": "Annual filing reports the value."}],
                    "limitations": ["Filing-only scope."],
                }
            }
        )
    )
    return [
        CandidateResultRef(
            case_id=case_id,
            candidate_key="baseline",
            run_id="run_baseline",
            result_path=str(v1_path),
        ),
        CandidateResultRef(
            case_id=case_id,
            candidate_key="candidate",
            run_id="run_candidate",
            result_path=str(v2_path),
        ),
    ]


def test_pairwise_review_pack_is_blind_stable_and_downloads_one_choice(tmp_path: Path) -> None:
    case_id = "case_private_1"
    seal = _seal(case_id, "pairwise_preference")
    runtime = _runtime(case_id)
    refs = _write_results(tmp_path, case_id)
    generated = datetime(2026, 9, 12, 2, 0, tzinfo=UTC)
    first = build_review_package(seal, [runtime], refs, generated_at=generated)
    second = build_review_package(seal, [runtime], list(reversed(refs)), generated_at=generated)
    assert first == second
    card = first.cases[0]
    assert card.candidate_a is not None and card.candidate_b is not None
    assert {card.candidate_a.run_id, card.candidate_b.run_id} == {"run_baseline", "run_candidate"}
    payload = first.model_dump_json()
    assert "candidate_key" not in payload
    assert '"baseline"' not in payload and '"candidate"' not in payload

    page = render_review_html(first)
    assert "A 更好" in page and "B 更好" in page and "差不多" in page and "都不行" in page
    assert "自动下载判断文件" in page
    assert "candidate_key" not in page
    assert "provider" not in page.casefold()


def test_pairwise_summary_restores_candidate_identity_after_blind_choice(tmp_path: Path) -> None:
    case_id = "case_private_1"
    seal = _seal(case_id, "pairwise_preference")
    runtime = _runtime(case_id)
    refs = _write_results(tmp_path, case_id)
    package = build_review_package(
        seal,
        [runtime],
        refs,
        generated_at=datetime(2026, 9, 12, 2, 0, tzinfo=UTC),
    )
    card = package.cases[0]
    assert card.candidate_a is not None and card.candidate_b is not None
    # Select whichever blind side actually contains the candidate implementation.
    candidate_is_a = card.candidate_a.run_id == "run_candidate"
    judgment = HeldOutHumanJudgment(
        case_id=case_id,
        review_mode="pairwise_preference",
        reviewer_id="owner",
        reviewed_at=datetime(2026, 9, 12, 2, 5, tzinfo=UTC),
        candidate_a_run_id=card.candidate_a.run_id,
        candidate_b_run_id=card.candidate_b.run_id,
        pairwise_verdict="a_better" if candidate_is_a else "b_better",
    )
    summary = summarize_human_acceptance(
        seal,
        HumanJudgmentFile(
            suite_id=seal.suite_id,
            bundle_hash=seal.bundle_hash,
            review_mode=seal.review_mode,
            judgments=[judgment],
        ),
        refs,
    )
    assert summary.candidate_preference_counts == {"candidate": 1}
    assert summary.decisive_pairwise_cases == 1


def test_meets_standard_review_pack_and_summary_need_only_one_click(tmp_path: Path) -> None:
    case_id = "case_private_1"
    seal = _seal(case_id, "meets_standard")
    runtime = _runtime(case_id)
    refs = [_write_results(tmp_path, case_id)[1]]
    package = build_review_package(
        seal,
        [runtime],
        refs,
        generated_at=datetime(2026, 9, 12, 2, 0, tzinfo=UTC),
    )
    card = package.cases[0]
    assert card.evaluated_candidate is not None
    page = render_review_html(package)
    assert "达标" in page and "不达标" in page and "无法判断" in page
    judgment = HeldOutHumanJudgment(
        case_id=case_id,
        review_mode="meets_standard",
        reviewer_id="owner",
        reviewed_at=datetime(2026, 9, 12, 2, 5, tzinfo=UTC),
        evaluated_run_id=card.evaluated_candidate.run_id,
        threshold_verdict="meets_standard",
    )
    summary = summarize_human_acceptance(
        seal,
        HumanJudgmentFile(
            suite_id=seal.suite_id,
            bundle_hash=seal.bundle_hash,
            review_mode=seal.review_mode,
            judgments=[judgment],
        ),
        refs,
    )
    assert summary.meets_standard_cases == 1
    assert summary.verdict_counts == {"meets_standard": 1}


def test_choice_summary_completes_the_armed_acceptance_attempt(tmp_path: Path) -> None:
    case_id = "case_private_1"
    seal = _seal(case_id, "meets_standard")
    attempt = HeldOutAcceptanceAttempt(
        attempt_id="private-choice-only-v2-acceptance-1-abc123",
        suite_id=seal.suite_id,
        bundle_hash=seal.bundle_hash,
        implementation_hash="1" * 64,
        git_head="2" * 40,
        git_dirty=True,
        started_at=datetime(2026, 9, 12, 2, 0, tzinfo=UTC),
        state="running",
    )
    ledger = tmp_path / "attempts.jsonl"
    ledger.write_text(attempt.model_dump_json() + "\n", encoding="utf-8")
    reviewed_at = datetime(2026, 9, 12, 2, 5, tzinfo=UTC)
    judgments = HumanJudgmentFile(
        suite_id=seal.suite_id,
        bundle_hash=seal.bundle_hash,
        review_mode=seal.review_mode,
        judgments=[
            HeldOutHumanJudgment(
                case_id=case_id,
                review_mode="meets_standard",
                reviewer_id="owner",
                reviewed_at=reviewed_at,
                evaluated_run_id="run_candidate",
                threshold_verdict="meets_standard",
            )
        ],
    )

    completed_id = _complete_attempt(ledger, seal, judgments)

    updated = HeldOutAcceptanceAttempt.model_validate_json(ledger.read_text(encoding="utf-8"))
    assert completed_id == attempt.attempt_id
    assert updated.state == "completed"
    assert updated.results_opened_at == reviewed_at
    assert updated.human_review_completed_at == reviewed_at
