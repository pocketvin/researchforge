"""Company-first official-disclosure preparation for ResearchForge product runs."""

# ruff: noqa: RUF001 -- issuer names include real CJK punctuation.

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from researchforge.application.contracts import (
    AutonomousResearchRequest,
    ResearchRunRequest,
    RunSubmission,
)
from researchforge.application.service import ResearchRunService
from researchforge.ingestion.discovery import (
    DiscoveredFiling,
    Market,
    OfficialDisclosureDiscovery,
    ResolvedCompany,
)
from researchforge.ingestion.errors import IngestionAbstention
from researchforge.ingestion.hk_ifrs import HkIfrsProductIngestion
from researchforge.ingestion.pipeline import FilingRegistry, ProductDisclosureIngestion
from researchforge.ingestion.sec_xbrl import SecXbrlProductIngestion

JsonObject = dict[str, Any]
ServiceFactory = Callable[[Path], ResearchRunService]
V17_EVIDENCE_INDEX_VERSION = "1.1.0"


def _entity_key(value: str) -> str:
    compact = re.sub(r"[\s.·\-_（）()]", "", value).casefold()
    for suffix in ("股份有限公司", "控股有限公司", "有限公司", "控股集团", "集团", "公司"):
        compact = compact.replace(suffix, "")
    return compact


def _period_label(period: JsonObject) -> str:
    return f"{period['fiscal_year']}{period['fiscal_period']}"


class AutonomousResearchCoordinator:
    """Resolve a company, acquire official data, and submit one immutable research run."""

    def __init__(
        self,
        artifact_root: Path,
        service_factory: ServiceFactory,
        *,
        discovery: OfficialDisclosureDiscovery | None = None,
        reviewed_root: Path | None = None,
    ) -> None:
        self.artifact_root = artifact_root.resolve()
        self.service_factory = service_factory
        self.discovery = discovery or OfficialDisclosureDiscovery()
        self.reviewed_root = reviewed_root.resolve() if reviewed_root is not None else None
        self.live_root = self.artifact_root / "live-data"

    def prepare(
        self,
        request: AutonomousResearchRequest,
    ) -> tuple[ResearchRunService, RunSubmission, DiscoveredFiling]:
        reviewed = (
            self._reviewed_package(request)
            if request.research_mode == "financial_snapshot"
            else None
        )
        if reviewed is None:
            filing = self.discovery.discover(
                request.company_query,
                period_label=request.requested_period_label,
                research_time=request.research_time,
                market_hint=request.market_hint,
            )
            record = filing.dynamic_record()
            if request.research_mode == "financial_snapshot":
                package_root = self.live_root / "packages" / str(record["record_id"])
            else:
                index_tag = V17_EVIDENCE_INDEX_VERSION.replace(".", "-")
                package_root = (
                    self.live_root / "v17-packages" / f"{record['record_id']}-evidence-{index_tag}"
                )
            self._ensure_package(record, filing, package_root)
        else:
            package_root, filing = reviewed
        service = self.service_factory(package_root)
        standard_request = ResearchRunRequest(
            task_type=(
                "filing_analysis"
                if request.research_mode == "financial_snapshot"
                else "company_research"
            ),
            research_question=request.research_question,
            company_ids=[filing.company.company_id],
            requested_period_labels=[filing.period_label],
            research_time=request.research_time,
            idempotency_key=request.idempotency_key,
        )
        return service, service.submit(standard_request), filing

    def _reviewed_package(
        self,
        request: AutonomousResearchRequest,
    ) -> tuple[Path, DiscoveredFiling] | None:
        if self.reviewed_root is None or request.requested_period_label is None:
            return None
        candidates: list[tuple[Path, DiscoveredFiling]] = []
        for package_root in sorted(self.reviewed_root.iterdir()):
            if not package_root.is_dir() or not (package_root / "manifest.json").is_file():
                continue
            sources = sorted((package_root / "source-documents").glob("*.json"))
            if len(sources) != 1:
                continue
            source = json.loads(sources[0].read_text(encoding="utf-8"))
            period = source.get("reporting_period")
            company = source.get("company")
            if not isinstance(period, dict) or not isinstance(company, dict):
                continue
            if _period_label(period) != request.requested_period_label:
                continue
            filing = self._cached_filing(source, period, company)
            if request.market_hint is not None and filing.company.market != request.market_hint:
                continue
            if datetime.fromisoformat(filing.published_at) > request.research_time:
                continue
            if self._matches_query(request.company_query, filing.company):
                candidates.append((package_root, filing))
        if len(candidates) > 1:
            raise IngestionAbstention(
                "COMPANY_NOT_UNAMBIGUOUS",
                "discovery",
                "Reviewed package cache matched more than one company package.",
            )
        return candidates[0] if candidates else None

    @staticmethod
    def _matches_query(query: str, company: ResolvedCompany) -> bool:
        raw = query.strip().casefold()
        if raw in {company.ticker.casefold(), company.company_id.casefold()}:
            return True
        needle = _entity_key(query)
        legal = _entity_key(company.legal_name)
        return bool(needle) and (needle == legal or (len(needle) >= 2 and needle in legal))

    @staticmethod
    def _cached_filing(
        source: JsonObject,
        period: JsonObject,
        company: JsonObject,
    ) -> DiscoveredFiling:
        country = str(company["country_code"])
        market: Market = "CN" if country == "CN" else "HK" if country == "HK" else "US"
        resolved = ResolvedCompany(
            company_id=str(company["company_id"]),
            legal_name=str(company["legal_name"]),
            ticker=str(company["ticker"]),
            exchange=str(company["exchange"]),
            country_code=country,
            market=market,
            provider_company_id=str(company["company_id"]),
        )
        document_type = str(source.get("document_type", "annual_report"))
        return DiscoveredFiling(
            provider="REVIEWED_CACHE",
            filing_id=f"cache-{source['document_id']}",
            title=str(source["title"]),
            document_type=document_type,
            evidence_document_type=document_type,
            source_uri=str(source["source_uri"]),
            published_at=str(source["published_at"]),
            reporting_period=period,
            company=resolved,
        )

    def _ensure_package(
        self,
        record: JsonObject,
        filing: DiscoveredFiling,
        package_root: Path,
    ) -> None:
        if (package_root / "manifest.json").is_file():
            return
        if filing.company.market == "US":
            SecXbrlProductIngestion().run(filing, package_root=package_root)
            return
        if filing.company.market == "HK":
            HkIfrsProductIngestion().run(filing, package_root=package_root)
            return
        registry_root = self.live_root / "registries"
        registry_root.mkdir(parents=True, exist_ok=True)
        registry_path = registry_root / f"{record['record_id']}.json"
        registry_payload = {
            "schema_version": "1.5.0",
            "data_namespace": "product",
            "records": [record],
        }
        registry_path.write_text(
            json.dumps(registry_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        ingestion = ProductDisclosureIngestion(FilingRegistry(registry_path))
        manifest = ingestion.run(
            company_id=filing.company.company_id,
            period_label=filing.period_label,
            raw_root=self.live_root / "raw",
            package_root=package_root,
        )
        if manifest["status"] != "ready":
            abstentions = manifest.get("abstentions") or []
            reason = abstentions[0] if abstentions else {"message": "Unknown ingestion abstention"}
            raise IngestionAbstention(
                str(reason.get("code", "LIVE_INGESTION_ABSTAINED")),
                str(reason.get("stage", "ingestion")),
                str(reason.get("reason", "Live official filing could not be normalized.")),
            )
