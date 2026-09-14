"""Sealed held-out quality-suite contracts with minimal human review.

Held-out is a usage discipline, not merely a split label. Product runtime inputs live in a private
bundle and Git tracks only a content seal. Humans do not author reference answers or evidence
labels;
they only make a blind pairwise preference choice or a simple meets-standard choice after product
runs terminate. Once results are used to tune the implementation, that seal is retired from held-out
use.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from researchforge.adapters.storage import canonical_json_bytes, payload_sha256


class HeldOutContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DevelopmentIssuerAliasGroup(HeldOutContract):
    group_key: str = Field(min_length=1)
    aliases: list[str] = Field(min_length=1)


class DevelopmentIssuerExclusionManifest(HeldOutContract):
    schema_version: Literal["2.0.0"] = "2.0.0"
    exclusion_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    issuer_alias_groups: list[DevelopmentIssuerAliasGroup] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_groups(self) -> DevelopmentIssuerExclusionManifest:
        keys = [group.group_key for group in self.issuer_alias_groups]
        if len(keys) != len(set(keys)):
            raise ValueError("development issuer exclusion group keys must be unique")
        aliases = [
            _normalized_company(alias)
            for group in self.issuer_alias_groups
            for alias in group.aliases
        ]
        if len(aliases) != len(set(aliases)):
            raise ValueError("development issuer aliases must be unique after normalization")
        return self

    def all_aliases(self) -> set[str]:
        return {alias for group in self.issuer_alias_groups for alias in group.aliases}

    def content_hash(self) -> str:
        return payload_sha256(self.model_dump(mode="json"))


class HeldOutDocument(HeldOutContract):
    document_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    relative_path: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_uri: str = Field(min_length=1)
    published_at: str = Field(min_length=1)
    document_type: str = Field(min_length=1)
    reporting_period: dict[str, object]

    @model_validator(mode="after")
    def private_source_path_only(self) -> HeldOutDocument:
        path = Path(self.relative_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("held-out document path must stay inside the private bundle")
        if not path.parts or path.parts[0] != "sources":
            raise ValueError("held-out document must live under the private sources directory")
        return self


class HeldOutRuntimeCase(HeldOutContract):
    schema_version: Literal["2.0.0"] = "2.0.0"
    case_id: str = Field(min_length=1)
    stratum: str = Field(min_length=1)
    company_group_key: str = Field(min_length=1)
    company_query: str = Field(min_length=1)
    company_id: str = Field(min_length=1)
    market_hint: Literal["CN", "US", "HK"]
    requested_period_label: str | None = None
    research_question: str = Field(min_length=1)
    research_time: str = Field(min_length=1)
    corpus_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    documents: list[HeldOutDocument] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def corpus_matches_documents(self) -> HeldOutRuntimeCase:
        expected = payload_sha256(sorted(document.content_hash for document in self.documents))
        if expected != self.corpus_hash:
            raise ValueError("held-out runtime corpus_hash does not match document hashes")
        return self


class HeldOutBundleManifest(HeldOutContract):
    schema_version: Literal["2.0.0"] = "2.0.0"
    suite_id: str = Field(min_length=1)
    protocol_version: Literal["acceptance-v2"] = "acceptance-v2"
    split: Literal["held_out"] = "held_out"
    created_at: datetime
    review_mode: Literal["pairwise_preference", "meets_standard"]
    runtime_cases_file: Literal["runtime-cases.jsonl"] = "runtime-cases.jsonl"
    source_directory: Literal["sources"] = "sources"
    case_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_case_ids(self) -> HeldOutBundleManifest:
        if len(self.case_ids) != len(set(self.case_ids)):
            raise ValueError("held-out bundle case IDs must be unique")
        return self


class HeldOutSuiteSeal(HeldOutContract):
    schema_version: Literal["2.0.0"] = "2.0.0"
    suite_id: str = Field(min_length=1)
    protocol_version: Literal["acceptance-v2"] = "acceptance-v2"
    split: Literal["held_out"] = "held_out"
    frozen_at: datetime
    review_mode: Literal["pairwise_preference", "meets_standard"]
    bundle_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    case_count: int = Field(gt=0)
    company_count: int = Field(gt=0)
    stratum_counts: dict[str, int]
    opaque_case_hashes: list[str] = Field(min_length=1)
    opaque_company_hashes: list[str] = Field(min_length=1)
    development_suite_hashes: list[str]
    development_exclusion_hashes: list[str]
    development_exposure_hashes: list[str]
    runtime_inputs_frozen: Literal[True] = True
    automated_checks_required: Literal[True] = True
    human_judgment_required: Literal[True] = True
    human_input_contract: Literal["choice_only"] = "choice_only"
    reference_labels_required: Literal[False] = False
    labels_tracked_in_git: Literal[False] = False
    questions_tracked_in_git: Literal[False] = False
    first_result_policy: Literal["single_acceptance_pass"] = "single_acceptance_pass"
    retirement_policy: Literal["retire_after_result_driven_tuning"] = (
        "retire_after_result_driven_tuning"
    )

    @model_validator(mode="after")
    def counts_match_hashes(self) -> HeldOutSuiteSeal:
        if self.case_count != len(self.opaque_case_hashes):
            raise ValueError("held-out case count does not match opaque case hashes")
        if self.company_count != len(self.opaque_company_hashes):
            raise ValueError("held-out company count does not match opaque company hashes")
        if sum(self.stratum_counts.values()) != self.case_count:
            raise ValueError("held-out stratum counts do not sum to case count")
        return self


class HeldOutHumanJudgment(HeldOutContract):
    """A deliberately tiny human-input contract: one choice, no authored rubric or explanation."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    case_id: str = Field(min_length=1)
    review_mode: Literal["pairwise_preference", "meets_standard"]
    reviewer_id: str = Field(min_length=1)
    reviewed_at: datetime
    candidate_a_run_id: str | None = None
    candidate_b_run_id: str | None = None
    evaluated_run_id: str | None = None
    pairwise_verdict: Literal["a_better", "b_better", "tie", "neither"] | None = None
    threshold_verdict: (
        Literal["meets_standard", "does_not_meet_standard", "cannot_judge"] | None
    ) = None

    @model_validator(mode="after")
    def exactly_one_choice_for_review_mode(self) -> HeldOutHumanJudgment:
        if self.review_mode == "pairwise_preference":
            if not self.candidate_a_run_id or not self.candidate_b_run_id:
                raise ValueError("pairwise held-out review requires candidate A and B run IDs")
            if self.candidate_a_run_id == self.candidate_b_run_id:
                raise ValueError("pairwise held-out candidates must be different runs")
            if self.evaluated_run_id is not None:
                raise ValueError("pairwise held-out review cannot set evaluated_run_id")
            if self.pairwise_verdict is None or self.threshold_verdict is not None:
                raise ValueError("pairwise held-out review requires exactly one pairwise verdict")
            return self
        if self.evaluated_run_id is None:
            raise ValueError("meets-standard held-out review requires evaluated_run_id")
        if self.candidate_a_run_id is not None or self.candidate_b_run_id is not None:
            raise ValueError("meets-standard held-out review cannot set pairwise run IDs")
        if self.threshold_verdict is None or self.pairwise_verdict is not None:
            raise ValueError(
                "meets-standard held-out review requires exactly one threshold verdict"
            )
        return self


