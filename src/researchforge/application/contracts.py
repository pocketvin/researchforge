"""Typed process-boundary contracts for research runs."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TaskType = Literal[
    "company_research",
    "filing_analysis",
    "peer_comparison",
    "thesis_investigation",
    "risk_detection",
]


class ResearchRunRequest(BaseModel):
    """Immutable public input accepted by the CLI and HTTP API."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_type: TaskType
    research_question: Annotated[str, Field(min_length=1, max_length=4000)]
    company_ids: Annotated[list[str], Field(min_length=1, max_length=2)]
    requested_period_labels: Annotated[list[str], Field(min_length=1, max_length=12)]
    research_time: datetime
    idempotency_key: Annotated[str, Field(min_length=8, max_length=256)]

    @model_validator(mode="after")
    def validate_company_count(self) -> ResearchRunRequest:
        """Apply the public one-company/two-company task rule before queueing."""
        unique_companies = set(self.company_ids)
        if len(unique_companies) != len(self.company_ids):
            raise ValueError("company_ids must be unique")
        if self.task_type == "peer_comparison" and len(self.company_ids) != 2:
            raise ValueError("peer_comparison requires exactly two companies")
        if self.task_type != "peer_comparison" and len(self.company_ids) != 1:
            raise ValueError("this task type requires exactly one company")
        if len(set(self.requested_period_labels)) != len(self.requested_period_labels):
            raise ValueError("requested_period_labels must be unique")
        if self.research_time.tzinfo is None:
            raise ValueError("research_time must include a timezone")
        return self


class RunLinks(BaseModel):
    """Stable links returned by run creation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str
    result: str
    trace: str


class RunSubmission(BaseModel):
    """HTTP/CLI submission response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    lifecycle_state: str
    created: bool
    links: RunLinks


class CatalogCompany(BaseModel):
    """One unambiguous company in the frozen L1 catalog."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    company_id: str
    legal_name: str
    ticker: str
    exchange: str
    country_code: str
    period_labels: list[str]


class CatalogResponse(BaseModel):
    """Current bounded product capabilities."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.4.0"] = "1.4.0"
    companies: list[CatalogCompany]
    supported_task_types: list[TaskType]
    implementation_level: Literal["G1_THIN", "G1_BREADTH"] = "G1_BREADTH"
    limitations: list[str]
