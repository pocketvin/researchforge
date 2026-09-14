"""ResearchForge HTTP application: one canonical V2 filing-research runtime."""

from __future__ import annotations

import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from researchforge.config import load_runtime_settings
from researchforge.v2.api import build_router
from researchforge.v2.runtime import ResearchService, build_service

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
API_VERSION = "2.0.0-alpha.1"


def build_default_service(artifact_root: Path | None = None) -> ResearchService:
    """Build the sole product research runtime over the canonical V2 artifact store."""
    settings = load_runtime_settings(PROJECT_ROOT)
    configured_root = (
        artifact_root or settings.researchforge_artifact_root or (PROJECT_ROOT / "artifacts")
    )
    return build_service(PROJECT_ROOT, configured_root)


def create_app(
    service: ResearchService | None = None,
    *,
    artifact_root: Path | None = None,
) -> FastAPI:
    """Create the HTTP app; browser, n8n and MCP all use this same V2 service."""
    runtime = service or build_default_service(artifact_root)
    settings = load_runtime_settings(PROJECT_ROOT)

    def recover_interrupted() -> None:
        try:
            runtime.recover()
        except Exception:
            LOGGER.exception("V2 background recovery failed safely")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        recovery_thread = threading.Thread(
            target=recover_interrupted,
            name="researchforge-v2-recovery",
            daemon=True,
        )
        recovery_thread.start()
        yield

    app = FastAPI(
        title="ResearchForge API",
        version=API_VERSION,
        docs_url="/docs" if settings.researchforge_api_docs_enabled else None,
        redoc_url="/redoc" if settings.researchforge_api_docs_enabled else None,
        openapi_url="/openapi.json" if settings.researchforge_api_docs_enabled else None,
        lifespan=lifespan,
        description="Evidence-first filing research over one canonical V2 runtime.",
    )
    app.include_router(build_router(runtime))
    app.state.research_service = runtime

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "version": API_VERSION, "runtime": "v2"}

    return app
