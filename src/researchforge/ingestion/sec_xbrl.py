"""Deterministic SEC XBRL ingestion for the six ResearchForge financial metrics."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from researchforge.ingestion.discovery import DiscoveredFiling
from researchforge.ingestion.errors import IngestionAbstention
from researchforge.ingestion.source_security import validate_official_https
from researchforge.retrieval.fulltext import index_html

JsonObject = dict[str, Any]


def _sec_headers() -> dict[str, str]:
    user_agent = os.getenv(
        "RESEARCHFORGE_SEC_USER_AGENT",
        "ResearchForge/1.7.3 researchforge@example.com",
    )
    return {"User-Agent": user_agent, "Accept": "application/json,text/html,*/*"}


DURATION_METRICS = frozenset({"revenue", "operating_cost", "net_income", "operating_cash_flow"})
TAG_ALIASES: dict[str, tuple[str, ...]] = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ),
    "operating_cost": (
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization",
    ),
}
TAG_ALIASES.update(
    {
        "net_income": ("NetIncomeLoss",),
        "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
        "accounts_receivable": ("AccountsReceivableNetCurrent", "AccountsReceivableNet"),
        "inventory": ("InventoryNet",),
    }
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


def _pretty_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fetch(url: str) -> bytes:
    allowed_hosts = {"www.sec.gov", "data.sec.gov"}
    validate_official_https(url, allowed_hosts=allowed_hosts, provider="SEC", stage="acquisition")
    request = Request(url, headers=_sec_headers())
    try:
        with urlopen(request, timeout=30) as response:
            validate_official_https(
                response.geturl(),
                allowed_hosts=allowed_hosts,
                provider="SEC",
                stage="acquisition",
            )
            return cast(bytes, response.read())
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise IngestionAbstention(
            "DISCLOSURE_PROVIDER_UNAVAILABLE",
            "acquisition",
            f"SEC filing acquisition failed safely ({type(exc).__name__}).",
        ) from exc


@dataclass(frozen=True, slots=True)
class SelectedXbrlFact:
    metric_code: str
    tag: str
    label: str
    entry: JsonObject


class SecXbrlProductIngestion:
    """Materialize one official SEC filing as a normal ResearchForge product package."""

    def run(self, filing: DiscoveredFiling, *, package_root: Path) -> JsonObject:
        accession = filing.filing_id.removeprefix("sec-")
        cik = filing.company.provider_company_id
        facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        companyfacts_bytes = _fetch(facts_url)
        companyfacts = cast(JsonObject, json.loads(companyfacts_bytes))
        source_bytes = _fetch(filing.source_uri)
        selected = self._select_facts(companyfacts, accession, filing)
        period = self._resolved_period(filing, selected)
        retrieved_at = datetime.now(UTC).isoformat()
        artifacts = self._artifacts(
            filing,
            selected,
            period=period,
            source_hash=_sha256(source_bytes),
            source_bytes=source_bytes,
            retrieved_at=retrieved_at,
        )
        artifact_hashes = {
            path: _sha256(_pretty_bytes(payload)) for path, payload in artifacts.items()
        }
        package_hash = _sha256(_canonical_bytes(artifact_hashes))
        ingestion = self._ingestion_manifest(
            filing,
            period,
            selected,
            package_hash,
            facts_hash=_sha256(companyfacts_bytes),
            source_hash=_sha256(source_bytes),
            retrieved_at=retrieved_at,
        )
        package_manifest = self._package_manifest(filing, artifacts, artifact_hashes, package_hash)
        self._write(package_root, artifacts, ingestion, package_manifest)
        return ingestion

    def _select_facts(
        self,
        companyfacts: JsonObject,
        accession: str,
        filing: DiscoveredFiling,
    ) -> tuple[SelectedXbrlFact, ...]:
        facts = cast(JsonObject, companyfacts.get("facts", {}))
        us_gaap = cast(JsonObject, facts.get("us-gaap", {}))
        report_end = str(filing.reporting_period["period_end"])
        selected: list[SelectedXbrlFact] = []
        for metric, aliases in TAG_ALIASES.items():
            match = self._select_metric(
                us_gaap,
                metric=metric,
                aliases=aliases,
                accession=accession,
                report_end=report_end,
            )
            if match is None:
                raise IngestionAbstention(
                    "SEC_XBRL_METRIC_MISSING",
                    "normalization",
                    f"SEC XBRL has no unambiguous {metric} fact for {accession}.",
                )
            selected.append(match)
        return tuple(selected)

    @staticmethod
    def _select_metric(
        us_gaap: JsonObject,
        *,
        metric: str,
        aliases: tuple[str, ...],
        accession: str,
        report_end: str,
    ) -> SelectedXbrlFact | None:
        for tag in aliases:
            concept = cast(JsonObject, us_gaap.get(tag, {}))
            units = cast(JsonObject, concept.get("units", {}))
            rows = [
                row
                for row in cast(list[JsonObject], units.get("USD", []))
                if row.get("accn") == accession and row.get("end") == report_end
            ]
            if not rows:
                continue
            if metric in DURATION_METRICS:
                rows = [row for row in rows if isinstance(row.get("start"), str)]
                if not rows:
                    continue
                chosen = min(rows, key=lambda row: str(row["start"]))
            else:
                rows = [row for row in rows if row.get("start") is None]
                if not rows:
                    continue
                chosen = rows[-1]
            if not isinstance(chosen.get("val"), (int, float)):
                continue
            return SelectedXbrlFact(
                metric_code=metric,
                tag=tag,
                label=str(concept.get("label") or tag),
                entry=chosen,
            )
        return None

    @staticmethod
    def _resolved_period(
        filing: DiscoveredFiling,
        selected: tuple[SelectedXbrlFact, ...],
    ) -> JsonObject:
        duration_starts = [
            str(item.entry["start"])
            for item in selected
            if item.metric_code in DURATION_METRICS and item.entry.get("start")
        ]
        period = dict(filing.reporting_period)
        if duration_starts:
            period["period_start"] = min(duration_starts)
        first = selected[0].entry
        if isinstance(first.get("fy"), int):
            period["fiscal_year"] = first["fy"]
        if first.get("fp") in {"FY", "Q1", "Q2", "Q3"}:
            period["fiscal_period"] = first["fp"]
        period["period_basis"] = "ytd"
        return period

    def _artifacts(
        self,
        filing: DiscoveredFiling,
        selected: tuple[SelectedXbrlFact, ...],
        *,
        period: JsonObject,
        source_hash: str,
        source_bytes: bytes,
        retrieved_at: str,
    ) -> dict[str, JsonObject]:
        record = filing.dynamic_record()
        source = self._source_document(
            filing, record, period, source_hash=source_hash, retrieved_at=retrieved_at
        )
        artifacts = {f"source-documents/{source['document_id']}.json": source}
        for item in selected:
            fact = self._fact(
                filing, record, period, item, source_hash=source_hash, retrieved_at=retrieved_at
            )
            chunk = self._evidence(filing, record, period, item, retrieved_at=retrieved_at)
            artifacts[f"financial-facts/{fact['fact_id']}.json"] = fact
            artifacts[f"evidence-chunks/{chunk['chunk_id']}.json"] = chunk
        slug = str(record["record_id"]).replace("-", "_")
        for chunk in index_html(source, source_bytes, id_prefix=f"chunk_product_{slug}_fulltext"):
            artifacts[f"evidence-chunks/{chunk['chunk_id']}.json"] = chunk
        return artifacts

    @staticmethod
    def _source_document(
        filing: DiscoveredFiling,
        record: JsonObject,
        period: JsonObject,
        *,
        source_hash: str,
        retrieved_at: str,
    ) -> JsonObject:
        return {
            "schema_version": "1.4.0",
            "document_id": record["document_id"],
            "source_id": record["source_id"],
            "company": filing.company.artifact_value(),
            "document_type": filing.document_type,
            "title": filing.title,
            "published_at": filing.published_at,
            "retrieved_at": retrieved_at,
            "available_from": filing.published_at,
            "source_uri": filing.source_uri,
            "content_hash": source_hash,
            "mime_type": "text/html",
            "language": "en-US",
            "reporting_period": period,
            "license": {
                "license_id": None,
                "publication_mode": "derived_facts_and_short_excerpts",
                "raw_payload_committed": False,
                "notes": "SEC filing is referenced by URL and hash; raw HTML is not committed.",
            },
            "parser_version": "sec-companyfacts-1.0.0",
            "quality_flags": [
                "official_sec_source",
                "xbrl_accession_matched",
                "raw_payload_excluded",
            ],
            "created_at": retrieved_at,
        }

    @staticmethod
    def _fact(
        filing: DiscoveredFiling,
        record: JsonObject,
        period: JsonObject,
        selected: SelectedXbrlFact,
        *,
        source_hash: str,
        retrieved_at: str,
    ) -> JsonObject:
        slug = str(record["record_id"]).replace("-", "_")
        return {
            "schema_version": "1.4.0",
            "fact_id": f"fact_product_{slug}_{selected.metric_code}",
            "fact_kind": "reported",
            "company": filing.company.artifact_value(),
            "metric_code": selected.metric_code,
            "value": str(selected.entry["val"]),
            "measurement_unit": "CURRENCY",
            "currency": "USD",
            "canonical_scale": 1,
            "period": period,
            "sign_convention": "natural_statement_value",
            "source": {
                "source_id": record["source_id"],
                "document_id": record["document_id"],
                "source_type": "official_filing_xbrl",
                "published_at": filing.published_at,
                "retrieved_at": retrieved_at,
                "uri": filing.source_uri,
                "content_hash": source_hash,
                "license_id": None,
                "redistribution_allowed": False,
            },
            "source_locator": {
                "page": None,
                "section": "SEC XBRL companyfacts",
                "table": f"us-gaap:{selected.tag}",
                "row_label": selected.label,
                "column_label": filing.period_label,
            },
            "formula_version": None,
            "source_fact_ids": [],
            "derivation": None,
            "availability": "available",
            "quality_flags": ["sec_xbrl", "accession_matched", "unit_normalized"],
            "created_at": retrieved_at,
        }

    @staticmethod
    def _evidence(
        filing: DiscoveredFiling,
        record: JsonObject,
        period: JsonObject,
        selected: SelectedXbrlFact,
        *,
        retrieved_at: str,
    ) -> JsonObject:
        slug = str(record["record_id"]).replace("-", "_")
        start = selected.entry.get("start")
        end = selected.entry.get("end")
        interval = f"{start} to {end}" if start else f"at {end}"
        text = (
            f"SEC XBRL us-gaap:{selected.tag} reports {selected.entry['val']} USD {interval}; "
            f"accession {filing.filing_id.removeprefix('sec-')}."
        )
        return {
            "schema_version": "1.4.0",
            "chunk_id": f"chunk_product_{slug}_{selected.metric_code}",
            "document_id": record["document_id"],
            "company": filing.company.artifact_value(),
            "reporting_period": period,
            "document_type": filing.evidence_document_type,
            "published_at": filing.published_at,
            "retrieved_at": retrieved_at,
            "content_role": "untrusted_source",
            "section": f"SEC XBRL concept: {selected.label}",
            "text": text,
            "text_hash": _sha256(text.encode()),
            "source_uri": filing.source_uri,
            "locator": {
                "page_start": 1,
                "page_end": 1,
                "paragraph_start": None,
                "paragraph_end": None,
                "char_start": None,
                "char_end": None,
            },
            "language": "en-US",
            "parser_version": "sec-companyfacts-1.0.0",
            "quality_flags": ["structured_xbrl", "accession_matched"],
        }

    @staticmethod
    def _ingestion_manifest(
        filing: DiscoveredFiling,
        period: JsonObject,
        selected: tuple[SelectedXbrlFact, ...],
        package_hash: str,
        *,
        facts_hash: str,
        source_hash: str,
        retrieved_at: str,
    ) -> JsonObject:
        record = filing.dynamic_record()
        return {
            "schema_version": "1.5.0",
            "ingestion_id": record["ingestion_id"],
            "package_id": record["package_id"],
            "data_namespace": "product",
            "status": "ready",
            "company": filing.company.artifact_value(),
            "reporting_period": period,
            "discovery": {
                "registry": "SEC",
                "announcement_id": filing.filing_id,
                "document_title": filing.title,
                "source_uri": filing.source_uri,
                "publication_time": filing.published_at,
                "discovered_at": retrieved_at,
            },
            "acquisition": {
                "retrieved_at": retrieved_at,
                "media_type": "text/html",
                "content_hash": source_hash,
                "raw_payload_committed": False,
            },
            "parser": {
                "parser_name": "sec_companyfacts",
                "parser_version": "1.0.0",
                "companyfacts_hash": facts_hash,
                "accession_matched": True,
            },
            "extraction": {
                "schema_version": "1.5.0",
                "extractor_name": "researchforge_sec_xbrl",
                "extractor_version": "1.0.0",
                "method": "official_sec_xbrl_accession_recovery",
                "numerical_truth_source": "SEC companyfacts",
                "llm_used": False,
                "target_metrics": list(TAG_ALIASES),
                "promoted_metric_count": len(selected),
                "recoveries": [
                    {"metric_code": item.metric_code, "tag": item.tag, "entry": item.entry}
                    for item in selected
                ],
            },
            "outputs": [],
            "abstentions": [],
            "created_at": retrieved_at,
            "package_hash": package_hash,
        }

    @staticmethod
    def _package_manifest(
        filing: DiscoveredFiling,
        artifacts: dict[str, JsonObject],
        artifact_hashes: dict[str, str],
        package_hash: str,
    ) -> JsonObject:
        record = filing.dynamic_record()
        sources = [v for k, v in artifacts.items() if k.startswith("source-documents/")]
        facts = [v for k, v in artifacts.items() if k.startswith("financial-facts/")]
        evidence = [v for k, v in artifacts.items() if k.startswith("evidence-chunks/")]
        return {
            "schema_version": "1.5.0",
            "package_id": record["package_id"],
            "package_hash": package_hash,
            "data_namespace": "product",
            "status": "ready",
            "source_document_count": len(sources),
            "financial_fact_count": len(facts),
            "evidence_chunk_count": len(evidence),
            "source_document_ids": sorted(item["document_id"] for item in sources),
            "financial_fact_ids": sorted(item["fact_id"] for item in facts),
            "evidence_chunk_ids": sorted(item["chunk_id"] for item in evidence),
            "artifact_hashes": dict(sorted(artifact_hashes.items())),
            "ingestion_manifest": "ingestion-manifest.json",
        }

    @staticmethod
    def _write(
        package_root: Path,
        artifacts: dict[str, JsonObject],
        ingestion: JsonObject,
        package_manifest: JsonObject,
    ) -> None:
        package_root.mkdir(parents=True, exist_ok=True)
        for relative, payload in artifacts.items():
            destination = package_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(_pretty_bytes(payload))
        (package_root / "ingestion-manifest.json").write_bytes(_pretty_bytes(ingestion))
        (package_root / "manifest.json").write_bytes(_pretty_bytes(package_manifest))
