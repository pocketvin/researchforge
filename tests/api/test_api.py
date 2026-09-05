"""FastAPI lifecycle and error-semantics tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from researchforge.adapters.evolution_storage import EvolutionArtifactRepository
from researchforge.api.app import create_app
from tests.runtime_helpers import build_service, catl_request


def test_healthcheck_does_not_require_a_run(tmp_path: Path) -> None:
    client = TestClient(create_app(build_service(tmp_path)))

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.7.3"}


def test_api_runs_one_complete_background_case(tmp_path: Path) -> None:
    client = TestClient(create_app(build_service(tmp_path)))
    payload = catl_request().model_dump(mode="json")

    created = client.post("/v1/research-runs", json=payload)

    assert created.status_code == 202
    run_id = created.json()["run_id"]
    status_response = client.get(f"/v1/research-runs/{run_id}")
    assert status_response.status_code == 200
    assert status_response.json()["lifecycle_state"] == "succeeded"
    assert client.get(f"/v1/research-runs/{run_id}/result").status_code == 200
    facts = client.get(f"/v1/research-runs/{run_id}/facts")
    assert facts.status_code == 200
    assert {fact["metric_code"] for fact in facts.json()} >= {
        "revenue",
        "operating_cash_flow",
    }
    evidence = client.get(f"/v1/research-runs/{run_id}/evidence")
    assert evidence.status_code == 200
    assert evidence.json()[0]["chunk_id"].startswith("chunk_")
    calculations = client.get(f"/v1/research-runs/{run_id}/calculations")
    assert calculations.status_code == 200
    assert {item["formula_code"] for item in calculations.json()} >= {
        "gross_margin",
        "cash_conversion",
    }
    trace = client.get(f"/v1/research-runs/{run_id}/trace")
    assert trace.status_code == 200
    assert len(trace.json()["stages"]) == 10


def test_api_lists_recent_product_runs_for_workspace_restore(tmp_path: Path) -> None:
    client = TestClient(create_app(build_service(tmp_path)))
    payload = {
        **catl_request(key="api-history").model_dump(mode="json"),
        "task_type": "company_research",
        "requested_period_labels": ["2024Q1", "2024H1"],
    }

    created = client.post("/v1/research-runs", json=payload)
    response = client.get("/v1/research-runs?limit=5")

    assert created.status_code == 202
    assert response.status_code == 200
    items = response.json()
    assert items[0]["run_id"] == created.json()["run_id"]
    assert items[0]["lifecycle_state"] == "succeeded"
    assert items[0]["company_id"] == "cn_300750"
    assert items[0]["company_name"] == "宁德时代新能源科技股份有限公司"
    assert items[0]["period_label"] == "2024Q1"
    assert items[0]["research_question"] == payload["research_question"]


def test_api_idempotency_and_conflict(tmp_path: Path) -> None:
    client = TestClient(create_app(build_service(tmp_path)))
    first_payload = catl_request().model_dump(mode="json")
    second_payload = {**first_payload, "research_question": "不同问题"}

    first = client.post("/v1/research-runs", json=first_payload)
    repeated = client.post("/v1/research-runs", json=first_payload)
    conflict = client.post("/v1/research-runs", json=second_payload)

    assert repeated.status_code == 202
    assert repeated.json()["run_id"] == first.json()["run_id"]
    assert repeated.json()["created"] is False
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_api_returns_409_for_terminal_run_without_result(tmp_path: Path) -> None:
    client = TestClient(create_app(build_service(tmp_path)))
    payload = catl_request(
        key="api-insufficient-2024h1",
        research_time="2024-07-01T00:00:00+08:00",
    ).model_dump(mode="json")

    created = client.post("/v1/research-runs", json=payload)
    result = client.get(f"/v1/research-runs/{created.json()['run_id']}/result")

    assert result.status_code == 409
    assert result.json()["failure"]["code"] == "INSUFFICIENT_DATA"


def test_api_rejects_mode_with_insufficient_periods_before_queueing(tmp_path: Path) -> None:
    client = TestClient(create_app(build_service(tmp_path)))
    payload = {
        **catl_request(key="api-company-research").model_dump(mode="json"),
        "task_type": "company_research",
    }

    response = client.post("/v1/research-runs", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "UNSUPPORTED_TASK"


def test_catalog_is_unambiguous_and_bounded(tmp_path: Path) -> None:
    client = TestClient(create_app(build_service(tmp_path)))

    response = client.get("/v1/catalog")

    assert response.status_code == 200
    assert response.json()["supported_task_types"] == [
        "company_research",
        "filing_analysis",
        "peer_comparison",
        "thesis_investigation",
        "risk_detection",
    ]
    assert {company["company_id"] for company in response.json()["companies"]} == {
        "cn_300014",
        "cn_300750",
    }


def test_evolution_endpoints_are_read_only_views_of_persisted_artifacts(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    repository = EvolutionArtifactRepository(tmp_path)
    experiment = {
        "schema_version": "1.4.0",
        "experiment_id": "experiment_read_only",
        "status": "preregistered",
        "outcome": "PENDING",
    }
    patch = {"schema_version": "1.4.0", "patch_id": "patch_read_only"}
    repository.save("experiment_read_only", "experiment", experiment)
    repository.save("experiment_read_only", "skill_patch", patch)
    client = TestClient(create_app(service))

    response = client.get("/v1/evolution-experiments/experiment_read_only")
    artifact = client.get("/v1/evolution-experiments/experiment_read_only/artifacts/skill_patch")
    missing = client.get("/v1/evolution-experiments/experiment_missing")

    assert response.status_code == 200
    assert response.json() == experiment
    assert artifact.status_code == 200
    assert artifact.json() == patch
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "EXPERIMENT_NOT_FOUND"


def test_api_history_paginates_without_hiding_older_runs(tmp_path: Path) -> None:
    client = TestClient(create_app(build_service(tmp_path)))
    run_ids: list[str] = []
    for index in range(3):
        payload = {
            **catl_request(key=f"api-history-page-{index}").model_dump(mode="json"),
            "task_type": "company_research",
            "requested_period_labels": ["2024Q1", "2024H1"],
        }
        created = client.post("/v1/research-runs", json=payload)
        assert created.status_code == 202
        run_ids.append(created.json()["run_id"])

    first = client.get("/v1/research-runs?limit=1&offset=0")
    second = client.get("/v1/research-runs?limit=1&offset=1")

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(first.json()) == 1
    assert len(second.json()) == 1
    assert first.json()[0]["run_id"] != second.json()[0]["run_id"]
    assert {first.json()[0]["run_id"], second.json()[0]["run_id"]}.issubset(set(run_ids))


def test_autonomous_api_rejects_investment_advice_before_queueing(tmp_path: Path) -> None:
    client = TestClient(create_app(build_service(tmp_path)))
    response = client.post(
        "/v1/autonomous-research-runs",
        json={
            "company_query": "贵州茅台",
            "market_hint": "CN",
            "requested_period_label": "2025FY",
            "research_mode": "general",
            "research_question": "请给出买入建议和目标价。",
            "research_time": "2026-09-05T20:00:00+08:00",
            "idempotency_key": "api-autonomous-advice-guard",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "UNSUPPORTED_TASK"
    assert "investment advice" in response.json()["detail"]["message"]
    assert client.get("/v1/research-runs?limit=10").json() == []


def test_packaged_method_archive_is_available_without_runtime_artifact(tmp_path: Path) -> None:
    client = TestClient(create_app(build_service(tmp_path)))

    experiment = client.get("/v1/evolution-experiments/experiment_contingency_v1_5_001")
    outcome = client.get(
        "/v1/evolution-experiments/experiment_contingency_v1_5_001/artifacts/project-research-outcome"
    )

    assert experiment.status_code == 200
    assert experiment.json()["experiment_id"] == "experiment_contingency_v1_5_001"
    assert outcome.status_code == 200
    assert outcome.json()["status"] == ("RESEARCH_HYPOTHESIS_UNSUPPORTED_AFTER_TWO_EXPERIMENTS")


def test_api_startup_recovery_runs_in_background_without_blocking_health(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import threading
    import time

    service = build_service(tmp_path)
    started = threading.Event()
    release = threading.Event()

    def slow_recovery(*, exclude_run_ids: set[str] | None = None) -> list[str]:
        del exclude_run_ids
        started.set()
        release.wait(timeout=2)
        return []

    monkeypatch.setattr(service, "recover_interrupted_runs", slow_recovery)
    app = create_app(service)
    try:
        with TestClient(app) as client:
            assert started.wait(timeout=1)
            before = time.monotonic()
            response = client.get("/healthz")
            elapsed = time.monotonic() - before
            assert response.status_code == 200
            assert elapsed < 0.5
            assert release.is_set() is False
    finally:
        release.set()
