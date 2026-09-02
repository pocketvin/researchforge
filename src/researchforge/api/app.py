"""Asynchronous research-run HTTP resources."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi import Path as ApiPath
from fastapi.responses import JSONResponse

from researchforge.adapters.evolution_storage import EvolutionArtifactRepository
from researchforge.adapters.storage import (
    IdempotencyConflictError,
    RunNotFoundError,
)
from researchforge.application.contracts import CatalogResponse, ResearchRunRequest, RunSubmission
from researchforge.application.service import ResearchRunService, UnsupportedCapabilityError

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURE_ROOT = PROJECT_ROOT / "data" / "fixtures" / "g0"
DEFAULT_SKILL_MANIFEST = (
    PROJECT_ROOT / "skills" / "fundamental-research" / "versions" / "1.0.0" / "skill-version.json"
)


def build_default_service(artifact_root: Path | None = None) -> ResearchRunService:
    """Build the zero-cost deterministic runtime used by L1."""
    configured_root = artifact_root or Path(
        os.getenv("RESEARCHFORGE_ARTIFACT_ROOT", str(PROJECT_ROOT / "artifacts"))
    )
    return ResearchRunService.build(
        configured_root,
        DEFAULT_FIXTURE_ROOT,
        DEFAULT_SKILL_MANIFEST,
        database_url=os.getenv("RESEARCHFORGE_DATABASE_URL"),
    )


def create_app(
    service: ResearchRunService | None = None,
    *,
    artifact_root: Path | None = None,
) -> FastAPI:
    """Create an app whose background tasks share one lifecycle service."""
    runtime = service or build_default_service(artifact_root)
    runtime.recover_interrupted_runs()
    evolution_repository = EvolutionArtifactRepository(runtime.repository.root)
    app = FastAPI(
        title="ResearchForge API",
        version="1.4.0",
        description="Evidence-grounded financial research run resources.",
    )

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "version": "1.4.0"}

    def not_found(run_id: str) -> HTTPException:
        return HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "run_id": run_id})

    @app.post(
        "/v1/research-runs",
        response_model=RunSubmission,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_research_run(
        request: ResearchRunRequest,
        background_tasks: BackgroundTasks,
    ) -> RunSubmission:
        try:
            submission = runtime.submit(request)
        except IdempotencyConflictError as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "IDEMPOTENCY_CONFLICT", "message": str(exc)},
            ) from exc
        except UnsupportedCapabilityError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "UNSUPPORTED_TASK", "message": str(exc)},
            ) from exc
        if submission.created:
            background_tasks.add_task(runtime.execute, submission.run_id)
        return submission

    @app.get("/v1/research-runs/{run_id}")
    def get_research_run(
        run_id: Annotated[str, ApiPath(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")],
    ) -> dict[str, Any]:
        try:
            return runtime.get_manifest(run_id)
        except RunNotFoundError as exc:
            raise not_found(run_id) from exc

    @app.get("/v1/research-runs/{run_id}/result", response_model=None)
    def get_research_result(
        run_id: Annotated[str, ApiPath(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")],
    ) -> dict[str, Any] | JSONResponse:
        try:
            manifest = runtime.get_manifest(run_id)
        except RunNotFoundError as exc:
            raise not_found(run_id) from exc
        if manifest["lifecycle_state"] in {"queued", "running"}:
            return JSONResponse(
                status_code=425,
                content={
                    "code": "RESULT_NOT_READY",
                    "lifecycle_state": manifest["lifecycle_state"],
                },
            )
        if manifest["lifecycle_state"] != "succeeded":
            return JSONResponse(
                status_code=409,
                content={
                    "code": "RUN_HAS_NO_RESULT",
                    "lifecycle_state": manifest["lifecycle_state"],
                    "failure": manifest["failure"],
                },
            )
        return runtime.get_result(run_id)

    @app.get("/v1/research-runs/{run_id}/trace", response_model=None)
    def get_workflow_trace(
        run_id: Annotated[str, ApiPath(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")],
    ) -> dict[str, Any] | JSONResponse:
        try:
            manifest = runtime.get_manifest(run_id)
            if manifest["artifacts"]["workflow_trace_id"] is None:
                return JSONResponse(
                    status_code=425,
                    content={
                        "code": "TRACE_NOT_READY",
                        "lifecycle_state": manifest["lifecycle_state"],
                    },
                )
            return runtime.get_trace(run_id)
        except RunNotFoundError as exc:
            raise not_found(run_id) from exc
        except KeyError:
            return JSONResponse(
                status_code=425,
                content={"code": "TRACE_NOT_READY", "lifecycle_state": "running"},
            )

    @app.get("/v1/research-runs/{run_id}/facts")
    def get_research_facts(
        run_id: Annotated[str, ApiPath(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")],
    ) -> list[dict[str, Any]]:
        try:
            return runtime.get_facts(run_id)
        except RunNotFoundError as exc:
            raise not_found(run_id) from exc

    @app.get("/v1/research-runs/{run_id}/evidence")
    def get_research_evidence(
        run_id: Annotated[str, ApiPath(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")],
    ) -> list[dict[str, Any]]:
        try:
            return runtime.get_evidence(run_id)
        except RunNotFoundError as exc:
            raise not_found(run_id) from exc

    @app.get("/v1/research-runs/{run_id}/calculations")
    def get_research_calculations(
        run_id: Annotated[str, ApiPath(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")],
    ) -> list[dict[str, Any]]:
        try:
            return runtime.get_calculations(run_id)
        except RunNotFoundError as exc:
            raise not_found(run_id) from exc

    @app.post("/v1/research-runs/{run_id}/cancel")
    def cancel_research_run(
        run_id: Annotated[str, ApiPath(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")],
    ) -> dict[str, Any]:
        try:
            return runtime.cancel(run_id)
        except RunNotFoundError as exc:
            raise not_found(run_id) from exc

    @app.get("/v1/catalog", response_model=CatalogResponse)
    def get_catalog() -> CatalogResponse:
        return runtime.fixture_catalog.catalog()

    @app.get("/v1/evolution-experiments/{experiment_id}")
    def get_evolution_experiment(
        experiment_id: Annotated[str, ApiPath(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")],
    ) -> dict[str, Any]:
        try:
            return evolution_repository.get(experiment_id)
        except KeyError as exc:
            raise HTTPException(
                status_code=404,
                detail={"code": "EXPERIMENT_NOT_FOUND", "experiment_id": experiment_id},
            ) from exc

    @app.get("/v1/evolution-experiments/{experiment_id}/artifacts/{kind}")
    def get_evolution_artifact(
        experiment_id: Annotated[str, ApiPath(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")],
        kind: Annotated[str, ApiPath(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")],
    ) -> dict[str, Any]:
        try:
            return evolution_repository.get(experiment_id, kind)
        except KeyError as exc:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "EXPERIMENT_ARTIFACT_NOT_FOUND",
                    "experiment_id": experiment_id,
                    "kind": kind,
                },
            ) from exc

    return app
