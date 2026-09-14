"""V2 boundary tests use labeled synthetic inputs, never product fallback data."""

from __future__ import annotations

import io
import threading
from datetime import datetime
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from researchforge.adapters.storage import IdempotencyConflictError
from researchforge.v2.compute import calculate
from researchforge.v2.contracts import CalculateInput, ResearchRequest, WorkingState
from researchforge.v2.documents import (
    _object,
    parse_html,
    parse_pdf,
    render_page,
    search_objects,
    windows,
)
from researchforge.v2.storage import ResearchRepository
from researchforge.v2.tools import FilingTools, bootstrap_evidence_candidates


def request(key: str = "test-v2-request") -> ResearchRequest:
    return ResearchRequest(
        company_query="Synthetic Test Co",
        market_hint="US",
        requested_period_label="2025FY",
        research_question="Explain cash flow and working capital changes.",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key=key,
    )


def synthetic_pdf() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=400, height=400)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(b"""
0 0 0 RG 1 w
40 300 m 360 300 l S 40 270 m 360 270 l S 40 240 m 360 240 l S
40 210 m 360 210 l S 40 180 m 360 180 l S
40 180 m 40 300 l S 220 180 m 220 300 l S 290 180 m 290 300 l S 360 180 m 360 300 l S
BT /F1 12 Tf 45 280 Td (Metric) Tj 180 0 Td (2025) Tj 70 0 Td (2024) Tj ET
BT /F1 12 Tf 45 250 Td (Revenue) Tj 180 0 Td (120) Tj 70 0 Td (100) Tj ET
BT /F1 12 Tf 45 220 Td (Cash flow) Tj 180 0 Td (20) Tj 70 0 Td (30) Tj ET
BT /F1 12 Tf 45 190 Td (Receivables) Tj 180 0 Td (25) Tj 70 0 Td (15) Tj ET
BT /F1 11 Tf 40 155 Td (Note 1: Values in USD millions.) Tj ET
BT /F1 10 Tf 40 130 Td (Cash flow fell as customer collection slowed.) Tj ET
""")
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.add_outline_item("Financial statements", 0)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def source(blob: str = "0" * 64 + ".pdf") -> dict:
    return {
        "document_id": "doc_synthetic",
        "title": "SYNTHETIC TEST FILING",
        "source_uri": "https://www.sec.gov/Archives/synthetic-test",
        "published_at": "2026-01-01T00:00:00+00:00",
        "raw_blob_id": blob,
        "content_hash": blob.split(".")[0],
        "company": {"company_id": "test_company", "legal_name": "Synthetic Test Co"},
        "period_label": "2025FY",
        "mime_type": "application/pdf",
    }


def environment() -> dict:
    src = source()
    text = "Cash flow decreased because customers paid later. Revenue grew but receivables rose."
    obj = _object("evidence", "ev_synthetic", src, text, page_id="page_synthetic_1", page_number=1)
    return {
        "schema_version": "2.0.0",
        "entity": src["company"],
        "documents": {src["document_id"]: src},
        "objects": {obj["artifact_id"]: obj},
        "facts": {},
        "gaps": ["SYNTHETIC TEST DATA"],
    }


def perform_informative_search(tools: FilingTools, call_id: str) -> str:
    src = source()
    artifact_id = f"ev_{call_id.replace('-', '_')}"
    obj = _object(
        "evidence",
        artifact_id,
        src,
        "Liquidity footnote gives a separate working-capital disclosure for active research.",
        page_id=f"page_{artifact_id}",
        page_number=2,
    )
    tools.environment["objects"][artifact_id] = obj
    result = tools.execute(
        call_id,
        "search_filing",
        {
            "query": "liquidity footnote separate working-capital disclosure",
            "kind": "evidence",
            "document_id": None,
            "offset": 0,
            "limit": 3,
        },
    )
    assert result["results"]
    receipt = tools.receipts[call_id]
    assert receipt["new_observed_count"] >= 1
    return result["results"][0]["evidence_id"]


def fact(identifier: str, metric: str, value: str, year: int = 2025) -> dict:
    return {
        "fact_id": identifier,
        "metric_code": metric,
        "value": value,
        "currency": "USD",
        "measurement_unit": "CURRENCY",
        "company": {"company_id": "test_company"},
        "period": {
            "period_start": f"{year}-01-01",
            "period_end": f"{year}-12-31",
            "fiscal_year": year,
            "fiscal_period": "FY",
            "period_basis": "ytd",
            "accounting_standard": "US_GAAP",
            "statement_scope": "consolidated",
            "restatement_status": "as_reported",
        },
    }


def test_cash_flow_health_exposes_multidimensional_methodology_guidance(tmp_path: Path) -> None:
    repository = ResearchRepository(tmp_path / "artifacts")
    req = ResearchRequest(
        company_query="Synthetic Test Co",
        market_hint="CN",
        requested_period_label="2024H1",
        research_question="分析现金流是否健康",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key="cash-flow-health-methodology",
    )
    manifest, _ = repository.create(req, {})
    tools = FilingTools(
        repository,
        manifest["run_id"],
        req,
        environment(),
        lambda: None,
    )
    checks = tools.completeness(include_required=False)["methodology_checks"]
    assert len(checks) == 1
    check = checks[0]
    assert check["methodology_id"] == "cash_flow_health_multidimensional_v1"
    assert {item["dimension"] for item in check["dimensions"]} == {
        "operating_cash_generation",
        "net_cash_and_liquidity",
        "investing_and_financing",
        "working_capital_and_one_offs",
    }
    assert "mixed" in check["direct_answer_rule"]
    assert "single-ratio threshold" in check["instruction"]


def test_bootstrap_metric_alias_and_statement_context_prioritizes_statement_evidence() -> None:
    src = source()
    objects = {
        "ev_discussion": _object(
            "evidence",
            "ev_discussion",
            src,
            "Capital expenditures support manufacturing growth and product demand.",
            page_id="page_47",
            page_number=47,
        ),
        "ev_cash_flow": _object(
            "evidence",
            "ev_cash_flow",
            src,
            (
                "Consolidated Statement of Cash Flows Years ended December 31 2018 2017 2016 "
                "Purchases of property, plant and equipment (1,577) (1,373) (1,420)"
            ),
            page_id="page_60",
            page_number=60,
        ),
        "ev_other": _object(
            "evidence",
            "ev_other",
            src,
            "Other cash-flow commentary without the requested statement row.",
            page_id="page_49",
            page_number=49,
        ),
    }
    question = (
        "What is the FY2018 capital expenditure amount? "
        "Use the details shown in the cash flow statement."
    )
    candidates, metrics = bootstrap_evidence_candidates(objects, question, limit=3)
    assert metrics == ["capital_expenditures"]
    assert candidates[0]["artifact_id"] == "ev_cash_flow"
    assert candidates[0]["bootstrap_source"] == "financial_metric_alias_and_statement"
    assert candidates[0]["bootstrap_metric_code"] == "capital_expenditures"


def test_bootstrap_metric_aliases_match_chinese_financial_question() -> None:
    src = source()
    objects = {
        "ev_cn_capex": _object(
            "evidence",
            "ev_cn_capex",
            src,
            "现金流量表 2025 2024 购建固定资产无形资产和其他长期资产支付的现金 123 100",
            page_id="page_cn_10",
            page_number=10,
        )
    }
    candidates, metrics = bootstrap_evidence_candidates(
        objects, "2025年资本开支是多少? 请看现金流量表。", limit=3
    )
    assert metrics == ["capital_expenditures"]
    assert candidates[0]["artifact_id"] == "ev_cn_capex"


