"""Validate a private held-out bundle and write only its non-revealing tracked seal."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from researchforge.v2.benchmarks.exposure import (
    build_development_exposure_snapshot,
)
from researchforge.v2.benchmarks.heldout import (
    DevelopmentIssuerExclusionManifest,
    assert_private_bundle_not_trackable,
    seal_heldout_bundle,
)
from researchforge.v2.benchmarks.suite import BenchmarkSuiteManifest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEVELOPMENT_SUITE = (
    PROJECT_ROOT / "docs/contracts/v2/benchmarks/financebench-public-development-10-v1.json"
)

DEFAULT_DEVELOPMENT_EXCLUSIONS = (
    PROJECT_ROOT / "docs/contracts/v2/benchmarks/development-issuer-exclusions-v1.json"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle_root", type=Path)
    parser.add_argument("--development-suite", type=Path, default=DEFAULT_DEVELOPMENT_SUITE)
    parser.add_argument(
        "--development-exclusions", type=Path, default=DEFAULT_DEVELOPMENT_EXCLUSIONS
    )
    parser.add_argument(
        "--exclude-bundle",
        type=Path,
        action="append",
        default=[],
        help="Previously result-exposed held-out bundle to promote into development exposure.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bundle_root = args.bundle_root.resolve()
    assert_private_bundle_not_trackable(bundle_root, PROJECT_ROOT)
    development = BenchmarkSuiteManifest.model_validate_json(
        args.development_suite.resolve().read_text(encoding="utf-8")
    )
    exclusions = DevelopmentIssuerExclusionManifest.model_validate_json(
        args.development_exclusions.resolve().read_text(encoding="utf-8")
    )
    retired_bundles = [path.resolve() for path in args.exclude_bundle]
    for retired_bundle in retired_bundles:
        assert_private_bundle_not_trackable(retired_bundle, PROJECT_ROOT)
    exposure = build_development_exposure_snapshot(
        PROJECT_ROOT,
        exclusions=exclusions,
        development_suites=[development],
        retired_heldout_bundles=retired_bundles,
    )
    exposure_path = bundle_root / "development-exposures.json"
    exposure_path.write_text(exposure.model_dump_json(indent=2) + "\n", encoding="utf-8")
    seal = seal_heldout_bundle(
        bundle_root,
        development_company_names=set(exposure.company_aliases),
        development_suite_hashes=[development.suite_hash],
        development_question_hashes=set(exposure.question_hashes),
        development_document_hashes=set(exposure.document_hashes),
        development_exclusion_hashes=[exclusions.content_hash()],
        development_exposure_hashes=[exposure.content_hash()],
    )
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(seal.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output),
                "suite_id": seal.suite_id,
                "bundle_hash": seal.bundle_hash,
                "case_count": seal.case_count,
                "company_count": seal.company_count,
                "stratum_counts": seal.stratum_counts,
                "review_mode": seal.review_mode,
                "reference_labels_required": seal.reference_labels_required,
                "development_exposure_hash": exposure.content_hash(),
                "development_exposed_issuers": len(exposure.company_aliases),
                "development_exposed_questions": len(exposure.question_hashes),
                "retired_bundles_excluded": len(retired_bundles),
                "questions_written": False,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
