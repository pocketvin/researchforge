"""Held-out candidate construction stays source-only and excludes known development exposure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from researchforge.v2.benchmarks.exposure import DevelopmentExposureSnapshot
from researchforge.v2.benchmarks.heldout import HeldOutRuntimeCase, seal_heldout_bundle
from researchforge.v2.benchmarks.heldout_candidates import (
    MIN_FILING_BYTES,
    build_private_heldout_bundle,
    select_unseen_sec_filings,
)


def _filing_payload(label: str) -> bytes:
    header = (
        "<html><body>CONSOLIDATED BALANCE SHEETS CONSOLIDATED STATEMENTS OF CASH FLOWS "
        f"Revenue Net Sales {label}</body></html>"
    ).encode()
    return header + b"x" * (MIN_FILING_BYTES - len(header) + 128)


def _submissions(cik: int) -> dict:
    return {
        "filings": {
            "recent": {
                "form": ["10-K"],
                "accessionNumber": [f"000000{cik:04d}-26-000001"],
                "primaryDocument": [f"issuer-{cik}.htm"],
                "acceptanceDateTime": ["2026-02-15T12:00:00Z"],
                "filingDate": ["2026-02-15"],
                "reportDate": ["2025-12-31"],
            }
        }
    }


def _ticker_payload() -> dict:
    rows = [
        (1001, "DEV", "Known Development Co"),
        (1002, "OLD", "Reused Source Co"),
        (1003, "A", "Unseen Alpha Co"),
        (1004, "B", "Unseen Beta Co"),
        (1005, "C", "Unseen Gamma Co"),
        (1006, "D", "Unseen Delta Co"),
        (1007, "E", "Unseen Extra Co"),
    ]
    return {
        str(index): {"cik_str": cik, "ticker": ticker, "title": title}
        for index, (cik, ticker, title) in enumerate(rows)
    }


def _exposure(reused_hash: str) -> DevelopmentExposureSnapshot:
    return DevelopmentExposureSnapshot(
        snapshot_id="test-exposure",
        source_hashes={"test": "a" * 64},
        company_aliases=["Known Development Co"],
        question_hashes=[],
        case_ids=[],
        document_hashes=[reused_hash],
    )


def test_candidate_selection_skips_known_issuer_and_known_source_bytes(tmp_path: Path) -> None:
    reused = _filing_payload("reused")
    reused_hash = hashlib.sha256(reused).hexdigest()
    exposure = _exposure(reused_hash)
    payloads = {
        cik: (_filing_payload(f"issuer-{cik}") if cik != 1002 else reused)
        for cik in range(1002, 1008)
    }
    requested_submissions: list[int] = []

    def json_fetch(url: str) -> dict:
        cik = int(url.split("CIK", 1)[1].split(".json", 1)[0])
        requested_submissions.append(cik)
        return _submissions(cik)

    def bytes_fetch(url: str) -> bytes:
        for cik, payload in payloads.items():
            if f"issuer-{cik}.htm" in url:
                return payload
        raise AssertionError(f"unexpected filing URL: {url}")

    filings = select_unseen_sec_filings(
        exposure,
        ticker_payload=_ticker_payload(),
        json_fetch=json_fetch,
        bytes_fetch=bytes_fetch,
        seed="private-seed-test",
        max_attempts=7,
    )

    assert len(filings) == 4
    assert all(filing.company.legal_name != "Known Development Co" for filing in filings)
    assert all(filing.content_hash != reused_hash for filing in filings)
    assert 1001 not in requested_submissions

    bundle = tmp_path / "private-bundle"
    manifest = build_private_heldout_bundle(
        bundle,
        exposure,
        filings,
        seed="private-seed-test",
        review_mode="meets_standard",
    )
    cases = [
        HeldOutRuntimeCase.model_validate_json(line)
        for line in (bundle / "runtime-cases.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert len(manifest.case_ids) == len(cases) == 8
    assert len({case.company_group_key for case in cases}) == 4
    assert {case.stratum for case in cases} == {
        "direct_extraction",
        "numerical_analysis",
        "analytical_explanation",
        "evidence_limited",
    }
    assert not (bundle / "reference-cases.jsonl").exists()
    assert not (bundle / "review-attestations.jsonl").exists()
    assert (bundle / "development-exposures.json").is_file()
    metadata = json.loads((bundle / "selection-metadata.json").read_text())
    assert metadata["reference_labels_created"] is False
    assert metadata["product_model_called"] is False

    seal = seal_heldout_bundle(
        bundle,
        development_company_names=set(exposure.company_aliases),
        development_suite_hashes=["b" * 64],
        development_question_hashes=set(exposure.question_hashes),
        development_document_hashes=set(exposure.document_hashes),
        development_exclusion_hashes=["c" * 64],
        development_exposure_hashes=[exposure.content_hash()],
    )
    assert seal.case_count == 8
    assert seal.company_count == 4
    assert seal.development_exposure_hashes == [exposure.content_hash()]


def test_candidate_bundle_contains_no_answer_or_reference_fields(tmp_path: Path) -> None:
    exposure = _exposure("f" * 64)
    filings = []
    for index in range(4):
        payload = _filing_payload(f"clean-{index}")
        from researchforge.v2.benchmarks.heldout_candidates import FrozenSecFiling, SecCompany

        filings.append(
            FrozenSecFiling(
                company=SecCompany(2000 + index, f"T{index}", f"Private Company {index}"),
                accession=f"000000{2000 + index}-26-000001",
                primary_document=f"private-{index}.htm",
                accepted_at="2026-02-15T12:00:00Z",
                report_date="2025-12-31",
                source_uri=(
                    "https://www.sec.gov/Archives/edgar/data/"
                    f"{2000 + index}/000000{2000 + index}26000001/private-{index}.htm"
                ),
                payload=payload,
                content_hash=hashlib.sha256(payload).hexdigest(),
            )
        )
    bundle = tmp_path / "private-bundle"
    build_private_heldout_bundle(bundle, exposure, filings, seed="another-private-seed")
    runtime_text = (bundle / "runtime-cases.jsonl").read_text().casefold()
    assert '"answer"' not in runtime_text
    assert '"reference"' not in runtime_text
    assert '"gold"' not in runtime_text
