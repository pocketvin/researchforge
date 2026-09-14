"""Pinned FinanceBench open-source adapter for isolated V2 evaluation.

Gold answers and annotated evidence are kept outside the product runtime environment.
The agent receives only the source PDF plus the benchmark question. This module does not
claim that the public FinanceBench sample is held out; it is an external validation set.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from researchforge.adapters.storage import canonical_json_bytes, payload_sha256
from researchforge.v2.contracts import Json
from researchforge.v2.documents import _object, parse_pdf
from researchforge.v2.quality import QualityCase
from researchforge.v2.storage import ResearchRepository, atomic_bytes

FINANCEBENCH_COMMIT = "cc39aeb4afdf33909ee1412188bf89035950c2eb"
FINANCEBENCH_LICENSE = "CC-BY-NC-4.0"
FINANCEBENCH_PUBLISHED_AT = "2023-11-20T17:28:02+00:00"
# Local source-consistency audit of canaries. This is not a substitute for an independent
# semantic assessor; it only records whether the pinned gold label agrees with its own page.
REFERENCE_INTEGRITY: dict[str, tuple[str, list[str]]] = {
    "financebench_id_03029": (
        "verified",
        ["Pinned evidence page reports Purchases of PP&E of 1,577 USD millions, matching gold."],
    ),
    "financebench_id_04672": (
        "suspect",
        [
            (
                "Pinned evidence reports FY2018 net PP&E of 8,738 USD millions "
                "(=8.738bn, 8.74bn to two decimals) while the provided gold answer is $8.70bn."
            )
        ],
    ),
}
RAW_BASE = f"https://raw.githubusercontent.com/patronus-ai/financebench/{FINANCEBENCH_COMMIT}"
QUESTIONS_URL = f"{RAW_BASE}/data/financebench_open_source.jsonl"
DOCUMENTS_URL = f"{RAW_BASE}/data/financebench_document_information.jsonl"


def _download(url: str, path: Path) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "ResearchForge/2.0 benchmark"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = cast(bytes, response.read())
    if not payload:
        raise RuntimeError(f"empty benchmark download: {url}")
    atomic_bytes(path, payload)
    return payload


def ensure_open_sample(root: Path) -> dict[str, Any]:
    """Download only the public 150-question metadata; raw files stay in ignored artifacts."""
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    questions_path = root / "financebench_open_source.jsonl"
    documents_path = root / "financebench_document_information.jsonl"
    if not questions_path.is_file():
        _download(QUESTIONS_URL, questions_path)
    if not documents_path.is_file():
        _download(DOCUMENTS_URL, documents_path)
    questions = _jsonl(questions_path)
    documents = _jsonl(documents_path)
    if len(questions) != 150:
        raise RuntimeError(f"expected 150 FinanceBench open-source questions, got {len(questions)}")
    manifest = {
        "benchmark": "FinanceBench open-source sample",
        "source_repository": "https://github.com/patronus-ai/financebench",
        "commit": FINANCEBENCH_COMMIT,
        "license": FINANCEBENCH_LICENSE,
        "question_count": len(questions),
        "document_metadata_count": len(documents),
        "questions_sha256": hashlib.sha256(questions_path.read_bytes()).hexdigest(),
        "documents_sha256": hashlib.sha256(documents_path.read_bytes()).hexdigest(),
        "fetched_at": datetime.now(UTC).isoformat(),
        "usage_boundary": (
            "External validation only. Public sample is not a hidden/held-out ResearchForge set. "
            "Gold labels must never enter the product model context."
        ),
    }
    atomic_bytes(root / "manifest.json", json.dumps(manifest, indent=2).encode())
    return manifest


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def load_case(root: Path, financebench_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    ensure_open_sample(root)
    questions = _jsonl(root / "financebench_open_source.jsonl")
    documents = _jsonl(root / "financebench_document_information.jsonl")
    matches = [item for item in questions if item.get("financebench_id") == financebench_id]
    if len(matches) != 1:
        raise KeyError(f"FinanceBench case not uniquely found: {financebench_id}")
    question = matches[0]
    doc_matches = [item for item in documents if item.get("doc_name") == question.get("doc_name")]
    if len(doc_matches) != 1:
        raise KeyError(f"FinanceBench document not uniquely found: {question.get('doc_name')}")
    return question, doc_matches[0]


def ensure_pdf(root: Path, doc_name: str) -> Path:
    if re.fullmatch(r"[A-Za-z0-9_.-]+", doc_name) is None:
        raise ValueError("unsafe FinanceBench document name")
    pdf_dir = root / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    path = pdf_dir / f"{doc_name}.pdf"
    if not path.is_file():
        _download(f"{RAW_BASE}/pdfs/{doc_name}.pdf", path)
    if not path.read_bytes().startswith(b"%PDF-"):
        raise RuntimeError(f"FinanceBench source is not a PDF: {doc_name}")
    return path


def period_label(document: dict[str, Any]) -> str:
    year = int(document["doc_period"])
    kind = str(document.get("doc_type", "")).casefold()
    if kind in {"10k", "10k_annual"}:
        return f"{year}FY"
    if kind == "10q":
        return f"{year}Q"
    return str(year)


def benchmark_company_id(company: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", company.casefold()).strip("-")
    return f"financebench-{normalized}"


def build_environment(
    repository: ResearchRepository,
    *,
    document: dict[str, Any],
    pdf_payload: bytes,
) -> Json:
    """Create the same run-owned document universe used by V2 tools, without gold labels."""
    digest = hashlib.sha256(pdf_payload).hexdigest()
    doc_name = str(document["doc_name"])
    doc_id = f"doc_fb_{digest[:24]}"
    blob = repository.put_blob(pdf_payload, "pdf")
    company = str(document["company"])
    entity: Json = {
        "company_id": benchmark_company_id(company),
        "legal_name": company,
        "ticker": None,
        "market": "US",
        "country_code": "US",
        "provider": "financebench_external_validation",
        "provider_company_id": doc_name,
    }
    label = period_label(document)
    source: Json = {
        "document_id": doc_id,
        "title": doc_name,
        "source_uri": str(document["doc_link"]),
        "benchmark_blob_source_uri": f"{RAW_BASE}/pdfs/{doc_name}.pdf",
        "document_type": str(document.get("doc_type", "benchmark_filing")),
        # FinanceBench metadata does not expose the original filing timestamp. This date means
        # the document was available in the published frozen benchmark, not SEC filing time.
        "published_at": FINANCEBENCH_PUBLISHED_AT,
        "published_at_semantics": "external_benchmark_snapshot_not_original_filing_timestamp",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "content_hash": digest,
        "raw_blob_id": blob,
        "period_label": label,
        "reporting_period": {
            "fiscal_year": int(document["doc_period"]),
            "fiscal_period": "FY" if label.endswith("FY") else label[-1:],
            "period_basis": "ytd",
            "statement_scope": "consolidated",
            "restatement_status": "benchmark_source",
        },
        "company": entity,
        "mime_type": "application/pdf",
        "parser_version": "v2-native-1",
        "data_namespace": "external_benchmark",
    }
    objects, pages, gaps = parse_pdf(pdf_payload, source)
    objects[doc_id] = _object(
        "document",
        doc_id,
        source,
        "\n\f\n".join(pages),
        title=doc_name,
        raw_blob_id=blob,
        page_number=None,
    )
    source["page_count"] = len(pages)
    source["text_block_count"] = len(pages)
    source["table_count"] = sum(item["kind"] == "table" for item in objects.values())
    # Deliberately do not inject benchmark answer/evidence or a canonical fact derived from gold.
    # The external track tests the document-access path rather than taking an XBRL shortcut.
    return {
        "schema_version": "2.0.0",
        "entity": entity,
        "documents": {doc_id: source},
        "objects": objects,
        "facts": {},
        "gaps": [
            *gaps,
            (
                "FinanceBench external validation: gold labels are withheld from runtime "
                "context; canonical benchmark facts are not injected."
            ),
        ],
        "parser_version": "v2-native-1",
        "benchmark": {
            "name": "FinanceBench",
            "commit": FINANCEBENCH_COMMIT,
            "document_name": doc_name,
            "gold_labels_in_runtime": False,
        },
    }


def load_or_build_environment(
    repository: ResearchRepository,
    *,
    document: dict[str, Any],
    pdf_payload: bytes,
) -> Json:
    """Cache parsed FinanceBench documents by source hash inside the isolated repository."""
    digest = hashlib.sha256(pdf_payload).hexdigest()
    key = payload_sha256(
        {"content_hash": digest, "parser": "v2-native-1", "benchmark": FINANCEBENCH_COMMIT}
    )
    cache_path = repository.root / "benchmark-document-cache" / f"{key}.json"
    if cache_path.is_file():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        environment = repository.cas.get(str(cached["digest"]))
        if not isinstance(environment, dict):
            raise RuntimeError("cached FinanceBench environment is not an object")
        for source in environment.get("documents", {}).values():
            repository.blob_path(str(source["raw_blob_id"]))
        return environment
    environment = build_environment(repository, document=document, pdf_payload=pdf_payload)
    environment_digest = repository.cas.put(environment).digest
    atomic_bytes(cache_path, canonical_json_bytes({"digest": environment_digest}))
    return environment


def make_quality_case(
    *,
    question: dict[str, Any],
    document: dict[str, Any],
    environment: Json,
    research_time: str,
) -> QualityCase:
    documents = list(environment["documents"].values())
    if len(documents) != 1:
        raise ValueError("FinanceBench case must be bound to exactly one frozen PDF")
    source = documents[0]
    digest = str(source["content_hash"])
    alternatives = []
    for evidence in question.get("evidence", []):
        text = str(evidence.get("evidence_text_full_page") or evidence.get("evidence_text") or "")
        if not text.strip():
            continue
        alternatives.append(
            {
                "document_hash": digest,
                "page_number": int(evidence["evidence_page_num"]) + 1,
                "required_text": text,
                "match_mode": "page",
            }
        )
    integrity, integrity_notes = REFERENCE_INTEGRITY.get(
        str(question["financebench_id"]), ("provided", [])
    )
    return QualityCase.model_validate(
        {
            "case_id": f"financebench:{question['financebench_id']}",
            "split": "development",
            "question": str(question["question"]),
            "company_id": str(environment["entity"]["company_id"]),
            "research_time": research_time,
            "corpus_hash": payload_sha256(sorted(str(item["content_hash"]) for item in documents)),
            "reference_author": "PatronusAI FinanceBench open-source human annotation",
            "reference_integrity": integrity,
            "reference_integrity_notes": integrity_notes,
            "reference_reviewed_by": None,
            "reference_reviewed_at": None,
            "required_evidence": [
                {
                    "requirement_id": "gold_evidence_page",
                    "description": (
                        "Observe at least one externally annotated FinanceBench evidence page."
                    ),
                    "alternatives": alternatives,
                    "materiality": "major",
                }
            ]
            if alternatives
            else [],
            "required_findings": [
                {
                    "requirement_id": "gold_answer",
                    "description": "Correctly answer the FinanceBench question.",
                    "materiality": "major",
                    "reference_answer": str(question["answer"]),
                }
            ],
            "acceptable_uncertainties": [],
        }
    )
