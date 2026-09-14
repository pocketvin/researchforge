"""Held-out quality acceptance freezes unseen inputs and keeps human review choice-only."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from researchforge.adapters.storage import payload_sha256
from researchforge.v2.benchmarks.exposure import normalized_question_hash
from researchforge.v2.benchmarks.heldout import (
    DevelopmentIssuerExclusionManifest,
    HeldOutAcceptanceAttempt,
    HeldOutBundleManifest,
    HeldOutDocument,
    HeldOutHumanJudgment,
    HeldOutRuntimeCase,
    arm_heldout_acceptance,
    assert_private_bundle_not_trackable,
    seal_heldout_bundle,
    validate_human_judgments,
    verify_heldout_bundle,
)


def json_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(json_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(json_keys(child) for child in value))
    return set()


def _bundle(
    root: Path,
    *,
    company: str = "Heldout Example Co",
    question: str = "What was the reported revenue in FY2025?",
    review_mode: str = "pairwise_preference",
    source_payload: bytes = b"%PDF-heldout-private-source",
) -> Path:
    source_path = root / "sources" / "source.pdf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(source_payload)
    source_hash = hashlib.sha256(source_payload).hexdigest()
    corpus_hash = payload_sha256([source_hash])
    case_id = "heldout_case_opaque_001"
    document = HeldOutDocument(
        document_id="doc_private_001",
        title="Private frozen filing",
        relative_path="sources/source.pdf",
        content_hash=source_hash,
        source_uri="https://example.invalid/private-frozen-filing.pdf",
        published_at="2025-12-31T00:00:00+00:00",
        document_type="annual_report",
        reporting_period={"fiscal_year": 2025, "fiscal_period": "FY"},
    )
    runtime = HeldOutRuntimeCase(
        case_id=case_id,
        stratum="direct_extraction",
        company_group_key="heldout-example-co",
        company_query=company,
        company_id="heldout-company-001",
        market_hint="US",
        requested_period_label="2025FY",
        research_question=question,
        research_time="2026-01-15T00:00:00+00:00",
        corpus_hash=corpus_hash,
        documents=[document],
    )
    manifest = HeldOutBundleManifest(
        suite_id="private-heldout-v2",
        protocol_version="acceptance-v2",
        created_at=datetime(2026, 1, 16, tzinfo=UTC),
        review_mode=review_mode,
        case_ids=[case_id],
    )
    (root / "bundle-manifest.json").write_text(manifest.model_dump_json(indent=2) + "\n")
    (root / "runtime-cases.jsonl").write_text(runtime.model_dump_json() + "\n")
    return root


def _seal(
    root: Path,
    *,
    development: set[str] | None = None,
    development_questions: set[str] | None = None,
    development_documents: set[str] | None = None,
):
    return seal_heldout_bundle(
        root,
        development_company_names=development or {"3M", "Activision Blizzard"},
        development_suite_hashes=["d" * 64],
        development_question_hashes=development_questions,
        development_document_hashes=development_documents,
        minimum_cases=1,
        minimum_companies=1,
        minimum_strata=1,
    )


def test_valid_private_bundle_seals_without_reference_labels_or_company_leak(
    tmp_path: Path,
) -> None:
    root = _bundle(tmp_path / "private")
    seal = _seal(root)
    assert seal.split == "held_out"
    assert seal.protocol_version == "acceptance-v2"
    assert seal.review_mode == "pairwise_preference"
    assert seal.case_count == 1
    assert seal.company_count == 1
    assert seal.stratum_counts == {"direct_extraction": 1}
    assert seal.reference_labels_required is False
    assert seal.human_input_contract == "choice_only"
    assert seal.first_result_policy == "single_acceptance_pass"
    assert seal.development_exposure_hashes == []
    payload = seal.model_dump_json().casefold()
    assert "what was the reported revenue" not in payload
    assert "heldout example co" not in payload
    assert "reviewer" not in payload


def test_no_reference_or_attestation_file_is_required_before_sealing(tmp_path: Path) -> None:
    root = _bundle(tmp_path / "private")
    assert not (root / "reference-cases.jsonl").exists()
    assert not (root / "review-attestations.jsonl").exists()
    seal = _seal(root)
    assert seal.runtime_inputs_frozen is True


def test_development_issuer_overlap_is_rejected(tmp_path: Path) -> None:
    root = _bundle(tmp_path / "private", company="3M")
    with pytest.raises(ValueError, match="overlaps the development exclusion set"):
        _seal(root, development={"3M"})


def test_development_question_overlap_is_rejected(tmp_path: Path) -> None:
    question = "What was the reported revenue in FY2025?"
    root = _bundle(tmp_path / "private", question=question)
    with pytest.raises(ValueError, match="question overlaps the development exposure set"):
        _seal(root, development_questions={normalized_question_hash(question)})


def test_development_document_overlap_is_rejected_even_if_question_and_issuer_differ(
    tmp_path: Path,
) -> None:
    payload = b"%PDF-development-exposed-source"
    digest = hashlib.sha256(payload).hexdigest()
    root = _bundle(
        tmp_path / "private",
        company="Entirely New Alias Co",
        question="A completely different held-out question?",
        source_payload=payload,
    )
    with pytest.raises(ValueError, match="source document overlaps"):
        _seal(root, development_documents={digest})


def test_private_source_tamper_breaks_seal(tmp_path: Path) -> None:
    root = _bundle(tmp_path / "private")
    (root / "sources" / "source.pdf").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="source hash mismatch"):
        _seal(root)


def test_heldout_document_cannot_escape_private_sources() -> None:
    with pytest.raises(ValueError, match="private sources directory"):
        HeldOutDocument(
            document_id="doc_bad",
            title="Bad",
            relative_path="elsewhere/source.pdf",
            content_hash="a" * 64,
            source_uri="https://example.invalid/bad.pdf",
            published_at="2025-01-01T00:00:00+00:00",
            document_type="annual_report",
            reporting_period={"fiscal_year": 2025},
        )


def test_tracked_development_exclusion_manifest_is_valid() -> None:
    project_root = Path(__file__).resolve().parents[2]
    path = project_root / "docs/contracts/v2/benchmarks/development-issuer-exclusions-v1.json"
    manifest = DevelopmentIssuerExclusionManifest.model_validate_json(path.read_text())
    aliases = manifest.all_aliases()
    assert {"CATL", "宁德时代", "3M", "Activision Blizzard", "贵州茅台"} <= aliases
    assert len(manifest.content_hash()) == 64


def test_private_bundle_inside_repo_must_be_ignored_and_untracked(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / ".gitignore").write_text("artifacts/\n")
    ignored = repo / "artifacts" / "private-heldout"
    ignored.mkdir(parents=True)
    assert_private_bundle_not_trackable(ignored, repo)

    visible = repo / "private-heldout"
    visible.mkdir()
    with pytest.raises(RuntimeError, match=r"not covered by \.gitignore"):
        assert_private_bundle_not_trackable(visible, repo)

    secret = ignored / "runtime-cases.jsonl"
    secret.write_text("private")
    subprocess.run(["git", "add", "-f", str(secret.relative_to(repo))], cwd=repo, check=True)
    with pytest.raises(RuntimeError, match="Git-tracked"):
        assert_private_bundle_not_trackable(ignored, repo)


def test_committed_heldout_acceptance_seals_remain_opaque() -> None:
    project_root = Path(__file__).resolve().parents[2]
    benchmark_dir = project_root / "docs/contracts/v2/benchmarks"
    seals = [path for path in benchmark_dir.glob("*heldout*seal*.json") if path.is_file()]
    assert seals
    forbidden_keys = {
        "case_id",
        "company_query",
        "company_name",
        "document_id",
        "legal_name",
        "reference_answer",
        "research_question",
        "source_uri",
        "ticker",
    }
    for path in seals:
        payload = json.loads(path.read_text())
        assert payload["split"] == "held_out"
        assert payload["questions_tracked_in_git"] is False
        assert payload["labels_tracked_in_git"] is False
        assert len(payload["opaque_case_hashes"]) == payload["case_count"]
        assert len(payload["opaque_company_hashes"]) == payload["company_count"]
        assert not forbidden_keys & set(json_keys(payload))


def test_frozen_seal_reverifies_same_private_bundle(tmp_path: Path) -> None:
    root = _bundle(tmp_path / "private")
    seal = _seal(root)
    verify_heldout_bundle(
        root,
        seal,
        development_company_names={"3M", "Activision Blizzard"},
        development_suite_hashes=["d" * 64],
        minimum_cases=1,
        minimum_companies=1,
        minimum_strata=1,
    )


def test_frozen_seal_detects_question_change(tmp_path: Path) -> None:
    root = _bundle(tmp_path / "private")
    seal = _seal(root)
    runtime_path = root / "runtime-cases.jsonl"
    runtime = HeldOutRuntimeCase.model_validate_json(runtime_path.read_text())
    changed = runtime.model_copy(update={"research_question": "What was FY2025 net income?"})
    runtime_path.write_text(changed.model_dump_json() + "\n")
    with pytest.raises(ValueError, match="no longer matches frozen seal"):
        verify_heldout_bundle(
            root,
            seal,
            development_company_names={"3M", "Activision Blizzard"},
            development_suite_hashes=["d" * 64],
            minimum_cases=1,
            minimum_companies=1,
            minimum_strata=1,
        )


def test_pairwise_human_review_is_one_choice_only() -> None:
    judgment = HeldOutHumanJudgment(
        case_id="heldout_case_opaque_001",
        review_mode="pairwise_preference",
        reviewer_id="owner",
        reviewed_at=datetime(2026, 1, 20, tzinfo=UTC),
        candidate_a_run_id="run_a",
        candidate_b_run_id="run_b",
        pairwise_verdict="a_better",
    )
    assert judgment.pairwise_verdict == "a_better"
    assert "comment" not in HeldOutHumanJudgment.model_fields
    assert "rationale" not in HeldOutHumanJudgment.model_fields


def test_meets_standard_human_review_is_one_choice_only() -> None:
    judgment = HeldOutHumanJudgment(
        case_id="heldout_case_opaque_001",
        review_mode="meets_standard",
        reviewer_id="owner",
        reviewed_at=datetime(2026, 1, 20, tzinfo=UTC),
        evaluated_run_id="run_v2",
        threshold_verdict="meets_standard",
    )
    assert judgment.threshold_verdict == "meets_standard"
    with pytest.raises(ValueError, match="cannot set pairwise run IDs"):
        HeldOutHumanJudgment(
            case_id="heldout_case_opaque_001",
            review_mode="meets_standard",
            reviewer_id="owner",
            reviewed_at=datetime(2026, 1, 20, tzinfo=UTC),
            candidate_a_run_id="run_a",
            candidate_b_run_id="run_b",
            evaluated_run_id="run_v2",
            threshold_verdict="meets_standard",
        )


def test_human_judgments_must_match_every_frozen_case_once(tmp_path: Path) -> None:
    seal = _seal(_bundle(tmp_path / "private"))
    judgment = HeldOutHumanJudgment(
        case_id="heldout_case_opaque_001",
        review_mode="pairwise_preference",
        reviewer_id="owner",
        reviewed_at=datetime(2026, 1, 20, tzinfo=UTC),
        candidate_a_run_id="run_a",
        candidate_b_run_id="run_b",
        pairwise_verdict="tie",
    )
    validate_human_judgments(seal, [judgment])
    with pytest.raises(ValueError, match="count"):
        validate_human_judgments(seal, [])


def test_heldout_acceptance_attempt_is_single_use_except_same_build_infra_retry(
    tmp_path: Path,
) -> None:
    seal = _seal(_bundle(tmp_path / "private"))
    implementation = "a" * 64
    first = arm_heldout_acceptance(
        seal,
        [],
        implementation_hash=implementation,
        git_head="b" * 40,
        git_dirty=True,
        started_at=datetime(2026, 1, 18, tzinfo=UTC),
    )
    assert first.state == "armed"
    completed = first.model_copy(update={"state": "completed"})
    with pytest.raises(ValueError, match="reuse is forbidden"):
        arm_heldout_acceptance(
            seal,
            [completed],
            implementation_hash=implementation,
            git_head="b" * 40,
            git_dirty=True,
            started_at=datetime(2026, 1, 19, tzinfo=UTC),
        )

    technical = HeldOutAcceptanceAttempt.model_validate(
        first.model_copy(update={"state": "technical_failure"}).model_dump()
    )
    retry = arm_heldout_acceptance(
        seal,
        [technical],
        implementation_hash=implementation,
        git_head="b" * 40,
        git_dirty=True,
        started_at=datetime(2026, 1, 19, tzinfo=UTC),
        retry_reason="provider transport failed before a valid product result was produced",
    )
    assert retry.retry_of == first.attempt_id
    with pytest.raises(ValueError, match="identical implementation"):
        arm_heldout_acceptance(
            seal,
            [technical],
            implementation_hash="c" * 64,
            git_head="c" * 40,
            git_dirty=True,
            started_at=datetime(2026, 1, 19, tzinfo=UTC),
            retry_reason="not a valid retry after changing code",
        )
