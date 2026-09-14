# ruff: noqa: RUF001 -- Chinese product copy intentionally uses Chinese punctuation.
"""Official filing acquisition and reusable complete-document packages for V2."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Any, cast
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from researchforge.adapters.storage import canonical_json_bytes, payload_sha256
from researchforge.file_lock import exclusive_file_lock
from researchforge.ingestion.discovery import DiscoveredFiling, OfficialDisclosureDiscovery
from researchforge.ingestion.errors import IngestionAbstention
from researchforge.ingestion.extraction import (
    METRIC_DEFINITIONS,
    DeterministicFinancialFactExtractor,
)
from researchforge.ingestion.hk_ifrs import HkIfrsExtractor
from researchforge.ingestion.sec_xbrl import DURATION_METRICS, TAG_ALIASES
from researchforge.v2.contracts import Json, ResearchRequest
from researchforge.v2.documents import _id, _object, parse_html, parse_pdf
from researchforge.v2.storage import ResearchRepository, atomic_bytes, now

HOSTS = frozenset(
    {
        ("static.cninfo.com.cn"),
        ("www.cninfo.com.cn"),
        ("www.sec.gov"),
        ("data.sec.gov"),
        ("www1.hkexnews.hk"),
    }
)
PARSER_VERSION = "v2-native-1"
MAX_SOURCE_BYTES = 64 * 1024 * 1024


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in {None, 443}
    ):
        raise IngestionAbstention(
            "UNTRUSTED_SOURCE_URI", "acquisition", "仅允许本项目已核验的官方财报域名和 HTTPS。"
        )


class OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> Any:
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_official(url: str, check: Callable[[], None]) -> bytes:
    validate_url(url)
    check()
    user_agent = os.getenv(
        "RESEARCHFORGE_SEC_USER_AGENT", "ResearchForge/2.0 researchforge@example.com"
    )
    opener = build_opener(OfficialRedirects())
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/pdf,application/json,text/html,*/*",
        },
    )
    data = bytearray()
    with opener.open(request, timeout=30) as response:
        validate_url(response.geturl())
        while block := response.read(256 * 1024):
            check()
            data.extend(block)
            if len(data) > MAX_SOURCE_BYTES:
                raise IngestionAbstention(
                    "DISCLOSURE_SIZE_INVALID",
                    "acquisition",
                    "官方文件超过单份 64 MiB 的运行保护边界。",
                )
    if not data:
        raise IngestionAbstention("DISCLOSURE_SIZE_INVALID", "acquisition", "官方文件为空。")
    return bytes(data)


def _fact(
    source: Json,
    metric: str,
    value: Decimal,
    currency: str,
    period: Json,
    *,
    page: int | None,
    label: str,
    statement: str,
    text: str,
) -> Json:
    doc_id = source["document_id"]
    identifier = _id("fact", doc_id, metric)
    fact_period = dict(period)
    if metric in {"accounts_receivable", "inventory"}:
        fact_period["period_basis"] = "instant"
        fact_period["period_start"] = None
    return {
        "fact_id": identifier,
        "artifact_id": identifier,
        "kind": "fact",
        "schema_version": "2.0.0",
        "document_id": doc_id,
        "metric_code": metric,
        "value": format(value, "f"),
        "currency": currency,
        "measurement_unit": "CURRENCY",
        "canonical_scale": 1,
        "period": fact_period,
        "company": source["company"],
        "fact_kind": "reported",
        "status": "verified_native_extraction",
        "text": text,
        "source": {
            "document_id": doc_id,
            "uri": source["source_uri"],
            "published_at": source["published_at"],
            "content_hash": source["content_hash"],
        },
        "source_locator": {
            "page": page,
            "page_id": _id("page", doc_id, page) if page is not None else None,
            "table_id": None,
            "cell_id": None,
            "row_label": label,
            "statement": statement,
        },
    }


def extract_pdf_facts(
    source: Json, pages: tuple[str, ...], market: str
) -> tuple[dict[str, Json], list[str]]:
    facts: dict[str, Json] = {}
    gaps: list[str] = []
    period = source["reporting_period"]
    if market == "HK":
        try:
            cells = HkIfrsExtractor().extract(pages)
            for cell in cells:
                fact = _fact(
                    source,
                    cell.metric_code,
                    cell.normalized_value,
                    cell.currency,
                    period,
                    page=cell.page,
                    label=cell.row_label,
                    statement=cell.statement,
                    text=cell.raw_line,
                )
                facts[fact["fact_id"]] = fact
        except IngestionAbstention as exc:
            gaps.append(f"港股规范财务事实未完整恢复：{exc.code}；页面和表格仍然可查。")
        return facts, gaps
    if market != "CN" or period.get("statement_scope") != "consolidated":
        return {}, ["本文件暂不支持规范数字提取，不能自动将表格候选作为财务事实。"]
    extractor = DeterministicFinancialFactExtractor()
    lines = extractor._statement_lines(pages, period)
    # Keep the V1 extractor/semantics. V2 changes failure granularity and never
    # invents missing metrics.
    for definition in METRIC_DEFINITIONS:
        try:
            cn_cell = extractor._extract_metric(definition, lines, pages)
            fact = _fact(
                source,
                cn_cell.metric_code,
                cn_cell.normalized_value,
                "CNY",
                period,
                page=cn_cell.page,
                label=cn_cell.row_label,
                statement=cn_cell.statement,
                text=cn_cell.evidence_text,
            )
            facts[fact["fact_id"]] = fact
        except IngestionAbstention as exc:
            gaps.append(f"{definition.metric_code}: {exc.code}，未生成该项规范财务事实。")
    return facts, gaps


def extract_sec_facts(
    source: Json, filing: DiscoveredFiling, payload: bytes
) -> tuple[dict[str, Json], list[str]]:
    decoded = json.loads(payload, parse_float=Decimal)
    gaap = decoded.get("facts", {}).get("us-gaap", {})
    accession = filing.filing_id.removeprefix("sec-")
    report_end = filing.reporting_period["period_end"]
    facts: dict[str, Json] = {}
    gaps: list[str] = []
    for metric, aliases in TAG_ALIASES.items():
        selected: tuple[str, Json, str] | None = None
        for tag in aliases:
            concept = gaap.get(tag, {})
            rows = [
                row
                for row in concept.get("units", {}).get("USD", [])
                if row.get("accn") == accession and row.get("end") == report_end
            ]
            if metric in DURATION_METRICS:
                rows = [row for row in rows if row.get("start")]
                if rows:
                    start = min(row["start"] for row in rows)
                    rows = [row for row in rows if row["start"] == start]
            else:
                rows = [row for row in rows if not row.get("start")]
            values = {
                str(row[("val")]) for row in rows if isinstance(row.get("val"), (int, Decimal))
            }
            if len(values) == 1:
                selected = (tag, rows[0], concept.get("label", tag))
                break
        if selected is None:
            gaps.append(f"{metric}: 没有同一 accession、日期和币种下唯一的 SEC XBRL 数值。")
            continue
        tag, row, label = selected
        period = dict(filing.reporting_period)
        period["period_start"] = row.get("start")
        period["period_basis"] = "ytd" if row.get("start") else "instant"
        value = Decimal(str(row["val"]))
        fact = _fact(
            source,
            metric,
            value,
            "USD",
            period,
            page=None,
            label=label,
            statement=f"us-gaap:{tag}",
            text=f"SEC {accession} {tag}: {value} USD; {row.get('start', '')} — {row['end']}",
        )
        fact["source"]["xbrl_blob_hash"] = hashlib.sha256(payload).hexdigest()
        fact["source"]["accession"] = accession
        facts[fact["fact_id"]] = fact
    return facts, gaps


def bind_fact_cells(facts: dict[str, Json], objects: dict[str, Json]) -> None:
    """Link only a uniquely matching row and amount; ambiguous links remain
    explicitly absent."""
    for fact in facts.values():
        locator = fact["source_locator"]
        label = re.sub(r"\s+", "", locator["row_label"])
        matches: list[tuple[str, str]] = []
        for table in objects.values():
            if table["kind"] != "table" or table.get("page_number") != locator["page"]:
                continue
            for row in table["rows"]:
                row_text = "".join(str(cell.get("text") or "") for cell in row)
                if label not in re.sub(r"\s+", "", row_text):
                    continue
                for cell in row:
                    raw = str(cell.get("text") or "").strip().replace(",", "")
                    try:
                        numeric = Decimal(raw)
                    except Exception:
                        continue
                    # Base-unit equality only; never infer a missing table scale.
                    if numeric == Decimal(fact["value"]):
                        matches.append((table["artifact_id"], cell["cell_id"]))
        if len(matches) == 1:
            locator["table_id"], locator["cell_id"] = matches[0]


class FilingPreparer:
    def __init__(self, repository: ResearchRepository) -> None:
        self.repository = repository
        self.discovery = OfficialDisclosureDiscovery()

    @staticmethod
    def _identity_token(value: str) -> str:
        return re.sub(r"\s+", "", value).casefold()

    def _cached_package(
        self,
        request: ResearchRequest,
        *,
        period_label: str | None,
        expected_company_id: str | None,
    ) -> Json | None:
        cache_dir = self.repository.root / "document-cache"
        target_period = period_label or request.requested_period_label
        query = self._identity_token(request.company_query)
        matches: dict[tuple[str, str, str], Json] = {}
        for path in cache_dir.glob("*.json"):
            try:
                package = cast(
                    Json, self.repository.cas.get(json.loads(path.read_text())["digest"])
                )
                if package.get("parser_version") != PARSER_VERSION:
                    continue
                entity = cast(Json, package["entity"])
                company_id = str(entity.get("company_id", ""))
                if expected_company_id is not None:
                    if company_id != expected_company_id:
                        continue
                else:
                    names = {
                        self._identity_token(str(entity.get(key, "")))
                        for key in ("company_id", "legal_name", "ticker")
                        if entity.get(key)
                    }
                    if query not in names:
                        continue
                if request.market_hint and entity.get("country_code") != request.market_hint:
                    continue
                documents = list(package.get("documents", {}).values())
                if len(documents) != 1:
                    continue
                document = cast(Json, documents[0])
                if target_period and document.get("period_label") != target_period:
                    continue
                if datetime.fromisoformat(str(document["published_at"])) > request.research_time:
                    continue
                self.repository.blob_path(str(document["raw_blob_id"]))
                identity = (
                    company_id,
                    str(document.get("period_label", "")),
                    str(document.get("content_hash", "")),
                )
                matches[identity] = package
            except (KeyError, TypeError, ValueError, RuntimeError, json.JSONDecodeError):
                continue
        if len(matches) != 1:
            return None
        return next(iter(matches.values()))

    def prepare(
        self,
        request: ResearchRequest,
        run_id: str,
        check: Callable[[], None],
        *,
        period_label: str | None = None,
        expected_company_id: str | None = None,
    ) -> Json:
        try:
            with self.repository.span(run_id, "discovery", "确认公司并定位官方财报"):
                check()
                filing = self.discovery.discover(
                    request.company_query,
                    period_label=period_label or request.requested_period_label,
                    research_time=request.research_time,
                    market_hint=request.market_hint,
                )
                check()
                if expected_company_id and filing.company.company_id != expected_company_id:
                    raise ValueError("additional filing resolved to a different company")
                if datetime.fromisoformat(filing.published_at) > request.research_time:
                    raise ValueError("filing exceeds research cutoff")
        except IngestionAbstention as exc:
            if exc.code != "DISCLOSURE_PROVIDER_UNAVAILABLE":
                raise
            package = self._cached_package(
                request, period_label=period_label, expected_company_id=expected_company_id
            )
            if package is None:
                raise
            self.repository.emit(
                run_id,
                "source_loaded",
                "verified_cache_fallback",
                "官方发现服务暂时不可用，复用唯一匹配的已校验财报缓存",
                "succeeded",
                data={
                    "document_ids": list(package["documents"]),
                    "fallback_reason": exc.code,
                    "cache_is_new_source_discovery": False,
                },
            )
            return package
        key = payload_sha256(
            {
                "filing": filing.filing_id,
                "source": filing.source_uri,
                "period": filing.reporting_period,
                "company": filing.company.company_id,
                "parser": PARSER_VERSION,
            }
        )
        cache_path = self.repository.root / "document-cache" / f"{key}.json"
        with exclusive_file_lock(self.repository.root / "locks" / f"document-{key}.lock"):
            if cache_path.is_file():
                package = cast(
                    Json, self.repository.cas.get(json.loads(cache_path.read_text())["digest"])
                )
                for source in package["documents"].values():
                    self.repository.blob_path(source["raw_blob_id"])
                self.repository.emit(
                    run_id,
                    "source_loaded",
                    "document_cache",
                    "复用已校验的原始财报与索引",
                    "succeeded",
                    data={"document_ids": list(package["documents"])},
                )
                return package
            with self.repository.span(run_id, "acquisition", "下载并固定财报原始文件"):
                payload = fetch_official(filing.source_uri, check)
                is_pdf = payload.startswith(b"%PDF-")
                if not is_pdf and filing.company.market != "US":
                    raise ValueError("official PDF source did not return PDF bytes")
                raw_blob_id = self.repository.put_blob(payload, "pdf" if is_pdf else "html")
                digest = hashlib.sha256(payload).hexdigest()
                doc_id = (
                    "doc_"
                    + payload_sha256(
                        {
                            "raw": digest,
                            "filing": filing.filing_id,
                            "company": filing.company.company_id,
                        }
                    )[:24]
                )
                source = {
                    "document_id": doc_id,
                    "title": filing.title,
                    "source_uri": filing.source_uri,
                    "document_type": filing.document_type,
                    "published_at": filing.published_at,
                    "retrieved_at": now(),
                    "content_hash": digest,
                    "raw_blob_id": raw_blob_id,
                    "reporting_period": filing.reporting_period,
                    "period_label": filing.period_label,
                    "company": filing.company.artifact_value(),
                    "mime_type": "application/pdf" if is_pdf else "text/html",
                    "parser_version": PARSER_VERSION,
                    "data_namespace": "product",
                }
            prior = self.repository.get(run_id)
            acquired = (
                self.repository.artifact(run_id, "acquired_sources")
                if "acquired_sources" in prior["artifacts"]
                else {}
            )
            acquired[doc_id] = source
            self.repository.attach(run_id, "acquired_sources", acquired)
            with self.repository.span(run_id, "document_parse", "建立页面、表格与全文索引") as span:

                def progress(done: int, total: int) -> None:
                    self.repository.emit(
                        run_id,
                        "parse_progress",
                        "document_parse",
                        f"已处理 {done} / {total} 页",
                        "running",
                        parent_span_id=span,
                        data={
                            ("pages_processed"): done,
                            ("pages_total"): total,
                            ("document_id"): doc_id,
                        },
                    )

                objects, pages, gaps = (
                    parse_pdf(payload, source, check=check, progress=progress)
                    if is_pdf
                    else parse_html(payload, source)
                )
                objects[doc_id] = _object(
                    "document",
                    doc_id,
                    source,
                    "\n\f\n".join(pages),
                    title=filing.title,
                    raw_blob_id=raw_blob_id,
                    page_number=None,
                )
                source["page_count"] = len(pages) if is_pdf else None
                source["text_block_count"] = len(pages)
                source["table_count"] = sum(item["kind"] == "table" for item in objects.values())
            with self.repository.span(run_id, "fact_extraction", "核验财务数字与口径"):
                check()
                if filing.company.market == "US":
                    cik = filing.company.provider_company_id
                    xbrl = fetch_official(
                        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", check
                    )
                    facts, fact_gaps = extract_sec_facts(source, filing, xbrl)
                else:
                    facts, fact_gaps = extract_pdf_facts(source, pages, filing.company.market)
                bind_fact_cells(facts, objects)
                for fact in facts.values():
                    evidence_id = fact["fact_id"].replace("fact_", "evfact_", 1)
                    objects[evidence_id] = _object(
                        "evidence",
                        evidence_id,
                        source,
                        fact["text"],
                        page_id=fact["source_locator"]["page_id"],
                        page_number=fact["source_locator"]["page"],
                        fact_id=fact["fact_id"],
                    )
                    fact["evidence_id"] = evidence_id
            package = {
                "schema_version": "2.0.0",
                "entity": filing.company.artifact_value(),
                "documents": {doc_id: source},
                "objects": objects,
                "facts": facts,
                "gaps": gaps + fact_gaps,
                "parser_version": PARSER_VERSION,
            }
            cache_digest = self.repository.cas.put(package).digest
            atomic_bytes(cache_path, canonical_json_bytes({"digest": cache_digest}))
            return package
