"""Freeze development exposure before a V2 held-out acceptance seal is created.

Held-out integrity cannot depend on a hand-maintained issuer denylist alone. This module builds a
deterministic snapshot of structured development inputs that have already been visible to
ResearchForge: the tracked issuer exclusions, the public development suite, the locally cached
FinanceBench public source when present, and persisted V2 product/development Runs.

The snapshot stores question hashes rather than question text. It is intended to live next to the
private held-out bundle and be content-bound by the public seal.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from researchforge.adapters.storage import payload_sha256
from researchforge.v2.benchmarks.heldout import (
    DevelopmentIssuerExclusionManifest,
    HeldOutBundleManifest,
    HeldOutRuntimeCase,
    development_question_hash,
)
from researchforge.v2.benchmarks.suite import BenchmarkSuiteManifest
from researchforge.v2.storage import ResearchRepository


class DevelopmentExposureSnapshot(BaseModel):
    """Content-stable development exposure set frozen before held-out execution."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["2.0.0"] = "2.0.0"
    snapshot_id: str = Field(min_length=1)
    source_hashes: dict[str, str]
    company_aliases: list[str]
    question_hashes: list[str]
    case_ids: list[str]
    document_hashes: list[str]

    @model_validator(mode="after")
    def normalized_and_unique(self) -> DevelopmentExposureSnapshot:
        expected_aliases = sorted(
            set(self.company_aliases), key=lambda value: (value.casefold(), value)
        )
        if self.company_aliases != expected_aliases:
            raise ValueError("development exposure company aliases must be sorted and unique")
        if self.question_hashes != sorted(set(self.question_hashes)):
            raise ValueError("development exposure question hashes must be sorted and unique")
        if self.case_ids != sorted(set(self.case_ids)):
            raise ValueError("development exposure case IDs must be sorted and unique")
        if self.document_hashes != sorted(set(self.document_hashes)):
            raise ValueError("development exposure document hashes must be sorted and unique")
        if any(
            len(digest) != 64 or set(digest) - set("0123456789abcdef")
            for digest in self.document_hashes
        ):
            raise ValueError("development exposure document hashes must be SHA-256 digests")
        if any(
            len(digest) != 64 or set(digest) - set("0123456789abcdef")
            for digest in self.source_hashes.values()
        ):
            raise ValueError("development exposure source hashes must be SHA-256 digests")
        return self

    def content_hash(self) -> str:
        return payload_sha256(self.model_dump(mode="json"))


normalized_question_hash = development_question_hash


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _add_suite_exposure(
    suite: BenchmarkSuiteManifest,
    companies: set[str],
    questions: set[str],
    case_ids: set[str],
) -> None:
    for case in suite.cases:
        companies.add(case.company)
        case_ids.add(case.financebench_id)
        question = getattr(case, "question", None)
        if isinstance(question, str) and question.strip():
            questions.add(normalized_question_hash(question))


def _add_financebench_public_source(
    project_root: Path,
    companies: set[str],
    questions: set[str],
    case_ids: set[str],
    document_hashes: set[str],
    source_hashes: dict[str, str],
) -> None:
    path = (
        project_root / "artifacts/v2-benchmarks/financebench/source/financebench_open_source.jsonl"
    )
    if not path.is_file():
        return
    source_hashes["financebench-public-source"] = _sha256_file(path)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        company = row.get("company")
        question = row.get("question")
        case_id = row.get("financebench_id")
        if isinstance(company, str) and company.strip():
            companies.add(company)
        if isinstance(question, str) and question.strip():
            questions.add(normalized_question_hash(question))
        if isinstance(case_id, str) and case_id.strip():
            case_ids.add(case_id)
    pdf_root = path.parent / "pdfs"
    if pdf_root.is_dir():
        for pdf in sorted(pdf_root.glob("*.pdf")):
            document_hashes.add(_sha256_file(pdf))


def _add_v2_run_exposure(
    project_root: Path,
    companies: set[str],
    questions: set[str],
    document_hashes: set[str],
    source_hashes: dict[str, str],
) -> None:
    root = project_root / "artifacts/v2"
    runs_dir = root / "runs"
    if not runs_dir.is_dir():
        return
    repository = ResearchRepository(root)
    exposed_requests: list[dict[str, str]] = []
    for pointer in sorted(runs_dir.glob("run_*.json")):
        try:
            manifest = repository.get(pointer.stem)
        except (FileNotFoundError, KeyError, ValueError):
            continue
        request = manifest.get("request")
        if not isinstance(request, dict):
            continue
        company = request.get("company_query")
        question = request.get("research_question")
        if isinstance(company, str) and company.strip():
            companies.add(company)
        if isinstance(question, str) and question.strip():
            questions.add(normalized_question_hash(question))
        exposed_requests.append(
            {
                "company_query": str(company or ""),
                "research_question_hash": (
                    normalized_question_hash(question)
                    if isinstance(question, str) and question.strip()
                    else ""
                ),
            }
        )
        artifacts = manifest.get("artifacts")
        if isinstance(artifacts, dict) and "environment" in artifacts:
            try:
                environment = repository.artifact(pointer.stem, "environment")
            except (FileNotFoundError, KeyError, ValueError):
                environment = None
            if isinstance(environment, dict):
                documents = environment.get("documents")
                values = documents.values() if isinstance(documents, dict) else []
                for document in values:
                    if isinstance(document, dict):
                        content_hash = document.get("content_hash")
                        if isinstance(content_hash, str) and len(content_hash) == 64:
                            document_hashes.add(content_hash)
    if exposed_requests:
        source_hashes["v2-run-requests"] = payload_sha256(exposed_requests)