def test_repository_idempotency_and_tamper_detection(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    first, created = repo.create(request(), {})
    again, second = repo.create(request(), {})
    assert created and not second and first["run_id"] == again["run_id"]
    with pytest.raises(IdempotencyConflictError):
        repo.create(request().model_copy(update={"research_question": "Different question"}), {})
    blob = repo.put_blob(b"%PDF-synthetic", "pdf")
    path = repo.blob_path(blob)
    path.write_bytes(b"corruption")
    with pytest.raises(RuntimeError, match="hash mismatch"):
        repo.blob_path(blob)
    with pytest.raises(ValueError):
        repo.blob_path("../../.env")


def test_event_sequence_is_durable_concurrent_and_replayable(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    manifest, _ = repo.create(request(), {})
    run_id = manifest["run_id"]
    writers = [ResearchRepository(tmp_path) for _ in range(4)]
    threads = [
        threading.Thread(
            target=lambda r=r: [
                r.emit(run_id, "test", "test", "test", "succeeded") for _ in range(5)
            ]
        )
        for r in writers
    ]
    for worker in threads:
        worker.start()
    for worker in threads:
        worker.join()
    events = ResearchRepository(tmp_path).events(run_id)
    assert [event["sequence"] for event in events] == list(range(1, 22))
    assert [event["sequence"] for event in repo.events(run_id, after=18)] == [19, 20, 21]
    with repo.span(run_id, "test", "test"):
        pass
    spans = repo.events(run_id, after=21)
    assert spans[0]["span_id"] == spans[1]["span_id"]
    assert spans[0]["timestamp"] <= spans[1]["timestamp"]
    assert spans[1]["duration_ms"] >= 0


def test_pdf_preserves_page_table_cell_footnote_and_renders(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    payload = synthetic_pdf()
    blob = repo.put_blob(payload, "pdf")
    objects, pages, gaps = parse_pdf(payload, source(blob))
    assert len(pages) == 1 and "Revenue" in pages[0]
    tables = [obj for obj in objects.values() if obj["kind"] == "table"]
    assert len(tables) == 1
    assert tables[0]["rows"][1][1]["text"] == "120"
    assert tables[0]["rows"][1][1]["bbox"] is not None
    assert tables[0]["footnote_ids"]
    assert any(obj["kind"] == "section" for obj in objects.values())
    page = next(obj for obj in objects.values() if obj["kind"] == "page")
    assert page["page_number"] == 1 and page["table_ids"]
    png_id = render_page(repo, page)
    assert repo.blob_path(png_id).read_bytes().startswith(b"\x89PNG")
    assert gaps  # extraction is never claimed universally complete


def test_html_native_spans_and_script_exclusion() -> None:
    payload = b"""<h1>Cash flow</h1><p>(In millions)</p><script>steal credentials</script>
<table><tr><th rowspan="2">Metric</th><th colspan="2">Years</th></tr>
<tr><th>2025</th><th>2024</th></tr><tr><td>Revenue</td><td>120</td><td>100</td></tr></table>"""
    objects, blocks, _ = parse_html(payload, source("0" * 64 + ".html"))
    assert "steal credentials" not in "".join(blocks)
    table = next(obj for obj in objects.values() if obj["kind"] == "table")
    assert table["rows"][0][0]["rowspan"] == 2
    assert table["rows"][1][0]["column"] == 1
    assert "(In millions)" in table["context_text"]
    assert all(obj["page_number"] is None for obj in objects.values() if obj["kind"] == "page")


def test_evidence_windows_preserve_token_prefix_at_fixed_chunk_boundary() -> None:
    text = "A " * 998 + "decreased 45% to $118 million." + " tail" * 100
    chunks = windows(text)
    start, chunk = chunks[1]
    assert start == 1996
    assert chunk.startswith("decreased 45%")


def test_compute_retains_financial_semantics() -> None:
    facts = {
        "f_current": fact("f_current", "revenue", "120.00"),
        "f_prior": fact("f_prior", "revenue", "100.00", 2024),
    }
    result = calculate(CalculateInput(formula="growth_rate", fact_ids=list(facts)), facts)
    assert result["value"] == "0.2" and result["input_fact_ids"] == list(facts)
    with pytest.raises(ValueError):
        calculate(CalculateInput(formula="growth_rate", fact_ids=list(reversed(facts))), facts)
    facts["f_prior"]["value"] = "0"
    assert (
        calculate(CalculateInput(formula="growth_rate", fact_ids=list(facts)), facts)["status"]
        == "not_meaningful"
    )
    facts["f_prior"]["currency"] = "CNY"
    with pytest.raises(ValueError, match="currency"):
        calculate(CalculateInput(formula="growth_rate", fact_ids=list(facts)), facts)


def test_tool_observed_evidence_and_stop_contract(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request()
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    bootstrap = tools.bootstrap()
    assert bootstrap["initial_evidence"]
    search_args = {
        "query": "cash flow",
        "kind": "evidence",
        "document_id": None,
        "offset": 0,
        "limit": 6,
    }
    first = tools.execute("call_one", "search_filing", search_args)
    assert tools.execute("call_one", "search_filing", search_args) == first
    with pytest.raises(ValueError, match="rebound"):
        tools.execute("call_one", "read_filing", {})
    bad = tools.execute(
        "call_bad",
        "submit_research",
        {
            "stop_reason": "sufficient_evidence",
            "summary": "done",
            "evidence_ids": ["ev_not_read"],
            "remaining_uncertainties": [],
            "why_stop": "done",
        },
    )
    assert bad["error"] == "TOOL_INPUT_REJECTED"
    evidence = first["results"][0]["evidence_id"]
    tools.execute(
        "call_counter",
        "search_counter_evidence",
        {"hypothesis": "Cash flow explanation is sufficient.", "query": "cash flow other reasons"},
    )
    perform_informative_search(tools, "stop-contract-maturity")
    state = tools.execute(
        "call_state",
        "update_research_state",
        {
            "objectives": [
                {
                    "objective_id": "obj_cash_flow_contract",
                    "question": "Explain cash flow and working-capital changes.",
                    "priority": "required",
                    "status": "answered",
                    "evidence_ids": [evidence],
                    "conclusion": "The filing supports a conditional answer.",
                    "remaining_uncertainty": "",
                }
            ],
            "hypotheses": [
                {
                    "hypothesis_id": "h_cash_flow",
                    "statement": "The filing explains the cash-flow change.",
                    "status": "supported",
                    "materiality": "major",
                    "evidence_for": [evidence],
                    "evidence_against": [],
                    "unknowns": [],
                    "would_change_conclusion": "A material contrary disclosure.",
                    "confidence": "medium",
                }
            ],
            "open_questions": [],
            "decision_summary": "The core filing evidence and counter-search have been checked.",
            "core_question_status": "answerable",
            "expected_value_of_more_research": "low",
        },
    )
    assert state["working_state"]["core_question_status"] == "answerable"
    good = tools.execute(
        "call_finish",
        "submit_research",
        {
            "stop_reason": "sufficient_evidence",
            "summary": "done",
            "evidence_ids": [evidence],
            "remaining_uncertainties": [],
            "why_stop": "question addressed",
        },
    )
    assert good["accepted"] is True
    persisted = repo.artifact(manifest["run_id"], "research_state")
    assert evidence in persisted["observed"]
    assert "hidden_reasoning" not in json_keys(persisted)


def test_completion_contract_orders_counter_review_then_submit(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("completion-contract-test")
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    seed = tools.bootstrap()["initial_evidence"][0]["evidence_id"]
    perform_informative_search(tools, "maturity-search")
    working = {
        "objectives": [
            {
                "objective_id": "obj_cash_flow",
                "question": "Explain the cash-flow movement.",
                "priority": "required",
                "status": "answered",
                "evidence_ids": [seed],
                "conclusion": "The filing provides enough evidence for the core question.",
                "remaining_uncertainty": "",
            }
        ],
        "hypotheses": [
            {
                "hypothesis_id": "h_completion",
                "statement": "Collections explain the cash-flow movement.",
                "status": "supported",
                "materiality": "major",
                "evidence_for": [seed],
                "evidence_against": [],
                "unknowns": [],
                "would_change_conclusion": "A material alternative explanation.",
                "confidence": "medium",
            }
        ],
        "open_questions": [],
        "decision_summary": "The core question is answerable from the filing.",
        "core_question_status": "answerable",
        "expected_value_of_more_research": "low",
    }
    tools.execute("state_before_counter", "update_research_state", working)
    assert tools.completeness()["required_before_submit"] == ["search_counter_evidence"]
    tools.execute(
        "counter_required",
        "search_counter_evidence",
        {
            "hypothesis": "Collections explain the cash-flow movement.",
            "query": "cash flow other reasons",
        },
    )
    assert tools.completeness()["required_state_refresh"] == ["runtime_reflection"]
    assert tools.completeness()["required_before_submit"] == []
    tools.execute("state_after_counter", "update_research_state", working)
    assert tools.completeness()["required_before_submit"] == ["submit_research"]


def test_repeated_tool_calls_are_compact_and_create_plateau_signal(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("plateau-test")
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    seed = tools.bootstrap()["initial_evidence"][0]["evidence_id"]
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_plateau",
                        "question": "Explain cash flow and working-capital changes.",
                        "priority": "required",
                        "status": "open",
                        "evidence_ids": [seed],
                        "conclusion": "",
                        "remaining_uncertainty": "More evidence is needed.",
                    }
                ],
                "hypotheses": [
                    {
                        "hypothesis_id": "h_plateau",
                        "statement": "Collections may explain the cash-flow change.",
                        "status": "investigating",
                        "materiality": "major",
                        "evidence_for": [seed],
                        "evidence_against": [],
                        "unknowns": ["Need more evidence."],
                        "would_change_conclusion": "A contradictory working-capital disclosure.",
                        "confidence": "low",
                    }
                ],
                "core_question_status": "investigating",
                "expected_value_of_more_research": "high",
            }
        )
    )
    arguments = {"metrics": [], "period_labels": []}
    first = tools.execute("facts_1", "get_financial_facts", arguments)
    assert "reused_cached_result" not in first
    for index in range(2, 7):
        repeated = tools.execute(f"facts_{index}", "get_financial_facts", arguments)
        assert repeated["reused_cached_result"] is True
        assert "facts" not in repeated
        assert repeated["previous_call_id"] == "facts_1"
    progress = tools.completeness()["recent_research_progress"]
    assert progress["plateau_detected"] is True
    assert progress["redundant_actions"] >= 5
    assert tools.reflection_needed() is True
    tools.mark_reflected()
    assert tools.reflection_needed() is False


def test_missing_comparison_period_is_explicit(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("missing-period-test")
    manifest, _ = repo.create(req, {})
    env = environment()
    tools = FilingTools(repo, manifest["run_id"], req, env, lambda: None)
    result = tools.execute(
        "facts-period",
        "get_financial_facts",
        {"metrics": ["revenue"], "period_labels": ["2025FY", "2024FY"]},
    )
    assert result["unavailable_period_labels"] == ["2024FY"]
    assert result["loaded_period_labels"] == ["2025FY"]
    assert result["coverage_by_period"]["2024FY"] == []
    assert result["next_action_hint"].startswith("Use add_filing")


def test_empty_granular_search_falls_back_to_readable_filing_candidates(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("granular-fallback-test")
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    result = tools.execute(
        "search-section-fallback",
        "search_filing",
        {
            "query": "cash flow collection",
            "kind": "section",
            "document_id": "doc_synthetic",
            "offset": 0,
            "limit": 6,
        },
    )
    assert result["fallback_applied"] is True
    assert result["fallback_from_kind"] == "section"
    assert result["results"]
    assert result["results"][0]["kind"] == "evidence"
    assert result["results"][0]["evidence_id"].startswith("view_")


def json_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(json_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(json_keys(child) for child in value))
    return set()


def test_working_state_invalid_references_are_dropped_and_audited(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("state-reference-repair")
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    bootstrap = tools.bootstrap()
    evidence_id = bootstrap["initial_evidence"][0]["evidence_id"]
    result = tools.execute(
        "state-with-invalid-ref",
        "update_research_state",
        {
            "hypotheses": [
                {
                    "hypothesis_id": "h_ref",
                    "statement": "Cash flow explanation is supported.",
                    "status": "supported",
                    "materiality": "major",
                    "evidence_for": ["view_invented_label"],
                    "evidence_against": [],
                    "unknowns": [],
                    "would_change_conclusion": "Contrary filing evidence.",
                    "confidence": "high",
                }
            ],
            "open_questions": [
                {
                    "question_id": "q_ref",
                    "question": "Is the explanation complete?",
                    "priority": "medium",
                    "status": "answered",
                    "evidence_ids": ["view_invented_label", evidence_id],
                    "explanation": "Checked the filing.",
                }
            ],
            "decision_summary": "Reference repair test.",
            "core_question_status": "answerable",
            "expected_value_of_more_research": "low",
        },
    )
    assert result["reference_corrections"]
    repaired = result["working_state"]
    assert repaired["hypotheses"][0]["status"] == "unresolved"
    assert repaired["hypotheses"][0]["evidence_for"] == []
    assert repaired["open_questions"][0]["evidence_ids"] == [evidence_id]
    registry = tools.context_state()["reference_registry"]
    assert any(item["evidence_id"] == evidence_id for item in registry["evidence"])
    assert "view_invented_label" not in {item["evidence_id"] for item in registry["evidence"]}
    assert any(
        event["event_type"] == "research_state_reference_correction"
        for event in repo.events(manifest["run_id"])
    )


def test_material_new_evidence_refreshes_notebook_without_forcing_stop(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("material-research-refresh")
    manifest, _ = repo.create(req, {})
    env = environment()
    tools = FilingTools(repo, manifest["run_id"], req, env, lambda: None)
    bootstrap = tools.bootstrap()
    evidence_id = bootstrap["initial_evidence"][0]["evidence_id"]
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_material",
                        "question": "Explain cash flow and working-capital changes.",
                        "priority": "required",
                        "status": "open",
                        "evidence_ids": [evidence_id],
                        "conclusion": "",
                        "remaining_uncertainty": "Working-capital explanation is still needed.",
                    }
                ],
                "hypotheses": [
                    {
                        "hypothesis_id": "h_material",
                        "statement": "Cash-flow quality requires further evidence.",
                        "status": "investigating",
                        "materiality": "major",
                        "evidence_for": [evidence_id],
                        "evidence_against": [],
                        "unknowns": ["Working-capital explanation"],
                        "would_change_conclusion": "Material contrary evidence.",
                        "confidence": "medium",
                    }
                ],
                "open_questions": [],
                "decision_summary": "Initial hypothesis.",
                "core_question_status": "investigating",
                "expected_value_of_more_research": "high",
            }
        )
    )
    source_obj = next(iter(env["objects"].values()))
    for index in range(6):
        tools._observe(source_obj, f"new material evidence {index}")
    decision = tools.reflection_decision()
    assert decision["needed"] is True
    assert decision["reason"] == "material_research_update"
    assert decision["evidence_gain_since_state"] == 6
    assert tools.working.core_question_status == "investigating"


