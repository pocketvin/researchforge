"""Shared runtime fixtures and V1.4 schema assertions."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from researchforge.api.app import DEFAULT_FIXTURE_ROOT, DEFAULT_SKILL_MANIFEST
from researchforge.application.contracts import ResearchRunRequest
from researchforge.application.service import ResearchRunService
from scripts.validate_contracts import (
    SCHEMA_DIR,
    V17_SCHEMA_DIR,
    V173_SCHEMA_DIR,
    load_json,
    validate_instance,
)


def build_service(artifact_root: Path) -> ResearchRunService:
    return ResearchRunService.build(
        artifact_root,
        DEFAULT_FIXTURE_ROOT,
        DEFAULT_SKILL_MANIFEST,
        data_namespace="fixture",
    )


def catl_request(
    *,
    key: str = "test-catl-2024h1",
    research_time: str = "2024-08-01T00:00:00+08:00",
    question: str = "2024年上半年利润是否转化为经营现金流?",
) -> ResearchRunRequest:
    return ResearchRunRequest(
        task_type="filing_analysis",
        research_question=question,
        company_ids=["cn_300750"],
        requested_period_labels=["2024H1"],
        research_time=datetime.fromisoformat(research_time),
        idempotency_key=key,
    )


def assert_v14_schema(payload: dict[str, Any], schema_name: str) -> None:
    schemas = {path.resolve(): load_json(path) for path in SCHEMA_DIR.glob("*.json")}
    schema_path = (SCHEMA_DIR / schema_name).resolve()
    validate_instance(payload, schemas[schema_path], schema_path, schemas)


def assert_v17_schema(payload: dict[str, Any], schema_name: str) -> None:
    schema_paths = [*SCHEMA_DIR.glob("*.json"), *V17_SCHEMA_DIR.glob("*.json")]
    schemas = {path.resolve(): load_json(path) for path in schema_paths}
    schema_path = (V17_SCHEMA_DIR / schema_name).resolve()
    validate_instance(payload, schemas[schema_path], schema_path, schemas)


def assert_v173_schema(payload: dict[str, Any], schema_name: str) -> None:
    schema_paths = [
        *SCHEMA_DIR.glob("*.json"),
        *V17_SCHEMA_DIR.glob("*.json"),
        *V173_SCHEMA_DIR.glob("*.json"),
    ]
    schemas = {path.resolve(): load_json(path) for path in schema_paths}
    schema_path = (V173_SCHEMA_DIR / schema_name).resolve()
    validate_instance(payload, schemas[schema_path], schema_path, schemas)
