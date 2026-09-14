"""Reference-backed V2 quality measurement, separate from regression and self-review.

The evaluator is intentionally conservative. A runnable benchmark is not automatically a
valid benchmark; independently reviewed references and report-bound semantic annotations
are required before a result is suitable for a product quality claim. Missing semantic
judgments stay unmeasured rather than being silently converted to zero or success.
"""

from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal, InvalidOperation
from statistics import median
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class QualityContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NumericReference(QualityContract):
    metric_code: str
    fiscal_year: int
    fiscal_period: str
    period_basis: str
    currency: str | None
    value: str
    absolute_tolerance: str = "0"
    source_document_hash: str
    source_locator: str

    @field_validator("value", "absolute_tolerance")
    @classmethod
    def valid_decimal_reference(cls, value: str) -> str:
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("reference must be a decimal string") from exc
        if not parsed.is_finite():
            raise ValueError("reference must be finite")
        return value

    @field_validator("absolute_tolerance")
    @classmethod
    def nonnegative_tolerance(cls, value: str) -> str:
        if Decimal(value) < 0:
            raise ValueError("reference tolerance must be nonnegative")
        return value


class EvidenceAlternative(QualityContract):
    document_hash: str
    page_number: int | None = None
    required_text: str = Field(min_length=1)
    match_mode: Literal["text", "page"] = "text"

    @model_validator(mode="after")
    def page_match_requires_page(self) -> EvidenceAlternative:
        if self.match_mode == "page" and self.page_number is None:
            raise ValueError("page evidence matching requires page_number")
        return self


class EvidenceRequirement(QualityContract):
    requirement_id: str
    description: str
    alternatives: list[EvidenceAlternative] = Field(min_length=1)
    materiality: Literal["major", "minor"] = "major"


class FindingRequirement(QualityContract):
    """Independent semantic requirement; never a model-generated report claim ID."""

    requirement_id: str
    description: str = Field(min_length=1)
    materiality: Literal["major", "minor"] = "major"
    reference_answer: str | None = None


class QualityCase(QualityContract):
    schema_version: Literal["2.0.0"] = "2.0.0"
    case_id: str
    split: Literal["development", "validation", "held_out", "synthetic_sanity"]
    question: str
    company_id: str
    research_time: str
    corpus_hash: str
    reference_author: str
    reference_integrity: Literal["provided", "verified", "suspect"] = "provided"
    reference_integrity_notes: list[str] = []
    reference_reviewed_by: str | None = None
    reference_reviewed_at: str | None = None
    numeric_references: list[NumericReference] = []
    required_evidence: list[EvidenceRequirement] = []
    required_findings: list[FindingRequirement] = []
    material_counter_evidence: list[str] = []
    acceptable_uncertainties: list[str] = []

    @model_validator(mode="after")
    def unique_requirement_ids(self) -> QualityCase:
        identifiers = [item.requirement_id for item in self.required_findings]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("required finding requirement IDs must be unique")
        if self.reference_integrity == "suspect" and not self.reference_integrity_notes:
            raise ValueError("suspect reference integrity requires an explicit note")
        return self


class RequirementAssessment(QualityContract):
    """Assessor mapping from one independent requirement to actual report claims."""

    requirement_id: str
    report_claim_ids: list[str] = []
    verdict: Literal["covered", "partial", "missed"]
    reason: str = Field(min_length=1)


class SemanticAnnotations(QualityContract):
    """Human or calibrated-assessor output bound to an exact report."""

    report_hash: str
    assessor_id: str
    assessor_version: str
    assessment_kind: Literal["human", "calibrated_model", "uncalibrated_model"]
    requirement_assessments: list[RequirementAssessment] = []
    assessed_report_claim_ids: list[str] = []
    assessed_atomic_claims: int = Field(ge=0)
    correct_atomic_claims: int = Field(ge=0)
    assessed_cited_claims: int = Field(ge=0)
    supported_cited_claims: int = Field(ge=0)
    claims_requiring_citations: int = Field(ge=0)
    claims_with_valid_support: int = Field(ge=0)
    premature_stop: bool | None = None
    unnecessary_continuation: bool | None = None
    notes: list[str] = []

    @model_validator(mode="after")
    def internally_consistent(self) -> SemanticAnnotations:
        if (
            self.correct_atomic_claims > self.assessed_atomic_claims
            or self.supported_cited_claims > self.assessed_cited_claims
            or self.claims_with_valid_support > self.claims_requiring_citations
        ):
            raise ValueError("semantic annotation numerators cannot exceed denominators")
        identifiers = [item.requirement_id for item in self.requirement_assessments]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("requirement assessments must not duplicate requirement IDs")
        if len(self.assessed_report_claim_ids) != len(set(self.assessed_report_claim_ids)):
            raise ValueError("assessed report claim IDs must be unique")
        return self


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "value": round(numerator / denominator, 6) if denominator else None,
        "numerator": numerator,
        "denominator": denominator,
        "status": "measured" if denominator else "not_measured",
    }


