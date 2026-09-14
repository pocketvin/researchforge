# ruff: noqa: RUF001 -- Chinese trace labels intentionally use Chinese punctuation.
"""Role-routed V2 provider: DeepSeek research/synthesis, Qwen review/vision, Kimi standby."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from openai import APIConnectionError, APITimeoutError, OpenAI
from pydantic import BaseModel

from researchforge.budget import BudgetExceededError, BudgetLedger
from researchforge.v2.contracts import (
    ClaimReview,
    Json,
    ResearchReport,
    ReviewSummary,
    SemanticReview,
    strict_schema,
)
from researchforge.v2.provider import REVIEW_POLICY, SYNTHESIS_POLICY, ContextTooLarge, _measure
from researchforge.v2.qwen_provider import (
    QWEN_REFLECTION_OUTPUT_BOUND,
    QWEN_STRUCTURED_OUTPUT_BOUND,
    QWEN_TOOL_OUTPUT_BOUND,
    QwenChatResearchModel,
)
from researchforge.v2.reporting import bound_report_schema
from researchforge.v2.storage import ResearchRepository

# These are conservative internal accounting ceilings, not billing truth. DeepSeek's
# public V4 Flash list price is lower; Kimi is deliberately over-reserved here until
# a project-frozen pricing contract is added. Product quality must not depend on this estimate.
QWEN_REVIEW_OUTPUT_BOUND = 4096


ROUTE_PRICING: dict[str, tuple[Decimal, Decimal]] = {
    "deepseek": (Decimal("0.20"), Decimal("0.50")),
    "kimi": (Decimal("1.00"), Decimal("4.00")),
    "qwen": (Decimal("0.30"), Decimal("2.50")),
}


class HybridResearchModel(QwenChatResearchModel):
    """Reuse one public research state while routing model roles independently."""

    def __init__(
        self,
        *,
        deepseek_client: OpenAI,
        kimi_client: OpenAI | None = None,
        qwen_client: OpenAI,
        ledger: BudgetLedger,
        repository: ResearchRepository,
        run_id: str,
        deepseek_model: str,
        kimi_model: str | None = None,
        qwen_research_model: str,
        qwen_text_model: str,
        qwen_fallback_synthesis_model: str,
        qwen_vision_model: str,
        remaining_seconds: Any,
        prior_usage: Json | None = None,
        run_cost_cap: Decimal = Decimal("0.50"),
    ) -> None:
        super().__init__(
            qwen_client,
            ledger,
            repository,
            run_id,
            model=deepseek_model,
            vision_model=qwen_vision_model,
            remaining_seconds=remaining_seconds,
            prior_usage=None,
            run_cost_cap=run_cost_cap,
        )
        self.deepseek_client = deepseek_client
        self.kimi_client = kimi_client
        self.qwen_client = qwen_client
        self.deepseek_model = deepseek_model
        self.kimi_model = kimi_model
        self.qwen_research_model = qwen_research_model
        self.qwen_text_model = qwen_text_model
        self.qwen_fallback_synthesis_model = qwen_fallback_synthesis_model
        self.qwen_vision_model = qwen_vision_model
        self._research_provider_fallback_seen = bool(
            (prior_usage or {}).get("research_provider_fallback_used", False)
        )
        self._usage = prior_usage or {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "provider_calls": 0,
            "failed_provider_calls": 0,
            "unconfirmed_failed_cost_ceiling": 0.0,
            "estimated_cost": 0.0,
            "cost_currency": "USD",
            "provider": "hybrid",
            "models": {
                "research": deepseek_model,
                "reflection": deepseek_model,
                "synthesis": deepseek_model,
                "research_fallback": qwen_research_model,
                "semantic_review": qwen_text_model,
                "synthesis_after_research_fallback": qwen_fallback_synthesis_model,
                "vision": qwen_vision_model,
                "kimi_standby": kimi_model if kimi_client is not None else None,
            },
            "calls_by_provider": {"deepseek": 0, "kimi": 0, "qwen": 0},
            "pricing_basis": "conservative-internal-routing-ceilings-not-billing",
        }

    @staticmethod
    def _text_only_messages(messages: list[Json]) -> list[Json]:
        cleaned: list[Json] = []
        for message in messages:
            content = message.get("content")
            if isinstance(content, list):
                text_parts = [
                    item
                    for item in content
                    if isinstance(item, dict)
                    and item.get("type") not in {"image_url", "input_image"}
                ]
                cleaned.append({**message, "content": text_parts})
            else:
                cleaned.append(dict(message))
        return cleaned

    def _route(self, operation: str, request_messages: list[Json]) -> tuple[str, str, OpenAI]:
        if self._contains_image(request_messages):
            return "qwen", self.qwen_vision_model, self.qwen_client
        if operation == "semantic_review":
            return "qwen", self.qwen_text_model, self.qwen_client
        if self._research_provider_fallback_seen and operation in {
            "state_reflection",
            "synthesis",
        }:
            return "qwen", self.qwen_fallback_synthesis_model, self.qwen_client
        if self._research_provider_fallback_seen and operation == "agent_model":
            return "qwen", self.qwen_research_model, self.qwen_client
        return "deepseek", self.deepseek_model, self.deepseek_client

    @staticmethod
    def _eligible_primary_provider_failure(exc: Exception) -> bool:
        status = getattr(exc, "status_code", None)
        return (
            isinstance(exc, (APITimeoutError, APIConnectionError, TimeoutError))
            or status in {402, 408, 429}
            or (isinstance(status, int) and status >= 500)
        )

    def synthesize(self, context: Json) -> ResearchReport:
        response = self._call(
            SYNTHESIS_POLICY,
            self._context_messages(context),
            output_model=ResearchReport,
            output_schema=bound_report_schema(context),
            operation="synthesis",
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("hybrid provider returned an empty structured research report")
        return ResearchReport.model_validate_json(content)

    @staticmethod
    def _compact_review_evidence(item: Json) -> Json:
        return {
            key: value
            for key, value in {
                "artifact_id": item.get("artifact_id"),
                "document_id": item.get("document_id"),
                "page_id": item.get("page_id"),
                "page_number": item.get("page_number"),
                "source_kind": item.get("source_kind"),
                # Evidence artifacts can be native filing tables whose decisive subtotal is
                # several thousand characters after the header. A 1,400-character head-only
                # slice made the semantic reviewer falsely reject source-linked values that
                # were present later in the exact cited artifact (for example an operating-
                # cash-flow subtotal). Keep the complete normal table/evidence slice up to a
                # bounded 6,000 characters so review sees the same cited evidence as Synthesis.
                "text": str(item.get("text", ""))[:6000],
                "image_blob_id": item.get("image_blob_id"),
            }.items()
            if value is not None
        }

    @staticmethod
    def _compact_review_fact(item: Json) -> Json:
        return {
            key: item.get(key)
            for key in (
                "fact_id",
                "metric_code",
                "value",
                "currency",
                "measurement_unit",
                "period",
                "source_locator",
            )
            if item.get(key) is not None
        }

    @staticmethod
    def _compact_review_calculation(item: Json) -> Json:
        return {
            key: item.get(key)
            for key in (
                "calculation_id",
                "formula_code",
                "value",
                "unrounded_value",
                "measurement_unit",
                "input_fact_ids",
                "input_series_ids",
                "period_label",
                "per_period",
            )
            if item.get(key) is not None
        }

    def review(self, context: Json, report: ResearchReport) -> SemanticReview:
        """Review claims independently so the product gate stays small and provider-resilient."""
        self._semantic_review_fallback_seen = False
        evidence_by_id = {item["artifact_id"]: item for item in context.get("evidence", [])}
        facts_by_id = {item["fact_id"]: item for item in context.get("financial_facts", [])}
        calculations_by_id = {
            item["calculation_id"]: item for item in context.get("calculations", [])
        }
        reviews: list[ClaimReview] = []
        for finding in report.findings:
            payload: Json = {
                "finding": finding.model_dump(mode="json"),
                "expected_claim_id": finding.claim_id,
                "evidence": [
                    self._compact_review_evidence(evidence_by_id[identifier])
                    for identifier in finding.evidence_ids
                    if identifier in evidence_by_id
                ],
                "financial_facts": [
                    self._compact_review_fact(facts_by_id[identifier])
                    for identifier in finding.fact_ids
                    if identifier in facts_by_id
                ],
                "calculations": [
                    self._compact_review_calculation(calculations_by_id[identifier])
                    for identifier in finding.calculation_ids
                    if identifier in calculations_by_id
                ],
                "semantic_review_protocol_feedback": context.get(
                    "semantic_review_protocol_feedback"
                ),
            }
            policy = (
                REVIEW_POLICY
                + "\n本次只审一个 finding。claim_id 必须原样返回 expected_claim_id；不要评价其他 "
                "finding。你不会收到整道用户问题或全局 direct_answer，这是刻意的：不要从标题、"
                "背景或常识重建整题，也不要要求这个局部 finding 单独承担全局分类结论。一个只负责"
                "报告已核验"
                "指标、来源或限制的 finding，只要它自己的断言被引用证据支持，就应按局部断言审为"
                "supported；整题是否真正回答由后面的 ReviewSummary 单独判断。若 finding.kind=limitation，"
                "请审它表达的证据边界：‘当前引用证据没有建立所需输入/基准，因此不能作更强结论’可以"
                "被支持，不要要求一段引用去证明全局不存在；只有把未观察到升级成‘整份财报不存在’等"
                "全称断言时才因缺证据降级。你的 reason 与 verdict 必须自洽，reason 若认为完整限制断言"
                "被充分支持，就必须返回 supported。若该 finding 使用财报外行业阈值、典型水平、没有证据"
                "的因果推断，或把前瞻性/结构性因素写成当期同比原因，即使方向看起来合理也必须降级。"
            )
            response = self._call(
                policy,
                self._context_messages(payload),
                output_model=ClaimReview,
                operation="semantic_review",
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("hybrid provider returned an empty claim review")
            review = ClaimReview.model_validate_json(content)
            if review.claim_id != finding.claim_id:
                raise ValueError("claim review returned a different claim_id")
            reviews.append(review)

        summary_payload: Json = {
            "question": context["request"]["research_question"],
            "direct_answer": report.direct_answer,
            "executive_summary": report.executive_summary,
            "findings": [
                {
                    "claim_id": finding.claim_id,
                    "title": finding.title,
                    "text": finding.text[:1600],
                    "review_verdict": review.verdict,
                    "review_reason": review.reason[:800],
                }
                for finding, review in zip(report.findings, reviews, strict=True)
            ],
            "limitations": report.limitations,
            "semantic_review_protocol_feedback": context.get("semantic_review_protocol_feedback"),
        }
        summary_response = self._call(
            REVIEW_POLICY
            + "\n本次只判断整题是否真正回答，以及是否遗漏重大主题；不要重新逐条审引用。",
            self._context_messages(summary_payload),
            output_model=ReviewSummary,
            operation="semantic_review",
        )
        summary_content = summary_response.choices[0].message.content
        if not summary_content:
            raise ValueError("hybrid provider returned an empty review summary")
        summary = ReviewSummary.model_validate_json(summary_content)
        return SemanticReview(
            claims=reviews,
            question_answered=summary.question_answered,
            missing_material_topics=summary.missing_material_topics,
        )

    def _reserve_route_cost(
        self, provider: str, input_bound: int, output_bound: int
    ) -> tuple[str, Decimal]:
        input_rate, output_rate = ROUTE_PRICING[provider]
        worst = (Decimal(input_bound) * input_rate + Decimal(output_bound) * output_rate) / Decimal(
            1_000_000
        )
        spent = Decimal(str(self._usage.get("estimated_cost", 0)))
        if spent + worst > self.run_cost_cap:
            raise BudgetExceededError("V2 hybrid per-run safety budget would be exceeded")
        return self.ledger.reserve(worst), worst

    def _complete_route_usage(
        self,
        response: Any,
        reservation: str,
        worst: Decimal,
        provider: str,
        model: str,
    ) -> None:
        usage = response.usage
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        input_rate, output_rate = ROUTE_PRICING[provider]
        actual = (
            Decimal(input_tokens) * input_rate + Decimal(output_tokens) * output_rate
        ) / Decimal(1_000_000)
        if actual > worst:
            self.ledger.complete(reservation, worst)
            raise BudgetExceededError("provider usage exceeded the hybrid reservation")
        self.ledger.complete(reservation, actual)
        self._usage["input_tokens"] = int(self._usage.get("input_tokens", 0)) + input_tokens
        self._usage["output_tokens"] = int(self._usage.get("output_tokens", 0)) + output_tokens
        self._usage["total_tokens"] = (
            int(self._usage.get("total_tokens", 0)) + input_tokens + output_tokens
        )
        self._usage["provider_calls"] = int(self._usage.get("provider_calls", 0)) + 1
        by_provider = dict(self._usage.get("calls_by_provider", {}))
        by_provider[provider] = int(by_provider.get(provider, 0)) + 1
        self._usage["calls_by_provider"] = by_provider
        self._usage["estimated_cost"] = float(
            Decimal(str(self._usage.get("estimated_cost", 0))) + actual
        )
        self.repository.update(self.run_id, usage=self.usage)
        self.repository.emit(
            self.run_id,
            "model_usage",
            provider,
            f"{provider} 模型调用已返回",
            "succeeded",
            data={
                "provider": provider,
                "model": getattr(response, "model", model),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost": float(actual),
                "pricing_is_billing_truth": False,
            },
        )

    def _call(
        self,
        instructions: str,
        messages: list[Json],
        *,
        tools: list[Json] | None = None,
        output_model: type[BaseModel] | None = None,
        output_schema: Json | None = None,
        operation: str,
    ) -> Any:
        request_messages: list[Json] = [{"role": "system", "content": instructions}, *messages]
        if operation == "synthesis":
            # The agent may have inspected page images, but final prose synthesis uses the
            # persisted text/source representation. Vision remains available to Agent turns
            # and semantic review when a claim actually cites visual evidence.
            request_messages = self._text_only_messages(request_messages)
        provider, model, client = self._route(operation, request_messages)
        if tools is None and output_model is not None and provider == "deepseek":
            request_messages[0]["content"] = (
                instructions
                + "\n只输出一个符合以下 JSON Schema 的对象；不要添加 Markdown 或额外字段：\n"
                + json.dumps(output_schema or strict_schema(output_model), ensure_ascii=False)
            )
        output_bound = (
            QWEN_TOOL_OUTPUT_BOUND
            if tools is not None
            else (
                QWEN_REFLECTION_OUTPUT_BOUND
                if operation == "state_reflection"
                else QWEN_REVIEW_OUTPUT_BOUND
                if operation in {"semantic_review", "semantic_review_fallback"}
                else QWEN_STRUCTURED_OUTPUT_BOUND
            )
        )
        text_bound, image_count = _measure(request_messages)
        input_bound = text_bound + image_count * 10000
        if input_bound > 140000:
            raise ContextTooLarge("混合模型 context 过大，请缩小研究摘要或重新读取精确证据。")
        reservation, worst = self._reserve_route_cost(provider, input_bound, output_bound)
        params: Json = {"model": model, "messages": request_messages}
        # The active hybrid route uses deterministic-style DeepSeek/Qwen calls.
        params["temperature"] = 0
        if tools is not None:
            params.update(
                {
                    "tools": tools,
                    "tool_choice": "required",
                    "parallel_tool_calls": False,
                }
            )
            if provider == "deepseek":
                params["max_tokens"] = QWEN_TOOL_OUTPUT_BOUND
                params["extra_body"] = {"thinking": {"type": "disabled"}}
            else:
                params["max_completion_tokens"] = QWEN_TOOL_OUTPUT_BOUND
        else:
            assert output_model is not None
            if provider == "qwen":
                params["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": output_model.__name__,
                        "strict": True,
                        "schema": output_schema or strict_schema(output_model),
                    },
                }
                params["max_completion_tokens"] = output_bound
            else:
                params["response_format"] = {"type": "json_object"}
                params["extra_body"] = {"thinking": {"type": "disabled"}}
                params["max_tokens"] = output_bound
        labels = {
            "agent_model": "DeepSeek 决定下一步研究动作",
            "state_reflection": "DeepSeek 整理公开研究状态",
            "synthesis": "DeepSeek 撰写结构化研究报告",
            "semantic_review": "Qwen 独立核查结论与证据",
            "semantic_review_fallback": "DeepSeek 执行降级语义复核",
        }
        if provider == "qwen" and model == self.qwen_vision_model:
            labels[operation] = "Qwen3-VL 核查财报原页"
        elif provider == "qwen":
            labels[operation] = "Qwen 独立核查结论与证据"
        timeout_cap = (
            35.0
            if operation == "state_reflection"
            else 25.0
            if operation in {"semantic_review", "semantic_review_fallback"}
            else 120.0
        )
        with self.repository.span(
            self.run_id,
            operation,
            labels[operation],
            data={"provider": provider, "model": model},
        ):
            try:
                response = client.chat.completions.create(
                    **params,
                    timeout=max(1.0, min(timeout_cap, self.remaining_seconds())),
                )
            except Exception as exc:
                self._record_failed_request(
                    reservation,
                    worst,
                    provider=provider,
                    model=model,
                    operation=operation,
                    error=exc,
                )
                if (
                    provider == "deepseek"
                    and operation in {"agent_model", "state_reflection", "synthesis"}
                    and self._eligible_primary_provider_failure(exc)
                ):
                    self._research_provider_fallback_seen = True
                    self._usage["research_provider_fallback_used"] = True
                    fallback_model = (
                        self.qwen_fallback_synthesis_model
                        if operation in {"state_reflection", "synthesis"}
                        else self.qwen_research_model
                    )
                    self.repository.update(self.run_id, usage=self.usage)
                    self.repository.emit(
                        self.run_id,
                        "research_provider_fallback",
                        operation,
                        "DeepSeek 当前不可用，本 Run 切换到分角色 Qwen 降级链路",
                        "needs_attention",
                        data={
                            "from_provider": "deepseek",
                            "from_model": model,
                            "to_provider": "qwen",
                            "to_model": fallback_model,
                            "error_type": type(exc).__name__,
                            "status_code": getattr(exc, "status_code", None),
                            "silent": False,
                        },
                    )
                    return self._call(
                        instructions,
                        messages,
                        tools=tools,
                        output_model=output_model,
                        output_schema=output_schema,
                        operation=operation,
                    )
                if (
                    operation == "semantic_review"
                    and provider == "qwen"
                    and model == self.qwen_text_model
                    and image_count == 0
                ):
                    self._semantic_review_fallback_seen = True
                    self.repository.emit(
                        self.run_id,
                        "semantic_review_provider_fallback",
                        "semantic_review",
                        "Qwen 复核未返回，改用 DeepSeek 降级复核",
                        "needs_attention",
                        data={
                            "from_provider": "qwen",
                            "to_provider": "deepseek",
                            "error_type": type(exc).__name__,
                            "independence": "reduced_same_provider",
                        },
                    )
                    return self._call(
                        instructions,
                        messages,
                        tools=tools,
                        output_model=output_model,
                        output_schema=output_schema,
                        operation="semantic_review_fallback",
                    )
                raise
            self._complete_route_usage(response, reservation, worst, provider, model)
            if operation == "semantic_review":
                semantic_fallback = bool(getattr(self, "_semantic_review_fallback_seen", False))
                research_fallback = self._research_provider_fallback_seen
                if semantic_fallback:
                    independence = "reduced_same_provider"
                elif research_fallback:
                    independence = "different_model_from_synthesis_same_provider"
                else:
                    independence = "independent_provider"
                self._review_metadata = {
                    "provider": provider,
                    "model": model,
                    "independence": independence,
                    "fallback_used": semantic_fallback,
                    "research_provider_fallback_used": research_fallback,
                    "strategy": "claim_wise_then_summary",
                }
            elif operation == "semantic_review_fallback":
                self._review_metadata = {
                    "provider": provider,
                    "model": model,
                    "independence": "reduced_same_provider",
                    "fallback_used": True,
                }
            return response
