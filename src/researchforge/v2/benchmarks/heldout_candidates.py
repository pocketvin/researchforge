"""Build a private held-out candidate bundle from unseen official SEC annual filings.

This module never creates gold answers. It freezes source bytes and research questions only. The
selection seed, issuer identities and questions live exclusively in the ignored private bundle.
Development exposure is checked at issuer, exact-question and source-byte level before a candidate
can enter the bundle.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from researchforge.adapters.storage import payload_sha256
from researchforge.ingestion.source_security import validate_official_https
from researchforge.v2.benchmarks.exposure import DevelopmentExposureSnapshot
from researchforge.v2.benchmarks.heldout import (
    HeldOutBundleManifest,
    HeldOutDocument,
    HeldOutRuntimeCase,
    development_question_hash,
)
from researchforge.v2.storage import atomic_bytes

SEC_HOSTS = {"www.sec.gov", "data.sec.gov"}
CANDIDATE_BUILDER_VERSION = "sec-heldout-v1"
MIN_FILING_BYTES = 250_000
MAX_FILING_BYTES = 32 * 1024 * 1024
MAX_DISCOVERY_ATTEMPTS = 80

JsonObject = dict[str, Any]
JsonFetcher = Callable[[str], JsonObject]
BytesFetcher = Callable[[str], bytes]


@dataclass(frozen=True, slots=True)
class SecCompany:
    cik: int
    ticker: str
    legal_name: str


@dataclass(frozen=True, slots=True)
class FrozenSecFiling:
    company: SecCompany
    accession: str
    primary_document: str
    accepted_at: str
    report_date: str
    source_uri: str
    payload: bytes
    content_hash: str


QUESTION_VARIANTS: dict[str, tuple[str, ...]] = {
    "direct_extraction": (
        "For {company}'s annual period ending {period_end}, what revenue or net sales amount does "
        "the filing report? State the exact value, unit and period, and cite the filing evidence.",
        "Using only {company}'s annual filing for the period ending {period_end}, what total "
        "revenue "
        "or net sales was reported? Give the exact amount and unit with source evidence.",
    ),
    "numerical_analysis": (
        "For {company}'s annual period ending {period_end}, compare operating cash flow with net "
        "income. Use deterministic calculation only after both source values are verified, then "
        "explain what the relationship does and does not support.",
        "Using only {company}'s annual filing for the period ending {period_end}, assess "
        "earnings-to-"
        "cash conversion from verified net income and operating cash flow. Calculate only from "
        "source-linked values and preserve any limitation.",
    ),
    "analytical_explanation": (
        "According to {company}'s annual filing for the period ending {period_end}, what filing-"
        "grounded factors explain the main year-over-year changes in revenue and operating "
        "performance? Separate disclosed facts from inference and note material uncertainty.",
        "What does {company}'s annual filing for the period ending {period_end} identify as "
        "the main "
        "drivers of its year-over-year operating performance? Ground each material explanation in "
        "the filing and distinguish management statements from your inference.",
    ),
    "evidence_limited": (
        "Can {company}'s annual filing for the period ending {period_end}, by itself, establish "
        "that "
        "the company is more capital-intensive than industry peers? Quantify what the filing can "
        "support and state clearly what cannot be determined without external peer evidence.",
        "Using only {company}'s annual filing for the period ending {period_end}, determine "
        "what can "
        "be said about its absolute capital requirements and whether the filing alone supports an "
        "industry-relative capital-intensity classification. Do not invent peer thresholds.",
    ),
}

STRATUM_ASSIGNMENT: tuple[tuple[str, str], ...] = (
    ("direct_extraction", "analytical_explanation"),
    ("numerical_analysis", "evidence_limited"),
    ("direct_extraction", "numerical_analysis"),
    ("analytical_explanation", "evidence_limited"),
)


def _normalize_company(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.casefold())


def _sec_url_bytes(url: str, *, user_agent: str, accept: str, limit: int) -> bytes:
    validate_official_https(url, allowed_hosts=SEC_HOSTS, provider="SEC", stage="heldout_candidate")
    request = Request(url, headers={"User-Agent": user_agent, "Accept": accept})
    try:
        with urlopen(request, timeout=30) as response:
            validate_official_https(
                response.geturl(),
                allowed_hosts=SEC_HOSTS,
                provider="SEC",
                stage="heldout_candidate",
            )
            payload = cast(bytes, response.read(limit + 1))
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"SEC held-out candidate fetch failed ({type(exc).__name__})") from exc
    if len(payload) > limit:
        raise RuntimeError("SEC held-out candidate response exceeds the bounded size")
    return payload


def sec_json_fetcher(user_agent: str) -> JsonFetcher:
    def fetch(url: str) -> JsonObject:
        payload = _sec_url_bytes(
            url,
            user_agent=user_agent,
            accept="application/json",
            limit=8 * 1024 * 1024,
        )
        value = json.loads(payload)
        if not isinstance(value, dict):
            raise RuntimeError("SEC JSON response is not an object")
        time.sleep(0.12)
        return value

    return fetch


def sec_bytes_fetcher(user_agent: str) -> BytesFetcher:
    def fetch(url: str) -> bytes:
        payload = _sec_url_bytes(
            url,
            user_agent=user_agent,
            accept="text/html,application/xhtml+xml,*/*",
            limit=MAX_FILING_BYTES,
        )
        time.sleep(0.12)
        return payload

    return fetch


def _ticker_universe(payload: JsonObject) -> list[SecCompany]:
    companies: dict[int, SecCompany] = {}
    for raw in payload.values():
        if not isinstance(raw, dict):
            continue
        cik = raw.get("cik_str")
        ticker = raw.get("ticker")
        title = raw.get("title")
        if not isinstance(cik, int) or not isinstance(ticker, str) or not isinstance(title, str):
            continue
        if not ticker.strip() or not title.strip():
            continue
        companies.setdefault(
            cik, SecCompany(cik=cik, ticker=ticker.strip(), legal_name=title.strip())
        )
    return sorted(companies.values(), key=lambda item: (item.cik, item.ticker, item.legal_name))


def _recent_10k(company: SecCompany, submissions: JsonObject) -> tuple[str, str, str, str] | None:
    filings = submissions.get("filings")
    recent = filings.get("recent") if isinstance(filings, dict) else None
    if not isinstance(recent, dict):
        return None
    forms = recent.get("form")
    accessions = recent.get("accessionNumber")
    primary_documents = recent.get("primaryDocument")
    accepted = recent.get("acceptanceDateTime")
    filing_dates = recent.get("filingDate")
    report_dates = recent.get("reportDate")
    if not isinstance(forms, list):
        return None
    if not isinstance(accessions, list) or not isinstance(primary_documents, list):
        return None
    if not isinstance(filing_dates, list) or not isinstance(report_dates, list):
        return None
    forms_list = forms
    accessions_list = accessions
    primary_documents_list = primary_documents
    filing_dates_list = filing_dates
    report_dates_list = report_dates
    accepted_values = accepted if isinstance(accepted, list) else []
    for index, form in enumerate(forms_list):
        if form != "10-K":
            continue
        try:
            accession = str(accessions_list[index])
            primary = str(primary_documents_list[index])
            filing_date = str(filing_dates_list[index])
            report_date = str(report_dates_list[index])
        except IndexError:
            return None
        if not primary.casefold().endswith((".htm", ".html")):
            continue
        accepted_at = (
            str(accepted_values[index])
            if index < len(accepted_values) and accepted_values[index]
            else filing_date + "T23:59:59+00:00"
        )
        return accession, primary, accepted_at, report_date
    return None


def _filing_url(company: SecCompany, accession: str, primary_document: str) -> str:
    compact = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{company.cik}/{compact}/{primary_document}"


def _eligible_filing(payload: bytes) -> bool:
    if len(payload) < MIN_FILING_BYTES or len(payload) > MAX_FILING_BYTES:
        return False
    sample = payload.lower()
    if b"<html" not in sample and b"<!doctype html" not in sample:
        return False
    statement_signals = sum(
        signal in sample
        for signal in (
            b"cash flows",
            b"balance sheets",
            b"statements of operations",
            b"statements of income",
            b"statements of earnings",
        )
    )
    revenue_signal = b"revenue" in sample or b"net sales" in sample
    return statement_signals >= 2 and revenue_signal


def _parse_accepted(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _freeze_candidate(
    company: SecCompany,
    submissions: JsonObject,
    *,
    bytes_fetch: BytesFetcher,
    exposed_documents: set[str],
) -> FrozenSecFiling | None:
    recent = _recent_10k(company, submissions)
    if recent is None:
        return None
    accession, primary, accepted_at, report_date = recent
    source_uri = _filing_url(company, accession, primary)
    payload = bytes_fetch(source_uri)
    if not _eligible_filing(payload):
        return None
    content_hash = hashlib.sha256(payload).hexdigest()
    if content_hash in exposed_documents:
        return None
    return FrozenSecFiling(
        company=company,
        accession=accession,
        primary_document=primary,
        accepted_at=accepted_at,
        report_date=report_date,
        source_uri=source_uri,
        payload=payload,
        content_hash=content_hash,
    )


def select_unseen_sec_filings(
    exposure: DevelopmentExposureSnapshot,
    *,
    ticker_payload: JsonObject,
    json_fetch: JsonFetcher,
    bytes_fetch: BytesFetcher,
    seed: str,
    issuer_count: int = 4,
    max_attempts: int = MAX_DISCOVERY_ATTEMPTS,
) -> list[FrozenSecFiling]:
    """Choose eligible SEC issuers without revealing the selected identities outside the caller."""

    if issuer_count < 4:
        raise ValueError("held-out candidate selection requires at least four issuer groups")
    excluded = {_normalize_company(value) for value in exposure.company_aliases}
    candidates = [
        item
        for item in _ticker_universe(ticker_payload)
        if _normalize_company(item.legal_name) not in excluded
    ]
    random.Random(seed).shuffle(candidates)
    selected: list[FrozenSecFiling] = []
    for company in candidates[:max_attempts]:
        submissions_url = f"https://data.sec.gov/submissions/CIK{company.cik:010d}.json"
        try:
            submissions = json_fetch(submissions_url)
            filing = _freeze_candidate(
                company,
                submissions,
                bytes_fetch=bytes_fetch,
                exposed_documents=set(exposure.document_hashes),
            )
        except RuntimeError:
            continue
        if filing is None:
            continue
        selected.append(filing)
        if len(selected) == issuer_count:
            return selected
    raise RuntimeError(
        "could not find enough unseen eligible SEC annual filings within the bounded search"
    )


def _question_for(
    filing: FrozenSecFiling,
    stratum: str,
    *,
    rng: random.Random,
    exposed_questions: set[str],
) -> str:
    variants = list(QUESTION_VARIANTS[stratum])
    rng.shuffle(variants)
    for template in variants:
        question = template.format(
            company=filing.company.legal_name,
            period_end=filing.report_date,
        )
        if development_question_hash(question) not in exposed_questions:
            return question
    raise RuntimeError("all generated held-out question variants overlap development exposure")


def build_private_heldout_bundle(
    output_dir: Path,
    exposure: DevelopmentExposureSnapshot,
    filings: list[FrozenSecFiling],
    *,
    seed: str,
    review_mode: str = "meets_standard",
) -> HeldOutBundleManifest:
    """Write eight source-only held-out cases without answers, labels or model output."""

    if len(filings) != 4:
        raise ValueError("default held-out bundle requires exactly four frozen issuers")
    if review_mode not in {"meets_standard", "pairwise_preference"}:
        raise ValueError("unsupported held-out review mode")
    output_dir = output_dir.resolve()
    sources = output_dir / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed + ":questions")
    cases: list[HeldOutRuntimeCase] = []
    for issuer_index, filing in enumerate(filings):
        document_id = f"doc_{filing.content_hash[:20]}"
        relative_path = f"sources/source-{issuer_index + 1:02d}.html"
        atomic_bytes(output_dir / relative_path, filing.payload)
        accepted = _parse_accepted(filing.accepted_at)
        report_year = int(filing.report_date[:4])
        document = HeldOutDocument(
            document_id=document_id,
            title=f"Frozen SEC annual filing {issuer_index + 1}",
            relative_path=relative_path,
            content_hash=filing.content_hash,
            source_uri=filing.source_uri,
            published_at=accepted.isoformat(),
            document_type="annual_report",
            reporting_period={
                "period_start": f"{report_year}-01-01",
                "period_end": filing.report_date,
                "fiscal_year": report_year,
                "fiscal_period": "FY",
                "period_basis": "ytd",
                "accounting_standard": "US_GAAP",
                "statement_scope": "consolidated",
                "restatement_status": "as_reported",
            },
        )
        company_group_key = (
            "issuer-" + hashlib.sha256(f"{seed}:{filing.company.cik}".encode()).hexdigest()[:16]
        )
        for stratum in STRATUM_ASSIGNMENT[issuer_index]:
            question = _question_for(
                filing,
                stratum,
                rng=rng,
                exposed_questions=set(exposure.question_hashes),
            )
            case_id = (
                "heldout-"
                + hashlib.sha256(f"{seed}:{filing.company.cik}:{stratum}".encode()).hexdigest()[:20]
            )
            cases.append(
                HeldOutRuntimeCase(
                    case_id=case_id,
                    stratum=stratum,
                    company_group_key=company_group_key,
                    company_query=filing.company.legal_name,
                    company_id=f"sec_{filing.company.cik:010d}",
                    market_hint="US",
                    requested_period_label=f"{report_year}FY",
                    research_question=question,
                    research_time=(accepted + timedelta(hours=1)).isoformat(),
                    corpus_hash=payload_sha256([filing.content_hash]),
                    documents=[document],
                )
            )
    suite_id = "heldout-" + hashlib.sha256(f"{seed}:suite".encode()).hexdigest()[:16]
    manifest = HeldOutBundleManifest(
        suite_id=suite_id,
        created_at=datetime.now(UTC),
        review_mode=review_mode,  # type: ignore[arg-type]
        case_ids=[case.case_id for case in cases],
    )
    atomic_bytes(
        output_dir / "runtime-cases.jsonl",
        "".join(case.model_dump_json() + "\n" for case in cases).encode("utf-8"),
    )
    atomic_bytes(
        output_dir / "bundle-manifest.json",
        (manifest.model_dump_json(indent=2) + "\n").encode("utf-8"),
    )
    atomic_bytes(
        output_dir / "development-exposures.json",
        (exposure.model_dump_json(indent=2) + "\n").encode("utf-8"),
    )
    selection_metadata = {
        "builder_version": CANDIDATE_BUILDER_VERSION,
        "seed": seed,
        "seed_hash": hashlib.sha256(seed.encode()).hexdigest(),
        "source_provider": "SEC",
        "issuer_count": len(filings),
        "case_count": len(cases),
        "reference_labels_created": False,
        "product_model_called": False,
    }
    atomic_bytes(
        output_dir / "selection-metadata.json",
        (json.dumps(selection_metadata, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    return manifest


def new_private_seed() -> str:
    return secrets.token_hex(16)