def _same_instant(left: object, right: object) -> bool:
    try:
        left_dt = datetime.fromisoformat(str(left).replace("Z", "+00:00"))
        right_dt = datetime.fromisoformat(str(right).replace("Z", "+00:00"))
    except ValueError:
        return str(left) == str(right)
    return left_dt == right_dt


def _normal_text(value: str) -> str:
    return "".join(value.split()).casefold()


def _reference_text_matches(required_text: str, observed_text: str) -> bool:
    required = _normal_text(required_text)
    observed = _normal_text(observed_text)
    if not required or not observed:
        return False
    if required in observed:
        return True
    # FinanceBench labels an entire evidence page while ResearchForge reads bounded windows.
    # A substantial observed snippet that is literally contained in the reviewed page is
    # therefore a valid page-observation hit; very short strings cannot trigger this path.
    return len(observed) >= 80 and observed in required


def _parse_scalar_reference(value: str) -> tuple[Decimal, str] | None:
    probe = value.strip()
    percent = probe.endswith("%")
    if percent:
        probe = probe[:-1].strip()
    if probe.startswith("$"):
        probe = probe[1:].strip()
    negative_parentheses = probe.startswith("(") and probe.endswith(")")
    if negative_parentheses:
        probe = probe[1:-1].strip()
    if not probe or any(char.isalpha() for char in probe):
        return None
    probe = probe.replace(",", "")
    try:
        number = Decimal(probe)
    except InvalidOperation:
        return None
    if not number.is_finite():
        return None
    if negative_parentheses:
        number = -number
    return number, "percent" if percent else "number"


def _summary_scalars(text: str) -> list[tuple[Decimal, str]]:
    import re

    tokens = re.findall(
        r"(?<![A-Za-z0-9])(?:\$?\(?[-+]?\d[\d,]*(?:\.\d+)?\)?%?)(?![A-Za-z0-9])", text
    )
    values: list[tuple[Decimal, str]] = []
    for token in tokens:
        parsed = _parse_scalar_reference(token)
        if parsed is not None:
            values.append(parsed)
    return values


