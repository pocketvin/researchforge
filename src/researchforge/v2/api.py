"""Versioned V2 resources; live streams replay persisted events rather than owning work."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Annotated, Any, cast

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse

from researchforge.adapters.storage import IdempotencyConflictError, RunNotFoundError
from researchforge.policy import UnsupportedCapabilityError
from researchforge.v2.contracts import Json, ResearchRequest
from researchforge.v2.documents import render_page, search_objects
from researchforge.v2.reporting import sanitize_public_prose
from researchforge.v2.runtime import ResearchService
from researchforge.v2.storage import TERMINAL, safe_id


def _sanitize_text_fields(item: Any, fields: tuple[str, ...]) -> Json:
    if not isinstance(item, dict):
        return {}
    output: Json = dict(item)
    for field in fields:
        value = output.get(field)
        if isinstance(value, str):
            output[field] = sanitize_public_prose(value)
    return output


def _public_working_state(value: Any) -> Json:
    if not isinstance(value, dict):
        return {"objectives": [], "hypotheses": [], "open_questions": []}

    output: Json = dict(value)
    objectives = output.get("objectives", [])
    if isinstance(objectives, list):
        output["objectives"] = [
            _sanitize_text_fields(item, ("question", "conclusion", "remaining_uncertainty"))
            for item in objectives
            if isinstance(item, dict)
        ]
    else:
        output["objectives"] = []

    hypotheses = output.get("hypotheses", [])
    public_hypotheses: list[Json] = []
    if isinstance(hypotheses, list):
        for item in hypotheses:
            if not isinstance(item, dict):
                continue
            hypothesis = _sanitize_text_fields(item, ("statement", "would_change_conclusion"))
            unknowns = hypothesis.get("unknowns")
            if isinstance(unknowns, list):
                hypothesis["unknowns"] = [
                    sanitize_public_prose(str(unknown)) for unknown in unknowns
                ]
            public_hypotheses.append(hypothesis)
    output["hypotheses"] = public_hypotheses

    open_questions = output.get("open_questions", [])
    if isinstance(open_questions, list):
        output["open_questions"] = [
            _sanitize_text_fields(item, ("question", "explanation"))
            for item in open_questions
            if isinstance(item, dict)
        ]
    else:
        output["open_questions"] = []

    decision_summary = output.get("decision_summary")
    if isinstance(decision_summary, str):
        output["decision_summary"] = sanitize_public_prose(decision_summary)
    return output


def _public_dossier(value: Any) -> Json | None:
    if not isinstance(value, dict):
        return None
    output = _sanitize_text_fields(value, ("summary", "why_stop"))
    uncertainties = output.get("remaining_uncertainties")
    if isinstance(uncertainties, list):
        output["remaining_uncertainties"] = [
            sanitize_public_prose(str(item)) for item in uncertainties
        ]
    return output


def build_router(service: ResearchService) -> APIRouter:
    router = APIRouter(prefix="/v2", tags=["filing-research-v2"])
    repository = service.repository

    def manifest_for(run_id: str) -> Json:
        try:
            safe_id(run_id)
            return repository.get(run_id)
        except (RunNotFoundError, ValueError) as exc:
            raise HTTPException(404, detail={"code": "RUN_NOT_FOUND"}) from exc

    def linked(run_id: str, name: str, default: Any = None) -> Any:
        manifest = manifest_for(run_id)
        return repository.artifact(run_id, name) if name in manifest["artifacts"] else default

    def source_for(run_id: str, artifact_id: str) -> Json:
        try:
            safe_id(artifact_id)
        except ValueError as exc:
            raise HTTPException(404, detail={"code": "SOURCE_NOT_FOUND"}) from exc
        environment = linked(run_id, "environment", {})
        working = linked(run_id, "research_state", {})
        for namespace in (
            environment.get("objects", {}),
            environment.get("facts", {}),
            working.get("observed", {}),
            working.get("calculations", {}),
        ):
            if artifact_id in namespace:
                return cast(Json, namespace[artifact_id])
        raise HTTPException(404, detail={"code": "SOURCE_NOT_IN_RUN"})

    @router.get("/capabilities")
    def capabilities() -> Json:
        return {
            "version": "2.0.0-alpha.1",
            "agent_ready": service.model_factory is not None,
            "provider": service.configuration.get("provider"),
            "model": service.configuration.get("model"),
            "reflection_model": service.configuration.get("reflection_model"),
            "synthesis_model": service.configuration.get("synthesis_model"),
            "semantic_review_model": service.configuration.get("semantic_review_model"),
            "research_fallback_model": service.configuration.get("research_fallback_model"),
            "fallback_semantic_review_model": service.configuration.get(
                "fallback_semantic_review_model"
            ),
            "vision_model": service.configuration.get("vision_model"),
            "source_scope": "official_financial_filings_only",
            "real_agent_loop": True,
            "page_image_inspection": True,
            "live_events": True,
            "quality_benchmark_verified": False,
        }

    @router.post("/research-runs", status_code=202)
    def create_run(request: ResearchRequest, background_tasks: BackgroundTasks) -> Json:
        try:
            manifest, created = service.submit(request)
        except IdempotencyConflictError as exc:
            raise HTTPException(409, detail={"code": "IDEMPOTENCY_CONFLICT"}) from exc
        except UnsupportedCapabilityError as exc:
            raise HTTPException(
                422, detail={"code": "UNSUPPORTED_TASK", "message": str(exc)}
            ) from exc
        except ValueError as exc:
            raise HTTPException(503, detail={"code": "V2_AGENT_MODEL_UNAVAILABLE"}) from exc
        run_id = manifest["run_id"]
        if created:
            background_tasks.add_task(service.execute, run_id)
        return {
            "run_id": run_id,
            "lifecycle_state": manifest["lifecycle_state"],
            "created": created,
            "links": {
                kind: f"/v2/research-runs/{run_id}/{kind}" for kind in ("result", "events", "trace")
            },
        }

    @router.get("/research-runs")
    def history(limit: Annotated[int, Query(ge=1, le=100)] = 30) -> list[Json]:
        return repository.list_runs(limit=limit)

    @router.get("/research-runs/{run_id}")
    def status(run_id: str) -> Json:
        return manifest_for(run_id)

    @router.get("/research-runs/{run_id}/result")
    def result(run_id: str) -> Json:
        manifest = manifest_for(run_id)
        if manifest["lifecycle_state"] not in TERMINAL:
            raise HTTPException(425, detail={"code": "RESULT_NOT_READY"})
        if manifest["lifecycle_state"] != "succeeded":
            raise HTTPException(
                409, detail={"code": "RUN_HAS_NO_RESULT", "failure": manifest["failure"]}
            )
        return cast(Json, repository.artifact(run_id, "result"))

    @router.get("/research-runs/{run_id}/trace")
    def trace(run_id: str, after: Annotated[int, Query(ge=0)] = 0) -> Json:
        manifest = manifest_for(run_id)
        return {
            "schema_version": "2.0.0",
            "run_id": run_id,
            "terminal_state": manifest["lifecycle_state"],
            "events": repository.events(run_id, after, 2000),
        }

    @router.get("/research-runs/{run_id}/events")
    async def events(
        run_id: str,
        request: Request,
        after: Annotated[int, Query(ge=0)] = 0,
    ) -> StreamingResponse:
        import asyncio

        try:
            service.repository.get(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND"}) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"code": "INVALID_RUN_ID"}) from exc
        last = request.headers.get("last-event-id")
        if last:
            try:
                after = max(after, int(last))
            except ValueError as exc:
                raise HTTPException(
                    status_code=400, detail={"code": "INVALID_EVENT_CURSOR"}
                ) from exc
            if after < 0:
                raise HTTPException(status_code=400, detail={"code": "INVALID_EVENT_CURSOR"})

        async def generate() -> AsyncIterator[str]:
            cursor = after
            last_heartbeat = time.monotonic()
            while not await request.is_disconnected():
                batch = await asyncio.to_thread(service.repository.events, run_id, after=cursor)
                for event in batch:
                    cursor = max(cursor, int(event["sequence"]))
                    data = json.dumps(event, ensure_ascii=False, allow_nan=False)
                    yield f"id: {cursor}\nevent: research\ndata: {data}\n\n"
                current = await asyncio.to_thread(service.repository.get, run_id)
                if current["lifecycle_state"] in {
                    "succeeded",
                    "failed",
                    "cancelled",
                    "timed_out",
                    "insufficient_data",
                }:
                    # Drain events persisted between the preceding read and terminal state.
                    tail = await asyncio.to_thread(service.repository.events, run_id, after=cursor)
                    for event in tail:
                        cursor = max(cursor, int(event["sequence"]))
                        data = json.dumps(event, ensure_ascii=False, allow_nan=False)
                        yield f"id: {cursor}\nevent: research\ndata: {data}\n\n"
                    yield (
                        "event: terminal\ndata: "
                        + json.dumps({"lifecycle_state": current["lifecycle_state"]})
                        + "\n\n"
                    )
                    return
                if time.monotonic() - last_heartbeat >= 10:
                    yield ": heartbeat\n\n"
                    last_heartbeat = time.monotonic()
                await asyncio.sleep(0.35)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
            },
        )

    @router.post("/research-runs/{run_id}/cancel")
    def cancel(run_id: str) -> Json:
        manifest_for(run_id)
        return service.cancel(run_id)

    @router.get("/research-runs/{run_id}/facts")
    def facts(run_id: str) -> list[Json]:
        environment = linked(run_id, "environment", {})
        return list(environment.get("facts", {}).values())

    @router.get("/research-runs/{run_id}/calculations")
    def calculations(run_id: str) -> list[Json]:
        state = linked(run_id, "research_state", {})
        return list(state.get("calculations", {}).values())

    @router.get("/research-runs/{run_id}/search")
    def search(
        run_id: str,
        query: Annotated[str, Query(min_length=1, max_length=500)],
        kind: Annotated[
            str, Query(pattern="^(all|page|section|table|figure|footnote|evidence|document)$")
        ] = "all",
        limit: Annotated[int, Query(ge=1, le=20)] = 8,
    ) -> Json:
        environment = linked(run_id, "environment", {})
        results = search_objects(environment.get("objects", {}), query, kind=kind)[:limit]
        return {
            "run_id": run_id,
            "query": query,
            "kind": kind,
            "count": len(results),
            "results": results,
        }

    @router.get("/research-runs/{run_id}/workspace")
    def workspace(run_id: str) -> Json:
        manifest = manifest_for(run_id)
        environment = linked(run_id, "environment", {})
        state = linked(run_id, "research_state", {})
        objects = environment.get("objects", {})
        return {
            "run_id": run_id,
            "lifecycle_state": manifest["lifecycle_state"],
            "documents": list(environment.get("documents", {}).values()),
            "catalog": [
                {
                    key: obj.get(key)
                    for key in (
                        "artifact_id",
                        "kind",
                        "document_id",
                        "title",
                        "label",
                        "page_id",
                        "page_number",
                        "row_count",
                        "column_count",
                        "extraction_status",
                    )
                }
                for obj in objects.values()
                if obj["kind"] in {"page", "section", "table", "figure", "footnote"}
            ],
            "facts": list(environment.get("facts", {}).values()),
            "calculations": list(state.get("calculations", {}).values()),
            "working": _public_working_state(state.get("working")),
            "stop_decision": _public_dossier(state.get("dossier")),
            "gaps": [
                sanitize_public_prose(item) if isinstance(item, str) else item
                for item in environment.get("gaps", [])
            ],
            "observed_evidence": list(state.get("observed", {}).values()),
        }

    @router.get("/research-runs/{run_id}/sources/{artifact_id}")
    def source(
        run_id: str,
        artifact_id: str,
        offset: Annotated[int, Query(ge=0)] = 0,
        max_chars: Annotated[int, Query(ge=100, le=24000)] = 18000,
    ) -> Json:
        obj = source_for(run_id, artifact_id)
        text = str(obj.get("text", ""))
        output = {
            **obj,
            "text": text[offset : offset + max_chars],
            "text_length": len(text),
            "next_offset": offset + max_chars if offset + max_chars < len(text) else None,
        }
        return output

    @router.get("/research-runs/{run_id}/page-images/{page_id}")
    def page_image(run_id: str, page_id: str) -> FileResponse:
        page = source_for(run_id, page_id)
        if page.get("kind") != "page" or not page.get("visual_inspection_available"):
            raise HTTPException(404, detail={"code": "PAGE_IMAGE_UNAVAILABLE"})
        blob_id = render_page(repository, page)
        return FileResponse(
            repository.blob_path(blob_id),
            media_type="image/png",
            headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"},
        )

    @router.get("/research-runs/{run_id}/documents/{document_id}/original")
    def original(run_id: str, document_id: str) -> FileResponse:
        environment = linked(run_id, "environment", {})
        document = environment.get("documents", {}).get(document_id)
        if document is None:
            raise HTTPException(404, detail={"code": "DOCUMENT_NOT_IN_RUN"})
        extension = document["raw_blob_id"].rsplit(".", 1)[1]
        # Serve raw HTML only as an attachment, never execute untrusted filing markup on our origin.
        return FileResponse(
            repository.blob_path(document["raw_blob_id"]),
            media_type=document["mime_type"],
            filename=f"{document_id}.{extension}",
            headers={"X-Content-Type-Options": "nosniff"},
        )

    return router
