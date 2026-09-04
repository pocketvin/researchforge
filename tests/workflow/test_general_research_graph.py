# ruff: noqa: RUF001 -- Chinese research prompts are intentional test input.

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from researchforge.application.research import LoadedResearchData
from tests.runtime_helpers import assert_v17_schema, build_service


def _narrative(
    base: dict[str, object], chunk_id: str, section: str, text: str, page: int
) -> dict[str, object]:
    return {
        **base,
        "chunk_id": chunk_id,
        "section": section,
        "text": text,
        "text_hash": "a" * 64,
        "locator": {
            "page_start": page,
            "page_end": page,
            "paragraph_start": None,
            "paragraph_end": None,
            "char_start": None,
            "char_end": None,
        },
    }


def test_company_research_graph_builds_question_aware_v17_result(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    loaded = service.fixture_catalog.load(
        ["cn_300750"], ["2024H1"], datetime.fromisoformat("2024-08-01T00:00:00+08:00")
    )
    seed = dict(loaded.evidence_chunks[0])
    broad = (
        _narrative(
            seed,
            "chunk_business",
            "Business and segments",
            "动力电池业务收入增长，海外市场需求继续扩展。",
            15,
        ),
        _narrative(
            seed,
            "chunk_mgmt",
            "Management discussion",
            "管理层说明销量增长与产品结构变化共同影响本期业绩。",
            21,
        ),
        _narrative(
            seed, "chunk_growth", "Growth drivers", "新能源车与储能需求是主要增长驱动之一。", 25
        ),
        _narrative(
            seed,
            "chunk_risk",
            "Risk factors",
            "市场竞争、原材料价格与海外监管构成主要不确定性。",
            31,
        ),
        _narrative(
            seed, "chunk_outlook", "Outlook", "公司计划继续投入技术研发与全球供应能力。", 36
        ),
    )
    enriched = LoadedResearchData(
        facts=loaded.facts,
        source_documents=loaded.source_documents,
        requested_periods=loaded.requested_periods,
        companies=loaded.companies,
        evidence_chunks=loaded.evidence_chunks + broad,
    )
    service.workflow.load_data = lambda *_args: enriched
    request = {
        "input_kind": "research",
        "task_type": "company_research",
        "research_question": "这家公司最近增长主要来自哪里？主要风险是什么？",
        "company_ids": ["cn_300750"],
        "requested_period_labels": ["2024H1"],
        "research_time": "2024-08-01T00:00:00+08:00",
    }
    outcome = service.workflow.run("run_general", "trace_general", request)
    assert outcome.terminal_state == "succeeded"
    assert outcome.result is not None
    assert outcome.result["schema_version"] == "1.7.0"
    assert_v17_schema(outcome.result, "research-result.schema.json")
    assert outcome.result["task_type"] == "company_research"
    assert outcome.result["research_intent"]["skill"] in {"growth_analysis", "risk_analysis"}
    assert len(outcome.result["research_plan"]) >= 5
    assert 2 <= len(outcome.result["claims"]) <= 8
    assert len(outcome.result["analysis_sections"]) >= 2
    assert len(outcome.result["suggested_follow_ups"]) >= 4
    assert outcome.result["evidence_coverage"]["selected_chunk_count"] >= 2
    cited = set(outcome.result["evidence_coverage"]["cited_evidence_ids"])
    selected = set(outcome.result["evidence_coverage"]["selected_evidence_ids"])
    counter = set(outcome.result["claims"][0]["counter_evidence_search"]["evidence_ids"])
    assert cited <= selected | counter
    assert len(outcome.trace["stages"]) == 10
