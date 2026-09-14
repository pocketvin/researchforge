"""Deterministic table/page series extraction and arithmetic."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from researchforge.v2.contracts import (
    ResearchRequest,
    SeriesCalculateInput,
    SeriesExtractInput,
    WorkingState,
)
from researchforge.v2.documents import parse_html
from researchforge.v2.series import calculate_series_metric, extract_statement_series
from researchforge.v2.storage import ResearchRepository
from researchforge.v2.tools import FilingTools


def document() -> dict:
    return {
        "document_id": "doc_series_test",
        "title": "Synthetic Annual Report",
        "source_uri": "https://www.sec.gov/Archives/series-test.pdf",
        "published_at": "2026-01-01T00:00:00+00:00",
        "content_hash": "a" * 64,
        "period_label": "2019FY",
        "company": {
            "company_id": "series_test_co",
            "legal_name": "Series Test Co",
            "market": "US",
            "country_code": "US",
        },
    }


def page(page_number: int, text: str) -> dict:
    doc = document()
    return {
        "artifact_id": f"page_series_test_{page_number}",
        "kind": "page",
        "document_id": doc["document_id"],
        "text": text,
        "source_uri": doc["source_uri"],
        "published_at": doc["published_at"],
        "page_id": f"page_series_test_{page_number}",
        "page_number": page_number,
        "visual_inspection_available": False,
    }


REVENUE_PAGE = """ACTIVISION BLIZZARD, INC. AND SUBSIDIARIES
CONSOLIDATED STATEMENTS OF OPERATIONS
(Amounts in millions, except per share data)
For the Years Ended December 31,
2019 2018 2017
Net revenues
Product sales $ 1,975 $ 2,255 $ 2,110
Subscription, licensing, and other revenues 4,514 5,245 4,907
Total net revenues 6,489 7,500 7,017
"""

CAPEX_PAGE = """ACTIVISION BLIZZARD, INC. AND SUBSIDIARIES
CONSOLIDATED STATEMENTS OF CASH FLOWS
(Amounts in millions)
For the Years Ended December 31,
2019 2018 2017
Cash flows from operating activities:
Net income $ 1,503 $ 1,848 $ 273
Adjustments to reconcile net income to net cash provided by operating activities:
Deferred income taxes (352) (35) (181)
Provision for inventories 6 6 33
Non-cash operating lease cost 64 — —
Depreciation and amortization 328 509 888
Amortization of capitalized software costs 225 489 311
Loss on extinguishment of debt — 40 12
Share-based compensation expense (2) 166 209 176
Unrealized gain on equity investment (Note 10) (38) — —
Other 51 7 40
Changes in operating assets and liabilities, net of effect from business acquisitions:
Accounts receivable, net 182 (114) (165)
Inventories 7 (5) (26)
Software development and intellectual property licenses (275) (372) (301)
Other assets 164 (51) (97)
Deferred revenues (154) (122) 220
Accounts payable 31 (65) 85
Accrued expenses and other liabilities (77) (554) 945
Net cash provided by operating activities 1,831 1,790 2,213
Cash flows from investing activities:
Proceeds from maturities of available-for-sale investments 153 116 80
Purchases of available-for-sale investments (65) (209) (135)
Capital expenditures (116) (131) (155)
"""


def test_native_statement_rows_become_verified_series_and_deterministic_ratio() -> None:
    doc = document()
    revenue = extract_statement_series(
        SeriesExtractInput(
            page_id="page_series_test_70",
            row_label="Total net revenues",
            metric_code="revenue",
        ),
        page(70, REVENUE_PAGE),
        doc,
    )
    capex = extract_statement_series(
        SeriesExtractInput(
            page_id="page_series_test_73",
            row_label="Capital expenditures",
            metric_code="capital_expenditures",
        ),
        page(73, CAPEX_PAGE),
        doc,
    )
    assert [(item["period_label"], item["normalized_value"]) for item in revenue["values"]] == [
        ("2019FY", "6489"),
        ("2018FY", "7500"),
        ("2017FY", "7017"),
    ]
    assert [(item["period_label"], item["normalized_value"]) for item in capex["values"]] == [
        ("2019FY", "116"),
        ("2018FY", "131"),
        ("2017FY", "155"),
    ]
    assert capex["sign_policy"] == "absolute"
    assert revenue["currency"] == capex["currency"] == "USD"
    assert revenue["canonical_scale"] == capex["canonical_scale"] == 1_000_000

    calculation = calculate_series_metric(
        SeriesCalculateInput(
            formula="average_ratio_percent",
            series_ids=[capex["series_id"], revenue["series_id"]],
            round_decimals=1,
        ),
        {capex["series_id"]: capex, revenue["series_id"]: revenue},
    )
    assert calculation["status"] == "valid"
    assert calculation["value"] == "1.9"
    assert calculation["measurement_unit"] == "PERCENT"
    assert calculation["input_series_ids"] == [capex["series_id"], revenue["series_id"]]

    fy2018 = calculate_series_metric(
        SeriesCalculateInput(
            formula="ratio_percent",
            series_ids=[capex["series_id"], revenue["series_id"]],
            period_label="2018FY",
            round_decimals=2,
        ),
        {capex["series_id"]: capex, revenue["series_id"]: revenue},
    )
    assert fy2018["value"] == "1.75"
    assert fy2018["per_period"] == [
        {"period_label": "2018FY", "value_percent": "1.746666666666666666666666667"}
    ]


def test_native_html_table_can_be_promoted_to_verified_series_with_adjacent_unit_context(
    tmp_path: Path,
) -> None:
    repo = ResearchRepository(tmp_path)
    doc = document()
    html = b"""<h2>Consolidated Statements of Cash Flows</h2>
