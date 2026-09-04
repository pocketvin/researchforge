# ruff: noqa: RUF001 -- Chinese test prompts intentionally use Chinese punctuation.

from __future__ import annotations

from researchforge.application.general_research import (
    EvidenceRetriever,
    QuestionRouter,
    ResearchPlanner,
)


def _chunk(chunk_id: str, section: str, text: str, page: int) -> dict[str, object]:
    return {
        "chunk_id": chunk_id,
        "section": section,
        "text": text,
        "locator": {"page_start": page},
    }


def test_router_maps_broad_questions_to_distinct_skills() -> None:
    router = QuestionRouter()
    assert router.route("帮我完整分析一下这家公司").skill == "company_overview"
    assert router.route("最近增长主要来自哪里？").skill == "growth_analysis"
    assert router.route("当前最大的风险是什么？").skill == "risk_analysis"
    assert router.route("现金流和债务压力怎么样？").skill == "financial_health"
    assert router.route("主要业务分部结构发生了什么变化？").skill == "business_analysis"
    assert router.route("为什么今年利润下降？").skill == "earnings_change"


def test_planner_changes_steps_with_question_intent() -> None:
    router = QuestionRouter()
    planner = ResearchPlanner()
    growth = planner.plan("run_demo", router.route("增长主要来自哪里？"))
    risk = planner.plan("run_demo", router.route("最大的风险是什么？"))
    assert growth != risk
    assert len(growth) >= 5
    assert any("分部" in step["description"] for step in growth)
    assert any("风险" in step["description"] for step in risk)


def test_retriever_prefers_question_relevant_sections_and_adds_counter_candidates() -> None:
    chunks = (
        _chunk(
            "business",
            "Business and segments",
            "Data center revenue growth was driven by AI demand.",
            3,
        ),
        _chunk(
            "risk", "Risk factors", "Customer concentration and regulation may affect demand.", 9
        ),
        _chunk(
            "finance",
            "Financial statements",
            "Revenue and cash flow are shown in the statements.",
            20,
        ),
        _chunk("other", "Filing narrative", "Corporate address and administrative information.", 1),
        _chunk(
            "mgmt",
            "Management discussion",
            "Management attributes growth to accelerated computing demand.",
            5,
        ),
        _chunk(
            "supplier", "Customers and suppliers", "Supply availability remains a constraint.", 10
        ),
    )
    router = QuestionRouter()
    intent = router.route("增长主要来自哪里？")
    selected = EvidenceRetriever().retrieve(
        chunks, question="增长主要来自哪里？", intent=intent, limit=4
    )
    assert selected
    assert selected[0]["chunk_id"] in {"business", "mgmt"}
    counters = EvidenceRetriever().counter_candidates(chunks, selected, limit=2)
    assert any(item["chunk_id"] == "risk" for item in counters)