def test_working_state_invented_references_are_removed_and_conservatively_downgraded(
    tmp_path: Path,
) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("invented-reference-test")
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    bootstrap = tools.bootstrap()
    valid = bootstrap["initial_evidence"][0]["evidence_id"]
    from researchforge.v2.contracts import WorkingState

    state = WorkingState.model_validate(
        {
            "core_question_status": "answerable",
            "expected_value_of_more_research": "low",
            "decision_summary": "Synthetic reference correction test.",
            "hypotheses": [
                {
                    "hypothesis_id": "h_invalid",
                    "statement": "A claim that lost its only cited support.",
                    "status": "supported",
                    "materiality": "major",
                    "evidence_for": ["view_174_table1"],
                    "evidence_against": [],
                    "unknowns": [],
                    "would_change_conclusion": "Valid contrary evidence.",
                    "confidence": "high",
                },
                {
                    "hypothesis_id": "h_mixed_refs",
                    "statement": "A claim with one valid and one invented reference.",
                    "status": "supported",
                    "materiality": "minor",
                    "evidence_for": [valid, "view_71_table1"],
                    "evidence_against": [],
                    "unknowns": [],
                    "would_change_conclusion": "Valid contrary evidence.",
                    "confidence": "medium",
                },
            ],
            "open_questions": [
                {
                    "question_id": "q_invalid",
                    "question": "Was the unsupported question actually answered?",
                    "priority": "medium",
                    "status": "answered",
                    "evidence_ids": ["view_71_table1"],
                    "explanation": "The model thought a page label was an evidence ID.",
                }
            ],
        }
    )
    result = tools.apply_working_state(state)
    corrected = result["working_state"]
    assert corrected["hypotheses"][0]["status"] == "unresolved"
    assert corrected["hypotheses"][0]["confidence"] == "low"
    assert corrected["hypotheses"][0]["evidence_for"] == []
    assert corrected["hypotheses"][1]["evidence_for"] == [valid]
    assert corrected["open_questions"][0]["status"] == "open"
    assert corrected["open_questions"][0]["evidence_ids"] == []
    assert {item["subject"] for item in result["reference_corrections"]} == {
        "h_invalid",
        "h_mixed_refs",
        "q_invalid",
    }
    events = repo.events(manifest["run_id"])
    assert any(event["event_type"] == "research_state_reference_correction" for event in events)


