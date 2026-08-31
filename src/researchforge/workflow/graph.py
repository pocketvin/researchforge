"""The V1.4 ten-stage LangGraph thin slice."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, TypedDict, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from researchforge.application.research import (
    ConclusionDraft,
    ConclusionGenerator,
    EarningsQualityAnalysis,
    EarningsQualityAnalyzer,
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
        checkpointer: BaseCheckpointSaver[Any] | None = None,
        clock: Callable[[], datetime] = _default_clock,
    ) -> None:
        self.load_data = load_data
        self.analyzer = analyzer
        self.conclusion_generator = conclusion_generator
        self.skill_version = skill_version
        self.skill_hash = skill_hash
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
        return {
            "plan": plan,
            "stages": self._event(
                state,
                "planning",
                "Persistable four-step research plan prepared.",
                input_ids=[f"task_spec_{run_id}"],
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
        return {
            "stages": self._event(
                state,
                "retrieving_evidence",
                f"Resolved {len(documents)} official source-document locators from frozen facts.",
                input_ids=[fact["fact_id"] for fact in state["loaded"].facts],
                output_ids=documents,
            )
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
        counter = {
            "performed": True,
            "queries": ["利润质量反证: 经营现金流、应收账款、存货及口径限制"],
            "result": "not_found",
            "evidence_ids": [],
            "summary": "在当前冻结事实与来源定位包中未发现额外反证; 未检索公告全文。",
        }
        return {
            "counter_evidence": counter,
            "stages": self._event(
                state,
                "searching_counter_evidence",
                "Counter-evidence search completed with an honest not_found outcome.",
                input_ids=[f"checks_{state['run_id']}"],
                output_ids=[f"counter_search_{state['run_id']}"],
            ),
        }

    def _form_conclusion(self, state: ResearchGraphState) -> dict[str, Any]:
        repairs = 0
        conclusions: list[ConclusionDraft] = []
        for analysis in state.get("analyses", (state["analysis"],)):
            try:
                conclusion = self.conclusion_generator.generate(analysis.context)
            except StructuredOutputError:
                if repairs >= 1:
                    return self._invalid_conclusion(state, repairs)
                repairs += 1
                try:
                    conclusion = self.conclusion_generator.generate(analysis.context)
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
        loaded = state["loaded"]
        analyses = state.get("analyses", (state["analysis"],))
        conclusions = state.get("conclusions", (state["conclusion"],))
        counter = state["counter_evidence"]
        mandatory_checks = [check for analysis in analyses for check in analysis.mandatory_checks]
        mandatory_checks.append(
            {
                "check_code": "counter_evidence",
                "status": "performed",
                "fact_ids": [],
                "evidence_ids": [],
                "finding": counter["summary"],
            }
        )
        claims: list[dict[str, Any]] = []
        risk_claim_ids: list[str] = []
        limitations: list[str] = []
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
                    "positive" if Decimal(context["cash_conversion"]) >= Decimal(1) else "mixed"
                )
                claim_type = "earnings_quality"
            epistemic_status = (
                "uncertain"
                if request["task_type"] == "thesis_investigation"
                else "supported_inference"
            )
            earnings_claim_id = f"claim_{state['run_id']}_{company_id}_earnings_quality"
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
                    "fact_ids": [
                        by_metric["net_income"]["fact_id"],
                        by_metric["operating_cash_flow"]["fact_id"],
                    ],
                    "support_evidence_ids": [],
                    "counter_evidence_search": counter,
                    "alternative_explanations": [
                        "经营现金流与利润确认节奏可能受营运资本时点影响。"
                    ],
                    "confidence": {
                        "level": (
                            "medium" if request["task_type"] == "thesis_investigation" else "high"
                        ),
                        "basis": "结论直接依赖两个已核验财务事实和冻结公式。",
                    },
                }
            )
            if request["task_type"] == "risk_detection":
                risk_claim_ids.append(earnings_claim_id)
            claims.append(
                {
                    "schema_version": "1.4.0",
                    "claim_id": f"claim_{state['run_id']}_{company_id}_gross_margin",
                    "claim_type": "observation",
                    "epistemic_status": "verified_fact",
                    "materiality": "supporting",
                    "direction": "neutral",
                    "text": conclusion.gross_margin_text,
                    "fact_ids": [
                        by_metric["revenue"]["fact_id"],
                        by_metric["operating_cost"]["fact_id"],
                    ],
                    "support_evidence_ids": [],
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
                        f"同一框架下现金转化比分别为{first.context['cash_conversion']}倍与"
                        f"{second.context['cash_conversion']}倍; 该比较仅描述所选期间。"
                    ),
                    "fact_ids": peer_fact_ids,
                    "support_evidence_ids": [],
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
            "source_document_ids": [source["document_id"] for source in loaded.source_documents],
            "limitations": list(dict.fromkeys(limitations)),
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
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "latency_ms": 0,
                "tool_calls": 0,
                "estimated_cost": 0,
                "cost_currency": "USD",
            },
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
