"""The V1.4 ten-stage LangGraph thin slice."""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal, TypedDict, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from researchforge.application.general_research import (
    EvidenceRetriever,
    QuestionRouter,
    ResearchPlanner,
    follow_up_templates,
)
from researchforge.application.research import (
    ConclusionDraft,
    ConclusionGenerator,
    EarningsQualityAnalysis,
    EarningsQualityAnalyzer,
    GeneralResearchDraft,
    InsufficientDataError,
    LoadedResearchData,
    StructuredOutputError,
)
from researchforge.domain.finance import FORMULA_VERSION

GRAPH_VERSION = "1.0.0"
CHECKPOINT_SCHEMA_VERSION = "1.0.0"
NODE_VERSION = "1.0.0"


class WorkflowInterrupted(RuntimeError):
    """Internal bounded-control signal raised between graph node operations."""

    def __init__(self, terminal_state: str, failure_code: str, stage: str) -> None:
        super().__init__(failure_code)
        self.terminal_state = terminal_state
        self.failure_code = failure_code
        self.stage = stage


@dataclass(frozen=True, slots=True)
class WorkflowControl:
    """Per-invocation cancellation and monotonic timeout controls."""

    should_cancel: Callable[[], bool]
    deadline: float
    monotonic: Callable[[], float]

    def check(self, stage: str) -> None:
        if self.should_cancel():
            raise WorkflowInterrupted("cancelled", "CANCELLED_BY_USER", stage)
        if self.monotonic() >= self.deadline:
            raise WorkflowInterrupted("timed_out", "TIMED_OUT", stage)


_ACTIVE_CONTROL: ContextVar[WorkflowControl | None] = ContextVar(
    "researchforge_workflow_control", default=None
)


class ResearchGraphState(TypedDict, total=False):
    """Typed transient state; persisted artifacts contain IDs and sanitized events."""

    run_id: str
    trace_id: str
    request: dict[str, Any]
    plan: list[dict[str, Any]]
    loaded: LoadedResearchData
    analysis: EarningsQualityAnalysis
    analyses: tuple[EarningsQualityAnalysis, ...]
    conclusion: ConclusionDraft
    conclusions: tuple[ConclusionDraft, ...]
    counter_evidence: dict[str, Any]
    research_intent: dict[str, Any]
    selected_evidence: tuple[dict[str, Any], ...]
    result: dict[str, Any]
    stages: list[dict[str, Any]]
    terminal_state: str
    failure: dict[str, Any] | None
    started_at: str
    repair_attempts: int


@dataclass(frozen=True, slots=True)
class WorkflowOutcome:
    """Persistable artifacts returned by one graph invocation."""

    terminal_state: str
    plan: list[dict[str, Any]]
    calculations: list[dict[str, Any]]
    result: dict[str, Any] | None
    trace: dict[str, Any]
    failure: dict[str, Any] | None


def _default_clock() -> datetime:
    return datetime.now(UTC)