def _scalar_reference_presence(
    case: QualityCase, report: dict[str, Any] | None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    references = [
        (requirement.requirement_id, parsed)
        for requirement in case.required_findings
        if requirement.reference_answer is not None
        and (parsed := _parse_scalar_reference(requirement.reference_answer)) is not None
    ]
    if not references:
        return _ratio(0, 0), []
    summary = str(report.get("executive_summary", "")) if isinstance(report, dict) else ""
    candidates = _summary_scalars(summary)
    details: list[dict[str, Any]] = []
    for requirement_id, (expected, expected_kind) in references:
        matched = any(kind == expected_kind and value == expected for value, kind in candidates)
        details.append(
            {
                "requirement_id": requirement_id,
                "expected_value": format(expected, "f"),
                "scalar_kind": expected_kind,
                "present_in_executive_summary": matched,
            }
        )
    return _ratio(
        sum(item["present_in_executive_summary"] for item in details), len(details)
    ), details


def _facts(environment: dict[str, Any]) -> list[dict[str, Any]]:
    raw = environment.get("facts", [])
    if isinstance(raw, dict):
        return [item for item in raw.values() if isinstance(item, dict)]
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def _report_claim_ids(report: dict[str, Any] | None) -> set[str]:
    if not isinstance(report, dict):
        return set()
    findings = report.get("findings", [])
    if not isinstance(findings, list):
        return set()
    return {
        str(item["claim_id"])
        for item in findings
        if isinstance(item, dict) and item.get("claim_id")
    }


def _trajectory(run: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    def count(*, event_type: str | None = None, name: str | None = None) -> int:
        return sum(
            1
            for event in events
            if (event_type is None or event.get("event_type") == event_type)
            and (name is None or event.get("name") == name)
        )

    usage = run.get("usage", {}) if isinstance(run.get("usage"), dict) else {}
    return {
        "agent_turns": count(event_type="agent_turn"),
        "tool_results": count(event_type="tool_result"),
        "counter_searches": count(event_type="tool_result", name="search_counter_evidence"),
        "state_reflections": count(event_type="research_reflection"),
        "report_repairs": count(event_type="report_repair_requested"),
        "returns_to_research": count(event_type="validation_feedback"),
        "provider_calls": int(usage.get("provider_calls", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
        "estimated_cost": usage.get("estimated_cost"),
        "cost_is_billing_truth": False,
    }


def evaluate_quality(
    case: QualityCase,
    *,
    run: dict[str, Any],
    environment: dict[str, Any],
    observed_evidence: list[dict[str, Any]],
    report_hash: str | None,
    report: dict[str, Any] | None = None,
    events: list[dict[str, Any]] | None = None,
    annotations: SemanticAnnotations | None = None,
) -> dict[str, Any]:
    """Measure one persisted run against independent sealed references."""
    request = run.get("request", {})
    context_errors: list[str] = []
    if request.get("research_question") != case.question:
        context_errors.append("question_differs_from_reference_case")
    if not _same_instant(request.get("research_time"), case.research_time):
        context_errors.append("cutoff_differs_from_reference_case")
    if environment.get("corpus_hash") != case.corpus_hash:
        context_errors.append("corpus_snapshot_differs_from_reference_case")
    if environment.get("company", {}).get("company_id") != case.company_id:
        context_errors.append("company_differs_from_reference_case")
    if annotations is not None and annotations.report_hash != report_hash:
        context_errors.append("semantic_annotations_belong_to_another_report")

    case_requirement_ids = {item.requirement_id for item in case.required_findings}
    actual_claim_ids = _report_claim_ids(report)
    if annotations is not None:
        annotated_requirements = {
            item.requirement_id for item in annotations.requirement_assessments
        }
        if not annotated_requirements <= case_requirement_ids:
            context_errors.append("semantic_annotations_reference_unknown_requirements")
        annotation_claim_ids = set(annotations.assessed_report_claim_ids)
        annotation_claim_ids.update(
            claim_id
            for assessment in annotations.requirement_assessments
            for claim_id in assessment.report_claim_ids
        )
        if annotation_claim_ids and report is None:
            context_errors.append("report_missing_for_semantic_annotations")
        elif not annotation_claim_ids <= actual_claim_ids:
            context_errors.append("semantic_annotations_reference_unknown_report_claims")

    if context_errors:
        return {
            "schema_version": "2.0.0",
            "case_id": case.case_id,
            "eligible": False,
            "errors": context_errors,
            "metrics": {},
        }

    facts = _facts(environment)
    numeric_details: list[dict[str, Any]] = []
    for reference in case.numeric_references:
        matches = [
            fact
            for fact in facts
            if fact.get("metric_code") == reference.metric_code
            and fact.get("currency") == reference.currency
            and fact.get("period", {}).get("fiscal_year") == reference.fiscal_year
            and fact.get("period", {}).get("fiscal_period") == reference.fiscal_period
            and fact.get("period", {}).get("period_basis") == reference.period_basis
            and fact.get("source", {}).get("content_hash") == reference.source_document_hash
        ]
        matched = False
        if len(matches) == 1:
            try:
                tolerance = Decimal(reference.absolute_tolerance)
                expected = Decimal(reference.value)
                actual = Decimal(str(matches[0].get("value")))
                matched = (
                    tolerance.is_finite()
                    and tolerance >= 0
                    and expected.is_finite()
                    and actual.is_finite()
                    and abs(actual - expected) <= tolerance
                )
            except (InvalidOperation, ValueError, TypeError):
                matched = False
        numeric_details.append(
            {
                "metric_code": reference.metric_code,
                "period": f"{reference.fiscal_year}{reference.fiscal_period}",
                "matched": matched,
                "candidate_count": len(matches),
                "reference_locator": reference.source_locator,
            }
        )

    evidence_details: list[dict[str, Any]] = []
    for evidence_requirement in case.required_evidence:
        matched_ids: list[str] = []
        for evidence in observed_evidence:
            for alternative in evidence_requirement.alternatives:
                document_hash = evidence.get("document_hash") or evidence.get("content_hash")
                page = evidence.get("page_number")
                location_matches = document_hash == alternative.document_hash and (
                    alternative.page_number is None or alternative.page_number == page
                )
                if not location_matches:
                    continue
                if alternative.match_mode == "page":
                    meaningful_observation = bool(
                        str(evidence.get("artifact_id", "")).strip()
                        and (str(evidence.get("text", "")).strip() or evidence.get("image_blob_id"))
                    )
                    if meaningful_observation:
                        matched_ids.append(str(evidence.get("artifact_id", "")))
                        break
                elif _reference_text_matches(
                    alternative.required_text, str(evidence.get("text", ""))
                ):
                    matched_ids.append(str(evidence.get("artifact_id", "")))
                    break
        evidence_details.append(
            {
                "requirement_id": evidence_requirement.requirement_id,
                "materiality": evidence_requirement.materiality,
                "observed": bool(matched_ids),
                "matched_observation_ids": sorted(set(matched_ids)),
            }
        )

    if case.reference_integrity == "suspect":
        scalar_presence = {
            **_ratio(0, 0),
            "reason": "reference_integrity_suspect",
        }
        scalar_reference_details: list[dict[str, Any]] = []
    else:
        scalar_presence, scalar_reference_details = _scalar_reference_presence(case, report)
    metrics: dict[str, Any] = {
        "reference_fact_recovery_accuracy": _ratio(
            sum(item["matched"] for item in numeric_details), len(numeric_details)
        ),
        "required_evidence_observation_recall": _ratio(
            sum(item["observed"] for item in evidence_details), len(evidence_details)
        ),
        "reference_answer_scalar_presence": scalar_presence,
        "answer_correctness": _ratio(0, 0),
        "reference_finding_coverage": _ratio(0, 0),
        "reference_finding_partial_or_better": _ratio(0, 0),
        "citation_support": _ratio(0, 0),
        "citation_completeness": _ratio(0, 0),
        "stop_quality": {"status": "not_measured", "value": None},
    }
    requirement_details: list[dict[str, Any]] = []
    if annotations is not None:
        by_requirement = {item.requirement_id: item for item in annotations.requirement_assessments}
        for finding_requirement in case.required_findings:
            assessment = by_requirement.get(finding_requirement.requirement_id)
            requirement_details.append(
                {
                    "requirement_id": finding_requirement.requirement_id,
                    "materiality": finding_requirement.materiality,
                    "verdict": assessment.verdict if assessment else "unassessed",
                    "report_claim_ids": assessment.report_claim_ids if assessment else [],
                    "reason": assessment.reason if assessment else "",
                }
            )
        covered = sum(item["verdict"] == "covered" for item in requirement_details)
        partial_or_better = sum(
            item["verdict"] in {"covered", "partial"} for item in requirement_details
        )
        metrics.update(
            {
                "answer_correctness": _ratio(
                    annotations.correct_atomic_claims, annotations.assessed_atomic_claims
                ),
                "reference_finding_coverage": _ratio(covered, len(case.required_findings)),
                "reference_finding_partial_or_better": _ratio(
                    partial_or_better, len(case.required_findings)
                ),
                "citation_support": _ratio(
                    annotations.supported_cited_claims, annotations.assessed_cited_claims
                ),
                "citation_completeness": _ratio(
                    annotations.claims_with_valid_support, annotations.claims_requiring_citations
                ),
                "stop_quality": {
                    "status": "assessed"
                    if annotations.premature_stop is not None
                    else "not_measured",
                    "premature_stop": annotations.premature_stop,
                    "unnecessary_continuation": annotations.unnecessary_continuation,
                    "assessor_kind": annotations.assessment_kind,
                },
            }
        )

    return {
        "schema_version": "2.0.0",
        "case_id": case.case_id,
        "run_id": run.get("run_id"),
        "eligible": True,
        "split": case.split,
        "corpus_hash": case.corpus_hash,
        "reference_integrity": case.reference_integrity,
        "reference_integrity_notes": case.reference_integrity_notes,
        "reference_reviewed": bool(case.reference_reviewed_by and case.reference_reviewed_at),
        "suitable_for_product_quality_claim": (
            case.split != "synthetic_sanity"
            and case.reference_integrity == "verified"
            and bool(case.reference_reviewed_by and case.reference_reviewed_at)
            and annotations is not None
            and annotations.assessment_kind != "uncalibrated_model"
        ),
        "run_completed": run.get("lifecycle_state") == "succeeded",
        "metrics": metrics,
        "numeric_details": numeric_details,
        "evidence_details": evidence_details,
        "scalar_reference_details": scalar_reference_details,
        "requirement_details": requirement_details,
        "trajectory": _trajectory(run, events or []),
        "semantic_assessor": annotations.model_dump() if annotations is not None else None,
        "overall_score": None,
        "notes": [
            "Fact recovery is not the same measurement as answer correctness.",
            "Observation recall is not proof the answer used or understood the evidence.",
            "Reference requirements are independent labels; report claim IDs are system output.",
            (
                "Scalar presence only checks an explicit gold scalar in the executive summary; "
                "it is not semantic correctness."
            ),
            "Unmeasured semantic and stop metrics remain null.",
            "Trajectory/cost diagnostics are not automatically quality scores.",
            "No preferred tool order or exact number of agent steps is required.",
            "Suspect reference labels are excluded from reference-answer scalar measurement.",
            "Benchmark validity requires reviewed references and an independently frozen split.",
        ],
    }


def _wilson(successes: int, total: int) -> dict[str, float | int | None]:
    if total <= 0:
        return {"low": None, "high": None, "confidence": 0.95, "n": total}
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = (
        z
        * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total))
        / denominator
    )
    return {
        "low": round(max(0.0, center - margin), 6),
        "high": round(min(1.0, center + margin), 6),
        "confidence": 0.95,
        "n": total,
    }


def summarize_quality_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate explicit denominators; never manufacture an overall composite score."""
    eligible = [item for item in results if item.get("eligible") is True]
    ratio_names = (
        "reference_fact_recovery_accuracy",
        "required_evidence_observation_recall",
        "reference_answer_scalar_presence",
        "answer_correctness",
        "reference_finding_coverage",
        "reference_finding_partial_or_better",
        "citation_support",
        "citation_completeness",
    )
    metrics: dict[str, Any] = {}
    for name in ratio_names:
        numerator = 0
        denominator = 0
        measured_cases = 0
        for result in eligible:
            metric = result.get("metrics", {}).get(name, {})
            if metric.get("status") != "measured":
                continue
            numerator += int(metric.get("numerator", 0))
            denominator += int(metric.get("denominator", 0))
            measured_cases += 1
        aggregate = _ratio(numerator, denominator)
        aggregate["measured_cases"] = measured_cases
        aggregate["wilson_95"] = _wilson(numerator, denominator)
        metrics[name] = aggregate

    trajectories = [item.get("trajectory", {}) for item in eligible]
    trajectory_summary: dict[str, Any] = {}
    for name in (
        "agent_turns",
        "tool_results",
        "counter_searches",
        "provider_calls",
        "total_tokens",
    ):
        values = [
            int(item[name])
            for item in trajectories
            if isinstance(item.get(name), int) and int(item[name]) >= 0
        ]
        trajectory_summary[name] = {
            "median": median(values) if values else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "cases": len(values),
        }

    stop_assessed = [
        item.get("metrics", {}).get("stop_quality", {})
        for item in eligible
        if item.get("metrics", {}).get("stop_quality", {}).get("status") == "assessed"
    ]
    return {
        "schema_version": "2.0.0",
        "case_ids": [str(item.get("case_id")) for item in eligible],
        "eligible_cases": len(eligible),
        "ineligible_cases": len(results) - len(eligible),
        "product_claim_suitable_cases": sum(
            item.get("suitable_for_product_quality_claim") is True for item in eligible
        ),
        "metrics": metrics,
        "stop_quality": {
            "assessed_cases": len(stop_assessed),
            "premature_stop_cases": sum(
                item.get("premature_stop") is True for item in stop_assessed
            ),
            "unnecessary_continuation_cases": sum(
                item.get("unnecessary_continuation") is True for item in stop_assessed
            ),
        },
        "trajectory": trajectory_summary,
        "overall_score": None,
        "notes": [
            "Confidence intervals are Wilson intervals over pooled binary denominators.",
            "Trajectory summaries describe efficiency only; they are not quality scores.",
            "No overall composite score is emitted.",
        ],
    }
