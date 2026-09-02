"""Alembic reversibility and hybrid artifact-index tests."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session

from researchforge.api.app import DEFAULT_FIXTURE_ROOT, DEFAULT_SKILL_MANIFEST, PROJECT_ROOT
from researchforge.application.service import ResearchRunService
from researchforge.persistence.models import (
    EvidenceChunkRecord,
    RunArtifactRecord,
    SourceDocumentRecord,
)
from tests.runtime_helpers import catl_request

EXPECTED_TABLES = {
    "cases",
    "runs",
    "skill_versions",
    "evolution_runs",
    "evaluations",
    "source_documents",
    "evidence_chunks",
    "run_artifacts",
}


def _config(database_url: str) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_migration_is_reversible_up_down_up(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    config = _config(database_url)
    engine = create_engine(database_url)

    command.upgrade(config, "head")
    assert set(inspect(engine).get_table_names()) >= EXPECTED_TABLES

    command.downgrade(config, "base")
    assert not (EXPECTED_TABLES & set(inspect(engine).get_table_names()))

    command.upgrade(config, "head")
    assert set(inspect(engine).get_table_names()) >= EXPECTED_TABLES
    engine.dispose()


def test_service_mirrors_run_and_hash_artifact_references(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    command.upgrade(_config(database_url), "head")
    artifact_root = tmp_path / "artifacts"
    service = ResearchRunService.build(
        artifact_root,
        DEFAULT_FIXTURE_ROOT,
        DEFAULT_SKILL_MANIFEST,
        database_url=database_url,
    )

    submission = service.submit(catl_request())
    manifest = service.execute(submission.run_id)

    assert manifest["lifecycle_state"] == "succeeded"
    assert service.database_index is not None
    mirrored = service.database_index.run_payload(submission.run_id)
    assert mirrored is not None
    assert mirrored["lifecycle_state"] == "succeeded"
    with Session(service.database_index.engine) as session:
        artifact_count = session.scalar(
            select(func.count())
            .select_from(RunArtifactRecord)
            .where(RunArtifactRecord.run_id == submission.run_id)
        )
        source_count = session.scalar(select(func.count()).select_from(SourceDocumentRecord))
        evidence_count = session.scalar(select(func.count()).select_from(EvidenceChunkRecord))
    assert artifact_count is not None and artifact_count >= 8
    assert source_count == evidence_count == 8