<p>(In millions)</p><p>Year Ended December 31</p>
<table>
<tr><th></th><th>2025</th><th>2024</th><th>2023</th></tr>
<tr><td>Capital expenditures</td><td>$ (145)</td><td>$ (142)</td><td>$ (120)</td></tr>
</table>"""
    source = {**doc, "raw_blob_id": repo.put_blob(html, "html")}
    objects, _blocks, _gaps = parse_html(html, source)
    table = next(item for item in objects.values() if item["kind"] == "table")
    request = ResearchRequest(
        company_query="Series Test Co",
        market_hint="US",
        requested_period_label="2025FY",
        research_question="What were capital expenditures?",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="native-html-table-series-test",
    )
    manifest, _ = repo.create(request, {})
    environment = {
        "schema_version": "2.0.0",
        "entity": doc["company"],
        "documents": {doc["document_id"]: doc},
        "objects": objects,
        "facts": {},
        "gaps": [],
    }
    tools = FilingTools(repo, manifest["run_id"], request, environment, lambda: None)
    result = tools.execute(
        "html-table-series",
        "extract_statement_series",
        {
            "artifact_id": table["artifact_id"],
            "row_label": "Capital expenditures",
            "metric_code": "capital_expenditures",
        },
    )
    assert result["source_kind"] == "table"
    assert result["source_artifact_id"] == table["artifact_id"]
    assert result["canonical_scale"] == 1_000_000
    assert result["currency"] == "USD"
    assert [(item["period_label"], item["normalized_value"]) for item in result["values"]] == [
        ("2025FY", "145"),
        ("2024FY", "142"),
        ("2023FY", "120"),
    ]
    evidence = tools.observed[result["evidence_id"]]
    assert evidence["source_kind"] == "table"
    schema = SeriesExtractInput.model_json_schema()
    assert "artifact_id" in schema["properties"]
    assert "page_id" not in schema["properties"]


def test_series_extraction_rejects_metric_mismatch_and_ambiguous_rows() -> None:
    doc = document()
    with pytest.raises(ValueError, match="metric semantics"):
        extract_statement_series(
            SeriesExtractInput(
                page_id="page_series_test_70",
                row_label="Total net revenues",
                metric_code="capital_expenditures",
            ),
            page(70, REVENUE_PAGE),
            doc,
        )
    ambiguous = REVENUE_PAGE + "\nTotal net revenues 1 2 3\n"
    with pytest.raises(ValueError, match="uniquely"):
        extract_statement_series(
            SeriesExtractInput(
                page_id="page_series_test_70",
                row_label="Total net revenues",
                metric_code="revenue",
            ),
            page(70, ambiguous),
            doc,
        )

    revenue = extract_statement_series(
        SeriesExtractInput(
            page_id="page_series_test_70",
            row_label="Total net revenues",
            metric_code="revenue",
        ),
        page(70, REVENUE_PAGE),
        doc,
    )
    with pytest.raises(ValueError, match="requires period_label"):
        calculate_series_metric(
            SeriesCalculateInput(formula="ratio_percent", series_ids=[revenue["series_id"]] * 2),
            {revenue["series_id"]: revenue},
        )


def test_sec_parenthetical_millions_headers_are_not_treated_as_unscaled() -> None:
    doc = document()
    revenue_page = page(
        48,
        """(Millions, except per share amounts) 2022 2021 2020
Net sales $ 34,229 $ 35,355 $ 32,184
""",
    )
    capex_page = page(
        39,
        """Year ended December 31, (Millions) 2022 2021