class ResearchWorkflow:
    """Orchestrate plain fixture, formula, conclusion, and assembly services."""

    stage_names = (
        "understanding_question",
        "planning",
        "loading_financial_data",
        "retrieving_evidence",
        "calculating",
        "cross_checking",
        "searching_counter_evidence",
        "forming_conclusion",
        "validating_output",
        "completed",
    )

    def __init__(
        self,
        load_data: Callable[[list[str], list[str], datetime], LoadedResearchData],
        analyzer: EarningsQualityAnalyzer,
        conclusion_generator: ConclusionGenerator,
        *,
        skill_version: str,
        skill_hash: str,
        synthesis_mode: Literal["model", "evidence_summary_fallback"] = "model",
        checkpointer: BaseCheckpointSaver[Any] | None = None,
        clock: Callable[[], datetime] = _default_clock,
    ) -> None:
        self.load_data = load_data
        self.analyzer = analyzer
        self.conclusion_generator = conclusion_generator
        self.question_router = QuestionRouter()
        self.research_planner = ResearchPlanner()
        self.evidence_retriever = EvidenceRetriever()
        self.skill_version = skill_version
        self.skill_hash = skill_hash
        self.synthesis_mode = synthesis_mode
        self.checkpointer = checkpointer
        self.clock = clock
        self._compiled = self._build_graph()

    def _build_graph(self) -> Any:
        builder = StateGraph(ResearchGraphState)
        builder.add_node(
            "understanding_question", self._guarded("understanding_question", self._understand)
        )
        builder.add_node("planning", self._guarded("planning", self._plan))
        builder.add_node(
            "loading_financial_data",
            self._guarded("loading_financial_data", self._load),
        )
        builder.add_node(
            "retrieving_evidence", self._guarded("retrieving_evidence", self._retrieve)
        )
        builder.add_node("calculating", self._guarded("calculating", self._calculate))
        builder.add_node("cross_checking", self._guarded("cross_checking", self._cross_check))
        builder.add_node(
            "searching_counter_evidence",
            self._guarded("searching_counter_evidence", self._counter_evidence),
        )
        builder.add_node(
            "forming_conclusion", self._guarded("forming_conclusion", self._form_conclusion)
        )
        builder.add_node(
            "validating_output", self._guarded("validating_output", self._validate_output)
        )
        builder.add_node("completed", self._guarded("completed", self._complete))
        builder.add_edge(START, "understanding_question")
        builder.add_edge("understanding_question", "planning")
        builder.add_edge("planning", "loading_financial_data")
        builder.add_conditional_edges(
            "loading_financial_data",
            self._route_after_loading,
            {"continue": "retrieving_evidence", "stop": END},
        )
        builder.add_edge("retrieving_evidence", "calculating")
        builder.add_edge("calculating", "cross_checking")
        builder.add_edge("cross_checking", "searching_counter_evidence")
        builder.add_edge("searching_counter_evidence", "forming_conclusion")
        builder.add_conditional_edges(
            "forming_conclusion",
            self._route_after_conclusion,
            {"continue": "validating_output", "stop": END},
        )
        builder.add_edge("validating_output", "completed")
        builder.add_edge("completed", END)
        return builder.compile(checkpointer=self.checkpointer)

    @staticmethod
    def _guarded(
        stage: str,
        node: Callable[[ResearchGraphState], dict[str, Any]],
    ) -> Any:
        def invoke(state: ResearchGraphState) -> dict[str, Any]:
            control = _ACTIVE_CONTROL.get()
            if control is not None:
                control.check(stage)
            output = node(state)
            if control is not None:
                control.check(stage)
            return output

        return invoke

    def _event(
        self,
        state: ResearchGraphState,
        stage: str,
        summary: str,
        *,
        input_ids: list[str] | None = None,
        output_ids: list[str] | None = None,
        status: str = "succeeded",
        failure_code: str | None = None,
    ) -> list[dict[str, Any]]:
        timestamp = self.clock().isoformat()
        events = list(state.get("stages", []))
        events.append(
            {
                "sequence": len(events) + 1,
                "stage": stage,
                "node_version": NODE_VERSION,
                "status": status,
                "started_at": timestamp,
                "finished_at": timestamp,
                "input_artifact_ids": input_ids or [],
                "output_artifact_ids": output_ids or [],
                "tool_record_ids": [],
                "sanitized_summary": summary,
                "failure_code": failure_code,
            }
        )
        return events

    def _understand(self, state: ResearchGraphState) -> dict[str, Any]:
        request = state["request"]
        if request["task_type"] == "company_research":
            intent = self.question_router.route(str(request["research_question"]))
            return {
                "research_intent": intent.artifact_value(),
                "stages": self._event(
                    state,
                    "understanding_question",
                    f"Routed general company question to {intent.skill}.",
                    input_ids=[f"request_{state['run_id']}"],
                    output_ids=[f"intent_{state['run_id']}"],
                ),
            }
        return {
            "stages": self._event(
                state,
                "understanding_question",
                "Validated one bounded filing-analysis earnings-quality request.",
                input_ids=[f"request_{state['run_id']}"],
                output_ids=[f"task_spec_{state['run_id']}"],
            )
        }

    def _plan(self, state: ResearchGraphState) -> dict[str, Any]:
        run_id = state["run_id"]
        if state["request"]["task_type"] == "company_research":
            intent = self.question_router.route(str(state["request"]["research_question"]))
            plan = self.research_planner.plan(run_id, intent)
            summary = f"Prepared {len(plan)} question-specific steps for {intent.skill}."
        else:
            plan = [
                {
                    "step_id": f"step_{run_id}_load",
                    "description": "加载截止时点可用财务事实",
                    "status": "completed",
                },
                {
                    "step_id": f"step_{run_id}_calculate",
                    "description": "执行冻结收益质量公式",
                    "status": "completed",
                },
                {
                    "step_id": f"step_{run_id}_counter",
                    "description": "搜索当前证据包中的反证",
                    "status": "completed",
                },
                {
                    "step_id": f"step_{run_id}_validate",
                    "description": "组装并验证结构化结果",
                    "status": "completed",
                },
            ]
            summary = "Persistable four-step research plan prepared."
        return {
            "plan": plan,
            "stages": self._event(
                state,
                "planning",
                summary,
                input_ids=[
                    f"intent_{run_id}"
                    if state["request"]["task_type"] == "company_research"
                    else f"task_spec_{run_id}"
                ],
                output_ids=[f"plan_{run_id}"],
            ),
        }

    def _load(self, state: ResearchGraphState) -> dict[str, Any]:
        request = state["request"]
        try:
            loaded = self.load_data(
                request["company_ids"],
                request["requested_period_labels"],
                datetime.fromisoformat(request["research_time"]),
            )
        except InsufficientDataError as exc:
            failure = {"code": "INSUFFICIENT_DATA", "message": str(exc), "retryable": False}
            return {
                "terminal_state": "insufficient_data",
                "failure": failure,
                "stages": self._event(
                    state,
                    "loading_financial_data",
                    "Mandatory point-in-time facts were unavailable; no result was fabricated.",
                    input_ids=[f"plan_{state['run_id']}"],
                    status="failed",
                    failure_code="INSUFFICIENT_DATA",
                ),
            }
        fact_ids = [fact["fact_id"] for fact in loaded.facts]
        return {
            "loaded": loaded,
            "stages": self._event(
                state,
                "loading_financial_data",
                f"Loaded {len(fact_ids)} eligible normalized financial facts.",
                input_ids=[f"plan_{state['run_id']}"],
                output_ids=fact_ids,
            ),
        }

    @staticmethod
    def _route_after_loading(state: ResearchGraphState) -> str:
        return "stop" if state.get("terminal_state") == "insufficient_data" else "continue"

    def _retrieve(self, state: ResearchGraphState) -> dict[str, Any]:
        documents = [source["document_id"] for source in state["loaded"].source_documents]
        if state["request"]["task_type"] == "company_research":
            intent = self.question_router.route(str(state["request"]["research_question"]))
            selected = self.evidence_retriever.retrieve(
                state["loaded"].evidence_chunks,
                question=str(state["request"]["research_question"]),
                intent=intent,
                limit=12,
            )
            evidence_ids = [str(chunk["chunk_id"]) for chunk in selected]
            return {
                "selected_evidence": selected,
                "stages": self._event(
                    state,
                    "retrieving_evidence",
                    (
                        f"Selected {len(selected)} relevant chunks from "
                        f"{len(state['loaded'].evidence_chunks)} indexed filing chunks."
                    ),
                    input_ids=[fact["fact_id"] for fact in state["loaded"].facts],
                    output_ids=evidence_ids,
                ),
            }
        evidence_ids = [chunk["chunk_id"] for chunk in state["loaded"].evidence_chunks]
        return {
            "selected_evidence": state["loaded"].evidence_chunks,
            "stages": self._event(
                state,
                "retrieving_evidence",
                (
                    f"Resolved {len(evidence_ids)} bounded evidence chunks across "
                    f"{len(documents)} official source documents."
                ),
                input_ids=[fact["fact_id"] for fact in state["loaded"].facts],
                output_ids=evidence_ids,
            ),
        }

    def _calculate(self, state: ResearchGraphState) -> dict[str, Any]:
        loaded = state["loaded"]
        analyses: list[EarningsQualityAnalysis] = []
        for company in loaded.companies:
            company_id = company["company_id"]
            facts = tuple(
                fact for fact in loaded.facts if fact["company"]["company_id"] == company_id
            )
            document_ids = {fact["source"]["document_id"] for fact in facts}
            company_data = LoadedResearchData(
                facts=facts,
                source_documents=tuple(
                    source
                    for source in loaded.source_documents
                    if source["document_id"] in document_ids
                ),
                requested_periods=loaded.requested_periods,
                companies=(company,),
                evidence_chunks=tuple(
                    chunk
                    for chunk in loaded.evidence_chunks
                    if chunk["document_id"] in document_ids
                ),
            )
            analyses.append(
                self.analyzer.analyze(
                    state["run_id"],
                    company_data,
                    self.clock(),
                    artifact_namespace=f"{state['run_id']}_{company_id}",
                )
            )
        calculation_ids = [
            item["calculation_id"] for analysis in analyses for item in analysis.calculation_records
        ]
        return {
            "analysis": analyses[0],
            "analyses": tuple(analyses),
            "stages": self._event(
                state,
                "calculating",
                "Calculated gross profit, gross margin, cash conversion and divergence signal.",
                input_ids=[
                    fact["fact_id"] for analysis in analyses for fact in analysis.current_facts
                ],
                output_ids=calculation_ids,
            ),
        }

    def _cross_check(self, state: ResearchGraphState) -> dict[str, Any]:
        analyses = state.get("analyses", (state["analysis"],))
        return {
            "stages": self._event(
                state,
                "cross_checking",
                (
                    f"Completed {sum(len(item.mandatory_checks) for item in analyses)} "
                    "deterministic checks."
                ),
                input_ids=[
                    calculation["calculation_id"]
                    for analysis in analyses
                    for calculation in analysis.calculation_records
                ],
                output_ids=[f"checks_{state['run_id']}"],
            )
        }

    def _counter_evidence(self, state: ResearchGraphState) -> dict[str, Any]:
        if state["request"]["task_type"] == "company_research":
            selected = state.get("selected_evidence", ())
            candidates = self.evidence_retriever.counter_candidates(
                state["loaded"].evidence_chunks, selected
            )
            counter: dict[str, Any] = {
                "performed": True,
                "queries": [
                    "risk, uncertainty, competition, regulation and contrary filing signals"
                ],
                "result": "found" if candidates else "not_found",
                "evidence_ids": [str(item["chunk_id"]) for item in candidates],
                "summary": (
                    (
                        f"Located {len(candidates)} additional risk-oriented filing chunks "
                        "for counter-checking."
                    )
                    if candidates
                    else (
                        "No additional risk-oriented chunk passed the bounded lexical "
                        "counter-evidence rule."
                    )
                ),
            }
            return {
                "counter_evidence": counter,
                "stages": self._event(
                    state,
                    "searching_counter_evidence",
                    counter["summary"],
                    input_ids=[f"checks_{state['run_id']}"],
                    output_ids=[
                        f"counter_search_{state['run_id']}",
                        *list(counter["evidence_ids"]),
                    ],
                ),
            }
        counter_chunks = [
            chunk
            for chunk in state["loaded"].evidence_chunks
            if str(chunk.get("section", "")).startswith("Counter evidence:")
        ]
        if counter_chunks:
            topics = []
            if any(
                chunk["section"] == "Counter evidence: non-recurring profit contribution"
                for chunk in counter_chunks
            ):
                topics.append("扣除非经常性损益后的净利润披露")
            if any(
                chunk["section"] == "Counter evidence: audit status" for chunk in counter_chunks
            ):
                topics.append("财务报告未经审计")
            counter = {
                "performed": True,
                "queries": ["利润质量反证: 非经常性损益、审计状态与口径限制"],
                "result": "found",
                "evidence_ids": sorted(chunk["chunk_id"] for chunk in counter_chunks),
                "summary": "该官方披露中已定位: "
                + "、".join(topics or ["来源限制"])
                + "; 不应仅凭单期现金转化外推长期收益质量。",
            }
            event_summary = (
                f"Counter-evidence search found {len(counter_chunks)} filing-based evidence chunks."
            )
        else:
            counter = {
                "performed": True,
                "queries": ["利润质量反证: 经营现金流、应收账款、存货及口径限制"],
                "result": "not_found",
                "evidence_ids": [],
                "summary": (
                    "在当前证据包的有界反证规则中未找到唯一可引用的额外反证; "
                    "不代表完整公告不存在反证或风险。"
                ),
            }
            event_summary = "Counter-evidence search completed with an honest not_found outcome."
        return {
            "counter_evidence": counter,
            "stages": self._event(
                state,
                "searching_counter_evidence",
                event_summary,
                input_ids=[f"checks_{state['run_id']}"],
                output_ids=[f"counter_search_{state['run_id']}"],
            ),
        }

    def _form_conclusion(self, state: ResearchGraphState) -> dict[str, Any]:
        repairs = 0
        if state["request"]["task_type"] == "company_research":
            analysis = state["analysis"]
            intent = self.question_router.route(str(state["request"]["research_question"]))
            selected = state.get("selected_evidence", ())
            context = {
                "response_contract": "general_research_v1_7",
                "research_question": state["request"]["research_question"],
                "research_intent": intent.artifact_value(),
                "research_plan": state["plan"],
                "company": analysis.current_facts[0]["company"],
                "period_label": analysis.context["period_label"],
                "financial_facts": list(analysis.current_facts),
                "calculations": list(analysis.calculation_records),
                "selected_evidence": [
                    {
                        "chunk_id": item["chunk_id"],
                        "section": item["section"],
                        "text": self._clean_evidence_for_synthesis(str(item["text"]))[:800],
                        "locator": item["locator"],
                    }
                    for item in selected[:14]
                ],
                "counter_evidence": state["counter_evidence"],
                "suggested_follow_ups": follow_up_templates(intent.skill),
                "source_document_ids": [
                    source["document_id"] for source in state["loaded"].source_documents
                ],
            }
            for attempt in range(2):
                try:
                    draft = self.conclusion_generator.generate(context)
                    if not isinstance(draft, GeneralResearchDraft):
                        raise StructuredOutputError(
                            "General research returned the legacy draft contract"
                        )
                    self._validate_general_draft(state, draft)
                    return {
                        "conclusion": draft,
                        "conclusions": (draft,),
                        "repair_attempts": repairs,
                        "stages": self._event(
                            state,
                            "forming_conclusion",
                            "Formed a question-aware evidence-linked V1.7 research draft.",
                            input_ids=[
                                f"checks_{state['run_id']}",
                                f"counter_search_{state['run_id']}",
                            ],
                            output_ids=[f"conclusion_{state['run_id']}"],
                        ),
                    }
                except StructuredOutputError:
                    if attempt == 1:
                        return self._invalid_conclusion(state, repairs)
                    repairs += 1
            raise AssertionError("unreachable general-research repair state")

        conclusions: list[ConclusionDraft] = []
        for analysis in state.get("analyses", (state["analysis"],)):
            conclusion_context = {
                **analysis.context,
                "counter_evidence": state["counter_evidence"],
            }
            if analysis.context.get("real_disclosure_evidence"):
                conclusion_context.update(
                    {
                        "research_question": state["request"]["research_question"],
                        "verified_fact_ids": [fact["fact_id"] for fact in analysis.current_facts],
                        "source_document_ids": [
                            source["document_id"]
                            for source in state["loaded"].source_documents
                            if source["company"]["company_id"]
                            == analysis.current_facts[0]["company"]["company_id"]
                        ],
                        "currency": "CNY",
                    }
                )
            try:
                generated = self.conclusion_generator.generate(conclusion_context)
                if not isinstance(generated, ConclusionDraft):
                    raise StructuredOutputError("Legacy research returned the V1.7 draft contract")
                conclusion = generated
            except StructuredOutputError:
                if repairs >= 1:
                    return self._invalid_conclusion(state, repairs)
                repairs += 1
                try:
                    generated = self.conclusion_generator.generate(conclusion_context)
                    if not isinstance(generated, ConclusionDraft):
                        raise StructuredOutputError(
                            "Legacy research returned the V1.7 draft contract"
                        )
                    conclusion = generated
                except StructuredOutputError:
                    return self._invalid_conclusion(state, repairs)
            conclusions.append(conclusion)
        return {
            "conclusion": conclusions[0],
            "conclusions": tuple(conclusions),
            "repair_attempts": repairs,
            "stages": self._event(
                state,
                "forming_conclusion",
                (
                    "Formed bounded language after one structure-only repair."
                    if repairs
                    else "Formed bounded language from precomputed facts and calculations."
                ),
                input_ids=[f"checks_{state['run_id']}", f"counter_search_{state['run_id']}"],
                output_ids=[f"conclusion_{state['run_id']}"],
            ),
        }

    @staticmethod
    def _clean_evidence_for_synthesis(text: str) -> str:
        """Remove common PDF form/table noise before text reaches the synthesis model."""
        cleaned = re.sub(r"[√□]\s*(?:适用|不适用)", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _validate_general_draft(
        self, state: ResearchGraphState, draft: GeneralResearchDraft
    ) -> None:
        allowed_evidence = {str(item["chunk_id"]) for item in state.get("selected_evidence", ())}
        allowed_evidence.update(str(item) for item in state["counter_evidence"]["evidence_ids"])
        allowed_facts = {str(item["fact_id"]) for item in state["loaded"].facts}
        for finding in draft.findings:
            if not set(finding.evidence_ids) <= allowed_evidence:
                raise StructuredOutputError(
                    "General finding cited evidence outside retrieved context"
                )
            if not set(finding.fact_ids) <= allowed_facts:
                raise StructuredOutputError("General finding cited facts outside verified context")
            if "官方披露在该部分记录" in finding.text or "√适用" in finding.text:
                raise StructuredOutputError(
                    "General finding copied filing boilerplate instead of synthesis"
                )
        source_section_titles = {
            "Business and segments",
            "Management discussion",
            "Customers and suppliers",
            "Financial statements",
            "Filing narrative",
            "Growth drivers",
            "Risk factors",
            "Outlook",
        }
        for section in draft.deep_analysis:
            if not set(section.evidence_ids) <= allowed_evidence:
                raise StructuredOutputError(
                    "General analysis cited evidence outside retrieved context"
                )
            if self.synthesis_mode == "model" and section.title in source_section_titles:
                raise StructuredOutputError(
                    "General analysis used a source-section heading instead of an "
                    "analytical heading"
                )
        if self.synthesis_mode == "model":
            intent = self.question_router.route(str(state["request"]["research_question"]))
            if intent.skill == "company_overview" and (
                len(draft.findings) < 5 or len(draft.deep_analysis) < 5
            ):
                raise StructuredOutputError(
                    "Comprehensive company research requires at least five findings "
                    "and five analytical sections"
                )

    @staticmethod
    def _relevant_fact_ids(
        text: str, requested_ids: list[str], facts: tuple[dict[str, Any], ...]
    ) -> list[str]:
        """Keep only facts whose metric is explicitly discussed by the finding text."""
        aliases = {
            "revenue": ("revenue", "营业收入", "营收", "收入"),
            "operating_cost": ("operating cost", "营业成本", "成本"),
            "net_income": ("net income", "净利润", "利润"),
            "operating_cash_flow": ("operating cash", "经营现金流", "现金流"),
            "accounts_receivable": ("receivable", "应收"),
            "inventory": ("inventory", "存货"),
        }
        lowered = text.casefold()
        fact_by_id = {str(item["fact_id"]): item for item in facts}
        kept: list[str] = []
        for fact_id in requested_ids:
            fact = fact_by_id.get(fact_id)
            if fact is None:
                continue
            metric = str(fact.get("metric_code", ""))
            if any(alias.casefold() in lowered for alias in aliases.get(metric, (metric,))):
                kept.append(fact_id)
        return kept

    def _invalid_conclusion(self, state: ResearchGraphState, repairs: int) -> dict[str, Any]:
        failure = {
            "code": "OUTPUT_SCHEMA_INVALID",
            "message": "Structured conclusion remained invalid after one repair attempt.",
            "retryable": False,
        }
        return {
            "repair_attempts": repairs,
            "terminal_state": "failed",
            "failure": failure,
            "stages": self._event(
                state,
                "forming_conclusion",
                "Structured output failed after the single allowed repair attempt.",
                input_ids=[
                    f"checks_{state['run_id']}",
                    f"counter_search_{state['run_id']}",
                ],
                status="failed",
                failure_code="OUTPUT_SCHEMA_INVALID",
            ),
        }

    @staticmethod
    def _route_after_conclusion(state: ResearchGraphState) -> str:
        return "stop" if state.get("terminal_state") == "failed" else "continue"

    def _validate_output(self, state: ResearchGraphState) -> dict[str, Any]:
        result = self._assemble_result(state)
        return {
            "result": result,
            "stages": self._event(
                state,
                "validating_output",
                "Assembled the canonical Research Result with fact-linked material claims.",
                input_ids=[f"conclusion_{state['run_id']}"],
                output_ids=[result["result_id"]],
            ),
        }

    def _complete(self, state: ResearchGraphState) -> dict[str, Any]:
        return {
            "terminal_state": "succeeded",
            "failure": None,
            "stages": self._event(
                state,
                "completed",
                "Completed the bounded workflow; immutable artifacts are ready to persist.",
                input_ids=[state["result"]["result_id"]],
                output_ids=[f"manifest_{state['run_id']}"],
            ),
        }

    def _assemble_result(self, state: ResearchGraphState) -> dict[str, Any]:
        request = state["request"]
        if request["task_type"] == "company_research":
            return self._assemble_general_result(state)
        loaded = state["loaded"]
        analyses = state.get("analyses", (state["analysis"],))
        conclusions = state.get("conclusions", (state["conclusion"],))
        counter = state["counter_evidence"]
        fact_by_id = {fact["fact_id"]: fact for fact in loaded.facts}
        evidence_by_document: dict[str, list[str]] = {}
        for chunk in loaded.evidence_chunks:
            evidence_by_document.setdefault(chunk["document_id"], []).append(chunk["chunk_id"])

        def evidence_for_facts(fact_ids: list[str]) -> list[str]:
            matched: set[str] = set()
            fallback_documents: set[str] = set()
            for fact_id in fact_ids:
                fact = fact_by_id.get(fact_id)
                if fact is None:
                    continue
                document_id = fact["source"]["document_id"]
                candidates = evidence_by_document.get(document_id, [])
                metric_suffix = f"_{fact['metric_code']}"
                metric_matches = {
                    evidence_id for evidence_id in candidates if evidence_id.endswith(metric_suffix)
                }
                if metric_matches:
                    matched.update(metric_matches)
                else:
                    fallback_documents.add(document_id)
            for document_id in fallback_documents:
                matched.update(evidence_by_document.get(document_id, []))
            return sorted(matched)

        skill_report_codes = {
            "operating_cash_flow",
            "accounts_receivable",
            "inventory",
            "cash_conversion",
            "profit_cash_divergence",
            "one_off_contribution",
        }
        native_coverage = all(conclusion.reported_check_codes is None for conclusion in conclusions)
        mandatory_checks: list[dict[str, Any]] = []
        for analysis, conclusion in zip(analyses, conclusions, strict=True):
            reported = set(conclusion.reported_check_codes or [])
            mandatory_checks.extend(
                check
                for check in analysis.mandatory_checks
                if check["check_code"] not in skill_report_codes
                or native_coverage
                or check["check_code"] in reported
            )
        counter_reported = native_coverage or any(
            "counter_evidence" in (conclusion.reported_check_codes or [])
            for conclusion in conclusions
        )
        if counter_reported:
            mandatory_checks.append(
                {
                    "check_code": "counter_evidence",
                    "status": "performed",
                    "fact_ids": [],
                    "evidence_ids": list(counter["evidence_ids"]),
                    "finding": counter["summary"],
                }
            )
        mandatory_checks = [
            {
                **check,
                "evidence_ids": (
                    check["evidence_ids"] or evidence_for_facts(list(check["fact_ids"]))
                ),
            }
            for check in mandatory_checks
        ]
        claims: list[dict[str, Any]] = []
        risk_claim_ids: list[str] = []
        limitations: list[str] = []
        monitoring_items: list[dict[str, Any]] = []
        for analysis, conclusion in zip(analyses, conclusions, strict=True):
            by_metric = {fact["metric_code"]: fact for fact in analysis.current_facts}
            context = analysis.context
            company_id = analysis.current_facts[0]["company"]["company_id"]
            divergence = bool(context["divergence_triggered"])
            if request["task_type"] == "risk_detection":
                direction = "negative" if divergence else "neutral"
                claim_type = "risk"
            else:
                direction = (
                    "positive"
                    if context["cash_conversion_status"] == "calculated"
                    and Decimal(context["cash_conversion"]) >= Decimal(1)
                    else "mixed"
                )
                claim_type = "earnings_quality"
            epistemic_status = (
                "uncertain"
                if request["task_type"] == "thesis_investigation"
                else "supported_inference"
            )
            earnings_claim_id = f"claim_{state['run_id']}_{company_id}_earnings_quality"
            earnings_fact_ids = [
                by_metric["net_income"]["fact_id"],
                by_metric["operating_cash_flow"]["fact_id"],
            ]
            claims.append(
                {
                    "schema_version": "1.4.0",
                    "claim_id": earnings_claim_id,
                    "claim_type": claim_type,
                    "epistemic_status": epistemic_status,
                    "materiality": "material",
                    "direction": direction,
                    "text": (
                        "命题评估为mixed: " + conclusion.earnings_quality_text
                        if request["task_type"] == "thesis_investigation"
                        else conclusion.earnings_quality_text
                    ),
                    "fact_ids": earnings_fact_ids,
                    "support_evidence_ids": evidence_for_facts(earnings_fact_ids),
                    "counter_evidence_search": counter,
                    "alternative_explanations": [
                        "经营现金流与利润确认节奏可能受营运资本时点影响。"
                    ],
                    "confidence": {
                        "level": (
                            "medium" if request["task_type"] == "thesis_investigation" else "high"
                        ),
                        "basis": (
                            "结论直接依赖两个已核验财务事实和确定性公式。"
                            if analysis.context.get("real_disclosure_evidence")
                            else "结论直接依赖两个已核验财务事实和冻结公式。"
                        ),
                    },
                }
            )
            if request["task_type"] == "risk_detection":
                risk_claim_ids.append(earnings_claim_id)
            margin_fact_ids = [
                by_metric["revenue"]["fact_id"],
                by_metric["operating_cost"]["fact_id"],
            ]
            claims.append(
                {
                    "schema_version": "1.4.0",
                    "claim_id": f"claim_{state['run_id']}_{company_id}_gross_margin",
                    "claim_type": "observation",
                    "epistemic_status": "verified_fact",
                    "materiality": "supporting",
                    "direction": "neutral",
                    "text": conclusion.gross_margin_text,
                    "fact_ids": margin_fact_ids,
                    "support_evidence_ids": evidence_for_facts(margin_fact_ids),
                    "counter_evidence_search": {
                        "performed": False,
                        "queries": [],
                        "result": "not_applicable",
                        "evidence_ids": [],
                        "summary": "该支持性观察不单独触发反证搜索。",
                    },
                    "alternative_explanations": [],
                    "confidence": {
                        "level": "high",
                        "basis": "营业收入、营业成本与公式均已冻结。",
                    },
                }
            )
            monitoring_fact_ids = [
                by_metric[metric]["fact_id"]
                for metric in (
                    "operating_cash_flow",
                    "net_income",
                    "accounts_receivable",
                    "inventory",
                )
            ]
            monitoring_items.append(
                {
                    "monitor_code": f"working_capital_cash_conversion_{company_id}",
                    "title": "下一同口径报告期复核现金转化与营运资本",
                    "rationale": (
                        "经营现金流与净利润存在背离时, 应同时跟踪应收账款和存货, "
                        "避免把营运资本时点影响误判为长期盈利质量变化。"
                    ),
                    "trigger": "经营现金流为负, 或现金转化比低于1.00倍。",
                    "next_review": "下一同口径财务报告发布后",
                    "fact_ids": monitoring_fact_ids,
                    "evidence_ids": evidence_for_facts(monitoring_fact_ids),
                }
            )
            limitations.extend(conclusion.limitations)

        if request["task_type"] == "peer_comparison":
            peer_fact_ids = [
                fact["fact_id"]
                for analysis in analyses
                for fact in analysis.current_facts
                if fact["metric_code"] in {"net_income", "operating_cash_flow"}
            ]
            first, second = analyses
            claims.append(
                {
                    "schema_version": "1.4.0",
                    "claim_id": f"claim_{state['run_id']}_peer_comparison",
                    "claim_type": "comparison",
                    "epistemic_status": "supported_inference",
                    "materiality": "material",
                    "direction": "mixed",
                    "text": (
                        "同一框架下现金转化比分别为"
                        f"{first.context['cash_conversion_display']}与"
                        f"{second.context['cash_conversion_display']}; 该比较仅描述所选期间。"
                    ),
                    "fact_ids": peer_fact_ids,
                    "support_evidence_ids": evidence_for_facts(peer_fact_ids),
                    "counter_evidence_search": counter,
                    "alternative_explanations": ["业务结构和营运资本季节性可能影响横向可比性。"],
                    "confidence": {
                        "level": "medium",
                        "basis": "两家公司使用相同公式、期间和事实字段。",
                    },
                }
            )
            limitations.append("横向结果只适用于已对齐期间, 不代表投资优劣。")

        summaries = [item.executive_summary for item in conclusions]
        if request["task_type"] == "peer_comparison":
            executive_summary = "同框架同行比较: " + " ".join(summaries)
        elif request["task_type"] == "thesis_investigation":
            executive_summary = "命题结论为mixed, 现有冻结证据不足以单向确认。" + summaries[0]
        elif request["task_type"] == "risk_detection":
            executive_summary = "已完成可解释风险信号扫描。" + summaries[0]
        else:
            executive_summary = " ".join(summaries)
        generated_at = self.clock().isoformat()
        return {
            "schema_version": "1.4.0",
            "result_id": f"result_{state['run_id']}",
            "run_id": state["run_id"],
            "task_type": request["task_type"],
            "research_question": request["research_question"],
            "companies": list(loaded.companies),
            "requested_periods": list(loaded.requested_periods),
            "research_time": request["research_time"],
            "evidence_cutoff": request["research_time"],
            "status": "completed",
            "research_plan": state["plan"],
            "executive_summary": executive_summary,
            "financial_snapshot_fact_ids": [fact["fact_id"] for fact in loaded.facts],
            "mandatory_checks": mandatory_checks,
            "claims": claims,
            "risk_claim_ids": risk_claim_ids,
            "monitoring_items": monitoring_items,
            "source_document_ids": [source["document_id"] for source in loaded.source_documents],
            "limitations": list(dict.fromkeys(limitations)),
            "skill_version": self.skill_version,
            "skill_hash": self.skill_hash,
            "formula_version": FORMULA_VERSION,
            "generated_at": generated_at,
        }

    def _assemble_general_result(self, state: ResearchGraphState) -> dict[str, Any]:
        loaded = state["loaded"]
        analysis = state["analysis"]
        draft = state["conclusion"]
        if not isinstance(draft, GeneralResearchDraft):
            raise StructuredOutputError("V1.7 result assembly requires GeneralResearchDraft")
        intent = self.question_router.route(str(state["request"]["research_question"]))
        counter = state["counter_evidence"]
        selected = state.get("selected_evidence", ())
        claims: list[dict[str, Any]] = []
        for index, finding in enumerate(draft.findings, start=1):
            claim_id = f"claim_{state['run_id']}_general_{index}"
            finding_text = f"{finding.title}: {finding.text}"
            claims.append(
                {
                    "schema_version": "1.4.0",
                    "claim_id": claim_id,
                    "claim_type": finding.claim_type,
                    "epistemic_status": finding.epistemic_status,
                    "materiality": "material" if index <= 4 else "supporting",
                    "direction": finding.direction,
                    "text": finding_text,
                    "fact_ids": self._relevant_fact_ids(
                        finding_text, list(finding.fact_ids), analysis.current_facts
                    ),
                    "support_evidence_ids": list(finding.evidence_ids),
                    "counter_evidence_search": counter,
                    "alternative_explanations": [],
                    "confidence": {
                        "level": finding.confidence,
                        "basis": (
                            f"V1.7 {intent.skill} finding cites {len(finding.evidence_ids)} "
                            "retrieved official-filing evidence chunk(s)."
                        ),
                    },
                }
            )
        checks = [dict(item) for item in analysis.mandatory_checks]
        metric_chunks = {
            str(chunk["chunk_id"]): chunk
            for chunk in loaded.evidence_chunks
            if str(chunk.get("section", "")).startswith("Financial statement fact:")
            or str(chunk.get("section", "")).startswith("SEC XBRL concept:")
        }
        for check in checks:
            if check["evidence_ids"]:
                continue
            metric_ids: list[str] = []
            for fact_id in check["fact_ids"]:
                fact = next((item for item in loaded.facts if item["fact_id"] == fact_id), None)
                if fact is None:
                    continue
                suffix = f"_{fact['metric_code']}"
                metric_ids.extend(
                    chunk_id for chunk_id in metric_chunks if chunk_id.endswith(suffix)
                )
            check["evidence_ids"] = sorted(set(metric_ids))
        selected_ids = [str(item["chunk_id"]) for item in selected]
        all_used_evidence = sorted(
            {evidence_id for claim in claims for evidence_id in claim["support_evidence_ids"]}
            | set(counter["evidence_ids"])
        )
        generated_at = self.clock().isoformat()
        company_id = str(analysis.current_facts[0]["company"]["company_id"])
        monitoring_fact_ids = [
            fact["fact_id"]
            for fact in analysis.current_facts
            if fact["metric_code"]
            in {"operating_cash_flow", "net_income", "accounts_receivable", "inventory"}
        ]
        return {
            "schema_version": "1.7.0",
            "result_id": f"result_{state['run_id']}",
            "run_id": state["run_id"],
            "task_type": "company_research",
            "research_question": state["request"]["research_question"],
            "companies": list(loaded.companies),
            "requested_periods": list(loaded.requested_periods),
            "research_time": state["request"]["research_time"],
            "evidence_cutoff": state["request"]["research_time"],
            "status": "completed",
            "synthesis_mode": self.synthesis_mode,
            "research_intent": intent.artifact_value(),
            "research_plan": state["plan"],
            "executive_summary": draft.executive_summary,
            "financial_snapshot_fact_ids": [fact["fact_id"] for fact in analysis.current_facts],
            "mandatory_checks": checks,
            "claims": claims,
            "risk_claim_ids": [
                claim["claim_id"] for claim in claims if claim["claim_type"] == "risk"
            ],
            "analysis_sections": [item.model_dump(mode="json") for item in draft.deep_analysis],
            "overall_judgment": {
                "label": draft.overall_judgment,
                "rationale": draft.overall_judgment_rationale,
            },
            "suggested_follow_ups": list(draft.suggested_follow_ups),
            "evidence_coverage": {
                "available_chunk_count": len(loaded.evidence_chunks),
                "selected_chunk_count": len(selected),
                "selected_evidence_ids": selected_ids,
                "cited_evidence_ids": all_used_evidence,
                "sections": sorted({str(item["section"]) for item in selected}),
            },
            "monitoring_items": [
                {
                    "monitor_code": f"v17_next_filing_{company_id}",
                    "title": "下一份同口径官方披露发布后复核本次研究结论",
                    "rationale": "关键业务驱动、风险和财务质量可能随下一报告期变化。",
                    "trigger": "下一份同口径财务报告或重大官方披露发布。",
                    "next_review": "下一份同口径官方披露发布后",
                    "fact_ids": monitoring_fact_ids,
                    "evidence_ids": all_used_evidence[:8],
                }
            ],
            "source_document_ids": [source["document_id"] for source in loaded.source_documents],
            "limitations": list(dict.fromkeys(draft.limitations)),
            "skill_version": self.skill_version,
            "skill_hash": self.skill_hash,
            "formula_version": FORMULA_VERSION,
            "generated_at": generated_at,
        }

    @staticmethod
    def _config(run_id: str) -> RunnableConfig:
        return {"configurable": {"thread_id": run_id}}

    def has_checkpoint(self, run_id: str) -> bool:
        """Return whether the durable graph state contains this run thread."""
        if self.checkpointer is None:
            return False
        return self.checkpointer.get_tuple(self._config(run_id)) is not None

    def _checkpoint_state(self, run_id: str) -> ResearchGraphState:
        if not self.has_checkpoint(run_id):
            return ResearchGraphState()
        snapshot = self._compiled.get_state(self._config(run_id))
        return cast(ResearchGraphState, dict(snapshot.values))

    def _outcome(
        self,
        run_id: str,
        trace_id: str,
        final_state: ResearchGraphState,
        *,
        fallback_started_at: str,
    ) -> WorkflowOutcome:
        finished_at = self.clock().isoformat()
        terminal_state = final_state.get("terminal_state", "failed")
        started_at = final_state.get("started_at", fallback_started_at)
        usage = getattr(self.conclusion_generator, "usage", None)
        if not isinstance(usage, dict):
            usage = {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "latency_ms": 0,
                "tool_calls": 0,
                "estimated_cost": 0,
                "cost_currency": "USD",
            }
        trace_without_hash = {
            "schema_version": "1.4.0",
            "trace_id": trace_id,
            "run_id": run_id,
            "engine": "langgraph",
            "graph_version": GRAPH_VERSION,
            "checkpoint_schema_version": CHECKPOINT_SCHEMA_VERSION,
            "started_at": started_at,
            "finished_at": finished_at,
            "terminal_state": terminal_state,
            "stages": final_state["stages"],
            "repair_attempts": final_state.get("repair_attempts", 0),
            "usage": usage,
        }
        trace_hash = hashlib.sha256(
            json.dumps(trace_without_hash, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        trace = {**trace_without_hash, "trace_hash": trace_hash}
        analyses = final_state.get("analyses")
        if analyses is not None:
            calculations = [
                calculation for analysis in analyses for calculation in analysis.calculation_records
            ]
        else:
            analysis = final_state.get("analysis")
            calculations = list(analysis.calculation_records) if analysis is not None else []
        return WorkflowOutcome(
            terminal_state=terminal_state,
            plan=final_state.get("plan", []),
            calculations=calculations,
            result=final_state.get("result"),
            trace=trace,
            failure=final_state.get("failure"),
        )

    def run(
        self,
        run_id: str,
        trace_id: str,
        request: dict[str, Any],
        *,
        resume: bool = False,
        should_cancel: Callable[[], bool] = lambda: False,
        timeout_seconds: float = 300,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> WorkflowOutcome:
        """Invoke or resume one checkpointed graph under bounded run controls."""
        begin_run = getattr(self.conclusion_generator, "begin_run", None)
        if callable(begin_run):
            begin_run()
        started_at = self.clock().isoformat()
        config = self._config(run_id)
        can_resume = resume and self.has_checkpoint(run_id)
        initial: ResearchGraphState | None
        if can_resume:
            initial = None
        else:
            initial = {
                "run_id": run_id,
                "trace_id": trace_id,
                "request": request,
                "stages": [],
                "started_at": started_at,
                "failure": None,
                "repair_attempts": 0,
            }
        control = WorkflowControl(
            should_cancel=should_cancel,
            deadline=monotonic() + timeout_seconds,
            monotonic=monotonic,
        )
        token = _ACTIVE_CONTROL.set(control)
        try:
            final_state = cast(ResearchGraphState, dict(self._compiled.invoke(initial, config)))
        except WorkflowInterrupted as exc:
            final_state = self._checkpoint_state(run_id)
            if not final_state:
                assert initial is not None
                final_state = initial
            message = (
                "The run was cancelled by the user."
                if exc.terminal_state == "cancelled"
                else "The run exceeded its configured monotonic deadline."
            )
            final_state["terminal_state"] = exc.terminal_state
            final_state["failure"] = {
                "code": exc.failure_code,
                "message": message,
                "retryable": False,
            }
            final_state["stages"] = self._event(
                final_state,
                exc.stage,
                message,
                status="cancelled" if exc.terminal_state == "cancelled" else "failed",
                failure_code=exc.failure_code,
            )
        finally:
            _ACTIVE_CONTROL.reset(token)
        return self._outcome(
            run_id,
            trace_id,
            final_state,
            fallback_started_at=started_at,
        )

    def failed_outcome(
        self,
        run_id: str,
        trace_id: str,
        request: dict[str, Any],
        exc: Exception,
    ) -> WorkflowOutcome:
        """Turn an unexpected adapter failure into a safe, auditable terminal trace."""
        timestamp = self.clock().isoformat()
        state = self._checkpoint_state(run_id)
        if not state:
            state = {
                "run_id": run_id,
                "trace_id": trace_id,
                "request": request,
                "stages": [],
                "started_at": timestamp,
                "repair_attempts": 0,
            }
        completed = {event["stage"] for event in state.get("stages", [])}
        failed_stage = next(
            (stage for stage in self.stage_names if stage not in completed),
            "completed",
        )
        state["terminal_state"] = "failed"
        state["failure"] = {
            "code": "TOOL_FAILED",
            "message": f"Research workflow failed safely: {type(exc).__name__}",
            "retryable": False,
        }
        state["stages"] = self._event(
            state,
            failed_stage,
            "An internal adapter failed; exception details were withheld from public artifacts.",
            status="failed",
            failure_code="TOOL_FAILED",
        )
        return self._outcome(
            run_id,
            trace_id,
            state,
            fallback_started_at=timestamp,
        )
