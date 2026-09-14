"""Typed public-development benchmark suites and repeatable execution metadata."""

from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from researchforge.adapters.storage import payload_sha256


class SuiteContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BenchmarkSuiteCase(SuiteContract):
    financebench_id: str = Field(min_length=1)
    stratum: str = Field(min_length=1)
    company: str = Field(min_length=1)
    doc_name: str = Field(min_length=1)
    question_type: str = Field(min_length=1)
    question_reasoning: str | None = None
    question: str = Field(min_length=1)


class BenchmarkSuiteManifest(SuiteContract):
    schema_version: Literal["2.0.0"] = "2.0.0"
    suite_id: str = Field(min_length=1)
    benchmark_name: Literal["FinanceBench open-source"] = "FinanceBench open-source"
    benchmark_commit: str = Field(min_length=40, max_length=40)
    benchmark_license: str = Field(min_length=1)
    split: Literal["development"] = "development"
    selector_version: str = Field(min_length=1)
    seed: int
    source_questions_sha256: str = Field(min_length=64, max_length=64)
    source_question_count: int = Field(gt=0)
    scope: str = Field(min_length=1)
    gold_fields_used_in_selection: Literal[False] = False
    anchors: list[str]
    cases: list[BenchmarkSuiteCase] = Field(min_length=1)
    suite_hash: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_suite(self) -> BenchmarkSuiteManifest:
        identifiers = [case.financebench_id for case in self.cases]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("benchmark suite case IDs must be unique")
        if not set(self.anchors) <= set(identifiers):
            raise ValueError("every anchor must be present in suite cases")
        expected = payload_sha256(self.model_dump(mode="json", exclude={"suite_hash"}))
        if self.suite_hash != expected:
            raise ValueError("benchmark suite hash does not match canonical manifest payload")
        return self


class SuiteCaseExecution(SuiteContract):
    financebench_id: str
    stratum: str
    company: str
    status: Literal["pending", "succeeded", "failed", "skipped"] = "pending"
    run_id: str | None = None
    lifecycle_state: str | None = None
    assessment_path: str | None = None
    estimated_cost_usd: float | None = None
    provider_calls: int | None = None
    total_tokens: int | None = None
    agent_turns: int | None = None
    error_type: str | None = None
    error_message: str | None = None


class BenchmarkSuiteExecution(SuiteContract):
    schema_version: Literal["2.0.0"] = "2.0.0"
    execution_id: str
    suite_id: str
    suite_hash: str
    implementation_hash: str
    git_head: str | None = None
    git_dirty: bool
    started_at: datetime
    finished_at: datetime | None = None
    stopped_reason: (
        Literal[
            "completed",
            "max_new_runs",
            "estimated_cost_cap",
            "case_failure",
            "operator_stop",
        ]
        | None
    ) = None
    new_runs_started: int = 0
    estimated_cost_usd: float = 0.0
    max_new_runs: int = Field(ge=0)
    max_estimated_cost_usd: float | None = Field(default=None, ge=0)
    target_case_ids: list[str] = Field(min_length=1)
    cases: list[SuiteCaseExecution]

    @model_validator(mode="after")
    def unique_case_ids(self) -> BenchmarkSuiteExecution:
        identifiers = [case.financebench_id for case in self.cases]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("suite execution case IDs must be unique")
        if identifiers != self.target_case_ids:
            raise ValueError("suite execution cases must exactly follow target_case_ids order")
        return self


def finalize_suite(payload: dict[str, object]) -> BenchmarkSuiteManifest:
    suite_hash = payload_sha256(payload)
    return BenchmarkSuiteManifest.model_validate({**payload, "suite_hash": suite_hash})


def implementation_fingerprint(project_root: Path) -> str:
    """Hash backend behavior inputs so dirty-tree benchmark runs remain comparable."""
    project_root = project_root.resolve()
    paths = sorted((project_root / "src/researchforge/v2").rglob("*.py"))
    paths.extend(
        path
        for path in (
            project_root / "src/researchforge/config.py",
            project_root / "src/researchforge/api/app.py",
            project_root / "scripts/run_v2_financebench.py",
            project_root / "pyproject.toml",
            project_root / "uv.lock",
        )
        if path.is_file()
    )
    digest = hashlib.sha256()
    for path in sorted(set(paths)):
        relative = path.relative_to(project_root).as_posix().encode()
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def execution_cost(execution: BenchmarkSuiteExecution) -> Decimal:
    return sum(
        (
            Decimal(str(case.estimated_cost_usd))
            for case in execution.cases
            if case.estimated_cost_usd
        ),
        start=Decimal("0"),
    )
