"""Build a private eight-case V2 held-out candidate bundle from unseen official SEC 10-Ks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from researchforge.config import load_runtime_settings
from researchforge.v2.benchmarks.exposure import build_development_exposure_snapshot
from researchforge.v2.benchmarks.heldout import (
    DevelopmentIssuerExclusionManifest,
    assert_private_bundle_not_trackable,
)
from researchforge.v2.benchmarks.heldout_candidates import (
    build_private_heldout_bundle,
    new_private_seed,
    sec_bytes_fetcher,
    sec_json_fetcher,
    select_unseen_sec_filings,
)
from researchforge.v2.benchmarks.suite import BenchmarkSuiteManifest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_SUITE = (
    PROJECT_ROOT / "docs/contracts/v2/benchmarks/financebench-public-development-10-v1.json"
)
DEVELOPMENT_EXCLUSIONS = (
    PROJECT_ROOT / "docs/contracts/v2/benchmarks/development-issuer-exclusions-v1.json"
)
TICKER_URL = "https://www.sec.gov/files/company_tickers.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--review-mode",
        choices=("meets_standard", "pairwise_preference"),
        default="meets_standard",
    )
    parser.add_argument("--seed", help="Private reproducibility seed; omitted generates one")
    parser.add_argument(
        "--exclude-bundle",
        type=Path,
        action="append",
        default=[],
        help="Previously result-exposed held-out bundle to promote into development exposure.",
    )
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    assert_private_bundle_not_trackable(output_dir, PROJECT_ROOT)
    exclusions = DevelopmentIssuerExclusionManifest.model_validate_json(
        DEVELOPMENT_EXCLUSIONS.read_text(encoding="utf-8")
    )
    suite = BenchmarkSuiteManifest.model_validate_json(
        DEVELOPMENT_SUITE.read_text(encoding="utf-8")
    )
    retired_bundles = [path.resolve() for path in args.exclude_bundle]
    for retired_bundle in retired_bundles:
        assert_private_bundle_not_trackable(retired_bundle, PROJECT_ROOT)
    exposure = build_development_exposure_snapshot(
        PROJECT_ROOT,
        exclusions=exclusions,
        development_suites=[suite],
        retired_heldout_bundles=retired_bundles,
    )
    settings = load_runtime_settings(PROJECT_ROOT)
    user_agent = settings.researchforge_sec_user_agent
    json_fetch = sec_json_fetcher(user_agent)
    bytes_fetch = sec_bytes_fetcher(user_agent)
    ticker_payload = json_fetch(TICKER_URL)
    seed = args.seed or new_private_seed()
    filings = select_unseen_sec_filings(
        exposure,
        ticker_payload=ticker_payload,
        json_fetch=json_fetch,
        bytes_fetch=bytes_fetch,
        seed=seed,
    )
    manifest = build_private_heldout_bundle(
        output_dir,
        exposure,
        filings,
        seed=seed,
        review_mode=args.review_mode,
    )
    print(
        json.dumps(
            {
                "bundle_root": str(output_dir),
                "suite_id": manifest.suite_id,
                "case_count": len(manifest.case_ids),
                "issuer_count": len(filings),
                "review_mode": manifest.review_mode,
                "seed_hash": hashlib.sha256(seed.encode()).hexdigest(),
                "issuer_identities_printed": False,
                "questions_printed": False,
                "reference_labels_created": False,
                "retired_bundles_excluded": len(retired_bundles),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
