"""Asynchronous research-run HTTP resources."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any, cast

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi import Path as ApiPath
from fastapi.responses import JSONResponse

from researchforge.adapters.evolution_storage import EvolutionArtifactRepository
from researchforge.adapters.openai_responses import (
    OpenAIResponsesConclusionGenerator,
    ResponsesResource,
)
from researchforge.adapters.storage import (
    IdempotencyConflictError,
    RunNotFoundError,
)
from researchforge.application.budget import BudgetLedger
from researchforge.application.contracts import (
    CatalogResponse,
    ResearchRunRequest,
    RunSubmission,
)
from researchforge.application.service import ResearchRunService, UnsupportedCapabilityError
from researchforge.config import load_runtime_settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURE_ROOT = PROJECT_ROOT / "data" / "fixtures" / "g0"
DEFAULT_PRODUCT_ROOT = PROJECT_ROOT / "data" / "product" / "packages"
DEFAULT_SKILL_MANIFEST = (
    PROJECT_ROOT / "skills" / "fundamental-research" / "versions" / "1.0.0" / "skill-version.json"
)
PRODUCT_REASONING_INSTRUCTIONS = """

V1.5 product-only response contract:
- Directly answer research_question in the first sentence with a bounded conclusion.
- Treat verified_fact_ids, source_document_ids, period_label, currency and counter_evidence as
  supplied; never claim that these identifiers, the reporting period or the currency are missing.
- A limitation must follow only from an explicit unavailable field or counter_evidence summary.
- Do not perform new arithmetic. Use cash_conversion_display, gross_margin and other precomputed
  values exactly as provided.
""".strip()


def build_default_service(artifact_root: Path | None = None) -> ResearchRunService:
    """Build the product runtime without any implicit fixture fallback."""
    settings = load_runtime_settings(PROJECT_ROOT)
    configured_root = (
        artifact_root or settings.researchforge_artifact_root or (PROJECT_ROOT / "artifacts")
    )
    data_namespace = settings.researchforge_data_namespace
    default_data_root = (
        DEFAULT_PRODUCT_ROOT if data_namespace == "product" else DEFAULT_FIXTURE_ROOT
    )
    data_root = settings.researchforge_data_root or default_data_root

    conclusion_generator: OpenAIResponsesConclusionGenerator | None = None
    model_config: dict[str, Any] | None = None
    prompt_hashes: dict[str, str] | None = None
    key = settings.openai_api_key
    openai_ready = key is not None and settings.researchforge_rotated_key_confirmed
    if settings.researchforge_reasoning_mode == "openai" and not openai_ready:
        raise RuntimeError("OpenAI reasoning mode requires a confirmed rotated API key")
    if settings.researchforge_reasoning_mode == "openai" or (
        settings.researchforge_reasoning_mode == "auto" and openai_ready
    ):
        from openai import OpenAI

        client = OpenAI(
            api_key=key.get_secret_value() if key is not None else None,
            timeout=120.0,
            max_retries=0,
        )
        conclusion_generator = OpenAIResponsesConclusionGenerator(
            cast(ResponsesResource, client.responses),
            BudgetLedger(
                cap=Decimal(settings.researchforge_budget_usd),
                state_path=configured_root / "budget" / "project-openai.json",
            ),
            model=settings.researchforge_model,
            max_input_tokens=4000,
            max_output_tokens=1200,
            skill_content=(
                (
                    PROJECT_ROOT
                    / "skills"
                    / "fundamental-research"
                    / "versions"
                    / "1.0.0"
                    / "SKILL.md"
                ).read_text(encoding="utf-8")
                + PRODUCT_REASONING_INSTRUCTIONS
            ),
            reasoning_effort=settings.researchforge_reasoning_effort,
        )
        model_config = {
            "provider": "openai",
            "model_id": settings.researchforge_model,
            "model_snapshot": None,
            "temperature": None,
            "seed": None,
            "reasoning_effort": settings.researchforge_reasoning_effort,
            "max_output_tokens": 1200,
            "tool_choice_policy": "controlled",
            "store": False,
            "built_in_tools": [],
        }
        prompt_hashes = conclusion_generator.prompt_hashes
    return ResearchRunService.build(
        configured_root,
        data_root,
        DEFAULT_SKILL_MANIFEST,
        database_url=(
            settings.researchforge_database_url if settings.researchforge_database_enabled else None
        ),
        data_namespace=data_namespace,
        conclusion_generator=conclusion_generator,
        model_config=model_config,
        prompt_hashes=prompt_hashes,
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
        version="1.5.0",
        description="Evidence-grounded A-share fundamental research workspace resources.",
    )

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "version": "1.5.0"}

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
