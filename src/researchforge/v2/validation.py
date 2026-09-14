# ruff: noqa: RUF001 -- Chinese product text intentionally uses Chinese punctuation.
"""Hard reference/numeric checks are separate from a fallible semantic model review."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from researchforge.v2.contracts import Json, ResearchReport, SemanticReview
from researchforge.v2.numeric_provenance import unsupported_percentages
from researchforge.v2.tools import FilingTools, _analytical_question, binary_question

_INTERNAL_PROSE_ID_RE = re.compile(
    r"\b(?:view|page|table|series|calc|fact|doc|run)_[A-Za-z0-9_.:-]+\b",
    re.IGNORECASE,
)
_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_SNAKE_CASE_RE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
_GLOBAL_ABSENCE_RE = re.compile(
    r"(?:"
    r"\b(?:the|this)\s+(?:filing|annual report)\b[^.!?]{0,40}\b(?:contains|provides|has)\s+no\b"
    r"|\b(?:the|this)\s+(?:filing|annual report)\b[^.!?]{0,40}\bdoes\s+not\s+(?:explicitly\s+)?(?:contain|provide|disclose|report|present|show|include|state|label|quantify|establish|attribute|rank)\b"
    r"|\bit\s+(?:contains|provides|has)\s+no\s+(?:peer|industry|benchmark|threshold|capital expenditure|capex|net pp&e|property|classification)\b"
    r"|(?:该|本|整份)?(?:财报|年报|报告)(?:中)?(?:没有|不存在|不含|未披露|未提供|未报告|未显示)"
    r")",
    re.IGNORECASE,
)

_INTERNAL_PROSE_TERMS = (
    "formula registry",
    "verified statement series",
    "verified_statement_series",
    "calculationrecord",
    "calculation record",
    "safe report",
    "安全报告",
    "frozen bundle",
    "held-out bundle",
    "heldout bundle",
    "run-owned",
    "html extraction",
    "html 表格提取",
    "native html marked unverified",
)


def _presentation_texts(report: ResearchReport) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = [
        ("title", report.title),
        ("executive_summary", report.executive_summary),
    ]
    for finding in report.findings:
        items.extend(
            [
                (f"{finding.claim_id}.title", finding.title),
                (f"{finding.claim_id}.text", finding.text),
                (f"{finding.claim_id}.uncertainty", finding.uncertainty),
            ]
        )
    for index, section in enumerate(report.sections, start=1):
        items.extend(
            [
                (f"section[{index}].title", section.title),
                (f"section[{index}].text", section.text),
            ]
        )
    items.extend(
        (f"limitation[{index}]", text) for index, text in enumerate(report.limitations, start=1)
    )
    items.extend(
        (f"follow_up_question[{index}]", text)
        for index, text in enumerate(report.follow_up_questions, start=1)
    )
    return items


def _presentation_errors(
    report: ResearchReport, *, analytical: bool, question: str = ""
) -> list[str]:
    errors: list[str] = []
    presentation_items = _presentation_texts(report)
    question_has_cjk = bool(_CJK_RE.search(question))
    report_has_cjk = any(_CJK_RE.search(text) for _label, text in presentation_items)
    if question and question_has_cjk and not report_has_cjk:
        errors.append(
            "REPORT_LANGUAGE_MISMATCH: Chinese question requires Chinese user-facing prose"
        )
    if question and not question_has_cjk:
        cjk_labels = [label for label, text in presentation_items if _CJK_RE.search(text)]
        if cjk_labels:
            errors.append(
                "REPORT_LANGUAGE_MISMATCH: English question contains Chinese user-facing prose in "
                + ", ".join(cjk_labels[:8])
            )
    for label, text in presentation_items:
        leaked_ids = sorted(set(_INTERNAL_PROSE_ID_RE.findall(text)))
        if leaked_ids:
            errors.append(f"{label}: INTERNAL_IDENTIFIER_IN_USER_PROSE: {', '.join(leaked_ids)}")
        snake_case_terms = sorted(set(_SNAKE_CASE_RE.findall(text)))
        if snake_case_terms:
            errors.append(
                f"{label}: INTERNAL_SNAKE_CASE_IN_USER_PROSE: " + ", ".join(snake_case_terms)
            )
        lowered = text.casefold()
        if _GLOBAL_ABSENCE_RE.search(text):
            errors.append(
                f"{label}: GLOBAL_ABSENCE_CLAIM_FROM_NONOBSERVATION: "
                "state the boundary as what the cited evidence does not establish; do not turn "
                "non-observation into a filing-wide nonexistence claim"
            )
        leaked_terms = [term for term in _INTERNAL_PROSE_TERMS if term.casefold() in lowered]
        if leaked_terms:
            errors.append(
                f"{label}: INTERNAL_IMPLEMENTATION_TERM_IN_USER_PROSE: " + ", ".join(leaked_terms)
            )
    if not analytical and len(report.executive_summary) > 1000:
        errors.append(
            "FOCUSED_EXECUTIVE_SUMMARY_TOO_LONG: "
            f"{len(report.executive_summary)} characters exceeds 1000"
        )
    if not analytical and len(report.limitations) > 3:
        errors.append(
            f"FOCUSED_REPORT_TOO_MANY_LIMITATIONS: {len(report.limitations)} limitations exceeds 3"
        )
    return errors


def validate_report(report: ResearchReport, tools: FilingTools) -> Json:
    errors: list[str] = []
    warnings: list[str] = []
    allowed = set(tools.dossier["evidence_ids"]) if tools.dossier else set()
    facts, calculations = tools.environment["facts"], tools.calculations
    allowed_evidence = [
        tools.observed[identifier] for identifier in allowed if identifier in tools.observed
    ]
    dossier_direct_answer = (
        str(tools.dossier.get("direct_answer", "not_applicable"))
        if tools.dossier
        else "not_applicable"
    )
    if report.direct_answer != dossier_direct_answer:
        errors.append(
            f"DIRECT_ANSWER_MISMATCH: report={report.direct_answer}; "
            f"research={dossier_direct_answer}"
        )
    if (
        binary_question(tools.request.research_question)
        and report.direct_answer == "not_applicable"
    ):
        errors.append("BINARY_DIRECT_ANSWER_MISSING")
    ids = [finding.claim_id for finding in report.findings]
    if len(ids) != len(set(ids)):
        errors.append("DUPLICATE_CLAIM_ID")
    required_objectives = [
        objective for objective in tools.working.objectives if objective.priority == "required"
    ]
    analytical = _analytical_question(tools.request.research_question)
    focused_scope_limit = max(1, len(required_objectives))
    material_findings = [finding for finding in report.findings if finding.kind != "limitation"]
    if (
        not _analytical_question(tools.request.research_question)
        and len(material_findings) > focused_scope_limit
    ):
        errors.append(
            "FOCUSED_REPORT_SCOPE_EXPANDED: "
            f"{len(material_findings)} material findings exceed {focused_scope_limit} "
            "required objective(s)"
        )
    errors.extend(
        _presentation_errors(
            report, analytical=analytical, question=tools.request.research_question
        )
    )
    references: set[str] = set()
    report_calculation_ids: set[str] = set()
    report_fact_ids: set[str] = set()
    assertion_count = 0
    unsupported_percentage_count = 0

    def check_percentages(
        label: str,
        text: str,
        *,
        declared_calculations: list[Json],
        declared_facts: list[Json],
        evidence: list[Json],
    ) -> None:
        nonlocal unsupported_percentage_count
        local_missing = unsupported_percentages(
            text,
            calculations=declared_calculations,
            facts=declared_facts,
            evidence=evidence,
        )
        if not local_missing:
            return
        globally_missing = set(
            unsupported_percentages(
                text,
                calculations=list(calculations.values()),
                facts=list(facts.values()),
                evidence=allowed_evidence,
            )
        )
        unsupported_percentage_count += len(local_missing)
        for percentage in sorted(set(local_missing)):
            code = (
                "DERIVED_PERCENTAGE_WITHOUT_CALCULATION"
                if percentage in globally_missing
                else "PERCENTAGE_PROVENANCE_NOT_LINKED"
            )
            errors.append(f"{label}: {code}: {percentage}")

    for finding in report.findings:
        references.update(finding.evidence_ids)
        report_calculation_ids.update(finding.calculation_ids)
        report_fact_ids.update(finding.fact_ids)
        if not set(finding.fact_ids) <= set(facts):
            errors.append(f"{finding.claim_id}: UNKNOWN_FACT")
        if not set(finding.calculation_ids) <= set(calculations):
            errors.append(f"{finding.claim_id}: UNKNOWN_CALCULATION")
        for assertion in finding.numeric_assertions:
            assertion_count += 1
            if assertion.source_id not in set(finding.fact_ids + finding.calculation_ids):
                errors.append(f"{finding.claim_id}: NUMERIC_ASSERTION_NOT_LINKED")
                continue
            source = facts.get(assertion.source_id) or calculations.get(assertion.source_id)
            try:
                value = Decimal(assertion.value)
                if source is None or source.get("value") is None or not value.is_finite():
                    raise InvalidOperation
                if value != Decimal(str(source["value"])):
                    errors.append(f"{finding.claim_id}: NUMERIC_ASSERTION_MISMATCH")
            except InvalidOperation:
                errors.append(f"{finding.claim_id}: INVALID_NUMERIC_ASSERTION")
        check_percentages(
            finding.claim_id,
            finding.title + "\n" + finding.text,
            declared_calculations=[
                calculations[identifier]
                for identifier in finding.calculation_ids
                if identifier in calculations
            ],
            declared_facts=[
                facts[identifier] for identifier in finding.fact_ids if identifier in facts
            ],
            evidence=[
                tools.observed[identifier]
                for identifier in finding.evidence_ids
                if identifier in tools.observed
            ],
        )
        if finding.kind == "inference" and not finding.uncertainty.strip():
            warnings.append(f"{finding.claim_id}: 推断未说明不确定性，请结合语义复核。")
    for section in report.sections:
        references.update(section.evidence_ids)

    global_calculations = [
        calculations[identifier]
        for identifier in report_calculation_ids
        if identifier in calculations
    ]
    global_facts = [facts[identifier] for identifier in report_fact_ids if identifier in facts]
    global_evidence = [
        tools.observed[identifier] for identifier in references if identifier in tools.observed
    ]
    check_percentages(
        "executive_summary",
        report.executive_summary,
        declared_calculations=global_calculations,
        declared_facts=global_facts,
        evidence=global_evidence,
    )
    for section in report.sections:
        check_percentages(
            f"section:{section.title}",
            section.text,
            declared_calculations=global_calculations,
            declared_facts=global_facts,
            evidence=global_evidence,
        )

    if not references <= allowed:
        errors.append("CITATION_OUTSIDE_SYNTHESIS_CONTEXT")
    for identifier in references & set(tools.observed):
        evidence = tools.observed[identifier]
        source = tools.environment["documents"].get(evidence["document_id"])
        if (
            source is None
            or source["company"]["company_id"] != tools.environment["entity"]["company_id"]
        ):
            errors.append(f"{identifier}: SOURCE_ENTITY_MISMATCH")
        if datetime.fromisoformat(evidence["published_at"]) > tools.request.research_time:
            errors.append(f"{identifier}: SOURCE_AFTER_CUTOFF")
    return {
        "schema_version": "2.0.0",
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "checks": {
            "structured_output": True,
            "claim_ids_unique": len(ids) == len(set(ids)),
            "citation_references": references <= allowed,
            "declared_numeric_assertions_checked": assertion_count,
            "unsupported_percentage_mentions": unsupported_percentage_count,
            "focused_material_findings": len(material_findings),
            "focused_scope_limit": focused_scope_limit,
        },
        "boundary": (
            "Checks verify declared references and deterministic numeric provenance; "
            "semantic truth still requires separate review."
        ),
    }


def validate_review(report: ResearchReport, review: SemanticReview) -> list[str]:
    expected = {finding.claim_id for finding in report.findings}
    observed = [item.claim_id for item in review.claims]
    if set(observed) != expected or len(observed) != len(expected):
        return ["SEMANTIC_REVIEW_CLAIM_SET_INVALID"]
    errors = [
        f"{item.claim_id}: {item.verdict}: {item.reason}"
        for item in review.claims
        if item.verdict != "supported"
    ]
    if not review.question_answered:
        errors.append("语义复核认为核心问题未得到回应。")
    return errors
