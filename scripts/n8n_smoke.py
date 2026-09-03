"""Exercise an imported, published n8n workflow against the real ResearchForge backend."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from scripts.validate_contracts import ROOT, load_json, validate_instance


def request(url: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"} if data else {}
    )
    try:
        with urllib.request.urlopen(req, timeout=240) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, json.load(exc)


def form_request(url: str, fields: dict[str, str] | None = None) -> tuple[int, str]:
    data: bytes | None = None
    headers: dict[str, str] = {}
    if fields is not None:
        boundary = f"researchforge-{uuid4().hex}"
        chunks: list[bytes] = []
        for name, value in fields.items():
            chunks.append(
                (
                    f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
                    f"{value}\r\n"
                ).encode()
            )
        chunks.append(f"--{boundary}--\r\n".encode())
        data = b"".join(chunks)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=240) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def validate_output(output: dict[str, Any]) -> None:
    schemas = {path.resolve(): load_json(path) for path in (ROOT / "schemas").glob("*/*.json")}
    schema = ROOT / "schemas/v1.5/n8n-research-output.schema.json"
    validate_instance(output, schemas[schema], schema, schemas)


def run_smoke(webhook: str, backend: str, form: str, output_dir: Path | None) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    cutoff = "2026-09-03T00:00:00+08:00"
    last_input: dict[str, Any] = {}
    last_output: dict[str, Any] = {}
    for company, period in [
        ("cn_300750", "2024H1"),
        ("cn_300750", "2024FY"),
        ("cn_002594", "2024H1"),
    ]:
        payload = {
            "company_id": company,
            "period": period,
            "research_question": f"{period}利润是否真正转化成了经营现金流?",
            "research_time": cutoff,
            "idempotency_key": f"n8n-smoke-{uuid4().hex}",
        }
        status, output = request(webhook, payload)
        if status != 200 or output.get("status") != "succeeded":
            raise RuntimeError(f"n8n case {company}/{period}: HTTP {status}, {output.get('code')}")
        validate_output(output)
        run_id = output["run_id"]
        pairs = {
            "research_result": "result",
            "financial_facts": "facts",
            "calculations": "calculations",
            "supporting_evidence": "evidence",
            "research_trace": "trace",
        }
        for field, resource in pairs.items():
            code, original = request(f"{backend}/v1/research-runs/{run_id}/{resource}")
            if code != 200 or output[field] != original:
                raise RuntimeError(f"n8n changed the authoritative {resource} artifact")
        original = output["research_result"]
        for alias, field in {
            "conclusion": "executive_summary",
            "findings": "claims",
            "limitations": "limitations",
            "monitoring": "monitoring_items",
        }.items():
            if output[alias] != original[field]:
                raise RuntimeError(f"n8n changed presentation alias {alias}")
        manifest_code, manifest = request(f"{backend}/v1/research-runs/{run_id}")
        if manifest_code != 200 or manifest["lifecycle_state"] != "succeeded":
            raise RuntimeError("same-backend run did not succeed")
        record = {
            "company_id": company,
            "period": period,
            "run_id": run_id,
            "status": "PASS",
            "fact_count": len(output["financial_facts"]),
            "calculation_count": len(output["calculations"]),
            "evidence_count": len(output["supporting_evidence"]),
            "trace_stage_count": len(output["research_trace"]["stages"]),
            "all_five_backend_artifacts_identical": True,
        }
        records.append(record)
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / f"{company}-{period}.json").write_text(
                json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        last_input, last_output = payload, output
        print(f"PASS real n8n → {company}/{period} → {run_id}", flush=True)
    status, retry = request(webhook, last_input)
    if status != 200 or retry["run_id"] != last_output["run_id"]:
        raise RuntimeError("identical webhook retry did not return the original run")
    failures = [
        ({}, 422, "INVALID_INPUT"),
        ({**last_input, "backend_url": "http://untrusted.invalid"}, 422, "INVALID_INPUT"),
        (
            {**last_input, "research_question": "同一幂等键不应创建不同研究问题"},
            409,
            "IDEMPOTENCY_CONFLICT",
        ),
        (
            {
                **last_input,
                "company_id": "cn_000001",
                "idempotency_key": f"n8n-refuse-{uuid4().hex}",
            },
            422,
            "UNSUPPORTED_OR_INVALID_INPUT",
        ),
        (
            {
                **last_input,
                "research_time": "2020-01-01T00:00:00Z",
                "idempotency_key": f"n8n-cutoff-{uuid4().hex}",
            },
            409,
            "RUN_INSUFFICIENT_DATA",
        ),
    ]
    for payload, expected_status, expected_code in failures:
        status, failure = request(webhook, payload)
        validate_output(failure)
        if status != expected_status or failure.get("code") != expected_code:
            raise RuntimeError(f"unexpected failure response {status}/{failure.get('code')}")
        if "research_result" in failure or "conclusion" in failure:
            raise RuntimeError("failure output invented a report")
    # Also exercise minimum three-field submission (including a short fresh n8n execution ID).
    status, minimal = request(
        webhook, {k: last_input[k] for k in ("company_id", "period", "research_question")}
    )
    if status != 200 or minimal.get("status") != "succeeded":
        raise RuntimeError("minimal Company + Period + Question input failed")
    validate_output(minimal)
    form_status, form_page = form_request(form)
    expected_form_fields = [
        "ResearchForge · 可核验 A 股基本面研究",
        "Company / 公司",
        "Period / 报告期",
        "Research Question / 研究问题",
    ]
    if form_status != 200 or any(field not in form_page for field in expected_form_fields):
        raise RuntimeError("native n8n research form is unavailable or incomplete")
    form_status, completed_page = form_request(
        form,
        {
            "field-0": "宁德时代 · 300750.SZSE",
            "field-1": "2024H1",
            "field-2": "2024年上半年利润是否真正转化成了经营现金流?",
        },
    )
    expected_result_sections = [
        "ResearchForge 研究完成",
        "Executive Conclusion",
        "Financial Facts",
        "Research Trace",
    ]
    if form_status != 200 or any(
        section not in completed_page for section in expected_result_sections
    ):
        raise RuntimeError("native n8n form did not render the verified research output")
    form_status, refused_page = form_request(
        form,
        {
            "field-0": "比亚迪 · 002594.SZSE",
            "field-1": "2024FY",
            "field-2": "该不支持期间应当明确拒绝且不生成研究结论。",
        },
    )
    if (
        form_status != 200
        or "研究未生成" not in refused_page
        or "UNSUPPORTED_OR_INVALID_INPUT" not in refused_page
        or "Executive Conclusion" in refused_page
    ):
        raise RuntimeError("native n8n form did not render the bounded failure state")
    summary = {
        "status": "PASS",
        "evidence_kind": "ENGINEERING_RUNTIME_NOT_HUMAN_EVALUATION",
        "human_user_value_validated": False,
        "verified_at": datetime.now(UTC).isoformat(),
        "n8n_version": "2.37.9",
        "workflow_sha256": hashlib.sha256(
            (ROOT / "integrations/n8n/researchforge.workflow.json").read_bytes()
        ).hexdigest(),
        "cases": records,
        "idempotent_retry": "PASS",
        "minimum_input": "PASS",
        "native_form_success": "PASS",
        "native_form_failure": "PASS",
        "real_http_failure_checks": len(failures),
    }
    if output_dir:
        (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return cast(dict[str, Any], summary)


def run_failure_fixture(webhook: str) -> dict[str, Any]:
    """Exercise real n8n looping/error routing; the stub never supplies financial truth."""
    scenarios = {
        "test-running-then-failed": (409, "RUN_FAILED", 3),
        "test-running-then-cancelled": (409, "RUN_CANCELLED", 3),
        "test-running-forever": (504, "POLL_LIMIT_EXCEEDED", 3),
        "test-status-unavailable": (502, "STATUS_UNAVAILABLE", 1),
        "test-missing-result": (502, "RESULT_ARTIFACTS_UNAVAILABLE", None),
    }
    for scenario, (expected_http, expected_code, expected_polls) in scenarios.items():
        code, output = request(
            webhook,
            {
                "company_id": "cn_300750",
                "period": "2024H1",
                "research_question": scenario,
            },
        )
        validate_output(output)
        if code != expected_http or output.get("code") != expected_code:
            raise RuntimeError(f"test-only runtime route {scenario} did not return {expected_code}")
        if expected_polls is not None and output.get("polls") != expected_polls:
            raise RuntimeError("actual n8n poll loop did not count/bound node executions")
        print(f"PASS actual n8n test-only transport route: {scenario}", flush=True)
    return {
        "status": "PASS",
        "evidence_kind": "TEST_ONLY_TRANSPORT_NOT_RESEARCH_NOT_HUMAN",
        "scenario_count": len(scenarios),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--webhook", default="http://127.0.0.1:5678/webhook/researchforge-v15")
    parser.add_argument("--backend", default="http://127.0.0.1:8000")
    parser.add_argument("--form", default="http://127.0.0.1:5678/form/researchforge-v15-form")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--failure-fixture", action="store_true")
    args = parser.parse_args()
    if args.failure_fixture:
        print(json.dumps(run_failure_fixture(args.webhook), indent=2))
    else:
        print(
            json.dumps(
                run_smoke(args.webhook, args.backend.rstrip("/"), args.form, args.output_dir),
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
