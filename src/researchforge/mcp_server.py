"""Thin MCP interface over the canonical ResearchForge V2 backend."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlencode

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from researchforge.ingestion.discovery import Market, OfficialDisclosureDiscovery
from researchforge.ingestion.errors import IngestionAbstention

JsonObject = dict[str, Any]


class ResearchForgeApiClient:
    """Small local API client so MCP remains transport, never a second research engine."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def request(
        self,
        path: str,
        *,
        method: Literal["GET", "POST"] = "GET",
        body: JsonObject | None = None,
    ) -> JsonObject:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=payload,
            method=method,
            headers={"Content-Type": "application/json"} if payload is not None else {},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.load(response)
                return {"ok": True, "status_code": response.status, "data": data}
        except urllib.error.HTTPError as exc:
            try:
                error = json.loads(exc.read().decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                error = {"detail": "ResearchForge API returned a non-JSON error."}
            return {"ok": False, "status_code": exc.code, "error": error}
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return {
                "ok": False,
                "status_code": 503,
                "error": {
                    "code": "RESEARCHFORGE_API_UNAVAILABLE",
                    "message": f"Local ResearchForge API is unavailable ({type(exc).__name__}).",
                },
            }


def _unwrap(response: JsonObject) -> JsonObject:
    if response.get("ok") is True:
        data = response.get("data")
        return data if isinstance(data, dict) else {"items": data}
    return {"error": response.get("error"), "status_code": response.get("status_code")}


def build_mcp_server(
    *,
    api_base: str = "http://127.0.0.1:8000",
    api_client: ResearchForgeApiClient | None = None,
    discovery: OfficialDisclosureDiscovery | None = None,
) -> MCPServer[None]:
    """Build MCP tools over the same V2 research/data path as Web and n8n."""
    client = api_client or ResearchForgeApiClient(api_base)
    official_discovery = discovery or OfficialDisclosureDiscovery()
    server: MCPServer[None] = MCPServer(
        name="researchforge",
        title="ResearchForge",
        description="Auditable public-company filing research over the canonical V2 runtime.",
        version="2.0.0-alpha.1",
        instructions=(
            "Use ResearchForge for evidence-grounded public-company filing research. "
            "Do not request trading instructions, price targets or investment recommendations."
        ),
    )

    @server.tool(
        name="resolve_company",
        description="Resolve a public-company name or ticker against supported official markets.",
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=True,
        ),
        structured_output=True,
    )
    def resolve_company(
        company_query: str,
        market_hint: Market | None = None,
    ) -> JsonObject:
        try:
            company = official_discovery.resolve(company_query, market_hint=market_hint)
        except IngestionAbstention as exc:
            return {
                "resolved": False,
                "code": exc.code,
                "stage": exc.stage,
                "message": str(exc),
            }
        return {"resolved": True, "company": company.artifact_value(), "market": company.market}

    @server.tool(
        name="discover_filing",
        description="Find one official periodic filing for a resolved supported issuer and period.",
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=True,
        ),
        structured_output=True,
    )
    def discover_filing(
        company_query: str,
        period_label: str | None = None,
        market_hint: Market | None = None,
        research_time: str | None = None,
    ) -> JsonObject:
        cutoff = datetime.fromisoformat(research_time) if research_time else datetime.now(UTC)
        try:
            filing = official_discovery.discover(
                company_query,
                period_label=period_label,
                research_time=cutoff,
                market_hint=market_hint,
            )
        except IngestionAbstention as exc:
            return {
                "found": False,
                "code": exc.code,
                "stage": exc.stage,
                "message": str(exc),
            }
        return {
            "found": True,
            "provider": filing.provider,
            "filing_id": filing.filing_id,
            "title": filing.title,
            "source_uri": filing.source_uri,
            "published_at": filing.published_at,
            "period_label": filing.period_label,
            "company": filing.company.artifact_value(),
        }

    @server.tool(
        name="run_company_research",
        description="Create one V2 filing-research run; read the persisted result/trace by run_id.",
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=True,
        ),
        structured_output=True,
    )
    def run_company_research(
        company_query: str,
        research_question: str,
        market_hint: Market | None = None,
        period_label: str | None = None,
        research_time: str | None = None,
        idempotency_key: str | None = None,
    ) -> JsonObject:
        response = client.request(
            "/v2/research-runs",
            method="POST",
            body={
                "company_query": company_query,
                "market_hint": market_hint,
                "requested_period_label": period_label,
                "research_question": research_question,
                "research_time": research_time or datetime.now(UTC).isoformat(),
                "idempotency_key": idempotency_key or f"mcp-{uuid.uuid4().hex}",
            },
        )
        return _unwrap(response)

    @server.tool(
        name="get_research_result",
        description="Read the immutable report/result for a persisted V2 ResearchForge run.",
        annotations=ToolAnnotations(
            read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
        ),
        structured_output=True,
    )
    def get_research_result(run_id: str) -> JsonObject:
        return _unwrap(client.request(f"/v2/research-runs/{run_id}/result"))

    @server.tool(
        name="get_research_trace",
        description="Read the persisted public research events for a V2 run.",
        annotations=ToolAnnotations(
            read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
        ),
        structured_output=True,
    )
    def get_research_trace(run_id: str) -> JsonObject:
        return _unwrap(client.request(f"/v2/research-runs/{run_id}/trace"))

    @server.tool(
        name="get_financial_facts",
        description="Read verified deterministic Financial Facts from the same V2 run workspace.",
        annotations=ToolAnnotations(
            read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
        ),
        structured_output=True,
    )
    def get_financial_facts(run_id: str) -> JsonObject:
        return _unwrap(client.request(f"/v2/research-runs/{run_id}/facts"))

    @server.tool(
        name="search_filing_evidence",
        description="Search the persisted V2 run's complete official-filing index without new research.",
        annotations=ToolAnnotations(
            read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
        ),
        structured_output=True,
    )
    def search_filing_evidence(run_id: str, question: str, limit: int = 8) -> JsonObject:
        if not 1 <= limit <= 20:
            return {"error": {"code": "INVALID_LIMIT", "message": "limit must be 1..20"}}
        query = urlencode({"query": question, "kind": "all", "limit": limit})
        return _unwrap(client.request(f"/v2/research-runs/{run_id}/search?{query}"))

    return server


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="researchforge-mcp")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument(
        "--api-base",
        default=os.getenv("RESEARCHFORGE_API_BASE", "http://127.0.0.1:8000"),
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    server = build_mcp_server(api_base=str(args.api_base))
    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        server.run(transport="streamable-http", host=str(args.host), port=int(args.port))


if __name__ == "__main__":
    main()