Purchases of property, plant and equipment (PP&E) $ (1,749) $ (1,603)
""",
    )
    revenue = extract_statement_series(
        SeriesExtractInput(
            page_id=revenue_page["artifact_id"], row_label="Net sales", metric_code="revenue"
        ),
        revenue_page,
        doc,
    )
    capex = extract_statement_series(
        SeriesExtractInput(
            page_id=capex_page["artifact_id"],
            row_label="Purchases of property, plant and equipment (PP&E)",
            metric_code="capital_expenditures",
        ),
        capex_page,
        doc,
    )
    assert revenue["canonical_scale"] == 1_000_000
    assert capex["canonical_scale"] == 1_000_000
    assert revenue["scale_label"] == capex["scale_label"] == "millions"
    calculation = calculate_series_metric(
        SeriesCalculateInput(
            formula="ratio_percent",
            series_ids=[capex["series_id"], revenue["series_id"]],
            period_label="2022FY",
            round_decimals=2,
        ),
        {capex["series_id"]: capex, revenue["series_id"]: revenue},
    )
    assert calculation["value"] == "5.11"


def test_filing_tools_persist_verified_series_and_calculation(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    request = ResearchRequest(
        company_query="Series Test Co",
        market_hint="US",
        requested_period_label="2019FY",
        research_question="What is the three-year average capex as a percent of revenue?",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="series-tool-test",
    )
    manifest, _ = repo.create(request, {})
    doc = document()
    revenue_page = page(70, REVENUE_PAGE)
    capex_page = page(73, CAPEX_PAGE)
    environment = {
        "schema_version": "2.0.0",
        "entity": doc["company"],
        "documents": {doc["document_id"]: doc},
        "objects": {
            revenue_page["artifact_id"]: revenue_page,
            capex_page["artifact_id"]: capex_page,
        },
        "facts": {},
        "gaps": [],
    }
    tools = FilingTools(repo, manifest["run_id"], request, environment, lambda: None)
    revenue = tools.execute(
        "series-revenue",
        "extract_statement_series",
        {
            "page_id": revenue_page["artifact_id"],
            "row_label": "Total net revenues",
            "metric_code": "revenue",
        },
    )
    capex = tools.execute(
        "series-capex",
        "extract_statement_series",
        {
            "page_id": capex_page["artifact_id"],
            "row_label": "Capital expenditures",
            "metric_code": "capital_expenditures",
        },
    )
    assert revenue["evidence_id"] in tools.observed
    assert capex["evidence_id"] in tools.observed
    calculation = tools.execute(
        "series-calc",
        "calculate_series_metric",
        {
            "formula": "average_ratio_percent",
            "series_ids": [capex["series_id"], revenue["series_id"]],
            "round_decimals": 1,
        },
    )
    assert calculation["value"] == "1.9"
    snapshot = repo.artifact(manifest["run_id"], "research_state")
    assert set(snapshot["verified_series"]) == {capex["series_id"], revenue["series_id"]}
    assert calculation["calculation_id"] in snapshot["calculations"]

    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_ratio",
                        "question": "What is the three-year average capex as a percent of revenue?",
                        "priority": "required",
                        "status": "answered",
                        "evidence_ids": [calculation["calculation_id"]],
                        "conclusion": "The deterministic calculation returns 1.9%.",
                        "remaining_uncertainty": "",
                    }
                ],
                "hypotheses": [],
                "open_questions": [],
                "decision_summary": "The verified series support the requested calculation.",
                "core_question_status": "answerable",
                "expected_value_of_more_research": "low",
            }
        )
    )
    submitted = tools.execute(
        "series-submit",
        "submit_research",
        {
            "stop_reason": "sufficient_evidence",
            "summary": "The requested three-year average is 1.9%.",
            "evidence_ids": [calculation["calculation_id"]],
            "remaining_uncertainties": [],
            "why_stop": (
                "The verified source rows and deterministic calculation answer the question."
            ),
        },
    )
    assert submitted["accepted"] is True
    assert submitted["dossier"]["evidence_ids"] == [
        capex["evidence_id"],
        revenue["evidence_id"],
    ]
    assert {item["resolved_evidence_id"] for item in submitted["support_reference_resolution"]} == {
        capex["evidence_id"],
        revenue["evidence_id"],
    }
    events = repo.events(manifest["run_id"])
    assert any(event["event_type"] == "submission_lineage_resolved" for event in events)

    rejected = tools.execute(
        "series-submit-unknown",
        "submit_research",
        {
            "stop_reason": "sufficient_evidence",
            "summary": "invalid",
            "evidence_ids": ["calc_not_in_this_run"],
            "remaining_uncertainties": [],
            "why_stop": "invalid",
        },
    )
    assert rejected["error"] == "TOOL_INPUT_REJECTED"
    assert "not observed evidence" in rejected["message"]


def test_required_objective_blocks_model_derived_percentage_until_calculation(
    tmp_path: Path,
) -> None:
    repo = ResearchRepository(tmp_path)
    request = ResearchRequest(
        company_query="Series Test Co",
        market_hint="US",
        requested_period_label="2019FY",
        research_question="What is FY2019 capex as a percent of revenue?",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="series-provenance-blocker-test",
    )
    manifest, _ = repo.create(request, {})
    doc = document()
    revenue_page = page(70, REVENUE_PAGE)
    capex_page = page(73, CAPEX_PAGE)
    env = {
        "schema_version": "2.0.0",
        "entity": doc["company"],
        "documents": {doc["document_id"]: doc},
        "objects": {
            revenue_page["artifact_id"]: revenue_page,
            capex_page["artifact_id"]: capex_page,
        },
        "facts": {},
        "gaps": [],
    }
    tools = FilingTools(repo, manifest["run_id"], request, env, lambda: None)
    revenue = tools.execute(
        "ratio-revenue",
        "extract_statement_series",
        {
            "page_id": revenue_page["artifact_id"],
            "row_label": "Total net revenues",
            "metric_code": "revenue",
        },
    )
    capex = tools.execute(
        "ratio-capex",
        "extract_statement_series",
        {
            "page_id": capex_page["artifact_id"],
            "row_label": "Capital expenditures",
            "metric_code": "capital_expenditures",
        },
    )
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_ratio",
                        "question": "What is FY2019 capex as a percent of revenue?",
                        "priority": "required",
                        "status": "answered",
                        "evidence_ids": [capex["evidence_id"], revenue["evidence_id"]],
                        "conclusion": "FY2019 capex/revenue is about 1.8%.",
                        "remaining_uncertainty": "",
                    }
                ],
                "core_question_status": "answerable",
                "expected_value_of_more_research": "low",
            }
        )
    )
    completeness = tools.completeness()
    assert "derived_percentage_calculation_missing" in completeness["submission_blockers"]
    assert completeness["required_before_submit"] == []

    calculation = tools.execute(
        "ratio-calc",
        "calculate_series_metric",
        {
            "formula": "ratio_percent",
            "series_ids": [capex["series_id"], revenue["series_id"]],
            "round_decimals": 1,
            "period_label": "2019FY",
        },
    )
    assert calculation["value"] == "1.8"
    assert tools.reflection_decision()["reason"] == "numeric_provenance_update"
    applied = tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_ratio",
                        "question": "What is FY2019 capex as a percent of revenue?",
                        "priority": "required",
                        "status": "answered",
                        "evidence_ids": [capex["evidence_id"], revenue["evidence_id"]],
                        "conclusion": (
                            "FY2019 capex/revenue is about 1.8%, based on deterministic "
                            f"calculation {calculation['calculation_id']}."
                        ),
                        "remaining_uncertainty": "",
                    }
                ],
                "core_question_status": "answerable",
                "expected_value_of_more_research": "low",
            }
        )
    )
    assert calculation["calculation_id"] in tools.working.objectives[0].evidence_ids
    assert any(
        item.get("correction") == "explicit_support_reference_recovered_from_objective_text"
        for item in applied["reference_corrections"]
    )
    assert tools.completeness()["required_before_submit"] == ["submit_research"]


def test_flow_to_average_balance_percent_computes_roa_from_verified_series() -> None:
    doc = document()
    income_page = page(
        48,
        """3M Company and Subsidiaries
