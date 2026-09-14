"""Canonical V2 JSON-schema exports derived from the live Pydantic contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from researchforge.v2.benchmarks.exposure import DevelopmentExposureSnapshot
from researchforge.v2.benchmarks.heldout import (
    DevelopmentIssuerAliasGroup,
    DevelopmentIssuerExclusionManifest,
    HeldOutAcceptanceAttempt,
    HeldOutBundleManifest,
    HeldOutDocument,
    HeldOutHumanJudgment,
    HeldOutRuntimeCase,
    HeldOutSuiteSeal,
)
from researchforge.v2.benchmarks.human_review import (
    BlindCandidate,
    BlindReviewCase,
    BlindReviewPackage,
    CandidateResultRef,
    HumanAcceptanceSummary,
    HumanJudgmentFile,
)
from researchforge.v2.benchmarks.semantic_assessor import (
    AtomicClaimAssessment,
    SemanticAssessmentDraft,
)
from researchforge.v2.benchmarks.suite import (
    BenchmarkSuiteExecution,
    BenchmarkSuiteManifest,
)
from researchforge.v2.contracts import (
    AnalysisSection,
    CalculateInput,
    ClaimReview,
    CounterInput,
    FactsInput,
    Finding,
    Hypothesis,
    ImageInput,
    NumericAssertion,
    OpenQuestion,
    ReadInput,
    ResearchObjective,
    ResearchReport,
    ResearchRequest,
    ReviewSummary,
    SearchInput,
    SemanticReview,
    SeriesCalculateInput,
    SeriesExtractInput,
    Submission,
    TraceEvent,
    WorkingState,
)
from researchforge.v2.quality import (
    EvidenceAlternative,
    EvidenceRequirement,
    FindingRequirement,
    NumericReference,
    QualityCase,
    RequirementAssessment,
    SemanticAnnotations,
)

SchemaMap = Mapping[str, type[BaseModel]]

V2_SCHEMA_MODELS: SchemaMap = {
    "research-request.schema.json": ResearchRequest,
    "search-input.schema.json": SearchInput,
    "read-input.schema.json": ReadInput,
    "image-input.schema.json": ImageInput,
    "facts-input.schema.json": FactsInput,
    "calculate-input.schema.json": CalculateInput,
    "counter-input.schema.json": CounterInput,
    "series-extract-input.schema.json": SeriesExtractInput,
    "series-calculate-input.schema.json": SeriesCalculateInput,
    "hypothesis.schema.json": Hypothesis,
    "open-question.schema.json": OpenQuestion,
    "research-objective.schema.json": ResearchObjective,
    "working-state.schema.json": WorkingState,
    "submission.schema.json": Submission,
    "numeric-assertion.schema.json": NumericAssertion,
    "finding.schema.json": Finding,
    "analysis-section.schema.json": AnalysisSection,
    "research-report.schema.json": ResearchReport,
    "claim-review.schema.json": ClaimReview,
    "review-summary.schema.json": ReviewSummary,
    "semantic-review.schema.json": SemanticReview,
    "trace-event.schema.json": TraceEvent,
    "numeric-reference.schema.json": NumericReference,
    "evidence-alternative.schema.json": EvidenceAlternative,
    "evidence-requirement.schema.json": EvidenceRequirement,
    "finding-requirement.schema.json": FindingRequirement,
    "requirement-assessment.schema.json": RequirementAssessment,
    "quality-case.schema.json": QualityCase,
    "semantic-annotations.schema.json": SemanticAnnotations,
    "benchmark-atomic-claim-assessment.schema.json": AtomicClaimAssessment,
    "benchmark-semantic-assessment-draft.schema.json": SemanticAssessmentDraft,
    "benchmark-suite-manifest.schema.json": BenchmarkSuiteManifest,
    "benchmark-suite-execution.schema.json": BenchmarkSuiteExecution,
    "heldout-document.schema.json": HeldOutDocument,
    "heldout-human-judgment.schema.json": HeldOutHumanJudgment,
    "heldout-candidate-result-ref.schema.json": CandidateResultRef,
    "heldout-blind-candidate.schema.json": BlindCandidate,
    "heldout-blind-review-case.schema.json": BlindReviewCase,
    "heldout-blind-review-package.schema.json": BlindReviewPackage,
    "heldout-human-judgment-file.schema.json": HumanJudgmentFile,
    "heldout-human-acceptance-summary.schema.json": HumanAcceptanceSummary,
    "heldout-runtime-case.schema.json": HeldOutRuntimeCase,
    "heldout-acceptance-attempt.schema.json": HeldOutAcceptanceAttempt,
    "heldout-bundle-manifest.schema.json": HeldOutBundleManifest,
    "heldout-suite-seal.schema.json": HeldOutSuiteSeal,
    "development-issuer-alias-group.schema.json": DevelopmentIssuerAliasGroup,
    "development-issuer-exclusion-manifest.schema.json": DevelopmentIssuerExclusionManifest,
    "development-exposure-snapshot.schema.json": DevelopmentExposureSnapshot,
}


def export_schema(model: type[BaseModel], filename: str) -> dict[str, Any]:
    schema = model.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = f"https://researchforge.local/schemas/v2/{filename}"
    return schema
