"""Versioned public artifacts and tool inputs for filing-only autonomous
research."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Json = dict[str, Any]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,254}$")]
Text = Annotated[str, Field(min_length=1, max_length=4000)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResearchRequest(Contract):
    company_query: Annotated[str, Field(min_length=1, max_length=200)]
    market_hint: Literal["CN", "US", "HK"] | None = None
    requested_period_label: Annotated[str | None, Field(max_length=16)] = None
    research_question: Text
    research_time: datetime
    idempotency_key: Annotated[str, Field(min_length=8, max_length=256)]

    @model_validator(mode="after")
    def validate_boundary(self) -> ResearchRequest:
        if self.research_time.tzinfo is None:
            raise ValueError("research_time must include a timezone")
        if not self.company_query.strip() or not self.research_question.strip():
            raise ValueError("company and question must not be blank")
        return self


class SearchInput(Contract):
    query: Annotated[str, Field(min_length=1, max_length=500)]
    kind: Literal["all", "page", "section", "table", "figure", "footnote", "evidence"] = "all"
    document_id: Identifier | None = None
    offset: Annotated[int, Field(ge=0, le=10000)] = 0
    limit: Annotated[int, Field(ge=1, le=12)] = 6


class ReadInput(Contract):
    artifact_id: Identifier
    offset: Annotated[int, Field(ge=0, le=10_000_000)] = 0
    max_chars: Annotated[int, Field(ge=100, le=18000)] = 10000


class ImageInput(Contract):
    page_id: Identifier


class FactsInput(Contract):
    metrics: Annotated[list[str], Field(max_length=24)] = []
    period_labels: Annotated[list[str], Field(max_length=12)] = []


class CalculateInput(Contract):
    formula: Literal[
        "growth_rate", "absolute_change", "gross_profit", "gross_margin", "cash_conversion"
    ]
    fact_ids: Annotated[list[Identifier], Field(min_length=2, max_length=2)]


class SeriesExtractInput(Contract):
    artifact_id: Identifier
    row_label: Annotated[str, Field(min_length=1, max_length=180)]
    metric_code: Literal[
        "revenue",
        "capital_expenditures",
        "net_income",
        "operating_cash_flow",
        "total_assets",
        "fixed_assets",
        "accounts_receivable",
        "inventory",
    ]

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_page_id(cls, value: Any) -> Any:
        """Accept the pre-table contract while advertising only the current artifact contract."""
        if not isinstance(value, dict) or "artifact_id" in value or "page_id" not in value:
            return value
        migrated = dict(value)
        migrated["artifact_id"] = migrated.pop("page_id")
        return migrated


class SeriesCalculateInput(Contract):
    formula: Literal[
        "ratio_percent",
        "average_ratio_percent",
        "flow_to_average_balance_percent",
        "average_balance_to_flow_percent",
        "average",
        "sum",
    ]
    series_ids: Annotated[list[Identifier], Field(min_length=1, max_length=2)]
    round_decimals: Annotated[int, Field(ge=0, le=6)] = 4
    period_label: Annotated[str | None, Field(max_length=16)] = None


class CounterInput(Contract):
    hypothesis: Annotated[str, Field(min_length=1, max_length=1000)]
    query: Annotated[str, Field(min_length=1, max_length=500)]


class Hypothesis(Contract):
    hypothesis_id: Identifier
    statement: Text
    status: Literal["investigating", "supported", "mixed", "rejected", "unresolved"]
    materiality: Literal["major", "minor"]
    evidence_for: Annotated[list[Identifier], Field(max_length=30)] = []
    evidence_against: Annotated[list[Identifier], Field(max_length=30)] = []
    unknowns: Annotated[list[Text], Field(max_length=10)] = []
    would_change_conclusion: Annotated[str, Field(max_length=2000)] = ""
    confidence: Literal["high", "medium", "low"]


class OpenQuestion(Contract):
    question_id: Identifier
    question: Text
    priority: Literal["high", "medium", "low"]
    status: Literal["open", "answered", "not_answerable_from_filings"]
    evidence_ids: Annotated[list[Identifier], Field(max_length=30)] = []
    explanation: Annotated[str, Field(max_length=2000)] = ""


class ResearchObjective(Contract):
    objective_id: Identifier
    question: Text
    priority: Literal["required", "supporting"]
    status: Literal["open", "answered", "limited"]
    evidence_ids: Annotated[list[Identifier], Field(max_length=30)] = []
    conclusion: Annotated[str, Field(max_length=2400)] = ""
    remaining_uncertainty: Annotated[str, Field(max_length=1600)] = ""


class WorkingState(Contract):
    objectives: Annotated[list[ResearchObjective], Field(max_length=8)] = []
    hypotheses: Annotated[list[Hypothesis], Field(max_length=16)] = []
    open_questions: Annotated[list[OpenQuestion], Field(max_length=20)] = []
    decision_summary: Annotated[str, Field(max_length=1200)] = ""
    core_question_status: Literal["investigating", "answerable", "evidence_exhausted"] = (
        "investigating"
    )
    expected_value_of_more_research: Literal["high", "medium", "low"] = "high"


class Submission(Contract):
    stop_reason: Literal["sufficient_evidence", "evidence_exhausted"]
    direct_answer: Literal["yes", "no", "mixed", "cannot_determine", "not_applicable"] = (
        "not_applicable"
    )
    summary: Text
    evidence_ids: Annotated[list[Identifier], Field(min_length=1, max_length=40)]
    remaining_uncertainties: Annotated[list[Text], Field(max_length=20)]
    why_stop: Text


class NumericAssertion(Contract):
    source_id: Identifier
    value: Annotated[str, Field(min_length=1, max_length=100)]


class Finding(Contract):
    claim_id: Identifier
    title: Annotated[str, Field(min_length=1, max_length=160)]
    text: Text
    kind: Literal["observation", "inference", "risk", "limitation"]
    evidence_ids: Annotated[list[Identifier], Field(min_length=1, max_length=20)]
    fact_ids: Annotated[list[Identifier], Field(max_length=20)]
    calculation_ids: Annotated[list[Identifier], Field(max_length=20)]
    numeric_assertions: Annotated[list[NumericAssertion], Field(max_length=20)]
    confidence: Literal["high", "medium", "low"]
    uncertainty: Annotated[str, Field(max_length=2000)]


class AnalysisSection(Contract):
    title: Annotated[str, Field(min_length=1, max_length=160)]
    text: Text
    evidence_ids: Annotated[list[Identifier], Field(min_length=1, max_length=30)]


class ResearchReport(Contract):
    schema_version: Literal["2.0.0"] = "2.0.0"
    direct_answer: Literal["yes", "no", "mixed", "cannot_determine", "not_applicable"] = (
        "not_applicable"
    )
    title: Annotated[str, Field(min_length=1, max_length=200)]
    executive_summary: Text
    findings: Annotated[list[Finding], Field(min_length=1, max_length=16)]
    sections: Annotated[list[AnalysisSection], Field(min_length=1, max_length=12)]
    limitations: Annotated[list[Text], Field(min_length=1, max_length=24)]
    follow_up_questions: Annotated[list[Text], Field(max_length=6)]


class ClaimReview(Contract):
    claim_id: Identifier
    verdict: Literal["supported", "partial", "unsupported", "contradicted", "unverifiable"]
    reason: Annotated[str, Field(min_length=1, max_length=1200)]


class ReviewSummary(Contract):
    question_answered: bool
    missing_material_topics: Annotated[list[Text], Field(max_length=10)]


class SemanticReview(Contract):
    claims: Annotated[list[ClaimReview], Field(min_length=1, max_length=16)]
    question_answered: bool
    missing_material_topics: Annotated[list[Text], Field(max_length=10)]


class TraceEvent(Contract):
    schema_version: Literal["2.0.0"] = "2.0.0"
    run_id: Identifier
    sequence: int
    event_type: str
    timestamp: str
    span_id: str | None = None
    parent_span_id: str | None = None
    name: str
    label: str
    status: str
    duration_ms: int | None = None
    data: Json = Field(default_factory=dict)


def strict_schema(model: type[BaseModel]) -> Json:
    """Responses strict schemas require all object properties, including
    nullable fields."""
    schema = model.model_json_schema()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            value.pop("default", None)
            if value.get("type") == "object" and "properties" in value:
                value["additionalProperties"] = False
                value["required"] = list(value["properties"])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(schema)
    return schema
