"""Run one sealed meets-standard held-out acceptance pass on frozen source bytes only.

This is deliberately fail-closed for pairwise review. A V1/V2 comparison is only valid after both
implementations can consume the same frozen corpus. Until that common-corpus baseline exists, the
formal current-runtime acceptance mode is the single-candidate meets-standard workflow.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from researchforge.v2.benchmarks.exposure import DevelopmentExposureSnapshot
from researchforge.v2.benchmarks.heldout import (
    DevelopmentIssuerExclusionManifest,
    HeldOutAcceptanceAttempt,
    HeldOutBundleManifest,
    HeldOutRuntimeCase,
    HeldOutSuiteSeal,
    arm_heldout_acceptance,
    assert_private_bundle_not_trackable,
    verify_heldout_bundle,
)
from researchforge.v2.benchmarks.heldout_runner import HeldOutCaseFailure, run_v2_heldout_case
from researchforge.v2.benchmarks.human_review import (
    CandidateResultRef,
    build_review_package,
    render_review_html,
)
from researchforge.v2.benchmarks.suite import BenchmarkSuiteManifest, implementation_fingerprint
from researchforge.v2.storage import atomic_bytes

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEVELOPMENT_SUITE = (
    PROJECT_ROOT / "docs/contracts/v2/benchmarks/financebench-public-development-10-v1.json"
)
DEFAULT_DEVELOPMENT_EXCLUSIONS = (
    PROJECT_ROOT / "docs/contracts/v2/benchmarks/development-issuer-exclusions-v1.json"
)


def _read_jsonl(
    path: Path, model: type[HeldOutAcceptanceAttempt] | type[HeldOutRuntimeCase]
) -> list[HeldOutAcceptanceAttempt | HeldOutRuntimeCase]:
    if not path.is_file():
        return []
    return [
        model.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_attempts(path: Path, attempts: list[HeldOutAcceptanceAttempt]) -> None:
    payload = "".join(item.model_dump_json() + "\n" for item in attempts)
    atomic_bytes(path, payload.encode("utf-8"))


def _replace_attempt(
    attempts: list[HeldOutAcceptanceAttempt], updated: HeldOutAcceptanceAttempt
) -> list[HeldOutAcceptanceAttempt]:
    return [updated if item.attempt_id == updated.attempt_id else item for item in attempts]


def _git_state() -> tuple[str | None, bool]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return head or None, dirty


def _verify_private_bundle(bundle_root: Path, seal: HeldOutSuiteSeal) -> None:
    development = BenchmarkSuiteManifest.model_validate_json(
        DEFAULT_DEVELOPMENT_SUITE.read_text(encoding="utf-8")
    )
    exclusions = DevelopmentIssuerExclusionManifest.model_validate_json(
        DEFAULT_DEVELOPMENT_EXCLUSIONS.read_text(encoding="utf-8")
    )
    exposure = DevelopmentExposureSnapshot.model_validate_json(
        (bundle_root / "development-exposures.json").read_text(encoding="utf-8")
    )
    if exposure.source_hashes.get("tracked-issuer-exclusions") != exclusions.content_hash():
        raise RuntimeError("frozen development exposure no longer matches issuer exclusions")
    if exposure.source_hashes.get("development-suite-1") != development.suite_hash:
        raise RuntimeError("frozen development exposure no longer matches the development suite")
    verify_heldout_bundle(
        bundle_root,
        seal,
        development_company_names=set(exposure.company_aliases),
        development_suite_hashes=[development.suite_hash],
        development_question_hashes=set(exposure.question_hashes),
        development_document_hashes=set(exposure.document_hashes),
        development_exclusion_hashes=[exclusions.content_hash()],
        development_exposure_hashes=[exposure.content_hash()],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle_root", type=Path)
    parser.add_argument("seal", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reviewer-id", default="owner")
    parser.add_argument("--retry-reason")
    args = parser.parse_args()

    bundle_root = args.bundle_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    assert_private_bundle_not_trackable(bundle_root, PROJECT_ROOT)
    assert_private_bundle_not_trackable(output_dir, PROJECT_ROOT)
    seal = HeldOutSuiteSeal.model_validate_json(args.seal.resolve().read_text(encoding="utf-8"))
    if seal.review_mode != "meets_standard":
        raise SystemExit(
            "Formal automatic acceptance currently requires review_mode=meets_standard. "
            "Pairwise execution remains locked until a same-frozen-corpus baseline adapter exists."
        )
    _verify_private_bundle(bundle_root, seal)

    implementation_hash = implementation_fingerprint(PROJECT_ROOT)
    git_head, git_dirty = _git_state()
    attempts_path = output_dir / "acceptance-attempts.jsonl"
    attempts = [
        item
        for item in _read_jsonl(attempts_path, HeldOutAcceptanceAttempt)
        if isinstance(item, HeldOutAcceptanceAttempt)
    ]
    attempt = arm_heldout_acceptance(
        seal,
        attempts,
        implementation_hash=implementation_hash,
        git_head=git_head,
        git_dirty=git_dirty,
        started_at=datetime.now(UTC),
        retry_reason=args.retry_reason,
    )
    attempts.append(attempt)
    attempt = attempt.model_copy(update={"state": "running"})
    attempts = _replace_attempt(attempts, attempt)
    _write_attempts(attempts_path, attempts)

    manifest = HeldOutBundleManifest.model_validate_json(
        (bundle_root / "bundle-manifest.json").read_text(encoding="utf-8")
    )
    runtime_cases = [
        item
        for item in _read_jsonl(bundle_root / manifest.runtime_cases_file, HeldOutRuntimeCase)
        if isinstance(item, HeldOutRuntimeCase)
    ]
    by_id = {case.case_id: case for case in runtime_cases}
    ordered_cases = [by_id[case_id] for case_id in manifest.case_ids]
    refs: list[CandidateResultRef] = []
    runtime_root = output_dir / "runtime"
    try:
        for case in ordered_cases:
            _final, ref = run_v2_heldout_case(
                PROJECT_ROOT,
                runtime_root,
                bundle_root,
                case,
                candidate_key="v2-current",
            )
            refs.append(ref)
    except Exception as exc:
        retry_eligible = bool(
            not refs and isinstance(exc, HeldOutCaseFailure) and exc.retry_eligible
        )
        attempt = attempt.model_copy(
            update={"state": "technical_failure" if retry_eligible else "retired"}
        )
        attempts = _replace_attempt(attempts, attempt)
        _write_attempts(attempts_path, attempts)
        failure = {
            "attempt_id": attempt.attempt_id,
            "state": attempt.state,
            "completed_product_results": len(refs),
            "error_type": type(exc).__name__,
            "message": str(exc),
            "retry_eligible": retry_eligible,
        }
        if isinstance(exc, HeldOutCaseFailure):
            failure["product_failure_code"] = exc.failure_code
        atomic_bytes(
            output_dir / "acceptance-failure.json",
            (json.dumps(failure, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
        raise

    refs_path = output_dir / "candidate-results.jsonl"
    atomic_bytes(
        refs_path,
        "".join(ref.model_dump_json() + "\n" for ref in refs).encode("utf-8"),
    )
    package = build_review_package(
        seal,
        ordered_cases,
        refs,
        reviewer_id=args.reviewer_id,
        generated_at=datetime.now(UTC),
    )
    review_dir = output_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    atomic_bytes(
        review_dir / "review-package.json",
        (package.model_dump_json(indent=2) + "\n").encode("utf-8"),
    )
    atomic_bytes(review_dir / "review.html", render_review_html(package).encode("utf-8"))
    print(
        json.dumps(
            {
                "attempt_id": attempt.attempt_id,
                "state": attempt.state,
                "cases_completed": len(refs),
                "review_mode": seal.review_mode,
                "review_html": str(review_dir / "review.html"),
                "candidate_results": str(refs_path),
                "human_actions_required": len(refs),
                "live_discovery_used": False,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
