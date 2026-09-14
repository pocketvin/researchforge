"""Formal held-out orchestration is single-pass and produces a choice-only review pack."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from researchforge.adapters.storage import payload_sha256
from researchforge.v2.benchmarks.exposure import build_development_exposure_snapshot
from researchforge.v2.benchmarks.heldout import (
    DevelopmentIssuerExclusionManifest,
    HeldOutAcceptanceAttempt,
    HeldOutBundleManifest,
    HeldOutDocument,
    HeldOutRuntimeCase,
    seal_heldout_bundle,
)
from researchforge.v2.benchmarks.human_review import CandidateResultRef
from researchforge.v2.benchmarks.suite import BenchmarkSuiteManifest
from scripts import run_v2_heldout_acceptance as acceptance_script

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _development_contracts() -> tuple[DevelopmentIssuerExclusionManifest, BenchmarkSuiteManifest]:
    exclusions = DevelopmentIssuerExclusionManifest.model_validate_json(
        (
            PROJECT_ROOT / "docs/contracts/v2/benchmarks/development-issuer-exclusions-v1.json"
        ).read_text(encoding="utf-8")
    )
    suite = BenchmarkSuiteManifest.model_validate_json(
        (
            PROJECT_ROOT / "docs/contracts/v2/benchmarks/financebench-public-development-10-v1.json"
        ).read_text(encoding="utf-8")
    )
    return exclusions, suite


def _private_bundle(tmp_path: Path) -> tuple[Path, Path]:
    bundle = tmp_path / "private"
    source_dir = bundle / "sources"
    source_dir.mkdir(parents=True)
    cases: list[HeldOutRuntimeCase] = []
    strata = [
        "direct_extraction",
        "numerical_analysis",
        "analytical_explanation",
        "evidence_limited",
    ]
    for index in range(8):
        payload = f"%PDF-private-orchestration-{index}".encode()
        digest = hashlib.sha256(payload).hexdigest()
        relative = f"sources/private-{index}.pdf"
        (bundle / relative).write_bytes(payload)
        document = HeldOutDocument(
            document_id=f"doc_private_{index}",
            title=f"Private filing {index}",
            relative_path=relative,
            content_hash=digest,
            source_uri=f"https://example.invalid/private-{index}.pdf",
            published_at="2026-01-01T00:00:00+00:00",
            document_type="annual_report",
            reporting_period={"fiscal_year": 2025, "fiscal_period": "FY"},
        )
        cases.append(
            HeldOutRuntimeCase(
                case_id=f"private_case_{index}",
                stratum=strata[index % len(strata)],
                company_group_key=f"private-issuer-{index % 4}",
                company_query=f"Private Issuer {index % 4}",
                company_id=f"private_issuer_{index % 4}",
                market_hint="US",
                requested_period_label="2025FY",
                research_question=f"Private acceptance question number {index}?",
                research_time="2026-02-01T00:00:00+00:00",
                corpus_hash=payload_sha256([digest]),
                documents=[document],
            )
        )
    manifest = HeldOutBundleManifest(
        suite_id="private-runner-test",
        created_at=datetime(2026, 9, 12, tzinfo=UTC),
        review_mode="meets_standard",
        case_ids=[case.case_id for case in cases],
    )
    (bundle / "bundle-manifest.json").write_text(
        manifest.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    (bundle / "runtime-cases.jsonl").write_text(
        "".join(case.model_dump_json() + "\n" for case in cases), encoding="utf-8"
    )
    exclusions, suite = _development_contracts()
    exposure = build_development_exposure_snapshot(
        PROJECT_ROOT,
        exclusions=exclusions,
        development_suites=[suite],
    )
    (bundle / "development-exposures.json").write_text(
        exposure.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    seal = seal_heldout_bundle(
        bundle,
        development_company_names=set(exposure.company_aliases),
        development_suite_hashes=[suite.suite_hash],
        development_question_hashes=set(exposure.question_hashes),
        development_document_hashes=set(exposure.document_hashes),
        development_exclusion_hashes=[exclusions.content_hash()],
        development_exposure_hashes=[exposure.content_hash()],
    )
    seal_path = tmp_path / "seal.json"
    seal_path.write_text(seal.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return bundle, seal_path


def test_meets_standard_runner_arms_once_and_builds_review_pack(
    tmp_path: Path, monkeypatch
) -> None:
    bundle, seal_path = _private_bundle(tmp_path)
    output = tmp_path / "acceptance"

    def fake_run(
        project_root: Path,
        runtime_root: Path,
        bundle_root: Path,
        case: HeldOutRuntimeCase,
        *,
        candidate_key: str = "v2-current",
    ):
        assert project_root == PROJECT_ROOT
        assert bundle_root == bundle
        result_dir = runtime_root / "heldout-results"
        result_dir.mkdir(parents=True, exist_ok=True)
        run_id = f"run_{case.case_id}"
        result_path = result_dir / f"{case.case_id}.json"
        result_path.write_text(
            json.dumps(
                {
                    "report": {
                        "title": "Private result",
                        "direct_answer": "not_applicable",
                        "executive_summary": f"Answer for {case.case_id}",
                        "findings": [
                            {"title": "Finding", "text": "Supported by the frozen filing."}
                        ],
                        "sections": [],
                        "limitations": ["Filing-only scope."],
                    }
                }
            ),
            encoding="utf-8",
        )
        return {"lifecycle_state": "succeeded"}, CandidateResultRef(
            case_id=case.case_id,
            candidate_key=candidate_key,
            run_id=run_id,
            result_path=str(result_path),
        )

    monkeypatch.setattr(acceptance_script, "run_v2_heldout_case", fake_run)
    monkeypatch.setattr(acceptance_script, "assert_private_bundle_not_trackable", lambda *_: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_v2_heldout_acceptance.py",
            str(bundle),
            str(seal_path),
            "--output-dir",
            str(output),
        ],
    )

    acceptance_script.main()

    attempts = [
        HeldOutAcceptanceAttempt.model_validate_json(line)
        for line in (output / "acceptance-attempts.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(attempts) == 1
    assert attempts[0].state == "running"
    refs = [
        CandidateResultRef.model_validate_json(line)
        for line in (output / "candidate-results.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(refs) == 8
    review = (output / "review" / "review.html").read_text(encoding="utf-8")
    assert "达标" in review and "不达标" in review and "无法判断" in review
    assert "v2-current" not in review


def test_partial_product_results_retire_attempt_instead_of_allowing_retry(
    tmp_path: Path, monkeypatch
) -> None:
    bundle, seal_path = _private_bundle(tmp_path)
    output = tmp_path / "acceptance"
    calls = 0

    def partial_run(
        project_root: Path,
        runtime_root: Path,
        bundle_root: Path,
        case: HeldOutRuntimeCase,
        *,
        candidate_key: str = "v2-current",
    ):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic infrastructure failure after first result")
        result_dir = runtime_root / "heldout-results"
        result_dir.mkdir(parents=True, exist_ok=True)
        result_path = result_dir / "first.json"
        result_path.write_text(
            json.dumps(
                {
                    "report": {
                        "title": "Result",
                        "executive_summary": "First valid result.",
                        "findings": [],
                        "sections": [],
                        "limitations": [],
                    }
                }
            ),
            encoding="utf-8",
        )
        return {"lifecycle_state": "succeeded"}, CandidateResultRef(
            case_id=case.case_id,
            candidate_key=candidate_key,
            run_id="run_first_valid_result",
            result_path=str(result_path),
        )

    monkeypatch.setattr(acceptance_script, "run_v2_heldout_case", partial_run)
    monkeypatch.setattr(acceptance_script, "assert_private_bundle_not_trackable", lambda *_: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_v2_heldout_acceptance.py",
            str(bundle),
            str(seal_path),
            "--output-dir",
            str(output),
        ],
    )

    try:
        acceptance_script.main()
    except RuntimeError as exc:
        assert "synthetic infrastructure failure" in str(exc)
    else:
        raise AssertionError("runner should surface the synthetic failure")

    attempt = HeldOutAcceptanceAttempt.model_validate_json(
        (output / "acceptance-attempts.jsonl").read_text(encoding="utf-8").strip()
    )
    assert attempt.state == "retired"
    failure = json.loads((output / "acceptance-failure.json").read_text(encoding="utf-8"))
    assert failure["completed_product_results"] == 1


def test_zero_result_product_failure_retires_seal(tmp_path: Path, monkeypatch) -> None:
    bundle, seal_path = _private_bundle(tmp_path)
    output = tmp_path / "acceptance-product-failure"

    def product_failure(*_args, **_kwargs):
        raise acceptance_script.HeldOutCaseFailure(
            "failed",
            "SAFE_REPORT_SEMANTIC_REJECTED",
            "研究未完成 (RunInterrupted)。",
        )

    monkeypatch.setattr(acceptance_script, "run_v2_heldout_case", product_failure)
    monkeypatch.setattr(acceptance_script, "assert_private_bundle_not_trackable", lambda *_: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_v2_heldout_acceptance.py",
            str(bundle),
            str(seal_path),
            "--output-dir",
            str(output),
        ],
    )

    try:
        acceptance_script.main()
    except acceptance_script.HeldOutCaseFailure:
        pass
    else:
        raise AssertionError("runner should surface the product failure")

    attempt = HeldOutAcceptanceAttempt.model_validate_json(
        (output / "acceptance-attempts.jsonl").read_text(encoding="utf-8").strip()
    )
    assert attempt.state == "retired"
    failure = json.loads((output / "acceptance-failure.json").read_text(encoding="utf-8"))
    assert failure["retry_eligible"] is False
    assert failure["product_failure_code"] == "SAFE_REPORT_SEMANTIC_REJECTED"


def test_zero_result_provider_transport_failure_is_retry_eligible(
    tmp_path: Path, monkeypatch
) -> None:
    bundle, seal_path = _private_bundle(tmp_path)
    output = tmp_path / "acceptance-provider-failure"

    def provider_failure(*_args, **_kwargs):
        raise acceptance_script.HeldOutCaseFailure(
            "failed",
            "V2_EXECUTION_FAILED",
            "研究未完成 (BadRequestError)。",
        )

    monkeypatch.setattr(acceptance_script, "run_v2_heldout_case", provider_failure)
    monkeypatch.setattr(acceptance_script, "assert_private_bundle_not_trackable", lambda *_: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_v2_heldout_acceptance.py",
            str(bundle),
            str(seal_path),
            "--output-dir",
            str(output),
        ],
    )

    try:
        acceptance_script.main()
    except acceptance_script.HeldOutCaseFailure:
        pass
    else:
        raise AssertionError("runner should surface the provider failure")

    attempt = HeldOutAcceptanceAttempt.model_validate_json(
        (output / "acceptance-attempts.jsonl").read_text(encoding="utf-8").strip()
    )
    assert attempt.state == "technical_failure"
    failure = json.loads((output / "acceptance-failure.json").read_text(encoding="utf-8"))
    assert failure["retry_eligible"] is True
    assert failure["product_failure_code"] == "V2_EXECUTION_FAILED"
