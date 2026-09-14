#!/usr/bin/env python3
"""Read-only/live-safe MCP smoke over the canonical ResearchForge V2 backend."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from mcp.client import Client

from researchforge.mcp_server import build_mcp_server


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--run-id")
    parser.add_argument("--include-discovery", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    server = build_mcp_server(api_base=str(args.api_base))
    payload: dict[str, Any] = {"schema_version": "2.0.0", "runtime": "v2"}
    async with Client(server) as client:
        listing = await client.list_tools()
        payload["tools"] = [tool.name for tool in listing.tools]
        if args.include_discovery:
            resolved = await client.call_tool(
                "resolve_company", {"company_query": "贵州茅台", "market_hint": "CN"}
            )
            filing = await client.call_tool(
                "discover_filing",
                {"company_query": "贵州茅台", "market_hint": "CN", "period_label": "2025FY"},
            )
            payload["resolve_company"] = resolved.structured_content
            payload["discover_filing"] = filing.structured_content
        if args.run_id:
            run_id = str(args.run_id)
            facts = await client.call_tool("get_financial_facts", {"run_id": run_id})
            evidence = await client.call_tool(
                "search_filing_evidence",
                {"run_id": run_id, "question": "盈利能力和现金流如何?", "limit": 5},
            )
            result = await client.call_tool("get_research_result", {"run_id": run_id})
            trace = await client.call_tool("get_research_trace", {"run_id": run_id})
            facts_data = facts.structured_content or {}
            evidence_data = evidence.structured_content or {}
            result_data = result.structured_content or {}
            trace_data = trace.structured_content or {}
            report = result_data.get("report", {})
            payload["existing_run"] = {
                "run_id": run_id,
                "fact_count": len(facts_data.get("items", [])),
                "evidence_count": evidence_data.get("count", 0),
                "direct_answer": report.get("direct_answer"),
                "finding_count": len(report.get("findings", [])),
                "trace_event_count": len(trace_data.get("events", [])),
            }
    return payload


def main() -> None:
    args = _parser().parse_args()
    payload = asyncio.run(_run(args))
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