Consolidated Statement of Income
(Millions, except per share amounts) 2022 2021 2020
Net income attributable to 3M $ 5,777 $ 5,921 $ 5,449
""",
    )
    assets_page = page(
        50,
        """3M Company and Subsidiaries
Consolidated Balance Sheet
(Dollars in millions, except per share amount) 2022 2021
Total assets $ 46,455 $ 47,072
""",
    )
    income = extract_statement_series(
        SeriesExtractInput(
            page_id=income_page["artifact_id"],
            row_label="Net income attributable to 3M",
            metric_code="net_income",
        ),
        income_page,
        doc,
    )
    assets = extract_statement_series(
        SeriesExtractInput(
            page_id=assets_page["artifact_id"],
            row_label="Total assets",
            metric_code="total_assets",
        ),
        assets_page,
        doc,
    )
    calculation = calculate_series_metric(
        SeriesCalculateInput(
            formula="flow_to_average_balance_percent",
            series_ids=[income["series_id"], assets["series_id"]],
            period_label="2022FY",
            round_decimals=1,
        ),
        {income["series_id"]: income, assets["series_id"]: assets},
    )
    assert calculation["value"] == "12.4"
    assert calculation["per_period"][0]["average_balance"] == "46763.5"
    assert calculation["measurement_unit"] == "PERCENT"


def test_flow_to_average_balance_percent_requires_prior_balance() -> None:
    series = {
        "series_income": {
            "series_id": "series_income",
            "document_id": "doc_test",
            "currency": "USD",
            "canonical_scale": 1_000_000,
            "measurement_unit": "CURRENCY",
            "values": [
                {
                    "fiscal_year": 2022,
                    "fiscal_period": "FY",
                    "period_label": "2022FY",
                    "normalized_value": "10",
                }
            ],
        },
        "series_assets": {
            "series_id": "series_assets",
            "document_id": "doc_test",
            "currency": "USD",
            "canonical_scale": 1_000_000,
            "measurement_unit": "CURRENCY",
            "values": [
                {
                    "fiscal_year": 2022,
                    "fiscal_period": "FY",
                    "period_label": "2022FY",
                    "normalized_value": "100",
                }
            ],
        },
    }
    with pytest.raises(ValueError, match="immediately prior period"):
        calculate_series_metric(
            SeriesCalculateInput(
                formula="flow_to_average_balance_percent",
                series_ids=["series_income", "series_assets"],
                period_label="2022FY",
            ),
            series,
        )


def test_capital_intensity_methodology_uses_direct_capital_demand_and_limits_classification(
    tmp_path: Path,
) -> None:
    repo = ResearchRepository(tmp_path)
    request = ResearchRequest(
        company_query="Methodology Test Co",
        market_hint="US",
        requested_period_label="2022FY",
        research_question="Is this company capital-intensive based on FY2022 data?",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="capital-intensity-methodology-test",
    )
    manifest, _ = repo.create(request, {})
    doc = document()
    income_page = page(
        48,
        """Consolidated Statement of Income
(Millions, except per share amounts) 2022 2021 2020
Net sales $ 34,229 $ 35,355 $ 32,184
""",
    )
    cash_page = page(
        52,
        """Consolidated Statement of Cash Flows
(Millions) 2022 2021 2020
Purchases of property, plant and equipment $ (1,749) $ (1,603) $ (1,501)
""",
    )
    assets_page = page(
        50,
        """Consolidated Balance Sheet
