"""Deterministic access to an explicit product, fixture, or benchmark package."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from researchforge.adapters.storage import payload_sha256
from researchforge.application.contracts import CatalogCompany, CatalogResponse, DataNamespace
from researchforge.application.research import InsufficientDataError, LoadedResearchData


class G0FixtureCatalog:
    """Load only facts from one explicit namespace and point-in-time cutoff.

    The historical class name is retained for compatibility with frozen experiment code.
    Product construction passes ``expected_namespace='product'`` and cannot fall back to a
    fixture or benchmark root.
    """

    _facts: tuple[dict[str, Any], ...]
    _sources: tuple[dict[str, Any], ...]
    _evidence: tuple[dict[str, Any], ...]

    def __init__(
        self,
        fixture_root: Path,
        *,
        expected_namespace: DataNamespace | None = None,
    ) -> None:
        self.root = fixture_root.resolve()
        self.fact_dir = self.root / "financial-facts"
        self.source_dir = self.root / "source-documents"
        self.evidence_dir = self.root / "evidence-chunks"
        if not self.evidence_dir.is_dir() and self.root.name == "g0":
            self.evidence_dir = self.root.parent / "v1.4-primary" / "evidence-chunks"
        self.manifest = self._load(self.root / "manifest.json")
        declared_namespace = self.manifest.get("data_namespace")
        if declared_namespace is None:
            declared_namespace = "benchmark" if self.root.name != "g0" else "fixture"
        if declared_namespace not in {"product", "fixture", "benchmark"}:
            raise ValueError("data package has an invalid namespace")
        self.data_namespace = cast(DataNamespace, declared_namespace)
        if expected_namespace is not None and self.data_namespace != expected_namespace:
            raise ValueError(
                f"expected {expected_namespace} data, got {self.data_namespace}; fallback refused"
            )
        if self.data_namespace == "product" and self.manifest.get("status") != "ready":
            raise ValueError("product data package must have ready status")
        if self.data_namespace == "product" and "packages" in self.manifest:
            children = self._product_children()
            self._facts = tuple(fact for child in children for fact in child._facts)
            self._sources = tuple(source for child in children for source in child._sources)
            self._evidence = tuple(chunk for child in children for chunk in child._evidence)
            for records, key in (
                (self._facts, "fact_id"),
                (self._sources, "document_id"),
                (self._evidence, "chunk_id"),
            ):
                if len({item[key] for item in records}) != len(records):
                    raise ValueError("product index contains duplicate artifact identities")
            return
        if self.data_namespace == "product":
            self._verify_product_package()
        self._facts = tuple(self._load(path) for path in sorted(self.fact_dir.glob("*.json")))
        self._sources = tuple(self._load(path) for path in sorted(self.source_dir.glob("*.json")))
        evidence = tuple(self._load(path) for path in sorted(self.evidence_dir.glob("*.json")))
        source_document_ids = {source["document_id"] for source in self._sources}
        self._evidence = tuple(
            chunk for chunk in evidence if chunk["document_id"] in source_document_ids
        )

    def _product_children(self) -> tuple[G0FixtureCatalog, ...]:
        entries = self.manifest["packages"]
        if not isinstance(entries, list) or not 1 <= len(entries) <= 3:
            raise ValueError("product index requires one to three explicit packages")
        if payload_sha256(entries) != self.manifest.get("package_hash"):
            raise ValueError("product index hash mismatch")
        children = []
        seen: set[str] = set()
        for entry in entries:
            name = entry["path"]
            if not isinstance(name, str) or re.fullmatch(r"[a-z0-9][a-z0-9-]*", name) is None:
                raise ValueError("unsafe product package path")
            child_root = (self.root / name).resolve()
            if child_root.parent != self.root or name in seen:
                raise ValueError("product package path escapes root or is duplicated")
            seen.add(name)
            manifest = self._load(child_root / "manifest.json")
            if "packages" in manifest:
                raise ValueError("nested product indexes are not supported")
            for key in ("package_id", "package_hash"):
                if entry[key] != manifest.get(key):
                    raise ValueError(f"indexed {key} differs from child package")
            children.append(G0FixtureCatalog(child_root, expected_namespace="product"))
        return tuple(children)

    def _verify_product_package(self) -> None:
        ingestion = self._load(self.root / "ingestion-manifest.json")
        hashes = self.manifest.get("artifact_hashes", {})
        if not hashes or payload_sha256(hashes) != self.manifest.get("package_hash"):
            raise ValueError("product package hash mismatch")
        if (
            ingestion.get("status") != "ready"
            or ingestion.get("package_hash") != self.manifest["package_hash"]
        ):
            raise ValueError("product ingestion is not ready; stale artifacts refused")
        actual = {
            str(path.relative_to(self.root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for directory in (self.fact_dir, self.source_dir, self.evidence_dir)
            for path in directory.glob("*.json")
        }
        if actual != hashes:
            raise ValueError("product artifact hashes differ from manifest")

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
        is_product = self.data_namespace == "product"
        return CatalogResponse(
            schema_version="1.5.0" if is_product else "1.4.0",
            data_namespace=self.data_namespace,
            companies=sorted(companies.values(), key=lambda item: item.company_id),
            supported_task_types=(
                ["filing_analysis"]
                if is_product
                else [
                    "company_research",
                    "filing_analysis",
                    "peer_comparison",
                    "thesis_investigation",
                    "risk_detection",
                ]
            ),
            implementation_level="V1_5_REAL_DATA" if is_product else "G1_BREADTH",
            limitations=(
                [
                    f"Real-data coverage: {len(self._sources)} reviewed filings in this catalog.",
                    "Research results are auditable analysis, not investment advice.",
                    "Human usefulness remains unvalidated until real pilot sessions are completed.",
                ]
                if is_product
                else [
                    "Explicit fixture/benchmark runtime; this is not real-product evidence.",
                    "The frozen catalog exists for reproducible tests and Quality Lab review.",
                ]
            ),
        )

    @property
    def source_documents(self) -> tuple[dict[str, Any], ...]:
        return self._sources

    @property
    def evidence_chunks(self) -> tuple[dict[str, Any], ...]:
        return self._evidence

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
        evidence = tuple(chunk for chunk in self._evidence if chunk["document_id"] in document_ids)
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
            evidence_chunks=evidence,
        )
