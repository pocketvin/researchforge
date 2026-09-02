"""FastAPI lifecycle and error-semantics tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from researchforge.adapters.evolution_storage import EvolutionArtifactRepository
from researchforge.api.app import create_app
from tests.runtime_helpers import build_service, catl_request


def test_healthcheck_does_not_require_a_run(tmp_path: Path) -> None:
    client = TestClient(create_app(build_service(tmp_path)))

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.4.0"}


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