def test_counter_evidence_requires_public_state_refresh_before_submit(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("counter-reflection-gate")
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    seed = tools.bootstrap()["initial_evidence"][0]["evidence_id"]
    perform_informative_search(tools, "maturity-search")
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_counter",
                        "question": "Explain the cash-flow change.",
                        "priority": "required",
                        "status": "answered",
                        "evidence_ids": [seed],
                        "conclusion": (
                            "The core filing evidence is sufficient for a conditional answer."
                        ),
                        "remaining_uncertainty": "",
                    }
                ],
                "hypotheses": [
                    {
                        "hypothesis_id": "h_counter",
                        "statement": "Collections explain the cash-flow change.",
                        "status": "supported",
                        "materiality": "major",
                        "evidence_for": [seed],
                        "evidence_against": [],
                        "unknowns": [],
                        "would_change_conclusion": "A material alternative explanation.",
                        "confidence": "medium",
                    }
                ],
                "open_questions": [],
                "decision_summary": "Core question is answerable before challenge search.",
                "core_question_status": "answerable",
                "expected_value_of_more_research": "low",
            }
        )
    )
    assert tools.completeness()["required_before_submit"] == ["search_counter_evidence"]
    tools.execute(
        "counter_once",
        "search_counter_evidence",
        {"hypothesis": "Collections explain the change.", "query": "other cash flow reasons"},
    )
    decision = tools.reflection_decision()
    assert decision["needed"] is True
    assert decision["reason"] == "counter_evidence_update"
    assert tools.completeness()["required_state_refresh"] == ["runtime_reflection"]
    assert tools.completeness()["required_before_submit"] == []
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_counter",
                        "question": "Explain the cash-flow change.",
                        "priority": "required",
                        "status": "answered",
                        "evidence_ids": [seed],
                        "conclusion": (
                            "The core filing evidence is sufficient for a conditional answer."
                        ),
                        "remaining_uncertainty": "",
                    }
                ],
                "hypotheses": [
                    {
                        "hypothesis_id": "h_counter",
                        "statement": "Collections remain the best supported explanation.",
                        "status": "supported",
                        "materiality": "major",
                        "evidence_for": [seed],
                        "evidence_against": [],
                        "unknowns": [],
                        "would_change_conclusion": "A material alternative explanation.",
                        "confidence": "medium",
                    }
                ],
                "open_questions": [],
                "decision_summary": "Counter search did not overturn the material conclusion.",
                "core_question_status": "answerable",
                "expected_value_of_more_research": "low",
            }
        )
    )
    assert tools.reflection_decision()["needed"] is False
    assert tools.completeness()["required_before_submit"] == ["submit_research"]


def test_non_objective_open_question_does_not_expand_completion_scope(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("objective-scope-test")
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    seed = tools.bootstrap()["initial_evidence"][0]["evidence_id"]
    perform_informative_search(tools, "maturity-search")
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_required",
                        "question": "Explain cash flow and working-capital changes.",
                        "priority": "required",
                        "status": "answered",
                        "evidence_ids": [seed],
                        "conclusion": "The filing supports the requested conclusion.",
                        "remaining_uncertainty": "Turnover days would add precision, not flip it.",
                    }
                ],
                "hypotheses": [
                    {
                        "hypothesis_id": "h_scope",
                        "statement": "The requested cash-flow conclusion is supportable.",
                        "status": "rejected",
                        "materiality": "major",
                        "evidence_for": [seed],
                        "evidence_against": [],
                        "unknowns": [],
                        "would_change_conclusion": "A contradictory filing disclosure.",
                        "confidence": "medium",
                    }
                ],
                "open_questions": [
                    {
                        "question_id": "q_nice_to_have",
                        "question": "What are exact receivable turnover days?",
                        "priority": "high",
                        "status": "open",
                        "evidence_ids": [seed],
                        "explanation": "Useful extra precision but not a user-required objective.",
                    }
                ],
                "decision_summary": "Required objective is resolved; extra precision remains.",
                "core_question_status": "answerable",
                "expected_value_of_more_research": "low",
            }
        )
    )
    tools.execute(
        "objective-scope-counter",
        "search_counter_evidence",
        {
            "hypothesis": "The required cash-flow conclusion is supportable.",
            "query": "cash flow contrary explanation working capital",
        },
    )
    tools.mark_reflected()
    completeness = tools.completeness()
    assert completeness["required_objectives_open"] == 0
    assert completeness["high_priority_open_questions"] == 1
    assert completeness["required_before_submit"] == ["submit_research"]
    result = tools.execute(
        "submit_objective_scope",
        "submit_research",
        {
            "stop_reason": "sufficient_evidence",
            "summary": "The required question can be answered.",
            "evidence_ids": [seed],
            "remaining_uncertainties": [
                "Exact turnover days were not needed to answer the question."
            ],
            "why_stop": (
                "Further filing work would add detail without changing the required conclusion."
            ),
        },
    )
    assert result["accepted"] is True


