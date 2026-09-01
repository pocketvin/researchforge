"""Exercise the packaged frontend, API, workflow, artifacts, and database."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from typing import Any, cast
from uuid import uuid4


def request_json(
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> dict[str, Any] | list[dict[str, Any]]:
    """Send one bounded HTTP request and decode its JSON response."""
    body = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"} if body is not None else {},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status not in {200, 202}:
            raise RuntimeError(f"unexpected HTTP {response.status} from {url}")
        return cast(dict[str, Any] | list[dict[str, Any]], json.load(response))


def request_text(url: str, *, timeout: float = 10.0) -> str:
    """Fetch one bounded text resource."""
    with urllib.request.urlopen(url, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP {response.status} from {url}")
        return cast(str, response.read().decode())


def wait_for_success(base_url: str, run_id: str, timeout: float) -> dict[str, Any]:
    """Poll the persisted manifest until the deterministic run succeeds."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        manifest = request_json(f"{base_url}/v1/research-runs/{run_id}")
        if not isinstance(manifest, dict):
            raise RuntimeError("run manifest was not a JSON object")
        state = manifest["lifecycle_state"]
        if state == "succeeded":
            return manifest
        if state in {"failed", "cancelled", "timed_out", "insufficient_data"}:
            raise RuntimeError(f"smoke run entered terminal state {state}")
        time.sleep(0.1)
    raise TimeoutError(f"smoke run did not finish within {timeout:.1f}s")


def run_smoke(base_url: str, timeout: float) -> dict[str, Any]:
    """Return concise, machine-readable evidence for a complete packaged run."""
    health = request_text(f"{base_url}/healthz")
    catalog = request_json(f"{base_url}/v1/catalog")
    if health != "ok":
        raise RuntimeError("packaged frontend health response was not 'ok'")
    if not isinstance(catalog, dict) or len(catalog.get("supported_task_types", [])) != 5:
        raise RuntimeError("catalog did not advertise all five research modes")

    submission = request_json(
        f"{base_url}/v1/research-runs",
        payload={
            "task_type": "filing_analysis",
            "research_question": "2024年上半年利润是否转化为经营现金流?",
            "company_ids": ["cn_300750"],
            "requested_period_labels": ["2024H1"],
            "research_time": "2024-08-01T00:00:00+08:00",
            "idempotency_key": f"docker-smoke-{uuid4().hex}",
        },
    )
    if not isinstance(submission, dict):
        raise RuntimeError("run submission was not a JSON object")
    run_id = str(submission["run_id"])
    manifest = wait_for_success(base_url, run_id, timeout)
    result = request_json(f"{base_url}/v1/research-runs/{run_id}/result")
    trace = request_json(f"{base_url}/v1/research-runs/{run_id}/trace")
    facts = request_json(f"{base_url}/v1/research-runs/{run_id}/facts")
    if not isinstance(result, dict) or result.get("run_id") != run_id:
        raise RuntimeError("result did not resolve to the submitted run")
    if not isinstance(trace, dict) or len(trace.get("stages", [])) != 10:
        raise RuntimeError("workflow trace did not contain ten stages")
    if not isinstance(facts, list) or len(facts) < 2:
        raise RuntimeError("persisted run did not expose its financial facts")

    frontend = request_text(f"{base_url}/")
    if 'id="root"' not in frontend:
        raise RuntimeError("frontend root was not served")
    return {
        "status": "PASS",
        "schema_version": "1.4.0",
        "run_id": run_id,
        "lifecycle_state": manifest["lifecycle_state"],
        "research_modes": len(catalog["supported_task_types"]),
        "workflow_stages": len(trace["stages"]),
        "fact_count": len(facts),
        "frontend_served": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:4173")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    try:
        print(json.dumps(run_smoke(args.base_url.rstrip("/"), args.timeout), indent=2))
    except (KeyError, OSError, RuntimeError, TimeoutError, urllib.error.HTTPError) as exc:
        raise SystemExit(f"Docker smoke failed: {exc}") from exc


if __name__ == "__main__":
    main()
