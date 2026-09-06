from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp.client import Client

from researchforge.mcp_server import ResearchForgeApiClient, build_mcp_server

ROOT = Path(__file__).resolve().parents[1]


class FakeApiClient(ResearchForgeApiClient):
    def __init__(self) -> None:
        pass

    def request(
        self, path: str, *, method: str = "GET", body: dict[str, object] | None = None
    ) -> dict[str, object]:
        if path.endswith("/facts"):
            return {"ok": True, "status_code": 200, "data": [{"fact_id": "fact_1"}]}
        if path.endswith("/evidence"):
            return {
                "ok": True,
                "status_code": 200,
                "data": [
                    {
                        "chunk_id": "chunk_1",
                        "section": "Financial statements",
                        "text": "经营现金流 100",
                        "locator": {"page_start": 1},
                        "source_uri": "https://example.invalid/report.pdf",
                    }
                ],
            }
        if path == "/v1/autonomous-research-runs" and method == "POST":
            assert body is not None
            assert body["research_mode"] == "general"
            return {
                "ok": True,
                "status_code": 202,
                "data": {"run_id": "run_mcp", "created": True},
            }
        return {"ok": True, "status_code": 200, "data": {"run_id": "run_mcp"}}


@pytest.mark.asyncio
async def test_mcp_server_exposes_bounded_backend_tools() -> None:
    server = build_mcp_server(api_client=FakeApiClient())
    async with Client(server) as client:
        listing = await client.list_tools()
        tools = {tool.name: tool for tool in listing.tools}
        assert set(tools) == {
            "resolve_company",
            "discover_filing",
            "run_company_research",
            "get_research_result",
            "get_research_trace",
            "get_financial_facts",
            "search_filing_evidence",
        }
        assert tools["get_research_trace"].annotations is not None
        assert tools["get_research_trace"].annotations.read_only_hint is True
        assert tools["run_company_research"].annotations is not None
        assert tools["run_company_research"].annotations.destructive_hint is False
        assert tools["run_company_research"].annotations.open_world_hint is True

        contract = json.loads(
            (ROOT / "examples/contracts/v1.8/mcp-toolset.example.json").read_text(encoding="utf-8")
        )
        assert [item["name"] for item in contract["tools"]] == [tool.name for tool in listing.tools]
        for item in contract["tools"]:
            annotations = tools[item["name"]].annotations
            assert annotations is not None
            assert annotations.read_only_hint is item["read_only"]
            assert annotations.destructive_hint is item["destructive"]
            assert annotations.idempotent_hint is item["idempotent"]
            assert annotations.open_world_hint is item["open_world"]


@pytest.mark.asyncio
async def test_mcp_reuses_backend_facts_retrieval_and_submission() -> None:
    server = build_mcp_server(api_client=FakeApiClient())
    async with Client(server) as client:
        facts = await client.call_tool("get_financial_facts", {"run_id": "run_mcp"})
        assert facts.structured_content == {"items": [{"fact_id": "fact_1"}]}

        evidence = await client.call_tool(
            "search_filing_evidence",
            {"run_id": "run_mcp", "question": "现金流如何", "limit": 5},
        )
        assert evidence.structured_content is not None
        assert evidence.structured_content["count"] == 1
        assert evidence.structured_content["intent"] == "financial_health"

        submission = await client.call_tool(
            "run_company_research",
            {
                "company_query": "贵州茅台",
                "research_question": "完整分析这家公司",
                "market_hint": "CN",
                "period_label": "2025FY",
            },
        )
        assert submission.structured_content == {"run_id": "run_mcp", "created": True}
