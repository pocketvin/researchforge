"""Held-out execution must use the exact sealed source bytes and never live discovery."""

from __future__ import annotations

import hashlib
import io
from datetime import datetime
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from researchforge.adapters.storage import payload_sha256
from researchforge.v2.benchmarks.heldout import HeldOutDocument, HeldOutRuntimeCase
from researchforge.v2.benchmarks.heldout_runner import (
    build_frozen_environment,
    load_or_build_frozen_environment,
)
from researchforge.v2.storage import ResearchRepository


def _pdf() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=400, height=400)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 40 300 Td (Revenue 120. Cash flow 20. Risk disclosure.) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _case(root: Path, *, published_at: str = "2025-03-01T00:00:00+00:00") -> HeldOutRuntimeCase:
    payload = _pdf()
    source = root / "sources" / "filing.pdf"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    document = HeldOutDocument(
        document_id="doc_heldout_001",
        title="Frozen filing",
        relative_path="sources/filing.pdf",
        content_hash=digest,
        source_uri="https://example.invalid/frozen-filing.pdf",
        published_at=published_at,
        document_type="annual_report",
        reporting_period={
            "fiscal_year": 2024,
            "fiscal_period": "FY",
            "period_basis": "ytd",
            "statement_scope": "consolidated",
        },
    )
    return HeldOutRuntimeCase(
        case_id="heldout_case_001",
        stratum="direct_extraction",
        company_group_key="never-seen-company",
        company_query="Never Seen Company",
        company_id="heldout_never_seen_company",
        market_hint="US",
        requested_period_label="2024FY",
        research_question="What did the filing report?",
        research_time="2025-04-01T00:00:00+00:00",
        corpus_hash=payload_sha256([digest]),
        documents=[document],
    )


def test_build_frozen_environment_uses_exact_sealed_bytes(tmp_path: Path) -> None:
    bundle = tmp_path / "private"
    case = _case(bundle)
    repository = ResearchRepository(tmp_path / "runtime")

    environment = build_frozen_environment(repository, bundle_root=bundle, case=case)

    assert environment["heldout"] == {
        "case_id": case.case_id,
        "corpus_hash": case.corpus_hash,
        "frozen_source_only": True,
        "live_discovery_used": False,
    }
    assert environment["entity"]["company_id"] == case.company_id
    assert set(environment["documents"]) == {"doc_heldout_001"}
    source = environment["documents"]["doc_heldout_001"]
    assert source["content_hash"] == case.documents[0].content_hash
    assert source["raw_blob_id"].startswith(case.documents[0].content_hash)
    assert source["data_namespace"] == "heldout_acceptance"
    assert source["frozen_source"] is True
    assert any(item["kind"] == "page" for item in environment["objects"].values())
    assert any("does not inject a live SEC" in gap for gap in environment["gaps"])


def test_frozen_environment_rejects_source_tamper(tmp_path: Path) -> None:
    bundle = tmp_path / "private"
    case = _case(bundle)
    (bundle / "sources" / "filing.pdf").write_bytes(b"tampered after seal")
    repository = ResearchRepository(tmp_path / "runtime")

    with pytest.raises(ValueError, match="source hash mismatch"):
        build_frozen_environment(repository, bundle_root=bundle, case=case)


def test_frozen_environment_rejects_future_document(tmp_path: Path) -> None:
    bundle = tmp_path / "private"
    case = _case(bundle, published_at="2025-05-01T00:00:00+00:00")
    repository = ResearchRepository(tmp_path / "runtime")

    with pytest.raises(ValueError, match="exceeds the frozen research cutoff"):
        build_frozen_environment(repository, bundle_root=bundle, case=case)


def test_frozen_environment_cache_roundtrip_preserves_corpus(tmp_path: Path) -> None:
    bundle = tmp_path / "private"
    case = _case(bundle)
    repository = ResearchRepository(tmp_path / "runtime")

    first = load_or_build_frozen_environment(repository, bundle_root=bundle, case=case)
    second = load_or_build_frozen_environment(repository, bundle_root=bundle, case=case)

    assert first == second
    assert first["heldout"]["corpus_hash"] == case.corpus_hash
    cache = repository.root / "heldout-document-cache"
    assert len(list(cache.glob("*.json"))) == 1


def test_research_time_parser_remains_timezone_aware(tmp_path: Path) -> None:
    bundle = tmp_path / "private"
    case = _case(bundle)
    assert datetime.fromisoformat(case.research_time).tzinfo is not None
