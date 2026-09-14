"""Small V2 command-line client for the canonical ResearchForge API."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from typing import Any

JsonObject = dict[str, Any]


def _request(base: str, path: str, *, body: JsonObject | None = None) -> Any:
    payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        base.rstrip("/") + path,
        data=payload,
        method="POST" if payload is not None else "GET",
        headers={"Content-Type": "application/json"} if payload is not None else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            detail = {"detail": "non-JSON ResearchForge API error"}
        raise SystemExit(
            json.dumps({"status_code": exc.code, "error": detail}, ensure_ascii=False)
        ) from None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="researchforge")
    parser.add_argument(
        "--api-base",
        default=os.getenv("RESEARCHFORGE_API_BASE", "http://127.0.0.1:8000"),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("capabilities", help="show the running V2 provider/tool capability surface")

    run = commands.add_parser("run", help="create one V2 filing-research run")
    run.add_argument("company")
    run.add_argument("question")
    run.add_argument("--market", choices=["CN", "US", "HK"])
    run.add_argument("--period")
    run.add_argument("--research-time")
    run.add_argument("--idempotency-key")

    show = commands.add_parser("show", help="read a persisted V2 run resource")
    show.add_argument("run_id")
    show.add_argument(
        "--resource",
        choices=["status", "result", "trace", "workspace", "facts", "calculations"],
        default="status",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    base = str(args.api_base)
    if args.command == "capabilities":
        output = _request(base, "/v2/capabilities")
    elif args.command == "run":
        output = _request(
            base,
            "/v2/research-runs",
            body={
                "company_query": args.company,
                "market_hint": args.market,
                "requested_period_label": args.period,
                "research_question": args.question,
                "research_time": args.research_time or datetime.now(UTC).isoformat(),
                "idempotency_key": args.idempotency_key or f"cli-{uuid.uuid4().hex}",
            },
        )
    else:
        suffix = "" if args.resource == "status" else f"/{args.resource}"
        output = _request(base, f"/v2/research-runs/{args.run_id}{suffix}")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
