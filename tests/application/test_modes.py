"""Frozen acceptance cases for all five product research modes."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from researchforge.application.contracts import ResearchRunRequest, TaskType
from researchforge.application.service import UnsupportedCapabilityError
from tests.runtime_helpers import assert_v14_schema, build_service


def _request(
    task_type: TaskType,
    *,
    companies: list[str],
    periods: list[str],
    research_time: str,
    question: str,
) -> ResearchRunRequest:
    return ResearchRunRequest(
        task_type=task_type,
        research_question=question,
        company_ids=companies,
        requested_period_labels=periods,
        research_time=datetime.fromisoformat(research_time),
        idempotency_key=f"mode-{task_type}-{'-'.join(companies)}",
    )


@pytest.mark.parametrize(
    ("run_request", "semantic_assertion"),
    [
        (
            _request(
                "company_research",
                companies=["cn_300750"],
                periods=["2023Q3", "2023FY", "2024Q1", "2024H1"],
                research_time="2024-08-01T00:00:00+08:00",
                question="基本面和利润质量发生了什么变化?",
            ),
            "trend",
        ),
        (
            _request(
                "filing_analysis",
                companies=["cn_300750"],
                periods=["2024Q1", "2024H1"],
                research_time="2024-08-01T00:00:00+08:00",
                question="半年报利润质量相较一季报如何?",
            ),
            "filing",
        ),
        (
            _request(
                "peer_comparison",
                companies=["cn_300750", "cn_300014"],
                periods=["2024H1"],
                research_time="2024-09-04T00:00:00+08:00",
                question="两家公司同期利润现金转化能力如何?",
            ),
            "peer",
        ),
        (
            _request(
                "thesis_investigation",
                companies=["cn_300750"],
                periods=["2024H1"],
                research_time="2024-08-01T00:00:00+08:00",
                question="可证伪命题: 利润增长完全由现金流改善支持。",
            ),
            "thesis",
        ),
        (
            _request(
                "risk_detection",
                companies=["cn_300014"],
                periods=["2023FY", "2024Q1"],
                research_time="2024-04-26T23:59:59+08:00",
                question="有哪些可解释的利润质量风险信号?",
            ),
            "risk",
        ),
    ],
)
def test_each_mode_runs_the_same_ten_stage_workflow(
    tmp_path: Path,
    run_request: ResearchRunRequest,
    semantic_assertion: str,
) -> None:
    service = build_service(tmp_path)
    submission = service.submit(run_request)

    manifest = service.execute(submission.run_id)
    result = service.get_result(submission.run_id)
    trace = service.get_trace(submission.run_id)

    assert manifest["lifecycle_state"] == "succeeded"
    assert result["task_type"] == run_request.task_type
    assert len(trace["stages"]) == 10
    assert [event["stage"] for event in trace["stages"]] == list(service.workflow.stage_names)
    if semantic_assertion == "trend":
        trend = next(
            check for check in result["mandatory_checks"] if check["check_code"] == "revenue_trend"
        )
        assert trend["status"] == "performed"
    elif semantic_assertion == "peer":
        assert len(result["companies"]) == 2
        assert any(claim["claim_type"] == "comparison" for claim in result["claims"])
    elif semantic_assertion == "thesis":
        assert "mixed" in result["executive_summary"]
        assert any(claim["epistemic_status"] == "uncertain" for claim in result["claims"])
    elif semantic_assertion == "risk":
        assert result["risk_claim_ids"]
        assert any(claim["claim_type"] == "risk" for claim in result["claims"])
    else:
        assert len(result["requested_periods"]) == 2
    assert_v14_schema(manifest, "run-manifest.schema.json")
    assert_v14_schema(result, "research-result.schema.json")
    assert_v14_schema(trace, "workflow-trace.schema.json")


def test_thesis_mode_refuses_investment_advice(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    request = _request(
        "thesis_investigation",
        companies=["cn_300750"],
        periods=["2024H1"],
        research_time="2024-08-01T00:00:00+08:00",
        question="请给出买入建议和目标价。",
    )

    with pytest.raises(UnsupportedCapabilityError, match="investment advice"):
        service.submit(request)


@pytest.mark.parametrize(
    ("task_type", "companies", "periods"),
    [
        ("company_research", ["cn_300750"], ["2023Q3", "2023FY"]),
        ("filing_analysis", ["cn_300750"], ["2023Q3"]),
        ("peer_comparison", ["cn_300750", "cn_300014"], ["2023Q3"]),
        ("thesis_investigation", ["cn_300750"], ["2023Q3"]),
        ("risk_detection", ["cn_300014"], ["2023Q3", "2023FY"]),
    ],
)
def test_each_mode_degrades_safely_when_cutoff_excludes_all_facts(
    tmp_path: Path,
    task_type: TaskType,
    companies: list[str],
    periods: list[str],
) -> None:
    service = build_service(tmp_path)
    request = _request(
        task_type,
        companies=companies,
        periods=periods,
        research_time="2023-01-01T00:00:00+08:00",
        question="在证据截止时间内能否形成可靠结论?",
    )

    submission = service.submit(request)
    manifest = service.execute(submission.run_id)
    trace = service.get_trace(submission.run_id)

    assert manifest["lifecycle_state"] == "insufficient_data"
    assert manifest["artifacts"]["result_id"] is None
    assert manifest["failure"]["code"] == "INSUFFICIENT_DATA"
    assert trace["terminal_state"] == "insufficient_data"
    assert_v14_schema(manifest, "run-manifest.schema.json")
    assert_v14_schema(trace, "workflow-trace.schema.json")
