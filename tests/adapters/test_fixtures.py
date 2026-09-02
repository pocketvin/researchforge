"""Point-in-time frozen fixture catalog tests."""

from __future__ import annotations

from datetime import datetime

import pytest

from researchforge.adapters.fixtures import G0FixtureCatalog
from researchforge.api.app import DEFAULT_FIXTURE_ROOT
from researchforge.application.research import InsufficientDataError


def test_catalog_loads_exact_current_period_metrics() -> None:
    catalog = G0FixtureCatalog(DEFAULT_FIXTURE_ROOT)

    loaded = catalog.load(
        ["cn_300750"],
        ["2024H1"],
        datetime.fromisoformat("2024-08-01T00:00:00+08:00"),
    )

    assert len(loaded.facts) == 6
    assert {fact["metric_code"] for fact in loaded.facts} == {
        "revenue",
        "operating_cost",
        "net_income",
        "operating_cash_flow",
        "accounts_receivable",
        "inventory",
    }
    assert [source["document_id"] for source in loaded.source_documents] == ["doc_g0_catl_2024h1"]


def test_catalog_enforces_publication_cutoff() -> None:
    catalog = G0FixtureCatalog(DEFAULT_FIXTURE_ROOT)

    with pytest.raises(InsufficientDataError, match="research cutoff"):
        catalog.load(
            ["cn_300750"],
            ["2024H1"],
            datetime.fromisoformat("2024-07-01T00:00:00+08:00"),
        )


def test_catalog_exposes_all_five_bounded_modes() -> None:
    catalog = G0FixtureCatalog(DEFAULT_FIXTURE_ROOT)

    response = catalog.catalog()

    assert response.supported_task_types == [
        "company_research",
        "filing_analysis",
        "peer_comparison",
        "thesis_investigation",
        "risk_detection",
    ]
    assert {company.company_id for company in response.companies} == {
        "cn_300014",
        "cn_300750",
    }


def test_product_catalog_exposes_only_the_verified_initial_capability() -> None:
    catalog = G0FixtureCatalog(
        DEFAULT_FIXTURE_ROOT.parent.parent / "product" / "packages" / "catl-2024h1",
        expected_namespace="product",
    )

    response = catalog.catalog()

    assert response.schema_version == "1.5.0"
    assert response.data_namespace == "product"
    assert response.supported_task_types == ["filing_analysis"]
    assert [company.company_id for company in response.companies] == ["cn_300750"]