def validate_human_judgments(
    seal: HeldOutSuiteSeal, judgments: Sequence[HeldOutHumanJudgment]
) -> None:
    """Require one choice per sealed case without asking humans for any authored reference data."""
    if len(judgments) != seal.case_count:
        raise ValueError("held-out human judgment count must equal sealed case count")
    if any(judgment.review_mode != seal.review_mode for judgment in judgments):
        raise ValueError("held-out human judgment mode must match the frozen suite review mode")
    opaque_ids = {_opaque(judgment.case_id) for judgment in judgments}
    if len(opaque_ids) != len(judgments):
        raise ValueError("held-out human judgments must contain exactly one choice per case")
    if opaque_ids != set(seal.opaque_case_hashes):
        raise ValueError("held-out human judgments do not match the frozen suite cases")


def _jsonl(path: Path, model: type[BaseModel]) -> list[BaseModel]:
    values: list[BaseModel] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            values.append(model.model_validate_json(line))
    return values


def _normalized_company(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.casefold())


def development_question_hash(value: str) -> str:
    """Hash an exact normalized development question without persisting its text."""
    normalized = re.sub(r"\s+", " ", value.casefold().strip())
    payload = ("researchforge-development-question-v1:" + normalized).encode()
    return hashlib.sha256(payload).hexdigest()


def _opaque(value: str) -> str:
    return hashlib.sha256(("researchforge-heldout-v2:" + value).encode()).hexdigest()


def _manifest_hash(values: Sequence[BaseModel]) -> str:
    return hashlib.sha256(
        b"\n".join(canonical_json_bytes(value.model_dump(mode="json")) for value in values)
    ).hexdigest()


