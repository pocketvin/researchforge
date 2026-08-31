"""Fixed twenty-run G1 reliability batch over all five research modes."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, cast

from researchforge.application.contracts import ResearchRunRequest, TaskType
from researchforge.application.service import ResearchRunService

CASE_CONFIGS: tuple[dict[str, Any], ...] = (
    {
        "task_type": "company_research",
        "question": "基本面和利润质量发生了什么变化?",
        "companies": ["cn_300750"],
        "periods": ["2023Q3", "2023FY", "2024Q1", "2024H1"],
        "research_time": "2024-08-01T00:00:00+08:00",
    },
    {
        "task_type": "filing_analysis",
        "question": "半年报利润质量相较一季报如何?",
        "companies": ["cn_300750"],
        "periods": ["2024Q1", "2024H1"],
        "research_time": "2024-08-01T00:00:00+08:00",
    },
    {
        "task_type": "peer_comparison",
        "question": "两家公司同期利润现金转化能力如何?",
        "companies": ["cn_300750", "cn_300014"],
        "periods": ["2024H1"],
        "research_time": "2024-09-04T00:00:00+08:00",
    },
    {
        "task_type": "thesis_investigation",
        "question": "可证伪命题: 利润增长完全由现金流改善支持。",
        "companies": ["cn_300750"],
        "periods": ["2024H1"],
        "research_time": "2024-08-01T00:00:00+08:00",
    },
    {
        "task_type": "risk_detection",
        "question": "有哪些可解释的利润质量风险信号?",
        "companies": ["cn_300014"],
        "periods": ["2023FY", "2024Q1"],
        "research_time": "2024-04-26T23:59:59+08:00",
    },
)


def run_reliability_batch(
    service: ResearchRunService,
    *,
    repeats: int = 4,
) -> dict[str, Any]:
    """Execute the frozen matrix and return exact denominators and states."""
    runs: list[dict[str, Any]] = []
    for repeat in range(1, repeats + 1):
        for config in CASE_CONFIGS:
            task_type = cast(TaskType, str(config["task_type"]))
            request = ResearchRunRequest(
                task_type=task_type,
                research_question=str(config["question"]),
                company_ids=list(config["companies"]),
                requested_period_labels=list(config["periods"]),
                research_time=datetime.fromisoformat(str(config["research_time"])),
                idempotency_key=f"reliability-{repeat}-{task_type}",
            )
            started = time.monotonic()
            submission = service.submit(request)
            manifest = service.execute(submission.run_id)
            runs.append(
                {
                    "run_id": submission.run_id,
                    "task_type": task_type,
                    "repeat": repeat,
                    "lifecycle_state": manifest["lifecycle_state"],
                    "latency_ms": round((time.monotonic() - started) * 1000, 3),
                }
            )
    succeeded = sum(item["lifecycle_state"] == "succeeded" for item in runs)
    return {
        "schema_version": "1.4.0",
        "total_runs": len(runs),
        "succeeded_runs": succeeded,
        "success_rate": succeeded / len(runs),
        "mode_denominators": {
            task_type: sum(item["task_type"] == task_type for item in runs)
            for task_type in (
                "company_research",
                "filing_analysis",
                "peer_comparison",
                "thesis_investigation",
                "risk_detection",
            )
        },
        "runs": runs,
    }
