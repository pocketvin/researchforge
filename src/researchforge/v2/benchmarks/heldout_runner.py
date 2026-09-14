"""Execute sealed held-out cases against frozen source bytes.

The acceptance runner must never rediscover or redownload a filing after a held-out seal exists.
This module turns each sealed runtime case into the normal V2 document environment using exactly
the source bytes named by the private bundle. The product Agent therefore sees the same immutable
corpus that was sealed, while the existing document parser, facts and tool runtime remain in use.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import cast

from researchforge.adapters.storage import payload_sha256
from researchforge.v2.benchmarks.heldout import HeldOutDocument, HeldOutRuntimeCase
from researchforge.v2.benchmarks.human_review import CandidateResultRef
from researchforge.v2.contracts import Json, ResearchRequest
from researchforge.v2.documents import _object, parse_html, parse_pdf
from researchforge.v2.preparation import PARSER_VERSION, bind_fact_cells, extract_pdf_facts
from researchforge.v2.runtime import build_service
from researchforge.v2.storage import ResearchRepository, atomic_bytes

_TECHNICAL_FAILURE_MARKERS = (
    "BadRequestError",
    "APIConnectionError",
    "APITimeoutError",
    "RateLimitError",
    "InternalServerError",
    "ServiceUnavailableError",
    "ConnectTimeout",
    "ConnectionError",
    "ReadTimeout",
    "HTTPStatusError",
)


class HeldOutCaseFailure(RuntimeError):
    """A terminated product run with explicit retry eligibility for acceptance orchestration."""

    def __init__(self, lifecycle_state: str, failure_code: str, failure_message: str) -> None:
        super().__init__(
            f"held-out case did not produce a valid product result: {lifecycle_state} "
            f"({failure_code})"
        )
        self.lifecycle_state = lifecycle_state
        self.failure_code = failure_code
        self.failure_message = failure_message
        self.retry_eligible = bool(
            failure_code == "V2_EXECUTION_FAILED"
            and any(marker in failure_message for marker in _TECHNICAL_FAILURE_MARKERS)
        )


def _period_label(document: HeldOutDocument, case: HeldOutRuntimeCase) -> str | None:
    year = document.reporting_period.get("fiscal_year")
    period = document.reporting_period.get("fiscal_period")
    if isinstance(year, int) and isinstance(period, str) and period.strip():
        return f"{year}{period.strip()}"
    return case.requested_period_label


def _entity(case: HeldOutRuntimeCase) -> Json:
    return {
        "company_id": case.company_id,
        "legal_name": case.company_query,
        "ticker": None,
        "market": case.market_hint,
        "country_code": case.market_hint,
        "provider": "heldout_frozen_bundle",
        "provider_company_id": case.company_id,
    }


def _source_path(bundle_root: Path, document: HeldOutDocument) -> Path:
    bundle_root = bundle_root.resolve()
    path = (bundle_root / document.relative_path).resolve()
    if bundle_root not in path.parents:
        raise ValueError("held-out source escaped the private bundle")
    return path


def _source_payload(bundle_root: Path, document: HeldOutDocument) -> tuple[Path, bytes]:
    path = _source_path(bundle_root, document)
    payload = path.read_bytes()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != document.content_hash:
        raise ValueError(f"held-out source hash mismatch: {document.document_id}")
    return path, payload


def build_frozen_environment(
    repository: ResearchRepository,
    *,
    bundle_root: Path,
    case: HeldOutRuntimeCase,
) -> Json:
    """Build the normal V2 document universe from the exact sealed source bytes."""

    research_time = datetime.fromisoformat(case.research_time)
    if research_time.tzinfo is None:
        raise ValueError("held-out research_time must include a timezone")
    entity = _entity(case)
    documents: dict[str, Json] = {}
    objects: dict[str, Json] = {}
    facts: dict[str, Json] = {}
    gaps: list[str] = []
    seen_document_ids: set[str] = set()

    for document in case.documents:
        if document.document_id in seen_document_ids:
            raise ValueError("held-out case contains duplicate document IDs")
        seen_document_ids.add(document.document_id)
        published_at = datetime.fromisoformat(document.published_at)
        if published_at.tzinfo is None:
            raise ValueError("held-out document published_at must include a timezone")
        if published_at > research_time:
            raise ValueError("held-out source exceeds the frozen research cutoff")

        path, payload = _source_payload(bundle_root, document)
        is_pdf = payload.startswith(b"%PDF-")
        is_html = path.suffix.casefold() in {".html", ".htm"}
        if not is_pdf and not is_html:
            raise ValueError("held-out source must be a PDF or HTML document")
        extension = "pdf" if is_pdf else "html"
        blob = repository.put_blob(payload, extension)
        source: Json = {
            "document_id": document.document_id,
            "title": document.title,
            "source_uri": document.source_uri,
            "document_type": document.document_type,
            "published_at": document.published_at,
            "retrieved_at": document.published_at,
            "retrieved_at_semantics": "frozen_bundle_snapshot_time_not_retrieval_time",
            "content_hash": document.content_hash,
            "raw_blob_id": blob,
            "reporting_period": document.reporting_period,
            "period_label": _period_label(document, case),
            "company": entity,
            "mime_type": "application/pdf" if is_pdf else "text/html",
            "parser_version": PARSER_VERSION,
            "data_namespace": "heldout_acceptance",
            "frozen_source": True,
        }
        parsed, pages, parse_gaps = (
            parse_pdf(payload, source) if is_pdf else parse_html(payload, source)
        )
        parsed[document.document_id] = _object(
            "document",
            document.document_id,
            source,
            "\n\f\n".join(pages),
            title=document.title,
            raw_blob_id=blob,
            page_number=None,
        )
        source["page_count"] = len(pages) if is_pdf else None
        source["text_block_count"] = len(pages)
        source["table_count"] = sum(item["kind"] == "table" for item in parsed.values())
        documents[document.document_id] = source
        for artifact_id, value in parsed.items():
            if artifact_id in objects:
                raise ValueError("held-out document parsing produced duplicate artifact IDs")
            objects[artifact_id] = value
        gaps.extend(f"{document.document_id}: {message}" for message in parse_gaps)

        if is_pdf and case.market_hint in {"CN", "HK"}:
            extracted, fact_gaps = extract_pdf_facts(source, pages, case.market_hint)
            for fact_id, fact in extracted.items():
                if fact_id in facts:
                    raise ValueError("held-out fact extraction produced duplicate fact IDs")
                facts[fact_id] = fact
            gaps.extend(f"{document.document_id}: {message}" for message in fact_gaps)
        elif case.market_hint == "US":
            gaps.append(
                f"{document.document_id}: frozen held-out filing does not inject a live SEC "
                "Company Facts/XBRL shortcut; the Agent must inspect the sealed filing itself."
            )

    bind_fact_cells(facts, objects)
    for fact in facts.values():
        evidence_id = str(fact["fact_id"]).replace("fact_", "evfact_", 1)
        if evidence_id in objects:
            continue
        source = documents[str(fact["document_id"])]
        objects[evidence_id] = _object(
            "evidence",
            evidence_id,
            source,
            str(fact["text"]),
            page_id=fact["source_locator"].get("page_id"),
            page_number=fact["source_locator"].get("page"),
            fact_id=fact["fact_id"],
        )
        fact["evidence_id"] = evidence_id

    observed_corpus_hash = payload_sha256(
        sorted(str(source["content_hash"]) for source in documents.values())
    )
    if observed_corpus_hash != case.corpus_hash:
        raise ValueError("held-out environment corpus differs from the sealed runtime case")
    return {
        "schema_version": "2.0.0",
        "entity": entity,
        "documents": documents,
        "objects": objects,
        "facts": facts,
        "gaps": gaps,
        "parser_version": PARSER_VERSION,
        "heldout": {
            "case_id": case.case_id,
            "corpus_hash": case.corpus_hash,
            "frozen_source_only": True,
            "live_discovery_used": False,
        },
    }


def load_or_build_frozen_environment(
    repository: ResearchRepository,
    *,
    bundle_root: Path,
    case: HeldOutRuntimeCase,
) -> Json:
    """Cache frozen parsing by case corpus and parser version without touching the network."""

    key = payload_sha256(
        {
            "case_id": case.case_id,
            "corpus_hash": case.corpus_hash,
            "parser": PARSER_VERSION,
            "market": case.market_hint,
        }
    )
    cache_path = repository.root / "heldout-document-cache" / f"{key}.json"
    if cache_path.is_file():
        pointer = json.loads(cache_path.read_text(encoding="utf-8"))
        environment = repository.cas.get(str(pointer["digest"]))
        if not isinstance(environment, dict):
            raise RuntimeError("cached held-out environment is not an object")
        for source in environment.get("documents", {}).values():
            repository.blob_path(str(source["raw_blob_id"]))
        if environment.get("heldout", {}).get("corpus_hash") != case.corpus_hash:
            raise RuntimeError("cached held-out environment corpus hash mismatch")
        return cast(Json, environment)
    environment = build_frozen_environment(repository, bundle_root=bundle_root, case=case)
    digest = repository.cas.put(environment).digest
    atomic_bytes(cache_path, json.dumps({"digest": digest}, sort_keys=True).encode())
    return environment


def run_v2_heldout_case(
    project_root: Path,
    runtime_root: Path,
    bundle_root: Path,
    case: HeldOutRuntimeCase,
    *,
    candidate_key: str = "v2-current",
) -> tuple[Json, CandidateResultRef]:
    """Run one sealed case through the real current V2 runtime from frozen bytes only."""

    service = build_service(project_root.resolve(), runtime_root.resolve())
    environment = load_or_build_frozen_environment(
        service.repository,
        bundle_root=bundle_root,
        case=case,
    )
    service.prepare = lambda _request, _run_id, _check: environment
    request = ResearchRequest(
        company_query=case.company_query,
        market_hint=case.market_hint,
        requested_period_label=case.requested_period_label,
        research_question=case.research_question,
        research_time=datetime.fromisoformat(case.research_time),
        idempotency_key=f"heldout-{case.case_id}-{uuid.uuid4().hex}",
    )
    manifest, _created = service.submit(request)
    run_id = str(manifest["run_id"])
    final = service.execute(run_id)
    if final["lifecycle_state"] != "succeeded":
        failure_value = final.get("failure")
        failure: Json = failure_value if isinstance(failure_value, dict) else {}
        raise HeldOutCaseFailure(
            str(final["lifecycle_state"]),
            str(failure.get("code") or "UNKNOWN_PRODUCT_FAILURE"),
            str(failure.get("message") or ""),
        )
    result = cast(Json, service.repository.artifact(run_id, "result"))
    result_dir = runtime_root.resolve() / "heldout-results"
    result_dir.mkdir(parents=True, exist_ok=True)
    result_path = result_dir / f"{case.case_id}-{run_id}.json"
    atomic_bytes(
        result_path,
        (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )
    return final, CandidateResultRef(
        case_id=case.case_id,
        candidate_key=candidate_key,
        run_id=run_id,
        result_path=str(result_path),
    )
