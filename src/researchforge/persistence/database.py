"""SQLAlchemy index that mirrors logical state and immutable artifact references."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from researchforge.persistence.models import (
    Base,
    EvaluationRecord,
    EvidenceChunkRecord,
    RunArtifactRecord,
    RunRecord,
    SkillVersionRecord,
    SourceDocumentRecord,
)


class DatabaseIndex:
    """Mirror queryable logical records while JSON blobs stay immutable files."""

    def __init__(self, database_url: str, *, artifact_root: Path) -> None:
        self.engine: Engine = create_engine(database_url, pool_pre_ping=True)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        self.artifact_root = artifact_root.resolve()

    def create_schema_for_tests(self) -> None:
        Base.metadata.create_all(self.engine)

    def close(self) -> None:
        self.engine.dispose()

    @staticmethod
    def _time(value: str | None) -> datetime:
        return datetime.fromisoformat(value) if value is not None else datetime.now(UTC)

    def mirror_skill(self, payload: dict[str, Any]) -> None:
        with self.sessions.begin() as session:
            session.merge(
                SkillVersionRecord(
                    version=str(payload["version"]),
                    content_hash=str(payload["content_hash"]),
                    status=str(payload["status"]),
                    payload=payload,
                    created_at=self._time(payload.get("created_at")),
                )
            )

    def mirror_sources(self, sources: tuple[dict[str, Any], ...]) -> None:
        with self.sessions.begin() as session:
            for source in sources:
                session.merge(
                    SourceDocumentRecord(
                        document_id=str(source["document_id"]),
                        content_hash=str(source["content_hash"]),
                        source_uri=str(source["source_uri"]),
                        published_at=self._time(source["published_at"]),
                        payload=source,
                    )
                )

    def mirror_evidence(self, evidence_chunks: tuple[dict[str, Any], ...]) -> None:
        with self.sessions.begin() as session:
            for chunk in evidence_chunks:
                session.merge(
                    EvidenceChunkRecord(
                        evidence_id=str(chunk["chunk_id"]),
                        document_id=str(chunk["document_id"]),
                        content_hash=str(chunk["text_hash"]),
                        section=chunk.get("section"),
                        payload=chunk,
                    )
                )

    def mirror_run(
        self,
        manifest: dict[str, Any],
        artifact_references: dict[str, str],
    ) -> None:
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            session.merge(
                RunRecord(
                    run_id=str(manifest["run_id"]),
                    run_kind=str(manifest["run_kind"]),
                    lifecycle_state=str(manifest["lifecycle_state"]),
                    idempotency_key=str(manifest["idempotency_key"]),
                    case_id=manifest["case_id"],
                    payload=manifest,
                    created_at=self._time(manifest["created_at"]),
                    updated_at=now,
                )
            )
            session.execute(
                delete(RunArtifactRecord).where(RunArtifactRecord.run_id == str(manifest["run_id"]))
            )
            for kind, digest in artifact_references.items():
                session.add(
                    RunArtifactRecord(
                        run_id=str(manifest["run_id"]),
                        kind=kind,
                        digest=digest,
                        artifact_uri=str(
                            self.artifact_root
                            / "objects"
                            / "sha256"
                            / digest[:2]
                            / f"{digest}.json"
                        ),
                        created_at=now,
                    )
                )

    def mirror_evaluation(self, evaluation: dict[str, Any]) -> None:
        with self.sessions.begin() as session:
            session.merge(
                EvaluationRecord(
                    evaluation_id=str(evaluation["evaluation_id"]),
                    run_id=str(evaluation["run_id"]),
                    verifier_version=str(evaluation["verifier_version"]),
                    task_score=str(evaluation["metrics"]["task_score"]),
                    payload=evaluation,
                    created_at=self._time(evaluation["created_at"]),
                )
            )

    def run_payload(self, run_id: str) -> dict[str, Any] | None:
        with Session(self.engine) as session:
            record = session.scalar(select(RunRecord).where(RunRecord.run_id == run_id))
            return None if record is None else record.payload
