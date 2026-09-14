"""Real LangGraph, storage, API and tools with explicit synthetic transport ports."""

from __future__ import annotations

import contextlib
import inspect
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from researchforge.adapters.storage import payload_sha256
from researchforge.v2.api import build_router
from researchforge.v2.contracts import (
    ResearchReport,
    ResearchRequest,
    SemanticReview,
    WorkingState,
)
from researchforge.v2.preparation import FilingPreparer
from researchforge.v2.runtime import ResearchService
from researchforge.v2.storage import ResearchRepository


def test_request(key: str) -> ResearchRequest:
    return ResearchRequest(
        company_query="Synthetic Company",
        market_hint="CN",
        requested_period_label="2025FY",
        research_question="Why did operating cash flow fall?",
        research_time=datetime.fromisoformat("2026-09-01T00:00:00+00:00"),
        idempotency_key=key,
    )


def test_environment() -> dict[str, Any]:
    company = {
        "company_id": "cn_000001",
        "legal_name": "Synthetic Company",
        "ticker": "000001",
        "exchange": "SZSE",
        "country_code": "CN",
    }
    source = {
        "document_id": "doc_synthetic",
        "company": company,
        "title": "Synthetic filing",
        "source_uri": "https://static.cninfo.com.cn/synthetic-test-only.pdf",
        "content_hash": "a" * 64,
        "published_at": "2026-04-01T00:00:00+00:00",
        "retrieved_at": "2026-09-01T00:00:00+00:00",
        "mime_type": "application/pdf",
        "period_label": "2025FY",
        "document_type": "annual_report",
        "reporting_period": {
            "fiscal_year": 2025,
            "fiscal_period": "FY",
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "period_basis": "ytd",
        },
    }
    text = "The synthetic company states: operating cash flow fell as collections slowed."
    common = {
        "document_id": source["document_id"],
        "published_at": source["published_at"],
        "company_id": company["company_id"],
        "content_role": "untrusted_source",
        "source_uri": source["source_uri"],
        "text": text,
        "text_hash": payload_sha256(text),
    }
    objects = {
        "doc_synthetic": {
            **common,
            "artifact_id": "doc_synthetic",
            "kind": "document",
            "title": source["title"],
        },
        "page_synthetic": {
            **common,
            "artifact_id": "page_synthetic",
            "kind": "page",
            "page_number": 1,
            "page_id": "page_synthetic",
            "table_ids": [],
            "figure_ids": [],
            "footnote_ids": [],
        },
        "evidence_synthetic": {
            **common,
            "artifact_id": "evidence_synthetic",
            "kind": "evidence",
            "page_number": 1,
            "page_id": "page_synthetic",
            "char_start": 0,
            "char_end": len(text),
        },
    }
    return {
        "schema_version": "2.0.0",
        "entity": company,
        "documents": {source["document_id"]: source},
        "objects": objects,
        "facts": {},
        "gaps": ["Synthetic test input, no financial truth claim."],
    }


# Helpers are not tests: explicit naming avoids accidental fixture collection.
test_request.__test__ = False
test_environment.__test__ = False


