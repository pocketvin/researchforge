# ruff: noqa: RUF001 -- Chinese product text intentionally uses Chinese punctuation.
"""Single LangGraph research loop, public-state recovery and explicit terminal outcomes."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict, cast

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from researchforge.adapters.checkpoints import DurableJsonCheckpointSaver
from researchforge.adapters.storage import payload_sha256
from researchforge.budget import BudgetExceededError, BudgetLedger
from researchforge.config import has_secret, load_runtime_settings
from researchforge.file_lock import exclusive_file_lock
from researchforge.ingestion.errors import IngestionAbstention
from researchforge.policy import enforce_research_question_policy
from researchforge.v2.contracts import Json, ResearchReport, ResearchRequest
from researchforge.v2.hybrid_provider import HybridResearchModel
from researchforge.v2.preparation import FilingPreparer
from researchforge.v2.provider import ContextTooLarge, ModelPort, ResponsesResearchModel
from researchforge.v2.qwen_provider import QwenChatResearchModel
from researchforge.v2.reporting import build_safe_dossier_report
from researchforge.v2.storage import TERMINAL, ResearchRepository, now
from researchforge.v2.tools import FilingTools
from researchforge.v2.validation import validate_report, validate_review

GRAPH_VERSION = "2.0.0-alpha.1"


class RunInterrupted(RuntimeError):
    def __init__(self, state: str, code: str) -> None:
        super().__init__(code)
        self.state, self.code = state, code


class LoopState(TypedDict, total=False):
    turn: int
    calls: list[Json]
    ready: bool
    validated: bool
    report: Json
    validation: Json
    semantic_review: Json
    failed_draft_hashes: list[str]


class ResearchLoop:
    def __init__(
        self,
        tools: FilingTools,
        model: ModelPort,
        bootstrap: Json,
        checkpointer: DurableJsonCheckpointSaver,
    ) -> None:
        self.tools, self.model, self.bootstrap = tools, model, bootstrap
        graph = StateGraph(LoopState)
        graph.add_node("agent", self.agent)
        graph.add_node("tools", self.execute_tools)
        graph.add_node("synthesis", self.synthesis)
        graph.add_edge(START, "agent")
        graph.add_edge("agent", "tools")
        graph.add_conditional_edges(
            "tools", lambda state: "synthesis" if state.get("ready") else "agent"
        )
        graph.add_conditional_edges(
            "synthesis", lambda state: END if state.get("validated") else "agent"
        )
        self.graph = graph.compile(checkpointer=checkpointer)

    def agent(self, state: LoopState) -> Json:
        self.tools.check()
        observations = self.tools.observation_messages(state.get("calls", []))
        if self.tools.consecutive_invalid_submission_count() >= 3:
            self.tools.repository.emit(
                self.tools.run_id,
                "submission_contract_repair_exhausted",
                "agent",
                "研究已完成，但提交契约连续修复失败；停止重复提交以避免无效模型循环",
                "failed",
                data={
                    "invalid_submission_attempts": self.tools.consecutive_invalid_submission_count(),
                },
            )
            raise RunInterrupted("failed", "SUBMISSION_CONTRACT_REPAIR_EXHAUSTED")
        reflection = self.tools.reflection_decision()
        self.tools.repository.emit(
            self.tools.run_id,
            "reflection_check",
            "research_state",
            "检查是否需要由 Agent 刷新研究假设与停止状态",
            "succeeded",
            data=reflection,
        )
        if reflection["needed"]:
            self.tools.repository.emit(
                self.tools.run_id,
                "research_state_refresh_requested",
                "research_state",
                "研究信息已发生实质变化，正在通过公共 Research State 刷新",
                "running",
                data={"reason": reflection["reason"]},
            )
            reflect = getattr(self.model, "reflect", None)
            if callable(reflect):
                reflected = reflect(
                    self.bootstrap,
                    self.tools.context_state(),
                    observations,
                )
                applied = self.tools.apply_working_state(
                    reflected, trigger_reason=str(reflection["reason"])
                )
                self.tools.save()
                self.tools.repository.emit(
                    self.tools.run_id,
                    "research_reflection",
                    "research_state",
                    "已通过公共研究摘要刷新假设、待查问题与停止状态",
                    "succeeded",
                    data={
                        "reason": reflection["reason"],
                        "completeness": applied["completeness"],
                        "reference_corrections": applied["reference_corrections"],
                    },
                )
        turn = state.get("turn", 0) + 1
        if turn > 128:
            raise RunInterrupted("failed", "EMERGENCY_STEP_LIMIT")
        self.tools.repository.emit(
            self.tools.run_id,
            "agent_turn",
            "agent",
            f"第 {turn} 轮研究",
            "running",
            data={"turn": turn, "completeness": self.tools.completeness()},
        )
        calls = self.model.next_action(
            self.bootstrap,
            self.tools.context_state(),
            observations,
        )
        self.tools.check()
        return {"turn": turn, "calls": calls, "ready": False, "validated": False}

    def execute_tools(self, state: LoopState) -> Json:
        self.tools.check()
        with self.tools.repository.span(
            self.tools.run_id, "tool_execution", "执行本轮研究工具"
        ) as span:
            for call in state["calls"]:
                self.tools.execute(call["call_id"], call["name"], call["arguments"], parent=span)
        return {"ready": self.tools.dossier is not None}

    def _safe_report_fallback(self, context: Json, previous: list[str], reason: str) -> Json:
        report = build_safe_dossier_report(context)
        self.tools.repository.attach(
            self.tools.run_id, "last_draft", report.model_dump(mode="json")
        )
        with self.tools.repository.span(
            self.tools.run_id,
            "safe_report_validation",
            "模型写作未稳定通过，正在验证保守 Research Dossier 报告",
        ):
            validation = validate_report(report, self.tools)
        if validation["errors"]:
            self.tools.repository.emit(
                self.tools.run_id,
                "safe_report_fallback_rejected",
                "synthesis",
                "保守报告仍未通过确定性校验，停止而不重新研究",
                "failed",
                data={"reason": reason, "issues": validation["errors"]},
            )
            raise RunInterrupted("failed", "SAFE_REPORT_VALIDATION_FAILED")

        review_context = context
        review = None
        review_errors: list[str] = []
        protocol_attempt = 0
        for attempt in range(2):
            protocol_attempt = attempt
            review = self.model.review(review_context, report)
            review_errors = validate_review(report, review)
            if review_errors != ["SEMANTIC_REVIEW_CLAIM_SET_INVALID"]:
                break
            expected_claim_ids = [finding.claim_id for finding in report.findings]
            observed_claim_ids = [item.claim_id for item in review.claims]
            review_context = {
                **context,
                "semantic_review_protocol_feedback": {
                    "error": "SEMANTIC_REVIEW_CLAIM_SET_INVALID",
                    "expected_claim_ids": expected_claim_ids,
                    "observed_claim_ids": observed_claim_ids,
                    "instruction": (
                        "Return exactly one review item for every expected claim_id; "
                        "do not omit, duplicate, rename, or add claim IDs."
                    ),
                },
            }
        assert review is not None
        if review_errors == ["SEMANTIC_REVIEW_CLAIM_SET_INVALID"]:
            raise RunInterrupted("failed", "SEMANTIC_REVIEW_PROTOCOL_INVALID")
        raw_review_metadata = getattr(self.model, "review_metadata", {})
        review_metadata = raw_review_metadata if isinstance(raw_review_metadata, dict) else {}
        semantic: Json = {
            "status": "model_reviewed",
            "is_ground_truth": False,
            "protocol_repair_attempts": protocol_attempt,
            "provider": review_metadata.get("provider"),
            "model": review_metadata.get("model"),
            "independence": review_metadata.get("independence", "unspecified"),
            "fallback_used": review_metadata.get("fallback_used", False),
            "research_provider_fallback_used": review_metadata.get(
                "research_provider_fallback_used", False
            ),
            "review": review.model_dump(mode="json"),
        }
        needs_more_research = bool(not review.question_answered or review.missing_material_topics)
        if review_errors:
            if needs_more_research:
                self.tools.feedback = review_errors[-12:]
                self.tools.dossier = None
                self.tools.save()
                self.tools.repository.emit(
                    self.tools.run_id,
                    "validation_feedback",
                    "validation",
                    "保守报告仍显示重大研究覆盖缺口，返回 Research Agent",
                    "needs_attention",
                    data={"issues": review_errors, "safe_report": True},
                )
                return {
                    "validated": False,
                    "ready": False,
                    "failed_draft_hashes": previous,
                }
            self.tools.repository.emit(
                self.tools.run_id,
                "safe_report_fallback_rejected",
                "semantic_review",
                "保守报告的研究结论仍不被证据支持，停止而不重新研究",
                "failed",
                data={"reason": reason, "issues": review_errors},
            )
            raise RunInterrupted("failed", "SAFE_REPORT_SEMANTIC_REJECTED")

        partial_claims = [item.claim_id for item in review.claims if item.verdict == "partial"]
        if partial_claims:
            validation["warnings"] = [
                *validation["warnings"],
                "语义复核认为部分结论仅有条件支持：" + ", ".join(partial_claims),
            ]
        self.tools.repository.attach(
            self.tools.run_id,
            "validation",
            {
                **validation,
                "semantic": semantic,
                "report_repair_attempt": "safe_dossier_renderer",
            },
        )
        self.tools.feedback = []
        self.tools.save()
        self.tools.repository.emit(
            self.tools.run_id,
            "safe_report_fallback_used",
            "synthesis",
            "模型草稿未稳定通过，已使用不新增推断的 Research Dossier 保守报告",
            "succeeded",
            data={"reason": reason},
        )
        return {
            "report": report.model_dump(mode="json"),
            "validation": validation,
            "semantic_review": semantic,
            "validated": True,
            "failed_draft_hashes": previous,
        }

    def synthesis(self, state: LoopState) -> Json:
        self.tools.check()
        previous = list(state.get("failed_draft_hashes", []))
        repair_limit = 2
        context = self.tools.synthesis_context()
        try:
            for repair_attempt in range(repair_limit + 1):
                context = self.tools.synthesis_context()
                report = self.model.synthesize(context)
                self.tools.repository.attach(
                    self.tools.run_id, "last_draft", report.model_dump(mode="json")
                )
                self.tools.check()
                with self.tools.repository.span(
                    self.tools.run_id,
                    "reference_validation",
                    "校验引用、数值关联与资料边界",
                ):
                    validation = validate_report(report, self.tools)
                errors = list(validation["errors"])
                semantic: Json = {"status": "not_scored"}
                # Required-objective numeric provenance is enforced before submission. Any new
                # uncomputed percentage introduced only by Synthesis is a writing-layer defect:
                # repair/remove it before considering another research pass.
                needs_more_research = False
                if not errors:
                    review_context = context
                    review = None
                    review_errors: list[str] = []
                    protocol_attempt = 0
                    for protocol_attempt in range(2):
                        review = self.model.review(review_context, report)
                        review_errors = validate_review(report, review)
                        if review_errors != ["SEMANTIC_REVIEW_CLAIM_SET_INVALID"]:
                            break
                        if protocol_attempt == 0:
                            expected_claim_ids = [finding.claim_id for finding in report.findings]
                            observed_claim_ids = [item.claim_id for item in review.claims]
                            self.tools.repository.emit(
                                self.tools.run_id,
                                "semantic_review_repair_requested",
                                "semantic_review",
                                "独立语义复核漏审或重复了结论，正在只修复审查结果",
                                "needs_attention",
                                data={
                                    "expected_claim_ids": expected_claim_ids,
                                    "observed_claim_ids": observed_claim_ids,
                                },
                            )
                            review_context = {
                                **context,
                                "semantic_review_protocol_feedback": {
                                    "error": "SEMANTIC_REVIEW_CLAIM_SET_INVALID",
                                    "expected_claim_ids": expected_claim_ids,
                                    "observed_claim_ids": observed_claim_ids,
                                    "instruction": (
                                        "Return exactly one review item for every expected "
                                        "claim_id; do not omit, duplicate, rename, "
                                        "or add claim IDs."
                                    ),
                                },
                            }
                    assert review is not None
                    if review_errors == ["SEMANTIC_REVIEW_CLAIM_SET_INVALID"]:
                        raise RunInterrupted("failed", "SEMANTIC_REVIEW_PROTOCOL_INVALID")
                    raw_review_metadata = getattr(self.model, "review_metadata", {})
                    review_metadata = (
                        raw_review_metadata if isinstance(raw_review_metadata, dict) else {}
                    )
                    semantic = {
                        "status": "model_reviewed",
                        "is_ground_truth": False,
                        "protocol_repair_attempts": protocol_attempt,
                        "provider": review_metadata.get("provider"),
                        "model": review_metadata.get("model"),
                        "independence": review_metadata.get("independence", "unspecified"),
                        "fallback_used": review_metadata.get("fallback_used", False),
                        "research_provider_fallback_used": review_metadata.get(
                            "research_provider_fallback_used", False
                        ),
                        "review": review.model_dump(mode="json"),
                    }
                    errors.extend(review_errors)
                    needs_more_research = bool(
                        not review.question_answered or review.missing_material_topics
                    )
                    partial_claims = [
                        item.claim_id for item in review.claims if item.verdict == "partial"
                    ]
                    if partial_claims:
                        validation["warnings"] = [
                            *validation["warnings"],
                            "语义复核认为部分结论仅有条件支持：" + ", ".join(partial_claims),
                        ]
                self.tools.check()
                self.tools.repository.attach(
                    self.tools.run_id,
                    "validation",
                    {
                        **validation,
                        "semantic": semantic,
                        "report_repair_attempt": repair_attempt,
                    },
                )
                if not errors:
                    self.tools.feedback = []
                    self.tools.save()
                    return {
                        "report": report.model_dump(mode="json"),
                        "validation": validation,
                        "semantic_review": semantic,
                        "validated": True,
                        "failed_draft_hashes": previous,
                    }
                failed_hash = payload_sha256(
                    {"draft": report.model_dump(mode="json"), "errors": errors}
                )
                if failed_hash in previous:
                    self.tools.repository.emit(
                        self.tools.run_id,
                        "report_model_stalled",
                        "synthesis",
                        "模型重复生成相同无效报告，改用保守 Research Dossier 报告",
                        "needs_attention",
                        data={"issues": errors},
                    )
                    return self._safe_report_fallback(context, previous, "identical_invalid_draft")
                previous.append(failed_hash)
                self.tools.feedback = errors[-12:]
                self.tools.save()
                if needs_more_research:
                    self.tools.dossier = None
                    self.tools.save()
                    self.tools.repository.emit(
                        self.tools.run_id,
                        "validation_feedback",
                        "validation",
                        "语义复核发现重大研究覆盖缺口，返回 Research Agent 补证据",
                        "needs_attention",
                        data={"issues": errors},
                    )
                    return {
                        "validated": False,
                        "ready": False,
                        "failed_draft_hashes": previous,
                    }
                if repair_attempt < repair_limit:
                    self.tools.repository.emit(
                        self.tools.run_id,
                        "report_repair_requested",
                        "synthesis",
                        "证据已足够，正在只重写报告表达与引用，不重新研究",
                        "needs_attention",
                        data={"issues": errors, "attempt": repair_attempt + 1},
                    )
                    continue
                self.tools.repository.emit(
                    self.tools.run_id,
                    "report_repair_exhausted",
                    "synthesis",
                    "模型报告连续修复未通过，改用保守 Research Dossier 报告",
                    "needs_attention",
                    data={"issues": errors, "attempts": repair_limit + 1},
                )
                return self._safe_report_fallback(
                    context, previous, "model_report_repair_exhausted"
                )
            raise RunInterrupted("failed", "REPORT_REPAIR_CONTROL_FLOW_INVALID")
        except (ContextTooLarge, ValidationError) as exc:
            feedback = (
                str(exc)
                if isinstance(exc, ContextTooLarge)
                else "模型输出结构不合约；请保持证据完整并精简提交。"
            )
            self.tools.feedback = [feedback]
            self.tools.save()
            self.tools.repository.emit(
                self.tools.run_id,
                "report_generation_fallback_requested",
                "synthesis",
                "模型报告结构或上下文不合约，改用保守 Research Dossier 报告",
                "needs_attention",
                data={"issues": [feedback]},
            )
            return self._safe_report_fallback(context, previous, type(exc).__name__)


PreparePort = Callable[[ResearchRequest, str, Callable[[], None]], Json]
ModelFactory = Callable[[str, Callable[[], float], Json], ModelPort]


class ResearchService:
    def __init__(
        self,
        repository: ResearchRepository,
        model_factory: ModelFactory | None,
        *,
        configuration: Json,
        prepare: PreparePort | None = None,
    ) -> None:
        self.repository, self.model_factory, self.configuration = (
            repository,
            model_factory,
            configuration,
        )
        self.prepare = prepare or FilingPreparer(repository).prepare

    def submit(self, request: ResearchRequest) -> tuple[Json, bool]:
        enforce_research_question_policy(request.research_question)
        if self.model_factory is None:
            raise ValueError("V2_AGENT_MODEL_UNAVAILABLE")
        return self.repository.create(request, self.configuration)

    def cancel(self, run_id: str) -> Json:
        manifest = self.repository.get(run_id)
        if manifest["lifecycle_state"] in TERMINAL:
            return manifest
        self.repository.update(run_id, cancel_requested=True)
        self.repository.emit(
            run_id, "cancel_requested", "cancel", "已请求取消；当前调用返回后停止", "running"
        )
        if manifest["lifecycle_state"] == "queued":
            return self.repository.update(
                run_id,
                lifecycle_state="cancelled",
                finished_at=now(),
                failure={"code": "CANCELLED_BY_USER", "message": "研究开始前已取消。"},
            )
        return self.repository.get(run_id)

    def execute(self, run_id: str) -> Json:
        repository = self.repository
        with exclusive_file_lock(repository.root / "locks" / f"{run_id}.execution.lock"):
            manifest = repository.get(run_id)
            if manifest["lifecycle_state"] in TERMINAL:
                return manifest
            started_at = manifest["started_at"] or now()
            repository.update(run_id, lifecycle_state="running", started_at=started_at)
            request = ResearchRequest.model_validate(manifest["request"])
            started = datetime.fromisoformat(started_at)
            timeout = float(manifest["configuration"].get("timeout_seconds", 900))

            def remaining() -> float:
                return timeout - (datetime.now(UTC) - started).total_seconds()

            def check() -> None:
                if repository.get(run_id)["cancel_requested"]:
                    raise RunInterrupted("cancelled", "CANCELLED_BY_USER")
                if remaining() <= 0:
                    raise RunInterrupted("timed_out", "TIMED_OUT")

            model: ModelPort | None = None
            checkpointer: DurableJsonCheckpointSaver | None = None
            try:
                check()
                if "environment" in manifest["artifacts"]:
                    environment = repository.artifact(run_id, "environment")
                else:
                    environment = self.prepare(request, run_id, check)
                    repository.attach(run_id, "environment", environment)
                check()
                latest = repository.get(run_id)
                snapshot = (
                    repository.artifact(run_id, "research_state")
                    if "research_state" in latest["artifacts"]
                    else None
                )
                tools = FilingTools(
                    repository, run_id, request, environment, check, snapshot=snapshot
                )
                if "bootstrap" in latest["artifacts"]:
                    bootstrap = repository.artifact(run_id, "bootstrap")
                else:
                    with repository.span(run_id, "bootstrap", "准备初始证据，不限制后续全文访问"):
                        bootstrap = tools.bootstrap()
                        repository.attach(run_id, "bootstrap", bootstrap)
                if self.model_factory is None:
                    raise ValueError("V2_AGENT_MODEL_UNAVAILABLE")
                model = self.model_factory(run_id, remaining, latest.get("usage", {}))
                checkpointer = DurableJsonCheckpointSaver(
                    repository.root / "checkpoints" / "research-v2.json"
                )
                loop = ResearchLoop(tools, model, bootstrap, checkpointer)
                config: Any = {"configurable": {"thread_id": run_id}, "recursion_limit": 512}
                resume = checkpointer.get_tuple(config) is not None
                if resume:
                    repository.emit(
                        run_id,
                        "run_resumed",
                        "recovery",
                        "从公开研究状态恢复，已完成工具结果可复用",
                        "running",
                    )
                final = cast(
                    LoopState,
                    loop.graph.invoke(
                        None if resume else {"turn": 0, "calls": [], "failed_draft_hashes": []},
                        config,
                    ),
                )
                check()
                report = ResearchReport.model_validate(final["report"])
                result = {
                    "schema_version": "2.0.0",
                    "run_id": run_id,
                    "request": request.model_dump(mode="json"),
                    "entity": environment["entity"],
                    "report": report.model_dump(mode="json"),
                    "hypotheses": tools.working.model_dump(mode="json"),
                    "stop_decision": tools.dossier,
                    "completeness": tools.completeness(),
                    "documents": list(environment["documents"].values()),
                    "facts": list(environment["facts"].values()),
                    "calculations": list(tools.calculations.values()),
                    "validation": final["validation"],
                    "semantic_review": final["semantic_review"],
                    "independent_quality_score": None,
                    "quality_note": "语义复核是模型判断；本次工程检查不能替代独立质量基准。",
                }
                repository.attach(run_id, "result", result)
                tools.save()
                repository.emit(
                    run_id,
                    "run_completed",
                    "completed",
                    "报告已生成，可逐项核查证据与研究过程",
                    "succeeded",
                    data={
                        "claim_count": len(report.findings),
                        "turn_count": final["turn"],
                        "usage": model.usage,
                    },
                )
                repository.attach(
                    run_id,
                    "trace",
                    {
                        "schema_version": "2.0.0",
                        "run_id": run_id,
                        "events": repository.events(run_id, limit=None),
                    },
                )
                repository.update(
                    run_id, lifecycle_state="succeeded", finished_at=now(), usage=model.usage
                )
            except Exception as exc:
                if isinstance(exc, RunInterrupted):
                    state, code = exc.state, exc.code
                elif isinstance(exc, BudgetExceededError):
                    state, code = "failed", "BUDGET_EXCEEDED"
                elif isinstance(exc, IngestionAbstention):
                    state, code = "insufficient_data", exc.code
                else:
                    state, code = "failed", "V2_EXECUTION_FAILED"
                failure = {
                    "code": code,
                    "message": (
                        f"研究未完成 ({type(exc).__name__})；已产生的原文、证据和轨迹保持可查。"
                    ),
                }
                repository.emit(
                    run_id,
                    "run_failed",
                    "terminal",
                    failure["message"],
                    state,
                    data={"failure": failure},
                )
                repository.attach(
                    run_id,
                    "trace",
                    {
                        "schema_version": "2.0.0",
                        "run_id": run_id,
                        "events": repository.events(run_id, limit=None),
                    },
                )
                repository.update(
                    run_id,
                    lifecycle_state=state,
                    finished_at=now(),
                    failure=failure,
                    usage=model.usage
                    if model is not None
                    else repository.get(run_id).get("usage", {}),
                )
            finally:
                if (
                    checkpointer is not None
                    and repository.get(run_id)["lifecycle_state"] in TERMINAL
                ):
                    checkpointer.delete_thread(run_id)
            return repository.get(run_id)

    def recover(self) -> None:
        for manifest in self.repository.list_runs(limit=10000):
            if manifest["lifecycle_state"] in {"queued", "running"}:
                self.execute(manifest["run_id"])


def build_service(project_root: Path, artifact_root: Path) -> ResearchService:
    settings = load_runtime_settings(project_root)
    repository = ResearchRepository(artifact_root / "v2")
    ready = settings.researchforge_reasoning_mode != "deterministic"
    factory: ModelFactory | None = None
    selected_model: str = settings.researchforge_model
    provider = settings.researchforge_provider
    if provider == "hybrid":
        selected_model = settings.researchforge_deepseek_model
        ready = bool(
            ready
            and has_secret(settings.researchforge_deepseek_api_key)
            and settings.researchforge_deepseek_base_url
            and has_secret(settings.researchforge_qwen_api_key)
            and settings.researchforge_qwen_base_url
        )
        if ready:
            from openai import OpenAI

            deepseek_key = settings.researchforge_deepseek_api_key
            qwen_key = settings.researchforge_qwen_api_key
            deepseek_base = settings.researchforge_deepseek_base_url
            qwen_base = settings.researchforge_qwen_base_url
            assert deepseek_key is not None and deepseek_base is not None
            assert qwen_key is not None and qwen_base is not None
            deepseek_client = OpenAI(
                api_key=deepseek_key.get_secret_value(),
                base_url=deepseek_base.rstrip("/") + "/beta",
                max_retries=0,
                timeout=120.0,
            )
            kimi_key = settings.researchforge_kimi_api_key
            kimi_base = settings.researchforge_kimi_base_url
            kimi_client = None
            if has_secret(kimi_key) and kimi_base:
                assert kimi_key is not None
                kimi_client = OpenAI(
                    api_key=kimi_key.get_secret_value(),
                    base_url=kimi_base,
                    max_retries=0,
                    timeout=120.0,
                )
            hybrid_qwen_client = OpenAI(
                api_key=qwen_key.get_secret_value(),
                base_url=qwen_base,
                max_retries=0,
                timeout=120.0,
            )
            hybrid_ledger = BudgetLedger(
                cap=settings.researchforge_budget_usd,
                state_path=artifact_root / "budget" / "project-hybrid.json",
            )

            def create_hybrid_model(
                run_id: str, remaining: Callable[[], float], usage: Json
            ) -> ModelPort:
                return HybridResearchModel(
                    deepseek_client=deepseek_client,
                    kimi_client=kimi_client,
                    qwen_client=hybrid_qwen_client,
                    ledger=hybrid_ledger,
                    repository=repository,
                    run_id=run_id,
                    deepseek_model=settings.researchforge_deepseek_model,
                    kimi_model=(
                        settings.researchforge_kimi_model if kimi_client is not None else None
                    ),
                    qwen_research_model=settings.researchforge_qwen_model,
                    qwen_text_model=settings.researchforge_qwen_review_model,
                    qwen_fallback_synthesis_model=settings.researchforge_qwen_fallback_synthesis_model,
                    qwen_vision_model=settings.researchforge_qwen_vision_model,
                    remaining_seconds=remaining,
                    prior_usage=usage or None,
                    run_cost_cap=settings.researchforge_v2_run_budget_usd,
                )

            factory = create_hybrid_model
    elif provider == "qwen":
        selected_model = settings.researchforge_qwen_model
        ready = bool(
            ready
            and has_secret(settings.researchforge_qwen_api_key)
            and settings.researchforge_qwen_base_url
        )
        if ready:
            from openai import OpenAI

            qwen_key = settings.researchforge_qwen_api_key
            assert qwen_key is not None
            qwen_base_url = settings.researchforge_qwen_base_url
            assert qwen_base_url is not None
            qwen_client = OpenAI(
                api_key=qwen_key.get_secret_value(),
                base_url=qwen_base_url,
                max_retries=0,
                timeout=120.0,
            )
            qwen_ledger = BudgetLedger(
                cap=settings.researchforge_budget_usd,
                state_path=artifact_root / "budget" / "project-qwen.json",
            )

            def create_qwen_model(
                run_id: str, remaining: Callable[[], float], usage: Json
            ) -> ModelPort:
                return QwenChatResearchModel(
                    qwen_client,
                    qwen_ledger,
                    repository,
                    run_id,
                    model=settings.researchforge_qwen_model,
                    vision_model=settings.researchforge_qwen_vision_model,
                    remaining_seconds=remaining,
                    prior_usage=usage or None,
                    run_cost_cap=settings.researchforge_v2_run_budget_usd,
                )

            factory = create_qwen_model
    else:
        ready = bool(
            ready
            and has_secret(settings.openai_api_key)
            and settings.researchforge_rotated_key_confirmed
        )
    if provider == "openai" and ready:
        from openai import OpenAI

        key = settings.openai_api_key
        assert key is not None
        client = OpenAI(api_key=key.get_secret_value(), max_retries=0, timeout=120.0)
        ledger = BudgetLedger(
            cap=settings.researchforge_budget_usd,
            state_path=artifact_root / "budget" / "project-openai.json",
        )

        def create_model(run_id: str, remaining: Callable[[], float], usage: Json) -> ModelPort:
            return ResponsesResearchModel(
                client.responses,
                ledger,
                repository,
                run_id,
                model=settings.researchforge_model,
                reasoning_effort=settings.researchforge_reasoning_effort,
                remaining_seconds=remaining,
                prior_usage=usage or None,
                run_cost_cap=settings.researchforge_v2_run_budget_usd,
            )

        factory = create_model
    return ResearchService(
        repository,
        factory,
        configuration={
            "graph_version": GRAPH_VERSION,
            "provider": provider,
            "model": selected_model,
            "vision_model": (
                settings.researchforge_qwen_vision_model if provider in {"qwen", "hybrid"} else None
            ),
            "reflection_model": (
                settings.researchforge_deepseek_model if provider == "hybrid" else None
            ),
            "synthesis_model": (
                settings.researchforge_deepseek_model if provider == "hybrid" else None
            ),
            "semantic_review_model": (
                settings.researchforge_qwen_review_model if provider == "hybrid" else None
            ),
            "research_fallback_model": (
                settings.researchforge_qwen_model if provider == "hybrid" else None
            ),
            "fallback_reflection_model": (
                settings.researchforge_qwen_fallback_synthesis_model
                if provider == "hybrid"
                else None
            ),
            "fallback_synthesis_model": (
                settings.researchforge_qwen_fallback_synthesis_model
                if provider == "hybrid"
                else None
            ),
            "fallback_semantic_review_model": (
                settings.researchforge_deepseek_model if provider == "hybrid" else None
            ),
            "reasoning_effort": settings.researchforge_reasoning_effort,
            "timeout_seconds": 900,
            "source_scope": "official_financial_filings_only",
            "per_run_estimated_cost_cap": float(settings.researchforge_v2_run_budget_usd),
            "operational_emergency_turn_limit": 128,
            "data_namespace": "product",
        },
    )