def test_required_objective_contract_is_locked_after_first_public_state(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("objective-lock-test")
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    seed = tools.bootstrap()["initial_evidence"][0]["evidence_id"]
    initial = WorkingState.model_validate(
        {
            "objectives": [
                {
                    "objective_id": "obj_cash",
                    "question": "Is operating cash flow consistent with profit?",
                    "priority": "required",
                    "status": "open",
                    "evidence_ids": [seed],
                    "conclusion": "",
                    "remaining_uncertainty": "Need one more filing passage.",
                },
                {
                    "objective_id": "obj_working_capital",
                    "question": "What do receivables and inventory imply?",
                    "priority": "required",
                    "status": "open",
                    "evidence_ids": [seed],
                    "conclusion": "",
                    "remaining_uncertainty": "Need balance-sheet context.",
                },
            ],
            "hypotheses": [],
            "open_questions": [],
            "decision_summary": "Initial user-required objective contract.",
            "core_question_status": "investigating",
            "expected_value_of_more_research": "high",
        }
    )
    tools.apply_working_state(initial)
    drifted = WorkingState.model_validate(
        {
            "objectives": [
                {
                    "objective_id": "obj_cash",
                    "question": "A rewritten and broader cash-flow research question.",
                    "priority": "required",
                    "status": "answered",
                    "evidence_ids": [seed],
                    "conclusion": "Cash flow is supportable.",
                    "remaining_uncertainty": "",
                },
                {
                    "objective_id": "obj_new_valuation",
                    "question": "Build a new valuation objective not asked by the user.",
                    "priority": "required",
                    "status": "open",
                    "evidence_ids": [seed],
                    "conclusion": "",
                    "remaining_uncertainty": "Would require more research.",
                },
            ],
            "hypotheses": [],
            "open_questions": [],
            "decision_summary": "Attempted objective drift.",
            "core_question_status": "investigating",
            "expected_value_of_more_research": "medium",
        }
    )
    result = tools.apply_working_state(drifted)
    objectives = {item["objective_id"]: item for item in result["working_state"]["objectives"]}
    assert objectives["obj_cash"]["question"] == "Is operating cash flow consistent with profit?"
    assert objectives["obj_cash"]["status"] == "answered"
    assert objectives["obj_working_capital"]["priority"] == "required"
    assert objectives["obj_working_capital"]["status"] == "open"
    assert objectives["obj_new_valuation"]["priority"] == "supporting"
    corrections = {item.get("correction") for item in result["reference_corrections"]}
    assert "required_objective_question_locked" in corrections
    assert "missing_required_objective_restored" in corrections
    assert "new_required_objective_downgraded_to_supporting" in corrections


def test_direct_fact_question_uses_runtime_reflection_after_first_research_evidence(
    tmp_path: Path,
) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("direct-fact-runtime-reflection").model_copy(
        update={"research_question": "What is the reported cash flow amount?"}
    )
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    tools.bootstrap()
    result = tools.execute(
        "direct-search",
        "search_filing",
        {"query": "cash flow", "kind": "all", "document_id": None, "offset": 0, "limit": 6},
    )
    assert result["results"]
    decision = tools.reflection_decision()
    assert decision["analytical_question"] is False
    assert decision["needed"] is True
    assert decision["reason"] == "first_research_evidence"
    assert tools.completeness()["required_state_refresh"] == ["runtime_reflection"]


def test_public_agent_toolset_excludes_working_state_mutation() -> None:
    from researchforge.v2.tools import AGENT_TOOL_NAMES

    assert "update_research_state" not in AGENT_TOOL_NAMES
    assert "search_filing" in AGENT_TOOL_NAMES
    assert "submit_research" in AGENT_TOOL_NAMES


def test_direct_fact_open_objective_refreshes_after_new_evidence(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("direct-fact-open-objective-refresh").model_copy(
        update={"research_question": "What is the reported cash flow amount?"}
    )
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    seed = tools.bootstrap()["initial_evidence"][0]["evidence_id"]
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_fact",
                        "question": "What is the reported cash flow amount?",
                        "priority": "required",
                        "status": "open",
                        "evidence_ids": [seed],
                        "conclusion": "",
                        "remaining_uncertainty": "Need the precise disclosure.",
                    }
                ],
                "hypotheses": [],
                "open_questions": [],
                "core_question_status": "investigating",
                "expected_value_of_more_research": "medium",
            }
        )
    )
    source_obj = next(iter(environment()["objects"].values()))
    tools._observe(source_obj, "A newly observed precise cash-flow disclosure.")
    decision = tools.reflection_decision()
    assert decision["needed"] is True
    assert decision["reason"] == "open_objective_research_update"
    assert decision["objective_research_update"] is True


def test_direct_fact_question_does_not_force_counter_search_for_incidental_hypothesis(
    tmp_path: Path,
) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("direct-fact-no-counter").model_copy(
        update={"research_question": "What is FY2018 net PP&E?"}
    )
    manifest, _ = repo.create(req, {})
    env = environment()
    tools = FilingTools(repo, manifest["run_id"], req, env, lambda: None)
    tools.bootstrap()
    source_obj = next(iter(env["objects"].values()))
    seed = tools._observe(source_obj, "Synthetic PP&E balance disclosure.")
    perform_informative_search(tools, "maturity-search")
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_fact",
                        "question": "What is FY2018 net PP&E?",
                        "priority": "required",
                        "status": "answered",
                        "evidence_ids": [seed],
                        "conclusion": "The filing states the requested amount.",
                        "remaining_uncertainty": "",
                    }
                ],
                "hypotheses": [
                    {
                        "hypothesis_id": "h_incidental",
                        "statement": "The table represents the requested balance.",
                        "status": "supported",
                        "materiality": "major",
                        "evidence_for": [seed],
                        "evidence_against": [],
                        "unknowns": [],
                        "would_change_conclusion": "A different accounting label.",
                        "confidence": "medium",
                    }
                ],
                "core_question_status": "answerable",
                "expected_value_of_more_research": "low",
            }
        )
    )
    assert tools.reflection_decision()["analytical_question"] is False
    assert tools.completeness()["required_before_submit"] == ["submit_research"]


def test_first_reflection_cannot_complete_required_objective_before_active_research(
    tmp_path: Path,
) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("first-reflection-maturity-guard").model_copy(
        update={"research_question": "What is FY2018 net PP&E?"}
    )
    manifest, _ = repo.create(req, {})
    env = environment()
    tools = FilingTools(repo, manifest["run_id"], req, env, lambda: None)
    tools.bootstrap()
    source_obj = next(iter(env["objects"].values()))
    seed = tools._observe(source_obj, "Synthetic source candidate only.")
    applied = tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_first",
                        "question": "What is FY2018 net PP&E?",
                        "priority": "required",
                        "status": "answered",
                        "evidence_ids": [seed],
                        "conclusion": "The answer is somewhere on the balance sheet.",
                        "remaining_uncertainty": "Exact value is not captured yet.",
                    }
                ],
                "core_question_status": "answerable",
                "expected_value_of_more_research": "low",
            }
        )
    )
    objective = applied["working_state"]["objectives"][0]
    assert objective["status"] == "open"
    assert applied["working_state"]["core_question_status"] == "investigating"
    assert applied["working_state"]["expected_value_of_more_research"] == "medium"
    assert any(
        item.get("correction") == "first_reflection_requires_active_research"
        for item in applied["reference_corrections"]
    )


def test_focused_question_rejects_submit_with_material_verification_question_open(
    tmp_path: Path,
) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("focused-open-question-submit-guard").model_copy(
        update={"research_question": "What is FY2018 net PP&E?"}
    )
    manifest, _ = repo.create(req, {})
    env = environment()
    tools = FilingTools(repo, manifest["run_id"], req, env, lambda: None)
    tools.bootstrap()
    source_obj = next(iter(env["objects"].values()))
    seed = tools._observe(source_obj, "Synthetic source candidate only.")
    tools.execute(
        "focused-search",
        "search_filing",
        {"query": "cash flow", "kind": "all", "document_id": None, "offset": 0, "limit": 3},
    )
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_focused",
                        "question": "What is FY2018 net PP&E?",
                        "priority": "required",
                        "status": "answered",
                        "evidence_ids": [seed],
                        "conclusion": "A provisional amount has been located.",
                        "remaining_uncertainty": "",
                    }
                ],
                "open_questions": [
                    {
                        "question_id": "q_verify_exact",
                        "question": "What is the exact balance-sheet amount?",
                        "priority": "medium",
                        "status": "open",
                        "evidence_ids": [],
                        "explanation": "",
                    }
                ],
                "core_question_status": "answerable",
                "expected_value_of_more_research": "low",
            }
        )
    )
    assert tools.completeness()["required_before_submit"] == []
    rejected = tools.execute(
        "focused-submit",
        "submit_research",
        {
            "stop_reason": "sufficient_evidence",
            "summary": "done",
            "evidence_ids": [seed],
            "remaining_uncertainties": [],
            "why_stop": "done",
        },
    )
    assert rejected["error"] == "TOOL_INPUT_REJECTED"
    assert "verification question" in rejected["message"]


def test_analytical_question_missing_hypothesis_uses_shared_submit_blocker(
    tmp_path: Path,
) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("analytical-missing-hypothesis").model_copy(
        update={"research_question": "Analyze whether cash flow quality is healthy."}
    )
    manifest, _ = repo.create(req, {})
    env = environment()
    tools = FilingTools(repo, manifest["run_id"], req, env, lambda: None)
    tools.bootstrap()
    evidence_id = perform_informative_search(tools, "hypothesis-maturity")
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_quality",
                        "question": "Is cash-flow quality healthy?",
                        "priority": "required",
                        "status": "answered",
                        "evidence_ids": [evidence_id],
                        "conclusion": "The observed evidence supports an answer.",
                        "remaining_uncertainty": "",
                    }
                ],
                "hypotheses": [],
                "open_questions": [],
                "core_question_status": "answerable",
                "expected_value_of_more_research": "low",
            }
        )
    )
    completeness = tools.completeness()
    assert completeness["required_before_submit"] == []
    assert "analytical_hypothesis_missing" in completeness["submission_blockers"]
    reflection = tools.reflection_decision()
    assert reflection["needed"] is True
    assert reflection["reason"] == "missing_analytical_hypothesis"
    rejected = tools.execute(
        "analytical-submit",
        "submit_research",
        {
            "stop_reason": "sufficient_evidence",
            "summary": "done",
            "evidence_ids": [evidence_id],
            "remaining_uncertainties": [],
            "why_stop": "done",
        },
    )
    assert rejected["error"] == "TOOL_INPUT_REJECTED"
    assert rejected["message"] == "analytical research requires an explicit hypothesis state"