(Dollars in millions) 2022 2021
Property, plant and equipment — net 9,178 9,429
Total assets $ 46,455 $ 47,072
""",
    )
    environment = {
        "schema_version": "2.0.0",
        "entity": doc["company"],
        "documents": {doc["document_id"]: doc},
        "objects": {
            income_page["artifact_id"]: income_page,
            cash_page["artifact_id"]: cash_page,
            assets_page["artifact_id"]: assets_page,
        },
        "facts": {},
        "gaps": [],
    }
    tools = FilingTools(repo, manifest["run_id"], request, environment, lambda: None)

    def extract(call: str, page_id: str, row_label: str, metric_code: str) -> dict:
        return tools.execute(
            call,
            "extract_statement_series",
            {"page_id": page_id, "row_label": row_label, "metric_code": metric_code},
        )

    revenue = extract("method-revenue", income_page["artifact_id"], "Net sales", "revenue")
    capex = extract(
        "method-capex",
        cash_page["artifact_id"],
        "Purchases of property, plant and equipment",
        "capital_expenditures",
    )
    fixed_assets = extract(
        "method-fixed-assets",
        assets_page["artifact_id"],
        "Property, plant and equipment — net",
        "fixed_assets",
    )
    total_assets = extract(
        "method-total-assets",
        assets_page["artifact_id"],
        "Total assets",
        "total_assets",
    )
    capex_ratio = tools.execute(
        "method-capex-ratio",
        "calculate_series_metric",
        {
            "formula": "ratio_percent",
            "series_ids": [capex["series_id"], revenue["series_id"]],
            "period_label": "2022FY",
            "round_decimals": 2,
        },
    )
    fixed_asset_intensity = tools.execute(
        "method-fixed-intensity",
        "calculate_series_metric",
        {
            "formula": "average_balance_to_flow_percent",
            "series_ids": [fixed_assets["series_id"], revenue["series_id"]],
            "period_label": "2022FY",
            "round_decimals": 2,
        },
    )
    assert capex_ratio["value"] == "5.11"
    assert fixed_asset_intensity["value"] == "27.18"
    evidence_ids = [
        revenue["evidence_id"],
        capex["evidence_id"],
        fixed_assets["evidence_id"],
        total_assets["evidence_id"],
        capex_ratio["calculation_id"],
        fixed_asset_intensity["calculation_id"],
    ]
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_capital_intensity",
                        "question": "Is the company capital-intensive?",
                        "priority": "required",
                        "status": "answered",
                        "evidence_ids": evidence_ids,
                        "conclusion": (
                            f"Direct measures include {capex_ratio['calculation_id']} and "
                            f"{fixed_asset_intensity['calculation_id']}."
                        ),
                        "remaining_uncertainty": "Total-asset intensity is still missing.",
                    }
                ],
                "hypotheses": [],
                "open_questions": [],
                "core_question_status": "answerable",
                "expected_value_of_more_research": "low",
            }
        )
    )
    incomplete = tools.completeness()
    methodology = incomplete["methodology_checks"][0]
    assert methodology["methodology_id"] == "capital_intensity_direct_v2"
    assert methodology["status"] == "calculation_pending"
    assert methodology["missing_dimensions"] == ["total_asset_intensity"]
    assert methodology["ready_to_calculate_dimensions"] == ["total_asset_intensity"]
    assert methodology["missing_input_dimensions"] == []
    assert "capital_intensity_calculation_pending" in incomplete["submission_blockers"]

    # A categorical classification may ultimately be evidence-exhausted, but that is not a
    # license to skip deterministic calculations when all required filing inputs are available.
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_capital_intensity",
                        "question": "Is the company capital-intensive?",
                        "priority": "required",
                        "status": "limited",
                        "evidence_ids": evidence_ids,
                        "conclusion": (
                            "The filing contains the direct capital-demand inputs but has no "
                            "classification threshold."
                        ),
                        "remaining_uncertainty": (
                            "Total-asset intensity still requires deterministic calculation, "
                            "and the filing has no categorical threshold."
                        ),
                    }
                ],
                "hypotheses": [],
                "open_questions": [],
                "core_question_status": "evidence_exhausted",
                "expected_value_of_more_research": "low",
            }
        )
    )
    exhausted_before_calc = tools.completeness()
    assert exhausted_before_calc["submission_blockers"] == ["capital_intensity_calculation_pending"]
    assert exhausted_before_calc["required_before_submit"] == ["calculate_series_metric"]
    rejected = tools.execute(
        "method-submit-before-total-intensity",
        "submit_research",
        {
            "stop_reason": "evidence_exhausted",
            "direct_answer": "cannot_determine",
            "summary": "The classification is not available from the filing alone.",
            "evidence_ids": evidence_ids,
            "remaining_uncertainties": ["A direct capital-demand calculation is still pending."],
            "why_stop": "No filing-linked categorical threshold is available.",
        },
    )
    assert rejected["error"] == "TOOL_INPUT_REJECTED"
    assert "cannot skip deterministic calculations" in rejected["message"]

    total_asset_intensity = tools.execute(
        "method-total-intensity",
        "calculate_series_metric",
        {
            "formula": "average_balance_to_flow_percent",
            "series_ids": [total_assets["series_id"], revenue["series_id"]],
            "period_label": "2022FY",
            "round_decimals": 2,
        },
    )
    assert total_asset_intensity["value"] == "136.62"
    complete = tools.completeness()
    method = complete["methodology_checks"][0]
    assert method["status"] == "complete"
    assert method["classification_status"] == "absolute_metrics_only"
    assert complete["submission_blockers"] == []
    assert complete["required_before_submit"] == ["submit_research"]

    # The filing has enough data to describe capital demand, but no linked threshold or explicit
    # classification. Preserve that boundary rather than inventing a categorical yes/no cutoff.
    limited_evidence = [*evidence_ids, total_asset_intensity["calculation_id"]]
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_capital_intensity",
                        "question": "Is the company capital-intensive?",
                        "priority": "required",
                        "status": "limited",
                        "evidence_ids": limited_evidence,
                        "conclusion": (
                            "The filing supports absolute capital-demand measures but not an "
                            "industry-relative categorical classification."
                        ),
                        "remaining_uncertainty": (
                            "No filing-linked capital-intensity threshold or peer benchmark exists."
                        ),
                    }
                ],
                "hypotheses": [],
                "open_questions": [],
                "core_question_status": "evidence_exhausted",
                "expected_value_of_more_research": "low",
            }
        )
    )
    assert tools.completeness()["required_before_submit"] == ["submit_research"]


def test_net_earnings_label_is_valid_net_income_series() -> None:
    doc = document()
    income_page = page(
        56,
        """Consolidated Statements of Earnings
($ in millions) 2017 2016 2015
Revenue $ 39,403 $ 39,528 $ 40,339
Net earnings including noncontrolling interests 1,228 897 1,235
""",
    )
    revenue = extract_statement_series(
        SeriesExtractInput(
            page_id=income_page["artifact_id"],
            row_label="Revenue",
            metric_code="revenue",
        ),
        income_page,
        doc,
    )
    earnings = extract_statement_series(
        SeriesExtractInput(
            page_id=income_page["artifact_id"],
            row_label="Net earnings including noncontrolling interests",
            metric_code="net_income",
        ),
        income_page,
        doc,
    )
    calculation = calculate_series_metric(
        SeriesCalculateInput(
            formula="average_ratio_percent",
            series_ids=[earnings["series_id"], revenue["series_id"]],
            round_decimals=1,
        ),
        {earnings["series_id"]: earnings, revenue["series_id"]: revenue},
    )
    assert calculation["value"] == "2.8"


def test_capital_intensity_methodology_allows_explicit_limited_objective(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    request = ResearchRequest(
        company_query="Limited Methodology Co",
        market_hint="US",
        requested_period_label="2022FY",
        research_question="Is this company capital-intensive based on FY2022 data?",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="capital-intensity-methodology-limited-test",
    )
    manifest, _ = repo.create(request, {})
    doc = document()
    evidence_page = page(
        10,
        """Capital investment discussion