@pytest.fixture(autouse=True)
def offline_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep live source/model access out of a controlled runtime-contract test."""
    monkeypatch.setattr(FilingPreparer, "prepare", lambda *args, **kwargs: test_environment())


def observation_ids(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            found.extend(observation_ids(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            found.extend(observation_ids(item))
    elif isinstance(value, str):
        if value.startswith("view_") and all(char.isalnum() or char in "_.:-" for char in value):
            found.append(value)
        elif value.startswith(("{", "[")):
            with contextlib.suppress(json.JSONDecodeError):
                found.extend(observation_ids(json.loads(value)))
    return list(dict.fromkeys(found))


class ScriptedTestModel:
    """A test-only provider port; product code never chooses this class."""

    def __init__(self, reject_once: bool = False) -> None:
        self.turn = 0
        self.evidence_id = ""
        self.reviews = 0
        self.reject_once = reject_once
        self.hidden_marker = "PRIVATE_REASONING_MUST_NOT_BE_PERSISTED_93821"

    @property
    def usage(self) -> dict[str, Any]:
        return {
            "provider_calls": 0,
            "estimated_cost": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "latency_ms": 0,
        }

    def next_action(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        self.turn += 1
        ids = observation_ids([args, kwargs])
        if ids:
            self.evidence_id = ids[-1]
        if self.turn == 1:
            name, arguments = (
                "search_filing",
                {
                    "query": "cash flow",
                    "kind": "evidence",
                    "document_id": None,
                    "offset": 0,
                    "limit": 6,
                },
            )
        elif self.turn == 2:
            name, arguments = (
                "read_filing",
                {"artifact_id": "page_synthetic", "offset": 0, "max_chars": 1000},
            )
        elif self.turn == 3:
            name, arguments = (
                "search_counter_evidence",
                {
                    "hypothesis": "Collections explain the cash-flow decline.",
                    "query": "cash flow decline other reasons collections",
                },
            )
        elif self.turn == 4:
            name, arguments = (
                "update_research_state",
                {
                    "objectives": [
                        {
                            "objective_id": "obj_test",
                            "question": "Explain operating cash-flow movement.",
                            "priority": "required",
                            "status": "answered",
                            "evidence_ids": [self.evidence_id],
                            "conclusion": (
                                "The filing supports the requested cash-flow explanation."
                            ),
                            "remaining_uncertainty": "",
                        }
                    ],
                    "hypotheses": [
                        {
                            "hypothesis_id": "h_test",
                            "statement": "Collections slowed cash flow.",
                            "status": "supported",
                            "materiality": "major",
                            "evidence_for": [self.evidence_id],
                            "evidence_against": [],
                            "unknowns": [],
                            "would_change_conclusion": "A restated filing.",
                            "confidence": "medium",
                        }
                    ],
                    "open_questions": [],
                    "decision_summary": (
                        "Read the stated explanation and searched for alternatives."
                    ),
                    "core_question_status": "answerable",
                    "expected_value_of_more_research": "low",
                },
            )
        else:
            name, arguments = (
                "submit_research",
                {
                    "stop_reason": "sufficient_evidence",
                    "summary": "Cash flow fell.",
                    "evidence_ids": [self.evidence_id],
                    "remaining_uncertainties": [],
                    "why_stop": "The cited synthetic filing explicitly explains the change.",
                },
            )
        return [{"call_id": f"test_call_{self.turn}", "name": name, "arguments": arguments}]

    def synthesize(self, *args: Any, **kwargs: Any) -> ResearchReport:
        return ResearchReport.model_validate(
            {
                "schema_version": "2.0.0",
                "title": "Synthetic integration report",
                "executive_summary": "Cash flow fell as collections slowed.",
                "findings": [
                    {
                        "claim_id": "claim_test",
                        "title": "Collections slowed",
                        "text": (
                            "The synthetic filing reports slower collection and lower cash flow."
                        ),
                        "kind": "observation",
                        "evidence_ids": [self.evidence_id],
                        "fact_ids": [],
                        "calculation_ids": [],
                        "numeric_assertions": [],
                        "confidence": "medium",
                        "uncertainty": "Synthetic test input only.",
                    }
                ],
                "sections": [
                    {
                        "title": "Cash flow",
                        "text": "Collections slowed.",
                        "evidence_ids": [self.evidence_id],
                    }
                ],
                "limitations": ["SYNTHETIC TEST, NOT REAL RESEARCH QUALITY EVIDENCE."],
                "follow_up_questions": [],
            }
        )

    def review(self, *args: Any, **kwargs: Any) -> SemanticReview:
        self.reviews += 1
        return SemanticReview.model_validate(
            {
                "claims": [
                    {
                        "claim_id": "claim_test",
                        "verdict": "unsupported"
                        if self.reject_once and self.reviews == 1
                        else "supported",
                        "reason": "Synthetic test reviewer response.",
                    }
                ],
                "question_answered": True,
                "missing_material_topics": [],
            }
        )


def make_service(root: Path, model: ScriptedTestModel) -> ResearchService:
    repository = ResearchRepository(root)
    configuration = {
        "data_namespace": "synthetic_test",
        "timeout_seconds": 30,
        "model": "synthetic-port-only",
        "max_agent_turns": 128,
        "max_documents": 6,
        "run_budget_usd": "0.35",
    }
    parameters = inspect.signature(ResearchService).parameters
    values: dict[str, Any] = {
        "repository": repository,
        "model_factory": lambda *args, **kwargs: model,
        "configuration": configuration,
        "config": configuration,
        "prepare": lambda *args, **kwargs: test_environment(),
    }
    # Supports both an optional injected preparation function and the official
    # preparer (patched above). Unknown required constructor fields still fail.
    kwargs = {name: values[name] for name in parameters if name in values}
    return ResearchService(**kwargs)


def submit(service: ResearchService, key: str) -> dict[str, Any]:
    submitted = service.submit(test_request(key))
    return submitted[0] if isinstance(submitted, tuple) else submitted


def execute(service: ResearchService, run_id: str) -> dict[str, Any]:
    service.execute(run_id)
    return service.repository.get(run_id)


class StateRefreshScriptedModel(ScriptedTestModel):
    def __init__(self) -> None:
        super().__init__()
        self.state_refreshes = 0

    def reflect(self, bootstrap: Any, public_state: Any, observations: Any) -> WorkingState:
        self.state_refreshes += 1
        ids = observation_ids([bootstrap, public_state, observations])
        if ids:
            self.evidence_id = ids[-1]
        evidence_ids = [self.evidence_id] if self.evidence_id else []
        mature = self.state_refreshes >= 2
        return WorkingState.model_validate(
            {
                "objectives": [
                    {
                        "objective_id": "obj_test",
                        "question": "Explain operating cash-flow movement.",
                        "priority": "required",
                        "status": "answered" if mature else "open",
                        "evidence_ids": evidence_ids,
                        "conclusion": (
                            "The filing attributes the movement to slower collections."
                            if mature
                            else ""
                        ),
                        "remaining_uncertainty": ""
                        if mature
                        else "More filing evidence is needed.",
                    }
                ],
                "hypotheses": [
                    {
                        "hypothesis_id": "h_test",
                        "statement": "Slower collections explain the cash-flow movement.",
                        "status": "supported" if mature else "investigating",
                        "materiality": "major",
                        "evidence_for": evidence_ids,
                        "evidence_against": [],
                        "unknowns": [] if mature else ["Need targeted evidence."],
                        "would_change_conclusion": "A contradictory filing explanation.",
                        "confidence": "medium" if mature else "low",
                    }
                ],
                "open_questions": [],
                "decision_summary": "Synthetic Runtime-owned public-state reflection.",
                "core_question_status": "answerable" if mature else "investigating",
                "expected_value_of_more_research": "low" if mature else "medium",
            }
        )

    def next_action(self, bootstrap: Any, state: Any, observations: Any) -> list[dict[str, Any]]:
        ids = observation_ids([bootstrap, state, observations])
        if ids:
            self.evidence_id = ids[-1]
        required = state.get("completeness", {}).get("required_before_submit", [])
        self.turn += 1
        if required == ["search_counter_evidence"]:
            return [
                {
                    "call_id": f"counter_{self.turn}",
                    "name": "search_counter_evidence",
                    "arguments": {
                        "hypothesis": "Slower collections explain the cash-flow movement.",
                        "query": "cash flow other causes collections",
                    },
                }
            ]
        if required == ["submit_research"]:
            return [
                {
                    "call_id": f"submit_{self.turn}",
                    "name": "submit_research",
                    "arguments": {
                        "stop_reason": "sufficient_evidence",
                        "summary": "Cash flow fell as collections slowed.",
                        "evidence_ids": [self.evidence_id],
                        "remaining_uncertainties": [],
                        "why_stop": "Required objective and counter-evidence step are complete.",
                    },
                }
            ]
        return [
            {
                "call_id": f"search_{self.turn}",
                "name": "search_filing",
                "arguments": {
                    "query": "cash flow collections",
                    "kind": "evidence",
                    "document_id": None,
                    "offset": 0,
                    "limit": 6,
                },
            }
        ]


def test_runtime_requests_state_refresh_after_new_analytical_evidence(
    tmp_path: Path,
) -> None:
    model = StateRefreshScriptedModel()
    service = make_service(tmp_path, model)
    manifest = submit(service, "runtime-semantic-state-refresh")
    finished = execute(service, manifest["run_id"])
    assert finished["lifecycle_state"] == "succeeded", finished.get("failure")
    assert model.state_refreshes >= 1
    events = service.repository.events(manifest["run_id"])
    checks = [event for event in events if event["event_type"] == "reflection_check"]
    assert any(
        event["data"]["needed"] is True and event["data"]["reason"] == "first_analytical_evidence"
        for event in checks
    )
    assert any(event["event_type"] == "research_state_refresh_requested" for event in events)


def test_graph_research_observe_submit_and_persist(tmp_path: Path) -> None:
    model = ScriptedTestModel()
    service = make_service(tmp_path, model)
    manifest = submit(service, "runtime-integration")
    finished = execute(service, manifest["run_id"])
    assert finished["lifecycle_state"] == "succeeded", finished.get("failure")
    assert model.turn == 5
    result = service.repository.artifact(manifest["run_id"], "result")
    assert result["validation"]["passed"] is True
    assert result["independent_quality_score"] is None
    events = service.repository.events(manifest["run_id"])
    assert len([event for event in events if event["event_type"] == "tool_result"]) == 5
    assert events[-1]["event_type"] == "run_completed"
    assert model.hidden_marker not in json.dumps([finished, result, events])
    assert execute(service, manifest["run_id"]) == finished


def test_semantic_rejection_repairs_report_without_research_replay(tmp_path: Path) -> None:
    model = ScriptedTestModel(reject_once=True)
    service = make_service(tmp_path, model)
    manifest = submit(service, "semantic-report-repair")
    finished = execute(service, manifest["run_id"])
    assert finished["lifecycle_state"] == "succeeded", finished.get("failure")
    assert model.reviews == 2 and model.turn == 5
    events = service.repository.events(manifest["run_id"])
    assert any(event["event_type"] == "report_repair_requested" for event in events)
    assert not any(event["event_type"] == "validation_feedback" for event in events)


def test_synthesis_only_derived_percentage_is_repaired_without_research_replay(
    tmp_path: Path,
) -> None:
    class PercentageRepairModel(ScriptedTestModel):
        def __init__(self) -> None:
            super().__init__()
            self.drafts = 0

        def synthesize(self, *args: Any, **kwargs: Any) -> ResearchReport:
            self.drafts += 1
            report = super().synthesize(*args, **kwargs)
            if self.drafts == 1:
                payload = report.model_dump(mode="json")
                payload["executive_summary"] += " An unsupported derived threshold is 10%."
                payload["findings"][0]["text"] += " An unsupported derived threshold is 10%."
                payload["sections"][0]["text"] += " Unsupported threshold: 10%."
                return ResearchReport.model_validate(payload)
            return report

    model = PercentageRepairModel()
    service = make_service(tmp_path, model)
    manifest = submit(service, "synthesis-percentage-report-repair")
    finished = execute(service, manifest["run_id"])
    assert finished["lifecycle_state"] == "succeeded", finished.get("failure")
    assert model.turn == 5
    assert model.drafts == 2
    events = service.repository.events(manifest["run_id"])
    repair_events = [event for event in events if event["event_type"] == "report_repair_requested"]
    assert len(repair_events) == 1
    assert any(
        "DERIVED_PERCENTAGE_WITHOUT_CALCULATION" in issue
        for issue in repair_events[0]["data"]["issues"]
    )
    assert not any(event["event_type"] == "validation_feedback" for event in events)


def test_exhausted_report_repair_uses_safe_dossier_without_replaying_research(
    tmp_path: Path,
) -> None:
    class AlwaysInvalidReportModel(ScriptedTestModel):
        def __init__(self) -> None:
            super().__init__()
            self.drafts = 0

        def synthesize(self, *args: Any, **kwargs: Any) -> ResearchReport:
            self.drafts += 1
            report = super().synthesize(*args, **kwargs)
            payload = report.model_dump(mode="json")
            threshold = 9 + self.drafts
            payload["executive_summary"] += f" Writer-invented threshold: {threshold}%."
            payload["findings"][0]["text"] += f" Writer-invented threshold: {threshold}%."
            return ResearchReport.model_validate(payload)

        def review(self, context: dict[str, Any], report: ResearchReport) -> SemanticReview:
            self.reviews += 1
            return SemanticReview.model_validate(
                {
                    "claims": [
                        {
                            "claim_id": finding.claim_id,
                            "verdict": "supported",
                            "reason": (
                                "Safe dossier claim is supported by submitted filing evidence."
                            ),
                        }
                        for finding in report.findings
                    ],
                    "question_answered": True,
                    "missing_material_topics": [],
                }
            )

    model = AlwaysInvalidReportModel()
    service = make_service(tmp_path, model)
    manifest = submit(service, "report-repair-exhaustion")
    finished = execute(service, manifest["run_id"])
    assert finished["lifecycle_state"] == "succeeded", finished.get("failure")
    assert model.turn == 5
    assert model.drafts == 3
    assert model.reviews == 1
    state = service.repository.artifact(manifest["run_id"], "research_state")
    assert state["dossier"] is not None
    result = service.repository.artifact(manifest["run_id"], "result")
    assert result["report"]["findings"][0]["claim_id"].startswith("claim_")
    events = service.repository.events(manifest["run_id"])
    assert sum(event["event_type"] == "report_repair_requested" for event in events) == 2
    assert sum(event["event_type"] == "report_repair_exhausted" for event in events) == 1
    assert sum(event["event_type"] == "safe_report_fallback_used" for event in events) == 1
    assert not any(event["event_type"] == "validation_feedback" for event in events)


def test_material_semantic_gap_returns_to_research_agent(tmp_path: Path) -> None:
    class MaterialGapModel(ScriptedTestModel):
        def next_action(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
            ids = observation_ids([args, kwargs])
            if ids:
                self.evidence_id = ids[-1]
            if self.turn < 5:
                return super().next_action(*args, **kwargs)
            self.turn += 1
            if self.turn == 6:
                return [
                    {
                        "call_id": "material_gap_search",
                        "name": "search_filing",
                        "arguments": {
                            "query": "material missing topic",
                            "kind": "evidence",
                            "document_id": None,
                            "offset": 0,
                            "limit": 6,
                        },
                    }
                ]
            return [
                {
                    "call_id": "material_gap_submit",
                    "name": "submit_research",
                    "arguments": {
                        "stop_reason": "sufficient_evidence",
                        "summary": "The material filing topic has now been checked.",
                        "evidence_ids": [self.evidence_id],
                        "remaining_uncertainties": [],
                        "why_stop": "The additional material topic was researched.",
                    },
                }
            ]

        def review(self, *args: Any, **kwargs: Any) -> SemanticReview:
            self.reviews += 1
            missing = self.reviews == 1
            return SemanticReview.model_validate(
                {
                    "claims": [
                        {
                            "claim_id": "claim_test",
                            "verdict": "supported",
                            "reason": "The local claim is supported by cited filing evidence.",
                        }
                    ],
                    "question_answered": not missing,
                    "missing_material_topics": ["A material filing topic is missing."]
                    if missing
                    else [],
                }
            )

    model = MaterialGapModel()
    service = make_service(tmp_path, model)
    manifest = submit(service, "material-gap-research-return")
    finished = execute(service, manifest["run_id"])
    assert finished["lifecycle_state"] == "succeeded", finished.get("failure")
    assert model.turn == 7
    assert model.reviews == 2
    events = service.repository.events(manifest["run_id"])
    assert sum(event["event_type"] == "validation_feedback" for event in events) == 1
    assert any(
        event["event_type"] == "tool_result" and event["name"] == "search_filing"
        for event in events
    )


def test_provider_failure_keeps_documents_observations_and_trace(tmp_path: Path) -> None:
    class BrokenModel(ScriptedTestModel):
        def next_action(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
            raise RuntimeError("private transport details should not appear")

    service = make_service(tmp_path, BrokenModel())
    manifest = submit(service, "provider-failure-persistence")
    result = execute(service, manifest["run_id"])
    assert result["lifecycle_state"] == "failed"
    assert "private transport details" not in str(result)
    assert service.repository.artifact(manifest["run_id"], "environment")
    assert service.repository.events(manifest["run_id"])[-1]["event_type"] == "run_failed"


def test_cancel_before_start_does_not_invoke_model(tmp_path: Path) -> None:
    model = ScriptedTestModel()
    service = make_service(tmp_path, model)
    manifest = submit(service, "queued-cancel-v2")
    service.cancel(manifest["run_id"])
    assert execute(service, manifest["run_id"])["lifecycle_state"] == "cancelled"
    assert model.turn == 0


def test_api_same_result_replay_source_boundary_and_idempotency(tmp_path: Path) -> None:
    service = make_service(tmp_path, ScriptedTestModel())
    app = FastAPI()
    app.include_router(build_router(service))
    client = TestClient(app)
    payload = test_request("api-v2-integration").model_dump(mode="json")
    response = client.post("/v2/research-runs", json=payload)
    assert response.status_code == 202
    run_id = response.json()["run_id"]
    assert client.get(f"/v2/research-runs/{run_id}").json()["lifecycle_state"] == "succeeded"
    repeated = client.post("/v2/research-runs", json=payload)
    assert repeated.json()["run_id"] == run_id and not repeated.json()["created"]
    report = client.get(f"/v2/research-runs/{run_id}/result").json()
    evidence = report["report"]["findings"][0]["evidence_ids"][0]
    assert client.get(f"/v2/research-runs/{run_id}/sources/{evidence}").status_code == 200
    assert client.get(f"/v2/research-runs/{run_id}/sources/not_in_run").status_code == 404
    assert client.get(f"/v2/research-runs/{run_id}/workspace").json()
    events = client.get(f"/v2/research-runs/{run_id}/trace").json()["events"]
    cursor = events[-2]["sequence"]
    replay = client.get(
        f"/v2/research-runs/{run_id}/events", headers={"Last-Event-ID": str(cursor)}
    )
    assert f"id: {events[-1]['sequence']}" in replay.text
    assert f"id: {cursor}\n" not in replay.text
    assert "event: terminal" in replay.text
    assert client.get(f"/v2/research-runs/{run_id}/events?after=-1").status_code == 422


class ReviewerProtocolRepairScriptedModel(ScriptedTestModel):
    def review(self, *args: Any, **kwargs: Any) -> SemanticReview:
        self.reviews += 1
        claim = {
            "claim_id": "claim_test",
            "verdict": "supported",
            "reason": "Synthetic protocol-repair reviewer response.",
        }
        return SemanticReview.model_validate(
            {
                "claims": [claim, claim] if self.reviews == 1 else [claim],
                "question_answered": True,
                "missing_material_topics": [],
            }
        )


def test_semantic_review_protocol_repair_does_not_rewrite_report_or_research(
    tmp_path: Path,
) -> None:
    model = ReviewerProtocolRepairScriptedModel()
    service = make_service(tmp_path, model)
    manifest = submit(service, "semantic-review-protocol-repair")
    finished = execute(service, manifest["run_id"])
    assert finished["lifecycle_state"] == "succeeded", finished.get("failure")
    assert model.reviews == 2 and model.turn == 5
    events = service.repository.events(manifest["run_id"])
    assert sum(event["event_type"] == "semantic_review_repair_requested" for event in events) == 1
    assert not any(event["event_type"] == "report_repair_requested" for event in events)
    assert not any(event["event_type"] == "validation_feedback" for event in events)
    result = service.repository.artifact(manifest["run_id"], "result")
    assert result["semantic_review"]["protocol_repair_attempts"] == 1
