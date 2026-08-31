"""Create the eight V1.4 logical record tables."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("case_id", sa.String(length=255), nullable=False),
        sa.Column("split", sa.String(length=32), nullable=True),
        sa.Column("group_key", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("case_id"),
    )
    op.create_index("ix_cases_split", "cases", ["split"])
    op.create_index("ix_cases_group_key", "cases", ["group_key"])

    op.create_table(
        "skill_versions",
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("version"),
        sa.UniqueConstraint("content_hash"),
    )
    op.create_index("ix_skill_versions_status", "skill_versions", ["status"])

    op.create_table(
        "source_documents",
        sa.Column("document_id", sa.String(length=255), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("document_id"),
    )
    op.create_index("ix_source_documents_content_hash", "source_documents", ["content_hash"])

    op.create_table(
        "runs",
        sa.Column("run_id", sa.String(length=255), nullable=False),
        sa.Column("run_kind", sa.String(length=64), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("case_id", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.case_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("run_id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_runs_case_id", "runs", ["case_id"])
    op.create_index("ix_runs_lifecycle_state", "runs", ["lifecycle_state"])
    op.create_index("ix_runs_run_kind", "runs", ["run_kind"])

    op.create_table(
        "evolution_runs",
        sa.Column("experiment_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("seed_skill_version", sa.String(length=64), nullable=False),
        sa.Column("candidate_skill_version", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["seed_skill_version"], ["skill_versions.version"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("experiment_id"),
    )
    op.create_index("ix_evolution_runs_status", "evolution_runs", ["status"])

    op.create_table(
        "evidence_chunks",
        sa.Column("evidence_id", sa.String(length=255), nullable=False),
        sa.Column("document_id", sa.String(length=255), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("section", sa.String(length=512), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"], ["source_documents.document_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("evidence_id"),
    )
    op.create_index("ix_evidence_chunks_content_hash", "evidence_chunks", ["content_hash"])
    op.create_index("ix_evidence_chunks_document_id", "evidence_chunks", ["document_id"])

    op.create_table(
        "evaluations",
        sa.Column("evaluation_id", sa.String(length=255), nullable=False),
        sa.Column("run_id", sa.String(length=255), nullable=False),
        sa.Column("verifier_version", sa.String(length=64), nullable=False),
        sa.Column("task_score", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("evaluation_id"),
    )
    op.create_index("ix_evaluations_run_id", "evaluations", ["run_id"])

    op.create_table(
        "run_artifacts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("digest", sa.String(length=64), nullable=False),
        sa.Column("artifact_uri", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "kind", "digest", name="uq_run_artifact_identity"),
    )
    op.create_index("ix_run_artifacts_run_kind", "run_artifacts", ["run_id", "kind"])


def downgrade() -> None:
    op.drop_index("ix_run_artifacts_run_kind", table_name="run_artifacts")
    op.drop_table("run_artifacts")
    op.drop_index("ix_evaluations_run_id", table_name="evaluations")
    op.drop_table("evaluations")
    op.drop_index("ix_evidence_chunks_document_id", table_name="evidence_chunks")
    op.drop_index("ix_evidence_chunks_content_hash", table_name="evidence_chunks")
    op.drop_table("evidence_chunks")
    op.drop_index("ix_evolution_runs_status", table_name="evolution_runs")
    op.drop_table("evolution_runs")
    op.drop_index("ix_runs_run_kind", table_name="runs")
    op.drop_index("ix_runs_lifecycle_state", table_name="runs")
    op.drop_index("ix_runs_case_id", table_name="runs")
    op.drop_table("runs")
    op.drop_index("ix_source_documents_content_hash", table_name="source_documents")
    op.drop_table("source_documents")
    op.drop_index("ix_skill_versions_status", table_name="skill_versions")
    op.drop_table("skill_versions")
    op.drop_index("ix_cases_group_key", table_name="cases")
    op.drop_index("ix_cases_split", table_name="cases")
    op.drop_table("cases")
