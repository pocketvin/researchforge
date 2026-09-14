"""Verify a private V2 held-out bundle against its non-revealing frozen seal."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from researchforge.v2.benchmarks.exposure import DevelopmentExposureSnapshot
from researchforge.v2.benchmarks.heldout import (
    DevelopmentIssuerExclusionManifest,
    HeldOutSuiteSeal,
    assert_private_bundle_not_trackable,
    verify_heldout_bundle,
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
    parser.add_argument("seal", type=Path)
    parser.add_argument("--development-suite", type=Path, default=DEFAULT_DEVELOPMENT_SUITE)
    parser.add_argument(
        "--development-exclusions", type=Path, default=DEFAULT_DEVELOPMENT_EXCLUSIONS
    )
    args = parser.parse_args()
    assert_private_bundle_not_trackable(args.bundle_root, PROJECT_ROOT)
    development = BenchmarkSuiteManifest.model_validate_json(
        args.development_suite.resolve().read_text(encoding="utf-8")
    )
    exclusions = DevelopmentIssuerExclusionManifest.model_validate_json(
        args.development_exclusions.resolve().read_text(encoding="utf-8")
    )
    exposure = DevelopmentExposureSnapshot.model_validate_json(
        (args.bundle_root.resolve() / "development-exposures.json").read_text(encoding="utf-8")
    )
    if exposure.source_hashes.get("tracked-issuer-exclusions") != exclusions.content_hash():
        raise SystemExit("Frozen development exposure does not match issuer exclusions.")
    if exposure.source_hashes.get("development-suite-1") != development.suite_hash:
        raise SystemExit("Frozen development exposure does not match the development suite.")
    seal = HeldOutSuiteSeal.model_validate_json(args.seal.resolve().read_text(encoding="utf-8"))
    verify_heldout_bundle(
        args.bundle_root,
        seal,
        development_company_names=set(exposure.company_aliases),
        development_suite_hashes=[development.suite_hash],
        development_question_hashes=set(exposure.question_hashes),
        development_document_hashes=set(exposure.document_hashes),
        development_exclusion_hashes=[exclusions.content_hash()],
        development_exposure_hashes=[exposure.content_hash()],
    )
    print(
        json.dumps(
            {
                "verified": True,
                "suite_id": seal.suite_id,
                "bundle_hash": seal.bundle_hash,
                "case_count": seal.case_count,
                "company_count": seal.company_count,
                "review_mode": seal.review_mode,
                "reference_labels_required": seal.reference_labels_required,
                "questions_printed": False,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
