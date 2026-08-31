"""Deterministic access to the owner-signed G0 fixture package."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from researchforge.application.contracts import CatalogCompany, CatalogResponse
from researchforge.application.research import InsufficientDataError, LoadedResearchData


class G0FixtureCatalog:
    """Load only facts published by the requested point-in-time cutoff."""

    def __init__(self, fixture_root: Path) -> None:
        self.root = fixture_root.resolve()
        self.fact_dir = self.root / "financial-facts"
        self.source_dir = self.root / "source-documents"
        self.manifest = self._load(self.root / "manifest.json")
        self._facts = tuple(self._load(path) for path in sorted(self.fact_dir.glob("*.json")))
        self._sources = tuple(self._load(path) for path in sorted(self.source_dir.glob("*.json")))

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))

    @staticmethod
    def _period_label(period: dict[str, Any]) -> str:
        return f"{period['fiscal_year']}{period['fiscal_period']}"

    def catalog(self) -> CatalogResponse:
        companies: dict[str, CatalogCompany] = {}
        for fact in self._facts:
            company = fact["company"]
            company_id = company["company_id"]
            existing = companies.get(company_id)
            period_labels = set(existing.period_labels if existing is not None else [])
            period_labels.add(self._period_label(fact["period"]))
            companies[company_id] = CatalogCompany(
                **company,
                period_labels=sorted(period_labels),
            )
        return CatalogResponse(
            companies=sorted(companies.values(), key=lambda item: item.company_id),
            supported_task_types=[
                "company_research",
                "filing_analysis",
                "peer_comparison",
                "thesis_investigation",
                "risk_detection",
            ],
            limitations=[
                "All modes use frozen facts and official source locators, not filing full text.",
                "The catalog is limited to the owner-signed CATL/EVE G0 fixture package.",
            ],
        )

    @property
    def source_documents(self) -> tuple[dict[str, Any], ...]:
        return self._sources

    def load(
        self,
        company_ids: list[str],
        requested_period_labels: list[str],
        research_time: datetime,
    ) -> LoadedResearchData:
        if research_time.tzinfo is None:
            raise ValueError("research_time must include a timezone")
        catalog_ids = {company.company_id for company in self.catalog().companies}
        unknown = sorted(set(company_ids) - catalog_ids)
        if unknown:
            raise InsufficientDataError("Unsupported company IDs: " + ", ".join(unknown))

        selected = tuple(
            fact
            for fact in self._facts
            if fact["company"]["company_id"] in company_ids
            and self._period_label(fact["period"]) in requested_period_labels
            and datetime.fromisoformat(fact["source"]["published_at"]) <= research_time
        )
        present = {
            (fact["company"]["company_id"], self._period_label(fact["period"])) for fact in selected
        }
        expected = {
            (company_id, period_label)
            for company_id in company_ids
            for period_label in requested_period_labels
        }
        missing = sorted(expected - present)
        if missing:
            labels = [f"{company_id}/{period}" for company_id, period in missing]
            raise InsufficientDataError(
                "Requested company/period facts are unavailable at the research cutoff: "
                + ", ".join(labels)
            )

        document_ids = {fact["source"]["document_id"] for fact in selected}
        sources = tuple(source for source in self._sources if source["document_id"] in document_ids)
        companies_by_id = {fact["company"]["company_id"]: fact["company"] for fact in selected}
        periods_by_label = {self._period_label(fact["period"]): fact["period"] for fact in selected}
        return LoadedResearchData(
            facts=selected,
            source_documents=sources,
            requested_periods=tuple(
                periods_by_label[label]
                for label in requested_period_labels
                if label in periods_by_label
            ),
            companies=tuple(companies_by_id[company_id] for company_id in company_ids),
        )
