"""Regression tests for the public-safe V1.4 primary benchmark package."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = ROOT / "data" / "fixtures" / "v1.4-primary"
SUITE_PATH = ROOT / "benchmark" / "suites" / "v1.4-primary-preregistered.json"
METRICS = {
    "accounts_receivable",
    "inventory",
    "net_income",
    "operating_cash_flow",
    "operating_cost",
    "revenue",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


SOURCES = {
    source["document_id"]: source
    for path in sorted((PACKAGE_DIR / "source-documents").glob("*.json"))
    for source in (load_json(path),)
}
FACTS = {
    fact["fact_id"]: fact
    for path in sorted((PACKAGE_DIR / "financial-facts").glob("*.json"))
    for fact in (load_json(path),)
}
CHUNKS = {
    chunk["chunk_id"]: chunk
    for path in sorted((PACKAGE_DIR / "evidence-chunks").glob("*.json"))
    for chunk in (load_json(path),)
}
CASES = {
    case["case_id"]: case
    for path in sorted((PACKAGE_DIR / "cases").glob("*.json"))
    for case in (load_json(path),)
}
MANIFEST = load_json(PACKAGE_DIR / "manifest.json")


def test_primary_package_shape_and_split_isolation_are_frozen() -> None:
    assert (len(SOURCES), len(FACTS), len(CHUNKS), len(CASES)) == (24, 144, 24, 24)
    assert MANIFEST["split_counts"] == {
        "evolution": 12,
        "validation": 6,
        "final_test": 6,
    }
    groups_by_split = {
        split: {case["group_key"] for case in CASES.values() if case["split"] == split}
        for split in ("evolution", "validation", "final_test")
    }
    assert groups_by_split == {
        "evolution": {"cn_300750", "cn_300014"},
        "validation": {"cn_002074"},
        "final_test": {"cn_300207"},
    }
    assert not (groups_by_split["evolution"] & groups_by_split["validation"])
    assert not (groups_by_split["evolution"] & groups_by_split["final_test"])
    assert not (groups_by_split["validation"] & groups_by_split["final_test"])
    assert not list(PACKAGE_DIR.rglob("*.pdf"))


def test_sources_and_facts_retain_full_semantics_and_official_lineage() -> None:
    facts_by_document: dict[str, list[dict[str, Any]]] = {}
    for fact in FACTS.values():
        document_id = fact["source"]["document_id"]
        source = SOURCES[document_id]
        facts_by_document.setdefault(document_id, []).append(fact)
        assert fact["company"] == source["company"]
        assert fact["source"]["content_hash"] == source["content_hash"]
        assert fact["source"]["published_at"] == source["published_at"]
        assert fact["value"] is not None
        assert all(
            fact["source_locator"].get(field)
            for field in ("page", "section", "table", "row_label", "column_label")
        )

    for document_id, source in SOURCES.items():
        assert urlparse(source["source_uri"]).netloc in {
            "static.cninfo.com.cn",
            "disc.static.szse.cn",
        }
        assert source["license"]["raw_payload_committed"] is False
        assert datetime.fromisoformat(source["published_at"]) <= datetime.fromisoformat(
            source["retrieved_at"]
        )
        document_facts = facts_by_document[document_id]
        assert len(document_facts) == 6
        assert {fact["metric_code"] for fact in document_facts} == METRICS


def test_cases_reference_only_same_report_artifacts_and_obey_cutoff() -> None:
    for case in CASES.values():
        assert len(case["target_periods"]) == 1
        assert len(case["allowed_document_ids"]) == 1
        assert len(case["allowed_evidence_chunk_ids"]) == 1
        assert len(case["allowed_financial_fact_ids"]) == 6
        document_id = case["allowed_document_ids"][0]
        source = SOURCES[document_id]
        chunk = CHUNKS[case["allowed_evidence_chunk_ids"][0]]
        facts = [FACTS[fact_id] for fact_id in case["allowed_financial_fact_ids"]]

        assert case["company"] == source["company"]
        assert case["target_periods"] == [source["reporting_period"]]
        assert chunk["document_id"] == document_id
        assert all(fact["source"]["document_id"] == document_id for fact in facts)
        assert {fact["metric_code"] for fact in facts} == METRICS
        assert datetime.fromisoformat(source["published_at"]) <= datetime.fromisoformat(
            case["research_time"]
        )
        assert case["sealed"] is (case["split"] == "final_test")
        assert (
            case["verifier_ground_truth_ref"]["artifact_hash"]
            == MANIFEST["ground_truth_hashes"][case["case_id"]]
        )


def test_public_evidence_is_explicitly_synthetic_and_non_verbatim() -> None:
    for chunk in CHUNKS.values():
        assert chunk["text"].startswith("SYNTHETIC PUBLIC EVIDENCE")
        assert "not verbatim filing text" in chunk["text"]
        assert hashlib.sha256(chunk["text"].encode()).hexdigest() == chunk["text_hash"]


def test_manifest_hashes_cover_every_public_artifact_and_package_is_stable() -> None:
    public_paths = sorted(
        path
        for directory in ("source-documents", "financial-facts", "evidence-chunks", "cases")
        for path in (PACKAGE_DIR / directory).glob("*.json")
    )
    expected_public_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in public_paths
    }
    assert MANIFEST["public_artifact_hashes"] == expected_public_hashes

    data_hashes = {
        **{f"source:{key}": canonical_hash(value) for key, value in SOURCES.items()},
        **{f"fact:{key}": canonical_hash(value) for key, value in FACTS.items()},
        **{f"chunk:{key}": canonical_hash(value) for key, value in CHUNKS.items()},
        **{f"ground_truth:{key}": value for key, value in MANIFEST["ground_truth_hashes"].items()},
        "preregistered_suite": hashlib.sha256(SUITE_PATH.read_bytes()).hexdigest(),
    }
    assert canonical_hash(data_hashes) == MANIFEST["package_hash"]
    assert {case["package_hash"] for case in CASES.values()} == {MANIFEST["package_hash"]}
    assert MANIFEST["formal_run_authorized"] is False
    assert MANIFEST["owner_signoff"] == {
        "status": "pending",
        "signed_at": None,
        "evidence_file": "docs/evidence/g3-primary-data-signoff.md",
    }