def test_binary_question_requires_explicit_direct_answer(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("binary-direct-answer").model_copy(
        update={"research_question": "Is the reported cash flow lower?"}
    )
    manifest, _ = repo.create(req, {})
    env = environment()
    tools = FilingTools(repo, manifest["run_id"], req, env, lambda: None)
    tools.bootstrap()
    evidence_id = perform_informative_search(tools, "binary-answer-evidence")
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_binary",
                        "question": req.research_question,
                        "priority": "required",
                        "status": "answered",
                        "evidence_ids": [evidence_id],
                        "conclusion": (
                            "No. The observed filing excerpt does not support a lower value."
                        ),
                        "remaining_uncertainty": "",
                    }
                ],
                "hypotheses": [],
                "open_questions": [],
                "core_question_status": "answerable",
                "expected_value_of_more_research": "low",
            }
        )
    )
    missing = tools.execute(
        "binary-submit-missing",
        "submit_research",
        {
            "stop_reason": "sufficient_evidence",
            "summary": "No.",
            "evidence_ids": [evidence_id],
            "remaining_uncertainties": [],
            "why_stop": "The required fact is available.",
        },
    )
    assert missing["error"] == "TOOL_INPUT_REJECTED"
    assert "explicit direct_answer" in missing["message"]

    accepted = tools.execute(
        "binary-submit-no",
        "submit_research",
        {
            "stop_reason": "sufficient_evidence",
            "direct_answer": "no",
            "summary": "No.",
            "evidence_ids": [evidence_id],
            "remaining_uncertainties": [],
            "why_stop": "The required fact is available.",
        },
    )
    assert accepted["accepted"] is True
    assert accepted["dossier"]["direct_answer"] == "no"


def test_non_binary_question_requires_not_applicable_direct_answer(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("non-binary-direct-answer").model_copy(
        update={"research_question": "What is the reported cash flow amount?"}
    )
    manifest, _ = repo.create(req, {})
    env = environment()
    tools = FilingTools(repo, manifest["run_id"], req, env, lambda: None)
    tools.bootstrap()
    evidence_id = perform_informative_search(tools, "non-binary-answer-evidence")
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_amount",
                        "question": req.research_question,
                        "priority": "required",
                        "status": "answered",
                        "evidence_ids": [evidence_id],
                        "conclusion": "The filing reports the requested amount.",
                        "remaining_uncertainty": "",
                    }
                ],
                "hypotheses": [],
                "open_questions": [],
                "core_question_status": "answerable",
                "expected_value_of_more_research": "low",
            }
        )
    )
    rejected = tools.execute(
        "non-binary-submit-yes",
        "submit_research",
        {
            "stop_reason": "sufficient_evidence",
            "direct_answer": "yes",
            "summary": "The requested amount is in the filing.",
            "evidence_ids": [evidence_id],
            "remaining_uncertainties": [],
            "why_stop": "The requested filing fact is available.",
        },
    )
    assert rejected["error"] == "TOOL_INPUT_REJECTED"
    assert "direct_answer=not_applicable" in rejected["message"]

    accepted = tools.execute(
        "non-binary-submit-not-applicable",
        "submit_research",
        {
            "stop_reason": "sufficient_evidence",
            "direct_answer": "not_applicable",
            "summary": "The requested amount is in the filing.",
            "evidence_ids": [evidence_id],
            "remaining_uncertainties": [],
            "why_stop": "The requested filing fact is available.",
        },
    )
    assert accepted["accepted"] is True
    assert accepted["dossier"]["direct_answer"] == "not_applicable"


def test_binary_evidence_exhaustion_requires_cannot_determine(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("binary-evidence-exhausted").model_copy(
        update={"research_question": "Is the company dependent on one customer?"}
    )
    manifest, _ = repo.create(req, {})
    env = environment()
    tools = FilingTools(repo, manifest["run_id"], req, env, lambda: None)
    tools.bootstrap()
    evidence_id = perform_informative_search(tools, "binary-exhausted-evidence")
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_exhausted",
                        "question": req.research_question,
                        "priority": "required",
                        "status": "limited",
                        "evidence_ids": [evidence_id],
                        "conclusion": "The filing excerpt does not disclose enough to decide.",
                        "remaining_uncertainty": "Customer concentration is not available here.",
                    }
                ],
                "hypotheses": [],
                "open_questions": [],
                "core_question_status": "evidence_exhausted",
                "expected_value_of_more_research": "low",
            }
        )
    )
    rejected = tools.execute(
        "binary-exhausted-wrong-polarity",
        "submit_research",
        {
            "stop_reason": "evidence_exhausted",
            "direct_answer": "no",
            "summary": "Not enough evidence.",
            "evidence_ids": [evidence_id],
            "remaining_uncertainties": ["Customer concentration is unavailable."],
            "why_stop": "The filing scope does not answer the question.",
        },
    )
    assert rejected["error"] == "TOOL_INPUT_REJECTED"
    assert "cannot_determine" in rejected["message"]

    accepted = tools.execute(
        "binary-exhausted-correct",
        "submit_research",
        {
            "stop_reason": "evidence_exhausted",
            "direct_answer": "cannot_determine",
            "summary": "Cannot determine from the filing evidence.",
            "evidence_ids": [evidence_id],
            "remaining_uncertainties": ["Customer concentration is unavailable."],
            "why_stop": "The filing scope does not answer the question.",
        },
    )
    assert accepted["accepted"] is True
    assert accepted["dossier"]["direct_answer"] == "cannot_determine"


def test_revenue_driver_question_is_analytical_not_focused() -> None:
    from researchforge.v2.tools import _analytical_question

    assert _analytical_question("What drove revenue change as of FY22 for AMD?") is True
    assert _analytical_question("Which segment contributed most to the revenue change?") is True
    assert (
        _analytical_question(
            "Assess earnings-to-cash conversion from net income and operating cash flow."
        )
        is True
    )
    assert _analytical_question("评估盈利到现金的转化质量。") is True
    assert _analytical_question("What is FY2022 revenue?") is False