The filing does not provide a recoverable prior-year balance needed for direct
capital-intensity measurement.
""",
    )
    environment = {
        "schema_version": "2.0.0",
        "entity": doc["company"],
        "documents": {doc["document_id"]: doc},
        "objects": {evidence_page["artifact_id"]: evidence_page},
        "facts": {},
        "gaps": ["Prior-year total assets could not be recovered reliably."],
    }
    tools = FilingTools(repo, manifest["run_id"], request, environment, lambda: None)
    read = tools.execute(
        "limited-read",
        "read_filing",
        {"artifact_id": evidence_page["artifact_id"], "offset": 0, "max_chars": 1200},
    )
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_capital_intensity",
                        "question": "Is the company capital-intensive?",
                        "priority": "required",
                        "status": "limited",
                        "evidence_ids": [read["evidence_id"]],
                        "conclusion": (
                            "The filing supports only a limited capital-intensity conclusion."
                        ),
                        "remaining_uncertainty": (
                            "Average-asset capital intensity cannot be computed because a "
                            "comparable prior total-assets balance could not be recovered reliably."
                        ),
                    }
                ],
                "hypotheses": [
                    {
                        "hypothesis_id": "h_limited",
                        "statement": (
                            "Available filing evidence is insufficient for full triangulation."
                        ),
                        "status": "unresolved",
                        "materiality": "major",
                        "evidence_for": [read["evidence_id"]],
                        "evidence_against": [],
                        "unknowns": ["A direct capital-demand dimension is unavailable."],
                        "would_change_conclusion": (
                            "Recovering a reliable prior-year asset balance."
                        ),
                        "confidence": "low",
                    }
                ],
                "open_questions": [],
                "core_question_status": "evidence_exhausted",
                "expected_value_of_more_research": "low",
            }
        )
    )
    completeness = tools.completeness()
    assert completeness["methodology_checks"][0]["status"] == "incomplete"
    assert "capital_intensity_methodology_incomplete" not in completeness["submission_blockers"]


def test_chinese_statement_series_preserves_metric_alias_currency_and_wan_unit() -> None:
    cn_document = {
        **document(),
        "company": {
            "company_id": "cn_series_test",
            "legal_name": "中文测试公司",
            "market": "CN",
            "country_code": "CN",
        },
    }
    cn_page = {
        **page(
            12,
            """某公司现金流量表
单位\uff1a万元
2025 2024
资本开支 1,234 1,000
营业收入 9,000 8,000
""",
        ),
        "document_id": cn_document["document_id"],
    }
    capex = extract_statement_series(
        SeriesExtractInput(
            page_id=cn_page["artifact_id"],
            row_label="资本开支",
            metric_code="capital_expenditures",
        ),
        cn_page,
        cn_document,
    )
    revenue = extract_statement_series(
        SeriesExtractInput(
            page_id=cn_page["artifact_id"],
            row_label="营业收入",
            metric_code="revenue",
        ),
        cn_page,
        cn_document,
    )
    assert capex["currency"] == "CNY"
    assert capex["canonical_scale"] == 10_000
    assert capex["scale_label"] == "万元"
    assert capex["values"][0]["period_label"] == "2025FY"
    assert capex["values"][0]["normalized_value"] == "1234"
    assert capex["values"][0]["base_unit_value"] == "12340000"
    assert revenue["values"][0]["normalized_value"] == "9000"


def test_legacy_series_calculation_arguments_are_migrated_without_model_arithmetic(
    tmp_path: Path,
) -> None:
    repo = ResearchRepository(tmp_path)
    request = ResearchRequest(
        company_query="Series Test Co",
        market_hint="US",
        requested_period_label="2019FY",
        research_question="What is the three-year average capex as a percent of revenue?",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="legacy-series-calc-protocol-test",
    )
    manifest, _ = repo.create(request, {})
    doc = document()
    revenue_page = page(70, REVENUE_PAGE)
    capex_page = page(73, CAPEX_PAGE)
    environment = {
        "schema_version": "2.0.0",
        "entity": doc["company"],
        "documents": {doc["document_id"]: doc},
        "objects": {
            revenue_page["artifact_id"]: revenue_page,
            capex_page["artifact_id"]: capex_page,
        },
        "facts": {},
        "gaps": [],
    }
    tools = FilingTools(repo, manifest["run_id"], request, environment, lambda: None)
    revenue = tools.execute(
        "legacy-series-revenue",
        "extract_statement_series",
        {
            "page_id": revenue_page["artifact_id"],
            "row_label": "Total net revenues",
            "metric_code": "revenue",
        },
    )
    capex = tools.execute(
        "legacy-series-capex",
        "extract_statement_series",
        {
            "page_id": capex_page["artifact_id"],
            "row_label": "Capital expenditures",
            "metric_code": "capital_expenditures",
        },
    )
    # Exact legacy shape observed in a real FinanceBench run.
    legacy_arguments = {
        "metric": "average_ratio_percent",
        "numerator_series_id": capex["series_id"],
        "denominator_series_id": revenue["series_id"],
    }
    first = tools.execute("legacy-series-calc-1", "calculate_series_metric", legacy_arguments)
    assert first["status"] == "valid"
    assert first["formula_code"] == "average_ratio_percent"
    assert first["input_series_ids"] == [capex["series_id"], revenue["series_id"]]
    assert first["protocol_migration"]["from"] == "legacy_series_pair_v1"
    assert first["calculation_id"] in tools.calculations
    receipt = tools.receipts["legacy-series-calc-1"]
    assert receipt["normalized_arguments"] == {
        "formula": "average_ratio_percent",
        "series_ids": [capex["series_id"], revenue["series_id"]],
        "round_decimals": 4,
        "period_label": None,
    }
    repeated = tools.execute("legacy-series-calc-2", "calculate_series_metric", legacy_arguments)
    assert repeated["reused_cached_result"] is True
    assert repeated["calculation_id"] == first["calculation_id"]
    assert any(
        event["event_type"] == "tool_protocol_migrated" for event in repo.events(manifest["run_id"])
    )


def test_failed_tool_result_is_never_reused_as_no_new_information(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    request = ResearchRequest(
        company_query="Series Test Co",
        market_hint="US",
        requested_period_label="2019FY",
        research_question="What is the three-year average capex as a percent of revenue?",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="failed-tool-cache-test",
    )
    manifest, _ = repo.create(request, {})
    doc = document()
    environment = {
        "schema_version": "2.0.0",
        "entity": doc["company"],
        "documents": {doc["document_id"]: doc},
        "objects": {},
        "facts": {},
        "gaps": [],
    }
    tools = FilingTools(repo, manifest["run_id"], request, environment, lambda: None)
    invalid_arguments = {"metric": "average_ratio_percent"}
    first = tools.execute("invalid-series-calc-1", "calculate_series_metric", invalid_arguments)
    second = tools.execute("invalid-series-calc-2", "calculate_series_metric", invalid_arguments)
    assert first["error"] == second["error"] == "INVALID_TOOL_ARGUMENTS"
    assert "reused_cached_result" not in second
    assert tools.receipts["invalid-series-calc-2"]["reused"] is False


def test_research_state_percentage_gate_uses_run_wide_source_provenance(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    request = ResearchRequest(
        company_query="Series Test Co",
        market_hint="US",
        requested_period_label="2019FY",
        research_question="Explain the year-over-year operating performance change.",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="run-wide-reported-percentage-test",
    )
    manifest, _ = repo.create(request, {})
    doc = document()
    narrative = page(80, "Gross profit changed year over year; explain the filing drivers.")
    reported = page(
        81,
        """Percent Change | Percent of Net Sales