def _source_manifest(
    bundle_root: Path, runtimes: list[HeldOutRuntimeCase]
) -> tuple[str, list[str]]:
    hashes: list[str] = []
    seen_paths: set[Path] = set()
    for runtime in runtimes:
        for document in runtime.documents:
            path = (bundle_root / document.relative_path).resolve()
            if bundle_root.resolve() not in path.parents:
                raise ValueError("held-out source escaped the private bundle")
            if path in seen_paths:
                continue
            seen_paths.add(path)
            payload = path.read_bytes()
            actual = hashlib.sha256(payload).hexdigest()
            if actual != document.content_hash:
                raise ValueError(f"held-out source hash mismatch: {document.document_id}")
            hashes.append(actual)
    hashes.sort()
    return payload_sha256(hashes), hashes


def assert_private_bundle_not_trackable(bundle_root: Path, project_root: Path) -> None:
    """Refuse private held-out questions/source manifests inside Git-visible project paths."""
    bundle_root = bundle_root.resolve()
    project_root = project_root.resolve()
    try:
        relative = bundle_root.relative_to(project_root)
    except ValueError:
        return
    tracked = subprocess.run(
        ["git", "ls-files", "--", relative.as_posix()],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if tracked:
        raise RuntimeError("private held-out bundle contains Git-tracked files")
    ignored = (
        subprocess.run(
            ["git", "check-ignore", "-q", "--", relative.as_posix()],
            cwd=project_root,
            check=False,
        ).returncode
        == 0
    )
    if not ignored:
        raise RuntimeError(
            "private held-out bundle is inside the repository but is not covered by .gitignore"
        )


def seal_heldout_bundle(
    bundle_root: Path,
    *,
    development_company_names: set[str],
    development_suite_hashes: list[str],
    development_question_hashes: set[str] | None = None,
    development_document_hashes: set[str] | None = None,
    development_exclusion_hashes: list[str] | None = None,
    development_exposure_hashes: list[str] | None = None,
    minimum_cases: int = 8,
    minimum_companies: int = 4,
    minimum_strata: int = 4,
) -> HeldOutSuiteSeal:
    """Validate and seal private runtime inputs without requiring human-authored gold labels."""
    bundle_root = bundle_root.resolve()
    manifest = HeldOutBundleManifest.model_validate_json(
        (bundle_root / "bundle-manifest.json").read_text(encoding="utf-8")
    )
    runtimes = [
        value
        for value in _jsonl(bundle_root / manifest.runtime_cases_file, HeldOutRuntimeCase)
        if isinstance(value, HeldOutRuntimeCase)
    ]
    if len(runtimes) != len(manifest.case_ids):
        raise ValueError("held-out runtime/manifest case counts differ")
    runtime_by_id = {case.case_id: case for case in runtimes}
    expected_ids = set(manifest.case_ids)
    if set(runtime_by_id) != expected_ids:
        raise ValueError("held-out runtime case IDs differ from bundle manifest")

    development = {_normalized_company(name) for name in development_company_names}
    exposed_questions = development_question_hashes or set()
    exposed_documents = development_document_hashes or set()
    for case_id in manifest.case_ids:
        runtime = runtime_by_id[case_id]
        if (
            _normalized_company(runtime.company_query) in development
            or _normalized_company(runtime.company_group_key) in development
        ):
            raise ValueError("held-out issuer overlaps the development exclusion set")
        if development_question_hash(runtime.research_question) in exposed_questions:
            raise ValueError("held-out question overlaps the development exposure set")
        if any(document.content_hash in exposed_documents for document in runtime.documents):
            raise ValueError("held-out source document overlaps the development exposure set")

    companies = {case.company_group_key for case in runtimes}
    strata = Counter(case.stratum for case in runtimes)
    if len(runtimes) < minimum_cases:
        raise ValueError(f"held-out acceptance suite requires at least {minimum_cases} cases")
    if len(companies) < minimum_companies:
        raise ValueError(f"held-out acceptance suite requires at least {minimum_companies} issuers")
    if len(strata) < minimum_strata:
        raise ValueError(f"held-out acceptance suite requires at least {minimum_strata} strata")

    source_manifest_hash, source_hashes = _source_manifest(bundle_root, runtimes)
    runtime_hash = _manifest_hash(runtimes)
    bundle_hash = payload_sha256(
        {
            "suite_id": manifest.suite_id,
            "protocol_version": manifest.protocol_version,
            "review_mode": manifest.review_mode,
            "runtime_manifest_hash": runtime_hash,
            "source_manifest_hash": source_manifest_hash,
            "source_hashes": source_hashes,
            "case_order": manifest.case_ids,
        }
    )
    return HeldOutSuiteSeal(
        suite_id=manifest.suite_id,
        protocol_version=manifest.protocol_version,
        frozen_at=datetime.now().astimezone(),
        review_mode=manifest.review_mode,
        bundle_hash=bundle_hash,
        runtime_manifest_hash=runtime_hash,
        source_manifest_hash=source_manifest_hash,
        case_count=len(runtimes),
        company_count=len(companies),
        stratum_counts=dict(sorted(strata.items())),
        opaque_case_hashes=[_opaque(case_id) for case_id in sorted(runtime_by_id)],
        opaque_company_hashes=[_opaque(company) for company in sorted(companies)],
        development_suite_hashes=sorted(development_suite_hashes),
        development_exclusion_hashes=sorted(development_exclusion_hashes or []),
        development_exposure_hashes=sorted(development_exposure_hashes or []),
    )


def verify_heldout_bundle(
    bundle_root: Path,
    seal: HeldOutSuiteSeal,
    *,
    development_company_names: set[str],
    development_suite_hashes: list[str],
    development_question_hashes: set[str] | None = None,
    development_document_hashes: set[str] | None = None,
    development_exclusion_hashes: list[str] | None = None,
    development_exposure_hashes: list[str] | None = None,
    minimum_cases: int = 8,
    minimum_companies: int = 4,
    minimum_strata: int = 4,
) -> None:
    """Recompute all content-bound seal fields; verification time is intentionally irrelevant."""
    recomputed = seal_heldout_bundle(
        bundle_root,
        development_company_names=development_company_names,
        development_suite_hashes=development_suite_hashes,
        development_question_hashes=development_question_hashes,
        development_document_hashes=development_document_hashes,
        development_exclusion_hashes=development_exclusion_hashes,
        development_exposure_hashes=development_exposure_hashes,
        minimum_cases=minimum_cases,
        minimum_companies=minimum_companies,
        minimum_strata=minimum_strata,
    )
    expected = seal.model_dump(mode="json", exclude={"frozen_at"})
    actual = recomputed.model_dump(mode="json", exclude={"frozen_at"})
    if actual != expected:
        changed = sorted(key for key in expected if expected.get(key) != actual.get(key))
        raise ValueError(f"held-out bundle no longer matches frozen seal: {', '.join(changed)}")


class HeldOutAcceptanceAttempt(HeldOutContract):
    schema_version: Literal["2.0.0"] = "2.0.0"
    attempt_id: str = Field(min_length=1)
    suite_id: str = Field(min_length=1)
    bundle_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    implementation_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    git_head: str | None = None
    git_dirty: bool
    started_at: datetime
    state: Literal["armed", "running", "completed", "technical_failure", "retired"] = "armed"
    retry_of: str | None = None
    retry_reason: str | None = None
    results_opened_at: datetime | None = None
    human_review_completed_at: datetime | None = None
    tuning_performed_after_results: bool = False

    @model_validator(mode="after")
    def retry_and_retirement_are_explicit(self) -> HeldOutAcceptanceAttempt:
        if (self.retry_of is None) != (self.retry_reason is None):
            raise ValueError("held-out retry_of and retry_reason must be supplied together")
        if self.tuning_performed_after_results and self.state != "retired":
            raise ValueError("held-out attempt must be retired after result-driven tuning")
        return self


def arm_heldout_acceptance(
    seal: HeldOutSuiteSeal,
    existing_attempts: Sequence[HeldOutAcceptanceAttempt],
    *,
    implementation_hash: str,
    git_head: str | None,
    git_dirty: bool,
    started_at: datetime,
    retry_reason: str | None = None,
) -> HeldOutAcceptanceAttempt:
    """Create the one allowed acceptance attempt, or an explicit same-build infra retry."""
    same_bundle = [item for item in existing_attempts if item.bundle_hash == seal.bundle_hash]
    retry_of: str | None = None
    if same_bundle:
        latest = max(same_bundle, key=lambda item: item.started_at)
        if latest.state != "technical_failure":
            raise ValueError(
                "held-out seal already has a non-technical-failure acceptance attempt; "
                "reuse is forbidden"
            )
        if retry_reason is None:
            raise ValueError("held-out technical failure retry requires an explicit reason")
        if latest.implementation_hash != implementation_hash:
            raise ValueError("held-out infrastructure retry must use the identical implementation")
        retry_of = latest.attempt_id
    elif retry_reason is not None:
        raise ValueError("held-out retry reason supplied without a prior technical failure")
    ordinal = len(same_bundle) + 1
    attempt_id = f"{seal.suite_id}-acceptance-{ordinal}-{implementation_hash[:10]}"
    return HeldOutAcceptanceAttempt(
        attempt_id=attempt_id,
        suite_id=seal.suite_id,
        bundle_hash=seal.bundle_hash,
        implementation_hash=implementation_hash,
        git_head=git_head,
        git_dirty=git_dirty,
        started_at=started_at,
        retry_of=retry_of,
        retry_reason=retry_reason,
    )
