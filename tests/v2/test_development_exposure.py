"""Development exposure snapshots prevent public/dev inputs from becoming fake held-out data."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from researchforge.adapters.storage import payload_sha256
from researchforge.v2.benchmarks.exposure import (
    build_development_exposure_snapshot,
    normalized_question_hash,
)
from researchforge.v2.benchmarks.heldout import (
    DevelopmentIssuerExclusionManifest,
    HeldOutBundleManifest,
    HeldOutDocument,
    HeldOutRuntimeCase,
)
from researchforge.v2.benchmarks.suite import BenchmarkSuiteManifest
from researchforge.v2.contracts import ResearchRequest
from researchforge.v2.storage import ResearchRepository

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _contracts() -> tuple[DevelopmentIssuerExclusionManifest, BenchmarkSuiteManifest]:
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


def _retired_bundle(root: Path) -> tuple[Path, str, str]:
    bundle = root / "retired-heldout"
    sources = bundle / "sources"
    sources.mkdir(parents=True)
    payload = b"<html><body>retired held-out source</body></html>"
    source_path = sources / "source-01.html"
    source_path.write_bytes(payload)
    content_hash = hashlib.sha256(payload).hexdigest()
    question = "What did the retired held-out filing report?"
    document = HeldOutDocument(
        document_id="doc_retired_heldout",
        title="Retired private filing",
        relative_path="sources/source-01.html",
        content_hash=content_hash,
        source_uri="https://www.sec.gov/Archives/retired-heldout.htm",
        published_at="2026-01-15T00:00:00+00:00",
        document_type="annual_report",
        reporting_period={"fiscal_year": 2025, "fiscal_period": "FY"},
    )
    case = HeldOutRuntimeCase(
        case_id="heldout_retired_case_001",
        stratum="direct_extraction",
        company_group_key="Retired Heldout Co",
        company_query="Retired Heldout Co",
        company_id="sec_retired_heldout",
        market_hint="US",
        requested_period_label="2025FY",
        research_question=question,
        research_time="2026-01-20T00:00:00+00:00",
        corpus_hash=payload_sha256([content_hash]),
        documents=[document],
    )
    manifest = HeldOutBundleManifest(
        suite_id="heldout-retired-development-exposure",
        created_at=datetime(2026, 1, 20, tzinfo=UTC),
        review_mode="meets_standard",
        case_ids=[case.case_id],
    )
    (bundle / "bundle-manifest.json").write_text(manifest.model_dump_json(indent=2) + "\n")
    (bundle / "runtime-cases.jsonl").write_text(case.model_dump_json() + "\n")
    return bundle, question, content_hash


def test_tracked_exclusions_cover_entire_financebench_public_issuer_universe() -> None:
    exclusions, _ = _contracts()
    financebench_issuers = {
        "3M",
        "AES Corporation",
        "AMD",
        "Activision Blizzard",
        "Adobe",
        "Amazon",
        "Amcor",
        "American Express",
        "American Water Works",
        "Best Buy",
        "Block",
        "Boeing",
        "CVS Health",
        "Coca-Cola",
        "Corning",
        "Costco",
        "Foot Locker",
        "General Mills",
        "JPMorgan",
        "Johnson & Johnson",
        "Kraft Heinz",
        "Lockheed Martin",
        "MGM Resorts",
        "Microsoft",
        "Netflix",
        "Nike",
        "Paypal",
        "PepsiCo",
        "Pfizer",
        "Ulta Beauty",
        "Verizon",
        "Walmart",
    }
    aliases = {alias.casefold() for alias in exclusions.all_aliases()}
    assert {issuer.casefold() for issuer in financebench_issuers} <= aliases


def test_snapshot_collects_full_public_source_and_persisted_v2_run(tmp_path: Path) -> None:
    exclusions, suite = _contracts()
    public_source = (
        tmp_path / "artifacts/v2-benchmarks/financebench/source/financebench_open_source.jsonl"
    )
    public_source.parent.mkdir(parents=True)
    public_source.write_text(
        json.dumps(
            {
                "financebench_id": "financebench_id_extra",
                "company": "Public Dev Extra Co",
                "question": "What is the public development value?",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    repository = ResearchRepository(tmp_path / "artifacts/v2")
    manifest, _created = repository.create(
        ResearchRequest(
            company_query="Persisted Dev Run Co",
            market_hint="US",
            requested_period_label="2025FY",
            research_question="What did this persisted development run ask?",
            research_time=datetime(2026, 1, 1, tzinfo=UTC),
            idempotency_key="development-exposure-test",
        ),
        configuration={},
    )
    persisted_document_hash = "a" * 64
    repository.attach(
        manifest["run_id"],
        "environment",
        {"documents": {"doc_dev": {"content_hash": persisted_document_hash}}},
    )

    snapshot = build_development_exposure_snapshot(
        tmp_path,
        exclusions=exclusions,
        development_suites=[suite],
    )

    assert "Public Dev Extra Co" in snapshot.company_aliases
    assert "Persisted Dev Run Co" in snapshot.company_aliases
    assert "financebench_id_extra" in snapshot.case_ids
    assert (
        normalized_question_hash("What is the public development value?")
        in snapshot.question_hashes
    )
    assert (
        normalized_question_hash("What did this persisted development run ask?")
        in snapshot.question_hashes
    )
    assert {
        "tracked-issuer-exclusions",
        "development-suite-1",
        "financebench-public-source",
        "v2-run-requests",
    } <= set(snapshot.source_hashes)
    assert persisted_document_hash in snapshot.document_hashes
    assert len(snapshot.content_hash()) == 64


def test_snapshot_is_deterministic_for_same_exposure(tmp_path: Path) -> None:
    exclusions, suite = _contracts()
    first = build_development_exposure_snapshot(
        tmp_path,
        exclusions=exclusions,
        development_suites=[suite],
    )
    second = build_development_exposure_snapshot(
        tmp_path,
        exclusions=exclusions,
        development_suites=[suite],
    )
    assert first == second
    assert first.content_hash() == second.content_hash()


def test_retired_heldout_bundle_becomes_development_exposure(tmp_path: Path) -> None:
    exclusions, suite = _contracts()
    bundle, question, document_hash = _retired_bundle(tmp_path)
    snapshot = build_development_exposure_snapshot(
        tmp_path,
        exclusions=exclusions,
        development_suites=[suite],
        retired_heldout_bundles=[bundle],
    )

    assert "Retired Heldout Co" in snapshot.company_aliases
    assert normalized_question_hash(question) in snapshot.question_hashes
    assert "heldout_retired_case_001" in snapshot.case_ids
    assert document_hash in snapshot.document_hashes
    assert "retired-heldout-bundle-1" in snapshot.source_hashes


def test_retired_heldout_bundle_source_hash_is_verified(tmp_path: Path) -> None:
    exclusions, suite = _contracts()
    bundle, _question, _document_hash = _retired_bundle(tmp_path)
    (bundle / "sources/source-01.html").write_bytes(b"tampered after retirement")

    with pytest.raises(ValueError, match="source hash mismatch"):
        build_development_exposure_snapshot(
            tmp_path,
            exclusions=exclusions,
            development_suites=[suite],
            retired_heldout_bundles=[bundle],
        )
