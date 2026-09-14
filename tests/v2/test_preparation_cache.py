"""Verified cache fallback must remain exact, bounded and fail-closed."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from researchforge.adapters.storage import canonical_json_bytes
from researchforge.ingestion.errors import IngestionAbstention
from researchforge.v2.contracts import Json, ResearchRequest
from researchforge.v2.preparation import PARSER_VERSION, FilingPreparer
from researchforge.v2.storage import ResearchRepository, atomic_bytes


def request(key: str) -> ResearchRequest:
    return ResearchRequest(
        company_query="Synthetic Test Co",
        market_hint="US",
        requested_period_label="2025FY",
        research_question="Analyze cash flow.",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key=key,
    )


def install_package(repo: ResearchRepository, marker: bytes) -> Json:
    blob = repo.put_blob(b"%PDF-" + marker, "pdf")
    digest = blob.split(".")[0]
    package = {
        "schema_version": "2.0.0",
        "entity": {
            "company_id": "us_test",
            "country_code": "US",
            "exchange": "NASDAQ",
            "legal_name": "Synthetic Test Co",
            "ticker": "TEST",
        },
        "documents": {
            f"doc_{digest[:8]}": {
                "document_id": f"doc_{digest[:8]}",
                "period_label": "2025FY",
                "published_at": "2026-01-01T00:00:00+00:00",
                "content_hash": digest,
                "raw_blob_id": blob,
            }
        },
        "objects": {},
        "facts": {},
        "gaps": ["synthetic"],
        "parser_version": PARSER_VERSION,
    }
    package_digest = repo.cas.put(package).digest
    cache = repo.root / "document-cache" / f"cache-{digest[:10]}.json"
    atomic_bytes(cache, canonical_json_bytes({"digest": package_digest}))
    return package


def provider_unavailable(*_args: object, **_kwargs: object) -> object:
    raise IngestionAbstention(
        "DISCLOSURE_PROVIDER_UNAVAILABLE", "discovery", "synthetic provider outage"
    )


def test_verified_cache_fallback_survives_discovery_outage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = ResearchRepository(tmp_path)
    expected = install_package(repo, b"one")
    req = request("cache-fallback")
    manifest, _ = repo.create(req, {})
    preparer = FilingPreparer(repo)
    monkeypatch.setattr(preparer.discovery, "discover", provider_unavailable)
    actual = preparer.prepare(req, manifest["run_id"], lambda: None)
    assert actual == expected
    events = repo.events(manifest["run_id"])
    fallback = [event for event in events if event["name"] == "verified_cache_fallback"]
    assert len(fallback) == 1
    assert fallback[0]["data"]["cache_is_new_source_discovery"] is False


def test_verified_cache_fallback_rejects_ambiguous_matching_packages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = ResearchRepository(tmp_path)
    install_package(repo, b"one")
    install_package(repo, b"two")
    req = request("cache-ambiguous")
    manifest, _ = repo.create(req, {})
    preparer = FilingPreparer(repo)
    monkeypatch.setattr(preparer.discovery, "discover", provider_unavailable)
    with pytest.raises(IngestionAbstention) as exc_info:
        preparer.prepare(req, manifest["run_id"], lambda: None)
    assert exc_info.value.code == "DISCLOSURE_PROVIDER_UNAVAILABLE"


def test_verified_cache_fallback_rejects_stale_parser_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = ResearchRepository(tmp_path)
    package = install_package(repo, b"stale-parser")
    package["parser_version"] = "v2-native-previous"
    package_digest = repo.cas.put(package).digest
    cache = next((repo.root / "document-cache").glob("*.json"))
    atomic_bytes(cache, canonical_json_bytes({"digest": package_digest}))
    req = request("cache-stale-parser")
    manifest, _ = repo.create(req, {})
    preparer = FilingPreparer(repo)
    monkeypatch.setattr(preparer.discovery, "discover", provider_unavailable)

    with pytest.raises(IngestionAbstention) as exc_info:
        preparer.prepare(req, manifest["run_id"], lambda: None)

    assert exc_info.value.code == "DISCLOSURE_PROVIDER_UNAVAILABLE"
