"""Zero-provider-call smoke for the published V2 n8n transport."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from typing import Any


def request(url: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"} if data else {}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            content_type = response.headers.get("Content-Type", "")
            payload = json.load(response) if "json" in content_type else response.read().decode()
            return response.status, payload
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw.decode()


def run_smoke(webhook: str, form: str) -> dict[str, Any]:
    form_code, form_page = request(form)
    if form_code != 200 or "ResearchForge V2" not in str(form_page):
        raise RuntimeError("V2 n8n form is unavailable")

    invalid_cases = [
        ({}, "INVALID_INPUT"),
        ({"company_query": "NVDA", "research_question": ""}, "INVALID_INPUT"),
        (
            {"company_query": "NVDA", "research_question": "test", "market_hint": "CRYPTO"},
            "INVALID_INPUT",
        ),
        (
            {
                "company_query": "NVDA",
                "research_question": "test",
                "requested_period_label": "2025Q5",
            },
            "INVALID_INPUT",
        ),
        (
            {"company_query": "NVDA", "research_question": "test", "research_mode": "general"},
            "INVALID_INPUT",
        ),
    ]
    for payload, expected in invalid_cases:
        code, output = request(webhook, payload)
        if code != 422 or not isinstance(output, dict) or output.get("code") != expected:
            raise RuntimeError(f"unexpected n8n failure envelope: {code}/{output}")
        if "conclusion" in output or "research_result" in output:
            raise RuntimeError("n8n invented research content for invalid input")

    return {
        "status": "PASS",
        "runtime": "v2",
        "form": "PASS",
        "invalid_transport_cases": len(invalid_cases),
        "provider_calls": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--webhook", default="http://127.0.0.1:5678/webhook/researchforge-v2")
    parser.add_argument("--form", default="http://127.0.0.1:5678/form/researchforge-v2-form")
    args = parser.parse_args()
    print(json.dumps(run_smoke(args.webhook, args.form), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
