"""Thin MCP interface over the existing ResearchForge research backend."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from researchforge.application.general_research import EvidenceRetriever, QuestionRouter
from researchforge.ingestion.discovery import Market, OfficialDisclosureDiscovery
from researchforge.ingestion.errors import IngestionAbstention

JsonObject = dict[str, Any]


class ResearchForgeApiClient:
    """Small local API client so MCP never becomes a second research engine."""

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
                return {
                    "ok": True,
                    "status_code": response.status,
                    "data": data,
                }
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
    return {
        "error": response.get("error"),
        "status_code": response.get("status_code"),
    }


def build_mcp_server(
    *,
    api_base: str = "http://127.0.0.1:8000",
    api_client: ResearchForgeApiClient | None = None,
    discovery: OfficialDisclosureDiscovery | None = None,
) -> MCPServer[None]:
    """Build an MCP server whose tools reuse existing discovery/research components."""
    client = api_client or ResearchForgeApiClient(api_base)
    official_discovery = discovery or OfficialDisclosureDiscovery()
    router = QuestionRouter()
    retriever = EvidenceRetriever()
    server: MCPServer[None] = MCPServer(
        name="researchforge",
        title="ResearchForge",
        description="Auditable public-company research tools over official filings.",
        version="1.8.5",
        instructions=(
            "Use ResearchForge for evidence-grounded public-company research. "
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
        description=(
            "Create one bounded ResearchForge General Research run. Returns a run_id; use read "
            "tools to inspect status/result/trace."
        ),
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
        cutoff = research_time or datetime.now(UTC).isoformat()
        key = idempotency_key or f"mcp-{uuid.uuid4().hex}"
        response = client.request(
            "/v1/autonomous-research-runs",
            method="POST",
            body={
                "company_query": company_query,
                "market_hint": market_hint,
                "requested_period_label": period_label,
                "research_question": research_question,
                "research_time": cutoff,
                "idempotency_key": key,
                "research_mode": "general",
            },
        )
        return _unwrap(response)

    @server.tool(
        name="get_research_result",
        description="Read the immutable result for a persisted ResearchForge run.",
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
        structured_output=True,
    )
    def get_research_result(run_id: str) -> JsonObject:
        return _unwrap(client.request(f"/v1/research-runs/{run_id}/result"))

    @server.tool(
        name="get_research_trace",
        description="Read the sanitized workflow trace for a persisted ResearchForge run.",
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
        structured_output=True,
    )
    def get_research_trace(run_id: str) -> JsonObject:
        return _unwrap(client.request(f"/v1/research-runs/{run_id}/trace"))

    @server.tool(
        name="get_financial_facts",
        description="Read verified deterministic Financial Facts for a persisted run.",
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
        structured_output=True,
    )
    def get_financial_facts(run_id: str) -> JsonObject:
        return _unwrap(client.request(f"/v1/research-runs/{run_id}/facts"))

    @server.tool(
        name="search_filing_evidence",
        description=(
            "Search a persisted run's verified filing Evidence with the same bounded lexical "
            "retriever used by ResearchForge."
        ),
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
        structured_output=True,
    )
    def search_filing_evidence(run_id: str, question: str, limit: int = 8) -> JsonObject:
        if not 1 <= limit <= 20:
            return {"error": {"code": "INVALID_LIMIT", "message": "limit must be 1..20"}}
        response = client.request(f"/v1/research-runs/{run_id}/evidence")
        if response.get("ok") is not True:
            return _unwrap(response)
        raw = response.get("data")
        if not isinstance(raw, list):
            return {"error": {"code": "INVALID_EVIDENCE_RESPONSE"}}
        chunks = tuple(item for item in raw if isinstance(item, dict))
        intent = router.route(question)
        selected = retriever.retrieve(chunks, question=question, intent=intent, limit=limit)
        return {
            "run_id": run_id,
            "intent": intent.skill,
            "count": len(selected),
            "evidence": list(selected),
        }

    return server


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="researchforge-mcp")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
    )
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