2025 | 2024 | Change | 2025 | 2024
Gross profit | $ | 362.9 | $ | 364.1 | $ | (1.2) | (0.3) | % | 18.3 | % | 18.4 | %
""",
    )
    environment = {
        "schema_version": "2.0.0",
        "entity": doc["company"],
        "documents": {doc["document_id"]: doc},
        "objects": {
            narrative["artifact_id"]: narrative,
            reported["artifact_id"]: reported,
        },
        "facts": {},
        "gaps": [],
    }
    tools = FilingTools(repo, manifest["run_id"], request, environment, lambda: None)
    tools.execute(
        "observe-reported-percentages",
        "search_filing",
        {
            "query": "gross profit percent net sales",
            "kind": "page",
            "document_id": doc["document_id"],
            "offset": 0,
            "limit": 3,
        },
    )
    narrative_evidence_id = tools._observe(narrative, narrative["text"])
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_operating_change",
                        "question": "Explain the year-over-year operating performance change.",
                        "priority": "required",
                        "status": "answered",
                        "evidence_ids": [narrative_evidence_id],
                        "conclusion": "Gross profit margin was 18.3% vs 18.4%, down -0.3%.",
                        "remaining_uncertainty": "",
                    }
                ],
                "core_question_status": "answerable",
                "expected_value_of_more_research": "low",
            }
        )
    )
    assert (
        "derived_percentage_calculation_missing" not in tools.completeness()["submission_blockers"]
    )


def test_table_internal_thousands_header_wins_even_with_long_adjacent_context() -> None:
    doc = document()
    source = {
        "artifact_id": "table_series_test_long_context",
        "kind": "table",
        "document_id": doc["document_id"],
        "text": """Year ended December 31,