def test_rejected_major_hypothesis_still_requires_counter_search(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("rejected-hypothesis-counter-test")
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    seed = tools.bootstrap()["initial_evidence"][0]["evidence_id"]
    perform_informative_search(tools, "rejected-hypothesis-maturity")
    working = {
        "objectives": [
            {
                "objective_id": "obj_cash_flow",
                "question": "Explain the cash-flow movement.",
                "priority": "required",
                "status": "answered",
                "evidence_ids": [seed],
                "conclusion": "No — the initial explanation is not supported by the filing.",
                "remaining_uncertainty": "",
            }
        ],
        "hypotheses": [
            {
                "hypothesis_id": "h_rejected",
                "statement": "Collections fully explain the cash-flow movement.",
                "status": "rejected",
                "materiality": "major",
                "evidence_for": [],
                "evidence_against": [seed],
                "unknowns": [],
                "would_change_conclusion": (
                    "Direct filing support for collections as the sole cause."
                ),
                "confidence": "medium",
            }
        ],
        "open_questions": [],
        "decision_summary": (
            "The initial major hypothesis was rejected by observed filing evidence."
        ),
        "core_question_status": "answerable",
        "expected_value_of_more_research": "low",
    }
    tools.execute("rejected-state-before-counter", "update_research_state", working)
    completeness = tools.completeness()
    assert completeness["required_before_submit"] == ["search_counter_evidence"]
    assert "counter_evidence_missing" in completeness["submission_blockers"]
    tools.execute(
        "rejected-counter",
        "search_counter_evidence",
        {
            "hypothesis": "The final conclusion is that collections are not the full explanation.",
            "query": "collections working capital alternative explanation cash flow",
        },
    )
    assert tools.completeness()["required_state_refresh"] == ["runtime_reflection"]
    tools.execute("rejected-state-after-counter", "update_research_state", working)
    assert tools.completeness()["required_before_submit"] == ["submit_research"]


def test_unresolved_major_hypothesis_blocks_answered_analytical_objective(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("unresolved-major-stop-test")
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    seed = tools.bootstrap()["initial_evidence"][0]["evidence_id"]
    perform_informative_search(tools, "unresolved-major-maturity")
    tools.execute(
        "unresolved-major-state",
        "update_research_state",
        {
            "objectives": [
                {
                    "objective_id": "obj_cash_flow",
                    "question": "Explain the cash-flow movement.",
                    "priority": "required",
                    "status": "answered",
                    "evidence_ids": [seed],
                    "conclusion": "The filing permits a provisional answer.",
                    "remaining_uncertainty": "A major causal hypothesis remains unresolved.",
                }
            ],
            "hypotheses": [
                {
                    "hypothesis_id": "h_unresolved",
                    "statement": "Collections are the dominant driver.",
                    "status": "unresolved",
                    "materiality": "major",
                    "evidence_for": [seed],
                    "evidence_against": [],
                    "unknowns": ["Alternative drivers remain material."],
                    "would_change_conclusion": "Evidence resolving the competing drivers.",
                    "confidence": "low",
                }
            ],
            "open_questions": [],
            "decision_summary": "The major driver remains unresolved.",
            "core_question_status": "answerable",
            "expected_value_of_more_research": "low",
        },
    )
    completeness = tools.completeness()
    assert "major_hypothesis_unresolved" in completeness["submission_blockers"]
    assert completeness["required_before_submit"] == []


def test_reflection_memory_keeps_older_objective_relevant_evidence(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("reflection-evidence-memory")
    manifest, _ = repo.create(req, {})
    env = environment()
    tools = FilingTools(repo, manifest["run_id"], req, env, lambda: None)
    seed = tools.bootstrap()["initial_evidence"][0]["evidence_id"]
    tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_memory",
                        "question": "Explain cash flow and customer collection changes.",
                        "priority": "required",
                        "status": "open",
                        "evidence_ids": [seed],
                        "conclusion": "",
                        "remaining_uncertainty": "Need filing evidence on collections.",
                    }
                ],
                "hypotheses": [],
                "open_questions": [],
                "decision_summary": "Need more evidence.",
                "core_question_status": "investigating",
                "expected_value_of_more_research": "high",
            }
        )
    )
    source_obj = next(iter(env["objects"].values()))
    old_relevant = tools._observe(
        source_obj,
        "Customer collection slowed materially and operating cash flow decreased.",
    )
    for index in range(12):
        tools._observe(source_obj, f"unrelated disclosure appendix item {index}")
    memory = tools.context_state()["reflection_evidence_memory"]
    assert len(memory) <= 18
    by_id = {item["evidence_id"]: item for item in memory}
    assert old_relevant in by_id
    assert "Customer collection" in by_id[old_relevant]["text_excerpt"]


def test_semantic_plateau_closes_stalled_research_as_limited(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("semantic-exhaustion-plateau")
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    seed = tools.bootstrap()["initial_evidence"][0]["evidence_id"]
    state = WorkingState.model_validate(
        {
            "objectives": [
                {
                    "objective_id": "obj_stalled",
                    "question": "Explain cash flow and working-capital changes.",
                    "priority": "required",
                    "status": "open",
                    "evidence_ids": [seed],
                    "conclusion": "",
                    "remaining_uncertainty": "The filing explanation remains incomplete.",
                }
            ],
            "hypotheses": [
                {
                    "hypothesis_id": "h_stalled",
                    "statement": "Collections may explain the cash-flow change.",
                    "status": "investigating",
                    "materiality": "major",
                    "evidence_for": [seed],
                    "evidence_against": [],
                    "unknowns": ["Need a stronger filing explanation."],
                    "would_change_conclusion": "A material alternative cause.",
                    "confidence": "low",
                }
            ],
            "open_questions": [
                {
                    "question_id": "q_stalled",
                    "question": "Does the filing provide a stronger causal explanation?",
                    "priority": "high",
                    "status": "open",
                    "evidence_ids": [],
                    "explanation": "",
                }
            ],
            "decision_summary": "Research is still open.",
            "core_question_status": "investigating",
            "expected_value_of_more_research": "high",
        }
    )
    tools.apply_working_state(state)
    arguments = {"metrics": [], "period_labels": []}
    for index in range(6):
        tools.execute(f"plateau_fact_{index}", "get_financial_facts", arguments)
    decision = tools.reflection_decision()
    assert decision["reason"] == "research_plateau"
    first = tools.apply_working_state(state, trigger_reason="research_plateau")
    assert first["working_state"]["core_question_status"] == "investigating"
    assert tools.stagnant_plateau_reflections == 1

    assert tools.reflection_decision()["reason"] != "research_exhaustion_review"
    for index in range(5):
        tools.execute(f"plateau_again_fact_{index}", "get_financial_facts", arguments)
    exhaustion = tools.reflection_decision()
    assert exhaustion["reason"] == "research_exhaustion_review"
    assert exhaustion["research_exhaustion_review_required"] is True
    final = tools.apply_working_state(state, trigger_reason="research_exhaustion_review")
    working = final["working_state"]
    assert working["objectives"][0]["status"] == "limited"
    assert working["open_questions"][0]["status"] == "not_answerable_from_filings"
    assert working["core_question_status"] == "evidence_exhausted"
    assert working["expected_value_of_more_research"] == "low"
    assert tools.stagnant_plateau_reflections == 0
    assert tools.completeness()["required_before_submit"] == ["submit_research"]
    assert any(
        item.get("correction") == "semantic_plateau_evidence_exhausted"
        for item in final["reference_corrections"]
    )


def test_semantic_plateau_rewrite_does_not_count_as_research_progress(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("semantic-plateau-progress")
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    seed = tools.bootstrap()["initial_evidence"][0]["evidence_id"]
    initial = WorkingState.model_validate(
        {
            "objectives": [
                {
                    "objective_id": "obj_progress",
                    "question": "Explain cash flow and working-capital changes.",
                    "priority": "required",
                    "status": "open",
                    "evidence_ids": [seed],
                    "conclusion": "",
                    "remaining_uncertainty": "Need more evidence.",
                }
            ],
            "hypotheses": [
                {
                    "hypothesis_id": "h_progress",
                    "statement": "Working-capital changes may explain the cash-flow movement.",
                    "status": "investigating",
                    "materiality": "major",
                    "evidence_for": [seed],
                    "evidence_against": [],
                    "unknowns": ["Need more evidence."],
                    "would_change_conclusion": "A material alternative explanation.",
                    "confidence": "low",
                }
            ],
            "open_questions": [],
            "decision_summary": "Open.",
            "core_question_status": "investigating",
            "expected_value_of_more_research": "high",
        }
    )
    tools.apply_working_state(initial)
    arguments = {"metrics": [], "period_labels": []}
    for index in range(6):
        tools.execute(f"progress_fact_{index}", "get_financial_facts", arguments)
    assert tools.reflection_decision()["reason"] == "research_plateau"
    progressed = initial.model_copy(deep=True)
    progressed.objectives[0].remaining_uncertainty = "A narrower remaining question."
    tools.apply_working_state(progressed, trigger_reason="research_plateau")
    assert tools.stagnant_plateau_reflections == 1
    assert tools.reflection_decision()["reason"] != "research_exhaustion_review"
    for index in range(5):
        tools.execute(f"rewrite_plateau_fact_{index}", "get_financial_facts", arguments)
    assert tools.reflection_decision()["reason"] == "research_exhaustion_review"


def test_real_evidence_progress_clears_prior_plateau_counter(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("semantic-plateau-real-progress")
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    seed = tools.bootstrap()["initial_evidence"][0]["evidence_id"]
    state = WorkingState.model_validate(
        {
            "objectives": [
                {
                    "objective_id": "obj_real_progress",
                    "question": "Explain cash flow and working-capital changes.",
                    "priority": "required",
                    "status": "open",
                    "evidence_ids": [seed],
                    "conclusion": "",
                    "remaining_uncertainty": "Need more evidence.",
                }
            ],
            "hypotheses": [
                {
                    "hypothesis_id": "h_real_progress",
                    "statement": "Working-capital timing may explain the cash-flow movement.",
                    "status": "investigating",
                    "materiality": "major",
                    "evidence_for": [seed],
                    "evidence_against": [],
                    "unknowns": ["Need a stronger filing explanation."],
                    "would_change_conclusion": "A material alternative explanation.",
                    "confidence": "low",
                }
            ],
            "open_questions": [],
            "decision_summary": "Open.",
            "core_question_status": "investigating",
            "expected_value_of_more_research": "high",
        }
    )
    tools.apply_working_state(state)
    arguments = {"metrics": [], "period_labels": []}
    for index in range(6):
        tools.execute(f"real_progress_plateau_{index}", "get_financial_facts", arguments)
    assert tools.reflection_decision()["reason"] == "research_plateau"
    tools.apply_working_state(state, trigger_reason="research_plateau")
    assert tools.stagnant_plateau_reflections == 1

    perform_informative_search(tools, "real-progress-evidence")
    decision = tools.reflection_decision()
    assert decision["reason"] != "research_exhaustion_review"
    tools.apply_working_state(state, trigger_reason=str(decision["reason"]))
    assert tools.stagnant_plateau_reflections == 0


def test_all_required_limited_state_converges_to_evidence_exhausted(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("all-required-limited-exhaustion")
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    seed = tools.bootstrap()["initial_evidence"][0]["evidence_id"]
    perform_informative_search(tools, "limited-state-maturity")
    applied = tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_limited",
                        "question": "Explain cash flow and working-capital changes.",
                        "priority": "required",
                        "status": "limited",
                        "evidence_ids": [seed],
                        "conclusion": "The observed filing evidence does not fully resolve the question.",
                        "remaining_uncertainty": "A stronger filing-grounded explanation is unavailable.",
                    }
                ],
                "hypotheses": [],
                "open_questions": [],
                "decision_summary": "Only a limited conclusion is supportable.",
                "core_question_status": "answerable",
                "expected_value_of_more_research": "medium",
            }
        )
    )
    state = applied["working_state"]
    assert state["core_question_status"] == "evidence_exhausted"
    assert state["expected_value_of_more_research"] == "low"
    assert tools.completeness()["required_before_submit"] == ["submit_research"]
    assert any(
        item.get("correction") == "all_required_limited_requires_evidence_exhausted"
        for item in applied["reference_corrections"]
    )


