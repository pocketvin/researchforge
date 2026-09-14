"""Derived percentages require deterministic provenance; reported percentages remain valid."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from researchforge.v2.contracts import ResearchReport, ResearchRequest, SemanticReview
from researchforge.v2.documents import windows
from researchforge.v2.numeric_provenance import percentage_mentions, reported_percentage_values
from researchforge.v2.validation import validate_report, validate_review


def tools_for(*, evidence_text: str, calculations: dict | None = None) -> SimpleNamespace:
    request = ResearchRequest(
        company_query="Synthetic",
        market_hint="US",
        requested_period_label="2022FY",
        research_question="Is the business capital intensive?",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="numeric-provenance-test",
    )
    return SimpleNamespace(
        dossier={"evidence_ids": ["view_source"], "direct_answer": "no"},
        request=request,
        working=SimpleNamespace(objectives=[SimpleNamespace(priority="required")]),
        calculations=calculations or {},
        observed={
            "view_source": {
                "artifact_id": "view_source",
                "document_id": "doc_source",
                "published_at": "2026-01-01T00:00:00+00:00",
                "text": evidence_text,
            }
        },
        environment={
            "entity": {"company_id": "synthetic_company"},
            "documents": {"doc_source": {"company": {"company_id": "synthetic_company"}}},
            "facts": {},
        },
    )


def report_for(
    *,
    percentage: str,
    calculation_ids: list[str] | None = None,
    numeric_assertions: list[dict] | None = None,
) -> ResearchReport:
    return ResearchReport.model_validate(
        {
            "direct_answer": "no",
            "title": "Synthetic report",
            "executive_summary": f"The relevant ratio is {percentage}.",
            "findings": [
                {
                    "claim_id": "claim_ratio",
                    "title": "Ratio assessment",
                    "text": f"The relevant ratio is {percentage}.",
                    "kind": "inference",
                    "evidence_ids": ["view_source"],
                    "fact_ids": [],
                    "calculation_ids": calculation_ids or [],
                    "numeric_assertions": numeric_assertions or [],
                    "confidence": "medium",
                    "uncertainty": "Synthetic validation case.",
                }
            ],
            "sections": [
                {
                    "title": "Analysis",
                    "text": f"The relevant ratio is {percentage}.",
                    "evidence_ids": ["view_source"],
                }
            ],
            "limitations": ["Synthetic validation case only."],
            "follow_up_questions": [],
        }
    )


def test_derived_percentage_without_calculation_is_rejected() -> None:
    tools = tools_for(evidence_text="Revenue 34,229 and capex 1,749, USD millions.")
    validation = validate_report(report_for(percentage="5.1%"), tools)  # type: ignore[arg-type]
    assert validation["passed"] is False
    assert any(
        "DERIVED_PERCENTAGE_WITHOUT_CALCULATION: 5.1%" in error for error in validation["errors"]
    )


def test_percentage_reported_by_source_table_does_not_require_new_calculation() -> None:
    tools = tools_for(
        evidence_text=(
            "(Percent of net sales) 2022 2021 Change\n"
            "Selling, general and administrative expenses (SG&A) 26.5 20.4 6.1\n"
            "Research, development and related expenses (R&D) 5.4 5.6 (0.2)"
        )
    )
    validation = validate_report(report_for(percentage="26.5%"), tools)  # type: ignore[arg-type]
    assert validation["passed"] is True
    assert not any("DERIVED_PERCENTAGE" in error for error in validation["errors"])


def test_percentage_backed_by_calculation_record_is_valid() -> None:
    calculations = {
        "calc_ratio": {
            "calculation_id": "calc_ratio",
            "measurement_unit": "PERCENT",
            "value": "5.1",
            "unrounded_value": "5.109",
        }
    }
    tools = tools_for(
        evidence_text="Revenue 34,229 and capex 1,749, USD millions.",
        calculations=calculations,
    )
    report = report_for(
        percentage="5.1%",
        calculation_ids=["calc_ratio"],
        numeric_assertions=[{"source_id": "calc_ratio", "value": "5.1"}],
    )
    validation = validate_report(report, tools)  # type: ignore[arg-type]
    assert validation["passed"] is True
    assert validation["checks"]["declared_numeric_assertions_checked"] == 1
    assert validation["checks"]["unsupported_percentage_mentions"] == 0


def test_existing_calculation_missing_from_finding_is_report_linkage_error() -> None:
    calculations = {
        "calc_ratio": {
            "calculation_id": "calc_ratio",
            "measurement_unit": "PERCENT",
            "value": "5.11",
            "unrounded_value": "5.1097022992",
        }
    }
    tools = tools_for(
        evidence_text="Revenue 34,229 and capex 1,749, USD millions.",
        calculations=calculations,
    )
    validation = validate_report(report_for(percentage="5.1%"), tools)  # type: ignore[arg-type]
    assert validation["passed"] is False
    assert any("PERCENTAGE_PROVENANCE_NOT_LINKED: 5.1%" in error for error in validation["errors"])
    assert not any(
        "DERIVED_PERCENTAGE_WITHOUT_CALCULATION" in error for error in validation["errors"]
    )


def test_binary_report_cannot_change_research_direct_answer() -> None:
    tools = tools_for(evidence_text="The filing supports the answer.")
    report = report_for(percentage="26.5%").model_copy(update={"direct_answer": "yes"})
    validation = validate_report(report, tools)  # type: ignore[arg-type]
    assert validation["passed"] is False
    assert any("DIRECT_ANSWER_MISMATCH" in error for error in validation["errors"])


def test_user_facing_report_rejects_internal_run_identifiers() -> None:
    tools = tools_for(evidence_text="(Percent of net sales) 2022 2021\nSG&A 26.5 20.4")
    report = report_for(percentage="26.5%").model_copy(
        update={"executive_summary": "The filing reports 26.5%; see view_source and calc_ratio."}
    )
    validation = validate_report(report, tools)  # type: ignore[arg-type]
    assert validation["passed"] is False
    assert any("INTERNAL_IDENTIFIER_IN_USER_PROSE" in error for error in validation["errors"])


def test_user_facing_report_rejects_raw_snake_case_metric_names() -> None:
    tools = tools_for(evidence_text="Net income was USD 100 million in FY2022.")
    report = report_for(percentage="100").model_copy(
        update={"executive_summary": "The verified net_income value is USD 100 million."}
    )
    validation = validate_report(report, tools)  # type: ignore[arg-type]
    assert validation["passed"] is False
    assert any("INTERNAL_SNAKE_CASE_IN_USER_PROSE" in error for error in validation["errors"])


def test_english_question_rejects_chinese_user_facing_report() -> None:
    tools = tools_for(evidence_text="Revenue was USD 100 million in FY2022.")
    tools.request = tools.request.model_copy(
        update={"research_question": "What was FY2022 revenue?"}
    )
    tools.dossier["direct_answer"] = "not_applicable"
    report = report_for(percentage="100").model_copy(
        update={
            "direct_answer": "not_applicable",
            "executive_summary": "FY2022 总收入为 100 million USD。",
        }
    )
    validation = validate_report(report, tools)  # type: ignore[arg-type]
    assert validation["passed"] is False
    assert any(error.startswith("REPORT_LANGUAGE_MISMATCH") for error in validation["errors"])


def test_focused_extraction_rejects_overlong_executive_summary() -> None:
    tools = tools_for(evidence_text="Revenue was USD 100 million in FY2022.")
    tools.request = tools.request.model_copy(
        update={"research_question": "What was FY2022 revenue?"}
    )
    tools.dossier["direct_answer"] = "not_applicable"
    report = report_for(percentage="100").model_copy(
        update={
            "direct_answer": "not_applicable",
            "executive_summary": "A" * 1001,
        }
    )
    validation = validate_report(report, tools)  # type: ignore[arg-type]
    assert validation["passed"] is False
    assert any(
        error.startswith("FOCUSED_EXECUTIVE_SUMMARY_TOO_LONG") for error in validation["errors"]
    )


def test_semantic_partial_and_unverifiable_are_report_repair_errors() -> None:
    report = report_for(percentage="26.5%")
    for verdict in ("partial", "unverifiable"):
        review = SemanticReview.model_validate(
            {
                "claims": [
                    {
                        "claim_id": "claim_ratio",
                        "verdict": verdict,
                        "reason": "The cited evidence does not fully support the complete claim.",
                    }
                ],
                "question_answered": True,
                "missing_material_topics": [],
            }
        )
        errors = validate_review(report, review)
        assert len(errors) == 1
        assert f": {verdict}:" in errors[0]


def test_display_rounding_from_calculation_allows_approximate_twenty_percent() -> None:
    calculations = {
        "calc_asset_share": {
            "calculation_id": "calc_asset_share",
            "measurement_unit": "PERCENT",
            "value": "19.76",
            "unrounded_value": "19.75675384888602",
        }
    }
    tools = tools_for(
        evidence_text="Net PP&E and total assets are reported in USD millions.",
        calculations=calculations,
    )
    report = report_for(
        percentage="about 20%",
        calculation_ids=["calc_asset_share"],
        numeric_assertions=[{"source_id": "calc_asset_share", "value": "19.76"}],
    )
    validation = validate_report(report, tools)  # type: ignore[arg-type]
    assert validation["passed"] is True
    assert validation["checks"]["unsupported_percentage_mentions"] == 0


def test_comparison_threshold_does_not_inherit_nearby_calculation_provenance() -> None:
    calculations = {
        "calc_asset_share": {
            "calculation_id": "calc_asset_share",
            "measurement_unit": "PERCENT",
            "value": "19.76",
            "unrounded_value": "19.75675384888602",
        }
    }
    tools = tools_for(
        evidence_text="Net PP&E and total assets are reported in USD millions.",
        calculations=calculations,
    )
    validation = validate_report(
        report_for(percentage="sub-20%", calculation_ids=["calc_asset_share"]),
        tools,  # type: ignore[arg-type]
    )
    assert validation["passed"] is False
    assert any(
        "DERIVED_PERCENTAGE_WITHOUT_CALCULATION: 20%" in error for error in validation["errors"]
    )


def test_explicit_less_than_threshold_is_not_treated_as_display_rounding() -> None:
    calculations = {
        "calc_asset_share": {
            "calculation_id": "calc_asset_share",
            "measurement_unit": "PERCENT",
            "value": "19.76",
            "unrounded_value": "19.75675384888602",
        }
    }
    tools = tools_for(
        evidence_text="Net PP&E and total assets are reported in USD millions.",
        calculations=calculations,
    )
    validation = validate_report(
        report_for(percentage="低于20%", calculation_ids=["calc_asset_share"]),
        tools,  # type: ignore[arg-type]
    )
    assert validation["passed"] is False
    assert any(
        "DERIVED_PERCENTAGE_WITHOUT_CALCULATION: 20%" in error for error in validation["errors"]
    )


def test_directly_reported_comparison_threshold_keeps_its_relation_provenance() -> None:
    tools = tools_for(evidence_text="The filing states that the ratio remained below 20%.")
    validation = validate_report(report_for(percentage="below 20%"), tools)  # type: ignore[arg-type]
    assert validation["passed"] is True
    assert validation["checks"]["unsupported_percentage_mentions"] == 0


def test_focused_extraction_rejects_extra_material_finding() -> None:
    tools = tools_for(evidence_text="Revenue was USD 100 million in FY2022.")
    tools.request = tools.request.model_copy(
        update={"research_question": "What was FY2022 revenue?"}
    )
    tools.dossier["direct_answer"] = "not_applicable"
    payload = {
        "direct_answer": "not_applicable",
        "title": "Focused revenue result",
        "executive_summary": "FY2022 revenue was USD 100 million.",
        "findings": [
            {
                "claim_id": "claim_revenue",
                "title": "FY2022 revenue",
                "text": "FY2022 revenue was USD 100 million.",
                "kind": "observation",
                "evidence_ids": ["view_source"],
                "fact_ids": [],
                "calculation_ids": [],
                "numeric_assertions": [],
                "confidence": "high",
                "uncertainty": "",
            },
            {
                "claim_id": "claim_label",
                "title": "Revenue line label",
                "text": "The filing uses a revenue line label.",
                "kind": "observation",
                "evidence_ids": ["view_source"],
                "fact_ids": [],
                "calculation_ids": [],
                "numeric_assertions": [],
                "confidence": "high",
                "uncertainty": "",
            },
        ],
        "sections": [
            {
                "title": "Source",
                "text": "The value is reported in the filing.",
                "evidence_ids": ["view_source"],
            }
        ],
        "limitations": ["Synthetic focused validation case."],
        "follow_up_questions": [],
    }
    expanded = ResearchReport.model_validate(payload)
    validation = validate_report(expanded, tools)  # type: ignore[arg-type]
    assert validation["passed"] is False
    assert any("FOCUSED_REPORT_SCOPE_EXPANDED" in error for error in validation["errors"])
    assert validation["checks"]["focused_material_findings"] == 2
    assert validation["checks"]["focused_scope_limit"] == 1

    payload["findings"] = payload["findings"][:1]
    focused = ResearchReport.model_validate(payload)
    validation = validate_report(focused, tools)  # type: ignore[arg-type]
    assert validation["passed"] is True


def test_native_table_pipe_percent_cells_preserve_reported_values_and_accounting_sign() -> None:
    tools = tools_for(
        evidence_text=(
            "Percent Change | Return on Net Sales\n"
            "FAM | $ | (359.8) | $ | 70.0 | $ | (429.8) | N.M. | (46.9) | % | 9.1 | %\n"
            "Total | $ | (384.4) | $ | 6.3 | $ | (390.7) | N.M. | (19.3) | % | 0.3 | %"
        )
    )
    for percentage in ("-46.9%", "9.1%", "-19.3%", "0.3%"):
        validation = validate_report(report_for(percentage=percentage), tools)  # type: ignore[arg-type]
        assert validation["passed"] is True, (percentage, validation["errors"])


def test_percent_change_table_context_recovers_sparse_percent_sign_cells() -> None:
    tools = tools_for(
        evidence_text=(
            "Percent Change in Net Sales\n"
            "FAM | SAS | Total\n"
            "Volume/mix | 0.1 | % | 2.0 | % | 1.3 | %\n"
            "Sales associated with exited facilities | — | (3.5) | (2.1)\n"
            "Total volume/mix | 0.1 | (1.5) | (0.8)\n"
            "Selling price | (1.1) | 1.0 | 0.2\n"
            "Currency translation | 1.1 | 0.9 | 0.9\n"
            "Total percent change | 0.1 | % | 0.4 | % | 0.3 | %"
        )
    )
    for percentage in ("-2.1%", "-0.8%", "+1.3%", "+0.2%", "+0.9%"):
        validation = validate_report(report_for(percentage=percentage), tools)  # type: ignore[arg-type]
        assert validation["passed"] is True, (percentage, validation["errors"])


def test_mixed_currency_table_does_not_promote_dollar_change_to_percentage() -> None:
    tools = tools_for(
        evidence_text=(
            "Percent Change | Return on Net Sales\n"
            "FAM | $ | (359.8) | $ | 70.0 | $ | (429.8) | N.M. | (46.9) | % | 9.1 | %"
        )
    )
    validation = validate_report(report_for(percentage="359.8%"), tools)  # type: ignore[arg-type]
    assert validation["passed"] is False
    assert any("DERIVED_PERCENTAGE" in error for error in validation["errors"])


def test_directional_percentage_survives_fixed_evidence_window_boundary() -> None:
    filing_text = "A " * 998 + "decreased 45% to $118 million." + " tail" * 100
    _start, evidence_text = windows(filing_text)[1]
    tools = tools_for(evidence_text=evidence_text)
    validation = validate_report(report_for(percentage="-45%"), tools)  # type: ignore[arg-type]
    assert validation["passed"] is True, validation["errors"]


def test_directional_decrease_percentage_matches_parenthetical_source_change() -> None:
    tools = tools_for(
        evidence_text=(
            "2025 Compared to 2024 % Change\n"
            "Total Softseed Segment EBIT | $ | 521 | $ | 663 | (21) | %"
        )
    )
    validation = validate_report(report_for(percentage="down 21%"), tools)  # type: ignore[arg-type]
    assert validation["passed"] is True

    suffix_direction = validate_report(
        report_for(percentage="the 21% Softseed EBIT decline"),
        tools,  # type: ignore[arg-type]
    )
    assert suffix_direction["passed"] is True

    bare = validate_report(report_for(percentage="21%"), tools)  # type: ignore[arg-type]
    assert bare["passed"] is False
    assert any("DERIVED_PERCENTAGE" in error for error in bare["errors"])


def test_percentage_direction_does_not_bind_to_later_clause_metric() -> None:
    text = (
        "Net interest margin was 4.55% versus 4.28%, primarily related to a 46 basis point "
        "decrease in the cost of funds."
    )
    mentions = percentage_mentions(text)
    assert [item["value"] for item in mentions] == [Decimal("4.55"), Decimal("4.28")]


def test_percentage_suffix_direction_still_binds_direct_decline_wording() -> None:
    mentions = percentage_mentions("Softseed EBIT recorded a 21% year-over-year decline.")
    assert [item["value"] for item in mentions] == [Decimal("-21")]


def test_percentage_present_elsewhere_in_dossier_is_linkage_error_not_new_derivation() -> None:
    tools = tools_for(evidence_text="Management fees declined year over year.")
    tools.dossier["evidence_ids"].append("view_fee_policy")
    tools.observed["view_fee_policy"] = {
        "artifact_id": "view_fee_policy",
        "document_id": "doc_source",
        "published_at": "2026-01-01T00:00:00+00:00",
        "text": "The management fee is 0.75% per annum of average daily total net assets.",
    }
    validation = validate_report(report_for(percentage="0.75%"), tools)  # type: ignore[arg-type]
    assert validation["passed"] is False
    assert any("PERCENTAGE_PROVENANCE_NOT_LINKED: 0.75%" in error for error in validation["errors"])
    assert not any(
        "DERIVED_PERCENTAGE_WITHOUT_CALCULATION: 0.75%" in error for error in validation["errors"]
    )


def test_report_rejects_filing_wide_absence_claim_from_nonobservation() -> None:
    tools = tools_for(evidence_text="The cited table reports total assets of USD 100 million.")
    report = report_for(percentage="100").model_copy(
        update={
            "executive_summary": (
                "The cited evidence does not establish the required peer comparison."
            ),
            "findings": [
                report_for(percentage="100")
                .findings[0]
                .model_copy(
                    update={
                        "kind": "limitation",
                        "text": (
                            "The filing contains no peer benchmark, so no relative classification "
                            "can be made."
                        ),
                    }
                )
            ],
        }
    )
    validation = validate_report(report, tools)  # type: ignore[arg-type]
    assert validation["passed"] is False
    assert any(
        "GLOBAL_ABSENCE_CLAIM_FROM_NONOBSERVATION" in error for error in validation["errors"]
    )


def test_report_allows_cited_evidence_boundary_without_global_absence() -> None:
    tools = tools_for(evidence_text="The cited table reports total assets of USD 100 million.")
    report = report_for(percentage="100").model_copy(
        update={
            "executive_summary": (
                "The cited evidence does not establish the required peer comparison."
            ),
            "findings": [
                report_for(percentage="100")
                .findings[0]
                .model_copy(
                    update={
                        "kind": "limitation",
                        "text": (
                            "The cited evidence does not establish a peer benchmark, so a relative "
                            "classification is left unresolved."
                        ),
                    }
                )
            ],
        }
    )
    validation = validate_report(report, tools)  # type: ignore[arg-type]
    assert not any(
        "GLOBAL_ABSENCE_CLAIM_FROM_NONOBSERVATION" in error for error in validation["errors"]
    )


def test_report_rejects_filing_wide_quantify_or_state_absence() -> None:
    tools = tools_for(evidence_text="Management attributes revenue growth to portfolio expansion.")
    for prose in (
        "The filing does not quantify the separate contribution of each driver.",
        "The filing does not state which factor is the primary driver.",
    ):
        report = report_for(percentage="100").model_copy(
            update={
                "executive_summary": "The cited evidence supports a bounded attribution.",
                "findings": [
                    report_for(percentage="100")
                    .findings[0]
                    .model_copy(update={"kind": "limitation", "text": prose})
                ],
            }
        )
        validation = validate_report(report, tools)  # type: ignore[arg-type]
        assert any(
            "GLOBAL_ABSENCE_CLAIM_FROM_NONOBSERVATION" in error for error in validation["errors"]
        )


def test_report_rejects_filing_wide_explicit_attribution_or_rank_absence() -> None:
    tools = tools_for(evidence_text="Management describes several year-over-year factors.")
    for prose in (
        "The filing does not explicitly attribute the change to the merger.",
        "The annual report does not rank the disclosed drivers.",
    ):
        report = report_for(percentage="100").model_copy(
            update={
                "executive_summary": "The cited evidence supports a bounded attribution.",
                "findings": [
                    report_for(percentage="100")
                    .findings[0]
                    .model_copy(update={"kind": "limitation", "text": prose})
                ],
            }
        )
        validation = validate_report(report, tools)  # type: ignore[arg-type]
        assert any(
            "GLOBAL_ABSENCE_CLAIM_FROM_NONOBSERVATION" in error for error in validation["errors"]
        )


def test_parenthetical_percentage_with_html_cell_separator_is_reported_source_value() -> None:
    source = (
        "(U.S. dollars in thousands) | December 31, 2025 | December 31, 2024 | Dollar | Percent\n"
        "Revenue | $ | 6,364,245 | $ | 6,750,576 | $ | (386,331 | ) | (5.7 | )%"
    )
    mentions = percentage_mentions(source)
    assert len(mentions) == 1
    assert mentions[0]["value"] == Decimal("-5.7")
    assert reported_percentage_values(source) == [Decimal("-5.7")]

    tools = tools_for(evidence_text=source)
    validation = validate_report(report_for(percentage="(5.7)%"), tools)  # type: ignore[arg-type]
    assert validation["passed"] is True, validation["errors"]
