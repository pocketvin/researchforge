"""Run live cross-market golden regression for V1.7 general company research."""

# ruff: noqa: RUF001 -- Chinese acceptance questions intentionally use Chinese punctuation.

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

os.environ.setdefault("RESEARCHFORGE_REASONING_MODE", "deterministic")

from researchforge.api.app import build_default_service
from researchforge.application.autonomous import AutonomousResearchCoordinator
from researchforge.application.contracts import AutonomousResearchRequest
from researchforge.ingestion.discovery import Market
from researchforge.ingestion.errors import IngestionAbstention

ROOT = Path(__file__).resolve().parents[1]
METRICS = {
    "revenue",
    "operating_cost",
    "net_income",
    "operating_cash_flow",
    "accounts_receivable",
    "inventory",
}
OFFICIAL_HOSTS = {
    "static.cninfo.com.cn",
    "disc.static.szse.cn",
    "www.sec.gov",
    "www1.hkexnews.hk",
}

QUICK_CASES: tuple[tuple[Market, str, str], ...] = (
    ("CN", "贵州茅台", "当前最值得关注的三个财务或经营风险是什么？请按证据强弱排序。"),
    ("US", "NVDA", "这家公司最近的增长主要来自哪里？哪些业务或因素贡献最大？"),
    ("HK", "腾讯", "公司的主要业务和分部结构是什么？最近发生了哪些重要变化？"),
)
ALL_CASES = (
    *QUICK_CASES,
    ("CN", "宁德时代", "帮我完整分析一下这家公司，覆盖业绩、增长、财务质量和主要风险。"),
    ("CN", "比亚迪", "最近一个报告期的业绩发生了什么重要变化？主要原因是什么？"),
    ("US", "AAPL", "这家公司的盈利能力怎么样？利润变化主要受什么影响？"),
    ("US", "MSFT", "管理层如何描述未来增长、经营重点和主要不确定性？"),
    ("HK", "小米集团", "这家公司最近的增长主要来自哪里？主要风险是什么？"),
    ("HK", "阿里巴巴", "公司的主要业务结构和增长驱动发生了哪些重要变化？"),
)


def _check_success(service: Any, run_id: str, source_uri: str) -> dict[str, Any]:
    facts = service.get_facts(run_id)
    evidence = service.get_evidence(run_id)
    result = service.get_result(run_id)
    trace = service.get_trace(run_id)
    metric_codes = {fact["metric_code"] for fact in facts}
    if metric_codes != METRICS:
        raise RuntimeError(f"six-metric contract failed: {sorted(metric_codes)}")
    fact_ids = {fact["fact_id"] for fact in facts}
    evidence_ids = {item["chunk_id"] for item in evidence}
    for claim in result["claims"]:
        if not set(claim["fact_ids"]).issubset(fact_ids):
            raise RuntimeError("claim references a missing financial fact")
        if not set(claim["support_evidence_ids"]).issubset(evidence_ids):
            raise RuntimeError("claim references missing supporting evidence")
    if result.get("schema_version") != "1.7.0":
        raise RuntimeError("general regression did not produce a V1.7 Research Result")
    if len(result.get("claims", [])) < 2:
        raise RuntimeError("general research requires multiple evidence-linked findings")
    if len(result.get("analysis_sections", [])) < 2:
        raise RuntimeError("general research is missing deep-analysis sections")
    if len(result.get("suggested_follow_ups", [])) < 4:
        raise RuntimeError("general research is missing suggested follow-up questions")
    coverage = result.get("evidence_coverage", {})
    if coverage.get("selected_chunk_count", 0) < 2:
        raise RuntimeError("general research selected too little filing evidence")
    if trace["terminal_state"] != "succeeded" or len(trace["stages"]) != 10:
        raise RuntimeError("successful run is missing the complete ten-stage trace")
    host = (urlparse(source_uri).hostname or "").casefold()
    if host not in OFFICIAL_HOSTS:
        raise RuntimeError(f"unexpected official-source host: {host}")
    return {
        "fact_count": len(facts),
        "evidence_count": len(evidence),
        "claim_count": len(result["claims"]),
        "analysis_section_count": len(result.get("analysis_sections", [])),
        "follow_up_count": len(result.get("suggested_follow_ups", [])),
        "research_skill": result.get("research_intent", {}).get("skill"),
        "trace_stage_count": len(trace["stages"]),
        "source_host": host,
    }


def run_case(
    coordinator: AutonomousResearchCoordinator,
    market: Market,
    query: str,
    question: str,
) -> dict[str, Any]:
    request = AutonomousResearchRequest(
        company_query=query,
        market_hint=market,
        requested_period_label=None,
        research_question=question,
        research_mode="general",
        research_time=datetime.now(UTC),
        idempotency_key=f"golden-{uuid4().hex}",
    )
    try:
        service, submission, filing = coordinator.prepare(request)
        manifest = service.execute(submission.run_id)
    except IngestionAbstention as exc:
        return {
            "market": market,
            "query": query,
            "question": question,
            "status": "abstained",
            "code": exc.code,
            "stage": exc.stage,
            "reason": exc.reason,
        }
    if manifest["lifecycle_state"] != "succeeded":
        failure = manifest.get("failure") or {}
        return {
            "market": market,
            "query": query,
            "question": question,
            "status": "abstained",
            "code": failure.get("code", "RUN_NOT_SUCCEEDED"),
            "stage": "research",
            "reason": failure.get("message", "Research run did not succeed."),
        }
    checks = _check_success(service, submission.run_id, filing.source_uri)
    return {
        "market": market,
        "query": query,
        "question": question,
        "status": "succeeded",
        "company_id": filing.company.company_id,
        "ticker": filing.company.ticker,
        "period": filing.period_label,
        "provider": filing.provider,
        "source_uri": filing.source_uri,
        **checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Run the nine-company extended set.")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts/golden-regression/summary.json"
    )
    args = parser.parse_args()
    artifact_root = ROOT / "artifacts/golden-regression/runtime"
    coordinator = AutonomousResearchCoordinator(
        artifact_root,
        lambda data_root: build_default_service(artifact_root, data_root_override=data_root),
        reviewed_root=None,
    )
    cases = ALL_CASES if args.all else QUICK_CASES
    results = [run_case(coordinator, market, query, question) for market, query, question in cases]
    successes = {item["market"] for item in results if item["status"] == "succeeded"}
    required = {"CN", "US", "HK"}
    summary = {
        "schema_version": "1.7.0",
        "verified_at": datetime.now(UTC).isoformat(),
        "mode": "extended" if args.all else "quick",
        "results": results,
        "success_markets": sorted(successes),
        "safe_outcome_count": len(results),
        "status": "PASS" if required.issubset(successes) else "FAIL",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["status"] != "PASS":
        raise SystemExit("quick regression requires at least one trusted success per market")


if __name__ == "__main__":
    main()
