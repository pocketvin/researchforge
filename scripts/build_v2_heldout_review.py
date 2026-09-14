"""Build a private, offline choice-only HTML review pack from completed held-out Runs."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from researchforge.v2.benchmarks.exposure import DevelopmentExposureSnapshot
from researchforge.v2.benchmarks.heldout import (
    DevelopmentIssuerExclusionManifest,
    HeldOutRuntimeCase,
    HeldOutSuiteSeal,
    assert_private_bundle_not_trackable,
    verify_heldout_bundle,
)
from researchforge.v2.benchmarks.human_review import (
    CandidateResultRef,
    build_review_package,
    render_review_html,
)
from researchforge.v2.benchmarks.suite import BenchmarkSuiteManifest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEVELOPMENT_SUITE = (
    PROJECT_ROOT / "docs/contracts/v2/benchmarks/financebench-public-development-10-v1.json"
)
DEFAULT_DEVELOPMENT_EXCLUSIONS = (
    PROJECT_ROOT / "docs/contracts/v2/benchmarks/development-issuer-exclusions-v1.json"
)


def _jsonl(path: Path, model: type[HeldOutRuntimeCase] | type[CandidateResultRef]):
    return [
        model.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle_root", type=Path)
    parser.add_argument("seal", type=Path)
    parser.add_argument(
        "candidate_results", type=Path, help="Private JSONL CandidateResultRef records"
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reviewer-id", default="owner")
    args = parser.parse_args()

    bundle_root = args.bundle_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    assert_private_bundle_not_trackable(bundle_root, PROJECT_ROOT)
    assert_private_bundle_not_trackable(output_dir, PROJECT_ROOT)
    development = BenchmarkSuiteManifest.model_validate_json(DEFAULT_DEVELOPMENT_SUITE.read_text())
    exclusions = DevelopmentIssuerExclusionManifest.model_validate_json(
        DEFAULT_DEVELOPMENT_EXCLUSIONS.read_text()
    )
    exposure = DevelopmentExposureSnapshot.model_validate_json(
        (bundle_root / "development-exposures.json").read_text(encoding="utf-8")
    )
    if exposure.source_hashes.get("tracked-issuer-exclusions") != exclusions.content_hash():
        raise SystemExit("Frozen development exposure does not match issuer exclusions.")
    if exposure.source_hashes.get("development-suite-1") != development.suite_hash:
        raise SystemExit("Frozen development exposure does not match the development suite.")
    seal = HeldOutSuiteSeal.model_validate_json(args.seal.resolve().read_text())
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
    manifest = json.loads((bundle_root / "bundle-manifest.json").read_text())
    runtime_cases = _jsonl(bundle_root / manifest["runtime_cases_file"], HeldOutRuntimeCase)
    refs = _jsonl(args.candidate_results.resolve(), CandidateResultRef)
    package = build_review_package(
        seal,
        runtime_cases,
        refs,
        reviewer_id=args.reviewer_id,
        generated_at=datetime.now(UTC),
    )
    package_path = output_dir / "review-package.json"
    html_path = output_dir / "review.html"
    package_path.write_text(package.model_dump_json(indent=2) + "\n")
    html_path.write_text(render_review_html(package), encoding="utf-8")
    print(
        json.dumps(
            {
                "review_html": str(html_path),
                "cases": len(package.cases),
                "review_mode": package.review_mode,
                "human_actions_required": len(package.cases),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
