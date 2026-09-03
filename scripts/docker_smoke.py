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
    if not isinstance(catalog, dict):
        raise RuntimeError("catalog was not a JSON object")
    if catalog.get("data_namespace") != "product":
        raise RuntimeError("packaged product did not enforce the product namespace")
    if catalog.get("supported_task_types") != ["filing_analysis"]:
        raise RuntimeError("catalog advertised an unverified product capability")
    companies = catalog.get("companies", [])
    cases = {
        (company["company_id"], period)
        for company in companies
        for period in company["period_labels"]
    }
    if cases != {("cn_300750", "2024H1"), ("cn_300750", "2024FY"), ("cn_002594", "2024H1")}:
        raise RuntimeError("catalog did not enforce the three-filing product boundary")
    results = [run_case(base_url, timeout, company, period) for company, period in sorted(cases)]
    frontend = request_text(f"{base_url}/")
    if 'id="root"' not in frontend:
        raise RuntimeError("frontend root was not served")
    return {
        "status": "PASS",
        "data_namespace": "product",
        "case_count": len(results),
        "cases": results,
    }


def run_case(base_url: str, timeout: float, company: str, period: str) -> dict[str, Any]:
    """Run the same public HTTP path for a selected catalog case."""

    submission = request_json(
        f"{base_url}/v1/research-runs",
        payload={
            "task_type": "filing_analysis",
            "research_question": f"{period}利润是否转化为经营现金流?",
            "company_ids": [company],
            "requested_period_labels": [period],
            "research_time": "2026-09-03T00:00:00+08:00",
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
    evidence = request_json(f"{base_url}/v1/research-runs/{run_id}/evidence")
    calculations = request_json(f"{base_url}/v1/research-runs/{run_id}/calculations")
    if not isinstance(result, dict) or result.get("run_id") != run_id:
        raise RuntimeError("result did not resolve to the submitted run")
    if not isinstance(trace, dict) or len(trace.get("stages", [])) != 10:
        raise RuntimeError("workflow trace did not contain ten stages")
    if not isinstance(facts, list) or len(facts) < 2:
        raise RuntimeError("persisted run did not expose its financial facts")
    if not isinstance(evidence, list) or not evidence:
        raise RuntimeError("persisted run did not expose bounded evidence chunks")
    if any("SYNTHETIC" in str(chunk.get("text", "")) for chunk in evidence):
        raise RuntimeError("product run exposed synthetic fixture evidence")
    if not all(
        str(chunk.get("source_uri", "")).startswith(
            ("https://disc.static.szse.cn/", "https://static.cninfo.com.cn/")
        )
        for chunk in evidence
    ):
        raise RuntimeError("product evidence did not resolve to the official source host")
    if not isinstance(calculations, list) or not calculations:
        raise RuntimeError("persisted run did not expose deterministic calculation records")
    if not result.get("monitoring_items"):
        raise RuntimeError("result did not expose an actionable monitoring item")
    if not result.get("limitations"):
        raise RuntimeError("result did not expose limitations")
    material_claims = [
        claim for claim in result.get("claims", []) if claim.get("materiality") == "material"
    ]
    if not material_claims or not all(
        claim.get("support_evidence_ids") for claim in material_claims
    ):
        raise RuntimeError("material claims did not resolve supporting evidence")
    if not all(
        claim.get("counter_evidence_search", {}).get("performed") is True
        and claim.get("counter_evidence_search", {}).get("result") in {"found", "not_found"}
        for claim in material_claims
    ):
        raise RuntimeError("product result did not expose an honest counter-evidence search")

    frontend = request_text(f"{base_url}/")
    if 'id="root"' not in frontend:
        raise RuntimeError("frontend root was not served")
    return {
        "status": "PASS",
        "schema_version": "1.5.0",
        "data_namespace": "product",
        "company_id": company,
        "period": period,
        "run_id": run_id,
        "lifecycle_state": manifest["lifecycle_state"],
        "product_capabilities": 1,
        "workflow_stages": len(trace["stages"]),
        "fact_count": len(facts),
        "evidence_count": len(evidence),
        "calculation_count": len(calculations),
        "monitoring_item_count": len(result["monitoring_items"]),
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