def test_limited_objective_softens_global_absence_to_observed_boundary(tmp_path: Path) -> None:
    repo = ResearchRepository(tmp_path)
    req = request("limited-global-absence-boundary")
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    seed = tools.bootstrap()["initial_evidence"][0]["evidence_id"]
    perform_informative_search(tools, "limited-boundary-maturity")
    applied = tools.apply_working_state(
        WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_boundary",
                        "question": "Can the filing support a peer-relative classification?",
                        "priority": "required",
                        "status": "limited",
                        "evidence_ids": [seed],
                        "conclusion": (
                            "The filing contains no peer set and the filing does not disclose "
                            "a classification benchmark."
                        ),
                        "remaining_uncertainty": (
                            "No classification threshold is present in the filing."
                        ),
                    }
                ],
                "hypotheses": [],
                "open_questions": [],
                "decision_summary": "The cited evidence does not establish a peer benchmark.",
                "core_question_status": "evidence_exhausted",
                "expected_value_of_more_research": "low",
            }
        )
    )
    objective = applied["working_state"]["objectives"][0]
    assert "the cited evidence does not establish peer set" in objective["conclusion"].casefold()
    assert (
        "the cited evidence does not establish a classification benchmark"
        in objective["conclusion"].casefold()
    )
    assert (
        "the cited evidence does not establish classification threshold"
        in objective["remaining_uncertainty"].casefold()
    )
    assert any(
        item.get("correction") == "limited_global_absence_softened_to_observed_boundary"
        for item in applied["reference_corrections"]
    )


def test_oversized_submission_returns_actionable_limit_and_stops_repair_loop(
    tmp_path: Path,
) -> None:
    from researchforge.v2.runtime import ResearchLoop, RunInterrupted

    repo = ResearchRepository(tmp_path)
    req = request("oversized-submission-repair")
    manifest, _ = repo.create(req, {})
    tools = FilingTools(repo, manifest["run_id"], req, environment(), lambda: None)
    seed = tools.bootstrap()["initial_evidence"][0]["evidence_id"]

    for index, size in enumerate((4101, 4201, 4301), start=1):
        result = tools.execute(
            f"oversized_submit_{index}",
            "submit_research",
            {
                "stop_reason": "sufficient_evidence",
                "direct_answer": "not_applicable",
                "summary": "x" * size,
                "evidence_ids": [seed],
                "remaining_uncertainties": ["No material uncertainty."],
                "why_stop": "The required conclusion is already established.",
            },
        )
        assert result["error"] == "INVALID_TOOL_ARGUMENTS"
        assert result["field_limits"]["summary_max_chars"] == 4000
        assert result["observed_lengths"]["summary"] == size
        assert "Retry submit_research only" in result["required_action"]
        assert any("max_length=4000" in detail for detail in result["details"])
        assert any(f"actual_length={size}" in detail for detail in result["details"])

    assert tools.consecutive_invalid_submission_count() == 3

    loop = object.__new__(ResearchLoop)
    loop.tools = tools
    with pytest.raises(RunInterrupted) as exc_info:
        loop.agent({"calls": []})
    assert exc_info.value.code == "SUBMISSION_CONTRACT_REPAIR_EXHAUSTED"


def test_search_prefers_relevant_native_table_across_common_wording_variants() -> None:
    doc = source("0" * 64 + ".html")
    objects: dict[str, dict] = {}
    table_text = """Market | Avg. Occupied Days Percentage | Avg. Monthly Realized Rent per Property | Avg. Blended Change in Rent
Atlanta | 94.1% | $2,349 | 1.7%
Total/Average | 94.4% | $2,318 | 2.5%
"""
    objects["table_metrics"] = {
        **doc,
        "artifact_id": "table_metrics",
        "kind": "table",
        "title": "HTML metrics table",
        "text": table_text,
    }
    # Competing long page chunks share several literal query words. The structured table should
    # still make the first page of results because occupancy/occupied, rental/rent and
    # growth/change are retrieval aliases and table structure receives a bounded bonus.
    for index in range(13):
        objects[f"page_{index}"] = {
            **doc,
            "artifact_id": f"page_{index}",
            "kind": "page",
            "title": f"Page {index}",
            "text": (
                "same-store occupancy rental rate year over year " + ("background narrative " * 700)
            ),
        }
    results = search_objects(
        objects,
        "same-store occupancy rental rate growth year over year",
        "all",
        doc["document_id"],
    )
    first_twelve = results[:12]
    table = next(item for item in first_twelve if item["artifact_id"] == "table_metrics")
    assert "Avg. Occupied Days Percentage" in table["snippet"]
    assert "Avg. Blended Change in Rent" in table["snippet"]


def test_search_snippet_is_centered_on_matching_late_content() -> None:
    doc = source("0" * 64 + ".html")
    text = (
        "irrelevant beginning " * 200
        + "\nAvg. Monthly Realized Rent per Property | $2,318\n"
        + "tail " * 200
    )
    objects = {
        "table_late": {
            **doc,
            "artifact_id": "table_late",
            "kind": "table",
            "title": "Metrics",
            "text": text,
        }
    }
    result = search_objects(objects, "rental rate", "all", doc["document_id"])[0]
    target = "Avg. Monthly Realized Rent per Property"
    assert target in result["snippet"]
    assert result["snippet"].find(target) < 500