def _add_retired_heldout_bundle_exposure(
    bundle_root: Path,
    *,
    index: int,
    companies: set[str],
    questions: set[str],
    case_ids: set[str],
    document_hashes: set[str],
    source_hashes: dict[str, str],
) -> None:
    """Promote a result-exposed private held-out suite into development exposure.

    Only hashes are added to the snapshot for questions/documents, while issuer aliases are needed
    by candidate selection to prevent the same company from being sampled again. Source bytes are
    re-hashed so a stale/tampered retired bundle cannot silently poison the exclusion boundary.
    """

    bundle_root = bundle_root.resolve()
    manifest_path = bundle_root / "bundle-manifest.json"
    manifest = HeldOutBundleManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    runtime_path = bundle_root / manifest.runtime_cases_file
    runtimes = [
        HeldOutRuntimeCase.model_validate_json(line)
        for line in runtime_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    runtime_by_id = {case.case_id: case for case in runtimes}
    if len(runtime_by_id) != len(runtimes) or set(runtime_by_id) != set(manifest.case_ids):
        raise ValueError("retired held-out runtime cases do not match bundle manifest")

    verified_document_hashes: set[str] = set()
    for case_id in manifest.case_ids:
        case = runtime_by_id[case_id]
        companies.add(case.company_query)
        companies.add(case.company_group_key)
        questions.add(normalized_question_hash(case.research_question))
        case_ids.add(case.case_id)
        for document in case.documents:
            path = (bundle_root / document.relative_path).resolve()
            if bundle_root not in path.parents:
                raise ValueError("retired held-out source escaped its private bundle")
            actual_hash = _sha256_file(path)
            if actual_hash != document.content_hash:
                raise ValueError(f"retired held-out source hash mismatch: {document.document_id}")
            verified_document_hashes.add(actual_hash)
            document_hashes.add(actual_hash)

    source_hashes[f"retired-heldout-bundle-{index}"] = payload_sha256(
        {
            "suite_id": manifest.suite_id,
            "bundle_manifest_hash": _sha256_file(manifest_path),
            "runtime_manifest_hash": _sha256_file(runtime_path),
            "document_hashes": sorted(verified_document_hashes),
        }
    )


def build_development_exposure_snapshot(
    project_root: Path,
    *,
    exclusions: DevelopmentIssuerExclusionManifest,
    development_suites: list[BenchmarkSuiteManifest],
    retired_heldout_bundles: list[Path] | None = None,
) -> DevelopmentExposureSnapshot:
    """Collect structured development exposure without reading held-out inputs."""

    project_root = project_root.resolve()
    companies = set(exclusions.all_aliases())
    questions: set[str] = set()
    case_ids: set[str] = set()
    document_hashes: set[str] = set()
    source_hashes = {"tracked-issuer-exclusions": exclusions.content_hash()}

    for index, suite in enumerate(development_suites, start=1):
        _add_suite_exposure(suite, companies, questions, case_ids)
        source_hashes[f"development-suite-{index}"] = suite.suite_hash

    _add_financebench_public_source(
        project_root, companies, questions, case_ids, document_hashes, source_hashes
    )
    _add_v2_run_exposure(project_root, companies, questions, document_hashes, source_hashes)

    for index, bundle_root in enumerate(retired_heldout_bundles or [], start=1):
        _add_retired_heldout_bundle_exposure(
            bundle_root,
            index=index,
            companies=companies,
            questions=questions,
            case_ids=case_ids,
            document_hashes=document_hashes,
            source_hashes=source_hashes,
        )

    return DevelopmentExposureSnapshot(
        snapshot_id="researchforge-development-exposures-v1",
        source_hashes=dict(sorted(source_hashes.items())),
        company_aliases=sorted(companies, key=lambda value: (value.casefold(), value)),
        question_hashes=sorted(questions),
        case_ids=sorted(case_ids),
        document_hashes=sorted(document_hashes),
    )