2025 2024 2023
(Dollars in thousands)
Operating activities:
Net income $ 228,213 $ 217,540 $ 192,296
""",
        "context_text": "\n".join(f"Nearby narrative line {index}" for index in range(30)),
        "source_uri": doc["source_uri"],
        "published_at": doc["published_at"],
        "page_id": None,
        "page_number": None,
    }
    result = extract_statement_series(
        SeriesExtractInput(
            artifact_id=source["artifact_id"],
            row_label="Net income",
            metric_code="net_income",
        ),
        source,
        doc,
    )
    assert result["canonical_scale"] == 1_000
    assert result["scale_label"] == "thousands"
    assert result["values"][0]["normalized_value"] == "228213"
    assert result["values"][0]["base_unit_value"] == "228213000"


def test_series_calculation_reuses_semantic_result_across_rounding_variants(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = ResearchRequest(
        company_query="Series Test Co",
        market_hint="US",
        requested_period_label="2019FY",
        research_question="What is FY2019 capex as a percent of revenue?",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="semantic-rounding-reuse-test",
    )
    manifest, _ = repo.create(req, {})
    doc = document()
    revenue_page = page(70, REVENUE_PAGE)
    capex_page = page(73, CAPEX_PAGE)
    env = {
        "schema_version": "2.0.0",
        "entity": doc["company"],
        "documents": {doc["document_id"]: doc},
        "objects": {
            revenue_page["artifact_id"]: revenue_page,
            capex_page["artifact_id"]: capex_page,
        },
        "facts": {},
        "gaps": [],
    }
    tools = FilingTools(repo, manifest["run_id"], req, env, lambda: None)
    revenue = tools.execute(
        "rounding-revenue",
        "extract_statement_series",
        {
            "artifact_id": revenue_page["artifact_id"],
            "row_label": "Total net revenues",
            "metric_code": "revenue",
        },
    )
    capex = tools.execute(
        "rounding-capex",
        "extract_statement_series",
        {
            "artifact_id": capex_page["artifact_id"],
            "row_label": "Capital expenditures",
            "metric_code": "capital_expenditures",
        },
    )
    first = tools.execute(
        "rounding-calc-1",
        "calculate_series_metric",
        {
            "formula": "ratio_percent",
            "series_ids": [capex["series_id"], revenue["series_id"]],
            "round_decimals": 2,
            "period_label": "2019FY",
        },
    )
    second = tools.execute(
        "rounding-calc-2",
        "calculate_series_metric",
        {
            "formula": "ratio_percent",
            "series_ids": [capex["series_id"], revenue["series_id"]],
            "round_decimals": 4,
            "period_label": "2019FY",
        },
    )
    assert second["semantic_reuse"] is True
    assert second["calculation_id"] == first["calculation_id"]
    assert second["requested_round_decimals"] == 4
    assert len(tools.calculations) == 1


def test_answered_objective_prunes_only_unsupported_convenience_percentage(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = ResearchRequest(
        company_query="Series Test Co",
        market_hint="US",
        requested_period_label="2019FY",
        research_question="What is FY2019 capex as a percent of revenue?",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="unsupported-convenience-percentage-test",
    )
    manifest, _ = repo.create(req, {})
    doc = document()
    revenue_page = page(70, REVENUE_PAGE)
    capex_page = page(73, CAPEX_PAGE)
    env = {
        "schema_version": "2.0.0",
        "entity": doc["company"],
        "documents": {doc["document_id"]: doc},
        "objects": {
            revenue_page["artifact_id"]: revenue_page,
            capex_page["artifact_id"]: capex_page,
        },
        "facts": {},
        "gaps": [],
    }
    tools = FilingTools(repo, manifest["run_id"], req, env, lambda: None)
    revenue = tools.execute(
        "prune-revenue",
        "extract_statement_series",
        {
            "artifact_id": revenue_page["artifact_id"],
            "row_label": "Total net revenues",
            "metric_code": "revenue",
        },
    )
    capex = tools.execute(
        "prune-capex",
        "extract_statement_series",
        {
            "artifact_id": capex_page["artifact_id"],
            "row_label": "Capital expenditures",
            "metric_code": "capital_expenditures",
        },
    )
    calculation = tools.execute(
        "prune-calc",
        "calculate_series_metric",
        {
            "formula": "ratio_percent",
            "series_ids": [capex["series_id"], revenue["series_id"]],
            "round_decimals": 2,
            "period_label": "2019FY",
        },
    )
    applied = tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_ratio",
                        "question": "What is FY2019 capex as a percent of revenue?",
                        "priority": "required",
                        "status": "answered",
                        "evidence_ids": [calculation["calculation_id"]],
                        "conclusion": (
                            f"FY2019 capex/revenue is {calculation['value']}%. "
                            "This means capex is about 98% below revenue."
                        ),
                        "remaining_uncertainty": "",
                    }
                ],
                "hypotheses": [],
                "open_questions": [],
                "decision_summary": "The deterministic ratio answers the question.",
                "core_question_status": "answerable",
                "expected_value_of_more_research": "low",
            }
        )
    )
    conclusion = tools.working.objectives[0].conclusion
    assert f"{calculation['value']}%" in conclusion
    assert "98%" not in conclusion
    assert any(
        item.get("correction")
        == "unsupported_convenience_percentage_removed_from_answered_objective"
        for item in applied["reference_corrections"]
    )
    assert tools.completeness()["required_before_submit"] == ["submit_research"]


def test_focused_amount_objective_prunes_unsupported_ancillary_percentage_without_calculation(
    tmp_path: Path,
) -> None:
    repo = ResearchRepository(tmp_path)
    req = ResearchRequest(
        company_query="Series Test Co",
        market_hint="US",
        requested_period_label="2019FY",
        research_question=(
            "What revenue amount does the annual filing report for FY2019? "
            "State the exact value, unit and period."
        ),
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="focused-amount-ancillary-percentage-prune",
    )
    manifest, _ = repo.create(req, {})
    doc = document()
    revenue_page = page(70, REVENUE_PAGE)
    env = {
        "schema_version": "2.0.0",
        "entity": doc["company"],
        "documents": {doc["document_id"]: doc},
        "objects": {revenue_page["artifact_id"]: revenue_page},
        "facts": {},
        "gaps": [],
    }
    tools = FilingTools(repo, manifest["run_id"], req, env, lambda: None)
    revenue = tools.execute(
        "focused-revenue-series",
        "extract_statement_series",
        {
            "artifact_id": revenue_page["artifact_id"],
            "row_label": "Total net revenues",
            "metric_code": "revenue",
        },
    )
    applied = tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_revenue",
                        "question": "What is the exact FY2019 revenue amount?",
                        "priority": "required",
                        "status": "answered",
                        "evidence_ids": [revenue["evidence_id"]],
                        "conclusion": (
                            "FY2019 total net revenues were $6,489 million. "
                            "Revenue decreased 5.7% from the prior year."
                        ),
                        "remaining_uncertainty": "",
                    }
                ],
                "hypotheses": [],
                "open_questions": [],
                "decision_summary": "The exact revenue value is verified.",
                "core_question_status": "answerable",
                "expected_value_of_more_research": "low",
            }
        )
    )
    conclusion = tools.working.objectives[0].conclusion
    assert "$6,489 million" in conclusion
    assert "5.7%" not in conclusion
    assert tools.calculations == {}
    assert any(
        item.get("correction")
        == "unsupported_convenience_percentage_removed_from_answered_objective"
        and item.get("focused_ancillary_percentage") is True
        for item in applied["reference_corrections"]
    )
    assert tools.completeness()["required_before_submit"] == ["submit_research"]
