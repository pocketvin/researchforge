"""Canonical FastAPI surface tests: one V2 runtime, no live V1 execution API."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from researchforge.api.app import create_app
from researchforge.v2.contracts import ResearchRequest
from researchforge.v2.runtime import ResearchService
from researchforge.v2.storage import ResearchRepository, now


def request(key: str = "api-v2-test") -> ResearchRequest:
    return ResearchRequest(
        company_query="Synthetic Test Co",
        market_hint="US",
        requested_period_label="2025FY",
        research_question="What does the filing say about cash flow?",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key=key,
    )


def service(tmp_path: Path) -> ResearchService:
    return ResearchService(
        ResearchRepository(tmp_path / "v2"),
        None,
        configuration={
            "provider": "hybrid",
            "model": "deepseek-v4-flash",
            "reflection_model": "deepseek-v4-flash",
            "synthesis_model": "deepseek-v4-flash",
            "semantic_review_model": "qwen-plus",
            "research_fallback_model": "qwen-plus",
            "fallback_reflection_model": "qwen3-max",
            "fallback_synthesis_model": "qwen3-max",
            "fallback_semantic_review_model": "deepseek-v4-flash",
            "vision_model": "qwen3-vl-plus",
            "data_namespace": "product",
        },
    )


def test_health_and_capabilities_are_v2_only(tmp_path: Path) -> None:
    client = TestClient(create_app(service(tmp_path)))
    assert client.get("/healthz").json() == {
        "status": "ok",
        "version": "2.0.0-alpha.1",
        "runtime": "v2",
    }
    capabilities = client.get("/v2/capabilities")
    assert capabilities.status_code == 200
    assert capabilities.json()["provider"] == "hybrid"
    assert capabilities.json()["agent_ready"] is False
    assert capabilities.json()["fallback_reflection_model"] == "qwen3-max"
    assert capabilities.json()["fallback_synthesis_model"] == "qwen3-max"
    assert capabilities.json()["fallback_semantic_review_model"] == "deepseek-v4-flash"
    assert client.get("/v1/runtime-capabilities").status_code == 404
    assert client.get("/v1/catalog").status_code == 404


def test_create_run_rejects_invalid_or_market_incompatible_period_before_queueing(
    tmp_path: Path,
) -> None:
    runtime = service(tmp_path)
    client = TestClient(create_app(runtime))
    payload = request("api-invalid-period").model_dump(mode="json")

    invalid = client.post(
        "/v2/research-runs",
        json={**payload, "requested_period_label": "2024Q4"},
    )
    assert invalid.status_code == 422
    assert runtime.repository.list_runs(limit=10) == []

    incompatible = client.post(
        "/v2/research-runs",
        json={**payload, "market_hint": "HK", "requested_period_label": "2024Q1"},
    )
    assert incompatible.status_code == 422
    assert runtime.repository.list_runs(limit=10) == []


def test_create_run_fails_closed_without_model_and_rejects_advice(tmp_path: Path) -> None:
    client = TestClient(create_app(service(tmp_path)))
    payload = request().model_dump(mode="json")
    unavailable = client.post("/v2/research-runs", json=payload)
    assert unavailable.status_code == 503
    advice = client.post(
        "/v2/research-runs",
        json={**payload, "research_question": "Should I buy this stock?"},
    )
    assert advice.status_code == 422
    assert advice.json()["detail"]["code"] == "UNSUPPORTED_TASK"


def test_read_resources_share_one_v2_repository(tmp_path: Path) -> None:
    runtime = service(tmp_path)
    manifest, _ = runtime.repository.create(request("api-read-resources"), runtime.configuration)
    run_id = manifest["run_id"]
    environment = {
        "documents": {},
        "objects": {
            "ev_cash": {
                "artifact_id": "ev_cash",
                "kind": "evidence",
                "document_id": "doc_test",
                "text": "Operating cash flow increased to 120 while revenue was 500.",
                "page_number": 3,
            }
        },
        "facts": {
            "fact_cash": {
                "fact_id": "fact_cash",
                "artifact_id": "fact_cash",
                "kind": "fact",
                "document_id": "doc_test",
                "metric_code": "operating_cash_flow",
                "value": "120",
                "currency": "USD",
            }
        },
        "gaps": [],
    }
    state = {
        "observed": {},
        "calculations": {
            "calc_ratio": {
                "calculation_id": "calc_ratio",
                "formula_code": "ratio_percent",
                "value": "24",
            }
        },
        "working": {"objectives": [], "hypotheses": [], "open_questions": []},
        "dossier": None,
    }
    runtime.repository.attach(run_id, "environment", environment)
    runtime.repository.attach(run_id, "research_state", state)
    runtime.repository.attach(
        run_id,
        "result",
        {
            "schema_version": "2.0.0",
            "run_id": run_id,
            "report": {"executive_summary": "Synthetic persisted result."},
        },
    )
    runtime.repository.update(run_id, lifecycle_state="succeeded")
    client = TestClient(create_app(runtime))

    assert client.get(f"/v2/research-runs/{run_id}").status_code == 200
    assert client.get(f"/v2/research-runs/{run_id}/result").json()["run_id"] == run_id
    assert client.get(f"/v2/research-runs/{run_id}/facts").json()[0]["fact_id"] == "fact_cash"
    assert (
        client.get(f"/v2/research-runs/{run_id}/calculations").json()[0]["calculation_id"]
        == "calc_ratio"
    )
    search = client.get(
        f"/v2/research-runs/{run_id}/search",
        params={"query": "operating cash flow", "limit": 5},
    )
    assert search.status_code == 200
    assert search.json()["results"][0]["artifact_id"] == "ev_cash"
    workspace = client.get(f"/v2/research-runs/{run_id}/workspace")
    assert workspace.status_code == 200
    assert workspace.json()["facts"][0]["fact_id"] == "fact_cash"


def test_workspace_sanitizes_internal_ids_only_in_public_prose(tmp_path: Path) -> None:
    runtime = service(tmp_path)
    manifest, _ = runtime.repository.create(request("api-public-prose"), runtime.configuration)
    run_id = manifest["run_id"]
    environment = {"documents": {}, "objects": {}, "facts": {}, "gaps": []}
    state = {
        "observed": {},
        "calculations": {},
        "working": {
            "objectives": [
                {
                    "objective_id": "objective_test",
                    "question": "What does the filing establish?",
                    "priority": "required",
                    "status": "answered",
                    "evidence_ids": ["view_cash"],
                    "conclusion": "Supported by the filing (view_cash) and page_8.",
                    "remaining_uncertainty": "Check table_cash and fact_cash before going further.",
                }
            ],
            "hypotheses": [
                {
                    "hypothesis_id": "hyp_test",
                    "statement": "The hypothesis references view_cash.",
                    "status": "investigating",
                    "materiality": "material",
                    "evidence_for": ["view_cash"],
                    "evidence_against": [],
                    "unknowns": ["Whether page_8 changes the conclusion."],
                    "would_change_conclusion": "A contradiction in table_cash.",
                    "confidence": "medium",
                }
            ],
            "open_questions": [
                {
                    "question_id": "question_test",
                    "question": "Should page_8 be read again?",
                    "priority": "low",
                    "explanation": "Do not expose view_cash in public prose.",
                }
            ],
            "decision_summary": "run_internal has enough evidence.",
        },
        "dossier": {
            "stop_reason": "sufficient_evidence",
            "direct_answer": "not_applicable",
            "summary": "The conclusion cites view_cash.",
            "evidence_ids": ["view_cash"],
            "remaining_uncertainties": ["Recheck page_8 if needed."],
            "why_stop": "calc_ratio is complete.",
        },
    }
    runtime.repository.attach(run_id, "environment", environment)
    runtime.repository.attach(run_id, "research_state", state)
    client = TestClient(create_app(runtime))

    payload = client.get(f"/v2/research-runs/{run_id}/workspace").json()
    objective = payload["working"]["objectives"][0]
    assert objective["evidence_ids"] == ["view_cash"]
    assert all(
        token not in objective["conclusion"] + objective["remaining_uncertainty"]
        for token in ("view_", "page_", "table_", "fact_")
    )
    hypothesis = payload["working"]["hypotheses"][0]
    assert "view_" not in hypothesis["statement"]
    assert "page_" not in hypothesis["unknowns"][0]
    assert "table_" not in hypothesis["would_change_conclusion"]
    assert "page_" not in payload["working"]["open_questions"][0]["question"]
    assert "view_" not in payload["working"]["open_questions"][0]["explanation"]
    assert "run_" not in payload["working"]["decision_summary"]
    assert payload["stop_decision"]["evidence_ids"] == ["view_cash"]
    assert "view_" not in payload["stop_decision"]["summary"]
    assert "page_" not in payload["stop_decision"]["remaining_uncertainties"][0]
    assert "calc_" not in payload["stop_decision"]["why_stop"]


def test_v2_history_reads_only_v2_runs(tmp_path: Path) -> None:
    runtime = service(tmp_path)
    first, _ = runtime.repository.create(request("api-history-1"), runtime.configuration)
    second, _ = runtime.repository.create(request("api-history-2"), runtime.configuration)
    client = TestClient(create_app(runtime))
    history = client.get("/v2/research-runs?limit=10").json()
    assert {item["run_id"] for item in history} == {first["run_id"], second["run_id"]}


def test_trace_and_sse_drain_the_complete_terminal_event_journal(
    tmp_path: Path, monkeypatch
) -> None:
    from researchforge.v2 import api as v2_api

    runtime = service(tmp_path)
    manifest, _ = runtime.repository.create(request("api-complete-trace"), runtime.configuration)
    run_id = manifest["run_id"]
    for index in range(12):
        runtime.repository.emit(run_id, "audit_event", "audit", f"event {index}", "running")
    runtime.repository.update(
        run_id,
        lifecycle_state="failed",
        finished_at=now(),
        failure={"code": "SYNTHETIC", "message": "synthetic"},
    )
    monkeypatch.setattr(v2_api, "SSE_EVENT_BATCH_SIZE", 5)
    client = TestClient(create_app(runtime))

    trace = client.get(f"/v2/research-runs/{run_id}/trace").json()["events"]
    assert len(trace) == 13  # run_queued + twelve synthetic audit events
    assert [event["sequence"] for event in trace] == list(range(1, 14))

    stream = client.get(f"/v2/research-runs/{run_id}/events")
    ids = [int(value) for value in re.findall(r"^id: (\d+)$", stream.text, flags=re.MULTILINE)]
    assert ids == list(range(1, 14))
    assert "event: terminal" in stream.text
