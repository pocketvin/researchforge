"""Plain earnings-quality services used by the LangGraph thin slice."""

# ruff: noqa: RUF001 -- persisted/user-facing Chinese prose uses Chinese punctuation.

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, ClassVar, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from researchforge.domain.finance import (
    FORMULA_VERSION,
    cash_conversion,
    gross_margin,
    gross_profit,
    growth_rate,
    profit_cash_divergence,
)
from researchforge.domain.models import CalculationResult, CalculationStatus


class InsufficientDataError(ValueError):
    """A safe research outcome caused by unavailable mandatory inputs."""


class StructuredOutputError(ValueError):
    """Model output failed the bounded structured-output contract."""


@dataclass(frozen=True, slots=True)
class LoadedResearchData:
    """Frozen facts and sources selected at the research cutoff."""

    facts: tuple[dict[str, Any], ...]
    source_documents: tuple[dict[str, Any], ...]
    requested_periods: tuple[dict[str, Any], ...]
    companies: tuple[dict[str, Any], ...]
    evidence_chunks: tuple[dict[str, Any], ...] = ()


class ConclusionDraft(BaseModel):
    """Small model-facing boundary; calculations and citations stay deterministic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    executive_summary: str = Field(min_length=1, max_length=4000)
    earnings_quality_text: str = Field(min_length=1, max_length=2000)
    gross_margin_text: str = Field(min_length=1, max_length=2000)
    limitations: list[str] = Field(max_length=10)
    reported_check_codes: (
        list[
            Literal[
                "operating_cash_flow",
                "accounts_receivable",
                "inventory",
                "cash_conversion",
                "profit_cash_divergence",
                "one_off_contribution",
                "counter_evidence",
            ]
        ]
        | None
    ) = Field(max_length=7)


class GeneralFindingDraft(BaseModel):
    """One evidence-linked analytical finding proposed by the V1.7 language layer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1, max_length=220)
    text: str = Field(min_length=1, max_length=2200)
    evidence_ids: list[str] = Field(min_length=1, max_length=5)
    fact_ids: list[str] = Field(max_length=6)
    claim_type: Literal[
        "observation",
        "comparison",
        "driver",
        "earnings_quality",
        "risk",
        "outlook",
        "limitation",
    ]
    epistemic_status: Literal[
        "verified_fact",
        "supported_inference",
        "causal_hypothesis",
        "uncertain",
        "limitation",
    ]
    confidence: Literal["high", "medium", "low"]
    direction: Literal["positive", "negative", "mixed", "neutral"]


class GeneralAnalysisSectionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=5000)
    evidence_ids: list[str] = Field(min_length=1, max_length=8)


class GeneralResearchDraft(BaseModel):
    """Question-aware research language over selected official filing evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    executive_summary: str = Field(min_length=1, max_length=8000)
    findings: list[GeneralFindingDraft] = Field(min_length=2, max_length=8)
    deep_analysis: list[GeneralAnalysisSectionDraft] = Field(min_length=2, max_length=6)
    limitations: list[str] = Field(max_length=12)
    suggested_follow_ups: list[str] = Field(min_length=4, max_length=6)
    overall_judgment: Literal[
        "Strongly Supported",
        "Supported",
        "Mixed",
        "Weak Evidence",
        "Insufficient Evidence",
        "AI Synthesis Unavailable",
    ]
    overall_judgment_rationale: str = Field(min_length=1, max_length=2200)


ResearchLanguageDraft = ConclusionDraft | GeneralResearchDraft


class ConclusionGenerator(Protocol):
    """Port implemented by deterministic tests or the OpenAI Responses adapter."""

    def generate(self, context: dict[str, Any]) -> ResearchLanguageDraft:
        """Generate bounded language from supplied, precomputed evidence only."""

        ...


class DeterministicConclusionGenerator:
    """Offline adapter used for tests, demos, and zero-cost development."""

    def generate(self, context: dict[str, Any]) -> ResearchLanguageDraft:
        if context.get("response_contract") == "general_research_v1_7":
            return self._generate_general(context)
        company = context["company"]["legal_name"]
        period = context["period_label"]
        conversion = context.get("cash_conversion_display", f"{context['cash_conversion']}倍")
        margin = context["gross_margin"]
        divergence = context["divergence_triggered"]
        real_disclosure = bool(context.get("real_disclosure_evidence"))
        divergence_text = (
            "触发利润与现金流背离信号"
            if divergence
            else "未触发预设的背离信号"
            if real_disclosure
            else "未触发冻结的背离信号"
        )
        limitations = (
            [
                "当前结论仅覆盖所选期间已哈希核验的官方报告和六项财务事实。",
                "一次性损益未纳入确定性公式; 反证与审计边界以实际来源证据为准。",
                str(context.get("counter_evidence", {}).get("summary", "反证搜索状态未提供。")),
                "单一报告期的现金转化不能证明长期收益质量, 需在下一同口径报告期复核。",
            ]
            if real_disclosure
            else [
                "当前薄切片只使用冻结的规范化财务事实和来源定位。",
                "未检索公告全文, 因此反证搜索结果只能标记为在当前证据包中未发现。",
                "当前事实包没有一次性损益贡献字段, 该项检查不可用且未作推断。",
            ]
        )
        return ConclusionDraft(
            executive_summary=(
                f"{company}{period}经营现金流/净利润为{conversion}, 毛利率为{margin}; "
                f"{divergence_text}。结论仅覆盖"
                f"{'已核验财务事实' if real_disclosure else '冻结财务事实'}, 不构成投资建议。"
            ),
            earnings_quality_text=(
                f"经营现金流与净利润的现金转化比为{conversion}, {divergence_text}。"
            ),
            gross_margin_text=f"按营业收入减营业成本计算, {period}毛利率为{margin}。",
            limitations=limitations,
            reported_check_codes=None,
        )

    @staticmethod
    def _generate_general(context: dict[str, Any]) -> GeneralResearchDraft:
        """Return an explicit evidence-summary fallback, never a faux research report."""
        evidence = list(context.get("selected_evidence", []))
        question = str(context.get("research_question", "公司基本面如何？"))
        if len(evidence) < 2:
            raise InsufficientDataError(
                "General research requires at least two filing evidence chunks."
            )

        section_items: dict[str, dict[str, Any]] = {}
        for item in evidence:
            section_items.setdefault(str(item.get("section", "官方披露")), item)
        findings: list[GeneralFindingDraft] = []
        for section, item in list(section_items.items())[:4]:
            page = item.get("locator", {}).get("page_start")
            page_text = f"P{page}" if page is not None else "已定位位置"
            findings.append(
                GeneralFindingDraft(
                    title=f"已定位 {section} 的官方证据",
                    text=(
                        f"ResearchForge 已核验与当前问题相关的官方披露（{page_text}）。"
                        "当前运行未执行模型综合，因此不会把该片段自动升级为经营判断；"
                        "请在 Supporting Evidence 中查看原始证据。"
                    ),
                    evidence_ids=[str(item["chunk_id"])],
                    fact_ids=[],
                    claim_type="limitation",
                    epistemic_status="limitation",
                    confidence="medium",
                    direction="neutral",
                )
            )
        while len(findings) < 2:
            item = evidence[len(findings)]
            findings.append(
                GeneralFindingDraft(
                    title="已定位额外官方证据",
                    text="该证据已通过来源与哈希链路核验，但当前未执行 AI 综合分析。",
                    evidence_ids=[str(item["chunk_id"])],
                    fact_ids=[],
                    claim_type="limitation",
                    epistemic_status="limitation",
                    confidence="medium",
                    direction="neutral",
                )
            )

        coverage_ids = [str(item["chunk_id"]) for item in evidence[:8]]
        sections = [
            GeneralAnalysisSectionDraft(
                title="当前可验证的证据范围",
                text=(
                    "已定位的官方披露覆盖："
                    + "、".join(list(section_items)[:8])
                    + "。这些内容可以审计，但在没有模型综合时不自动等同于研究结论。"
                ),
                evidence_ids=coverage_ids[:4],
            ),
            GeneralAnalysisSectionDraft(
                title="为什么没有生成完整研究判断",
                text=(
                    "当前运行处于 Verified Evidence Summary fallback。系统宁可明确降级，"
                    "也不会把财报原文摘录伪装成业绩归因、风险排序或管理层展望判断。"
                ),
                evidence_ids=coverage_ids[4:8] or coverage_ids[:2],
            ),
        ]
        follow_ups = list(context.get("suggested_follow_ups", []))[:6]
        while len(follow_ups) < 4:
            follow_ups.append(f"围绕“{question}”还需要补充哪些官方证据？")
        return GeneralResearchDraft(
            executive_summary=(
                "当前仅生成 Verified Evidence Summary，未执行 AI Research Synthesis。"
                f"系统已定位 {len(evidence)} 条与问题相关的官方证据，但不会把原始披露摘录"
                "冒充完整公司分析。请在模型综合可用后重新运行，或展开 Evidence/Trace 审计当前证据。"
            ),
            findings=findings,
            deep_analysis=sections,
            limitations=[
                "当前运行未执行 AI Research Synthesis；主报告仅为已核验证据摘要。",
                "证据相关性不自动等于因果关系、增长归因或风险重要性判断。",
                str(context.get("counter_evidence", {}).get("summary", "反向证据状态未提供。")),
            ],
            suggested_follow_ups=follow_ups,
            overall_judgment="AI Synthesis Unavailable",
            overall_judgment_rationale=(
                "官方证据本身可追溯，但当前没有执行模型综合；因此不能把证据集合包装成完整研究判断。"
            ),
        )


@dataclass(frozen=True, slots=True)
class EarningsQualityAnalysis:
    """Deterministic analysis outputs consumed by conclusion assembly."""

    current_facts: tuple[dict[str, Any], ...]
    calculation_records: tuple[dict[str, Any], ...]
    mandatory_checks: tuple[dict[str, Any], ...]
    context: dict[str, Any]


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _calculation_record(
    run_id: str,
    calculation_id: str,
    result: CalculationResult,
    fact_ids: list[str],
    created_at: str,
    *,
    formula_code: str | None = None,
) -> dict[str, Any]:
    unit = result.measurement_unit.value if result.measurement_unit is not None else None
    return {
        "schema_version": "1.4.0",
        "calculation_id": calculation_id,
        "run_id": run_id,
        "formula_code": formula_code or result.formula_code,
        "formula_version": FORMULA_VERSION,
        "input_fact_ids": fact_ids,
        "status": result.status.value,
        "value": _decimal_text(result.value) if result.value is not None else None,
        "measurement_unit": unit,
        "explanation": result.explanation,
        "created_at": created_at,
    }


class EarningsQualityAnalyzer:
    """Run frozen formulas without importing LangGraph or any model SDK."""

    required_metrics: ClassVar[set[str]] = {
        "revenue",
        "operating_cost",
        "net_income",
        "operating_cash_flow",
        "accounts_receivable",
        "inventory",
    }

    def analyze(
        self,
        run_id: str,
        loaded: LoadedResearchData,
        created_at: datetime,
        *,
        artifact_namespace: str | None = None,
    ) -> EarningsQualityAnalysis:
        if not loaded.facts:
            raise InsufficientDataError("No eligible financial facts were loaded.")
        latest_period = max(fact["period"]["period_end"] for fact in loaded.facts)
        current = tuple(
            fact for fact in loaded.facts if fact["period"]["period_end"] == latest_period
        )
        by_metric = {fact["metric_code"]: fact for fact in current}
        earlier_periods = sorted(
            {
                fact["period"]["period_end"]
                for fact in loaded.facts
                if fact["period"]["period_end"] < latest_period
            }
        )
        previous = tuple(
            fact
            for fact in loaded.facts
            if earlier_periods and fact["period"]["period_end"] == earlier_periods[-1]
        )
        previous_by_metric = {fact["metric_code"]: fact for fact in previous}
        missing = sorted(self.required_metrics - set(by_metric))
        if missing:
            raise InsufficientDataError("Missing mandatory metrics: " + ", ".join(missing))

        def value(metric: str) -> Decimal:
            raw_value = by_metric[metric]["value"]
            if raw_value is None:
                raise InsufficientDataError(f"Mandatory metric {metric} is unavailable.")
            return Decimal(raw_value)

        gross_profit_result = gross_profit(value("revenue"), value("operating_cost"))
        assert gross_profit_result.value is not None
        gross_margin_result = gross_margin(gross_profit_result.value, value("revenue"))
        conversion_result = cash_conversion(
            value("operating_cash_flow"),
            value("net_income"),
        )
        divergence_result = profit_cash_divergence(
            value("net_income"),
            value("operating_cash_flow"),
        )
        mandatory_calculated = (
            gross_profit_result,
            gross_margin_result,
            divergence_result,
        )
        if any(
            result.status is not CalculationStatus.CALCULATED for result in mandatory_calculated
        ) or conversion_result.status not in {
            CalculationStatus.CALCULATED,
            CalculationStatus.NOT_MEANINGFUL,
        }:
            raise InsufficientDataError("A mandatory deterministic calculation was unavailable.")

        timestamp = created_at.isoformat()
        namespace = artifact_namespace or run_id
        calculation_items = [
            _calculation_record(
                run_id,
                f"calc_{namespace}_gross_profit",
                gross_profit_result,
                [by_metric["revenue"]["fact_id"], by_metric["operating_cost"]["fact_id"]],
                timestamp,
            ),
            _calculation_record(
                run_id,
                f"calc_{namespace}_gross_margin",
                gross_margin_result,
                [by_metric["revenue"]["fact_id"], by_metric["operating_cost"]["fact_id"]],
                timestamp,
            ),
            _calculation_record(
                run_id,
                f"calc_{namespace}_cash_conversion",
                conversion_result,
                [
                    by_metric["operating_cash_flow"]["fact_id"],
                    by_metric["net_income"]["fact_id"],
                ],
                timestamp,
            ),
            _calculation_record(
                run_id,
                f"calc_{namespace}_profit_cash_divergence",
                divergence_result,
                [
                    by_metric["net_income"]["fact_id"],
                    by_metric["operating_cash_flow"]["fact_id"],
                ],
                timestamp,
            ),
        ]
        trend_results: dict[str, CalculationResult] = {}
        for metric, formula_code in (
            ("revenue", "revenue_growth"),
            ("net_income", "profit_growth"),
        ):
            if metric not in previous_by_metric:
                continue
            trend = growth_rate(value(metric), Decimal(previous_by_metric[metric]["value"]))
            trend_results[metric] = trend
            calculation_items.append(
                _calculation_record(
                    run_id,
                    f"calc_{namespace}_{formula_code}",
                    trend,
                    [by_metric[metric]["fact_id"], previous_by_metric[metric]["fact_id"]],
                    timestamp,
                    formula_code=formula_code,
                )
            )
        calculations = tuple(calculation_items)
        checks = (
            self._fact_check("operating_cash_flow", by_metric, "已核对经营活动现金流。"),
            self._fact_check("accounts_receivable", by_metric, "已核对应收账款期末余额。"),
            self._fact_check("inventory", by_metric, "已核对存货期末余额。"),
            self._calculation_check(
                "gross_margin", by_metric, gross_margin_result, "毛利率由确定性公式计算。"
            ),
            self._calculation_check(
                "cash_conversion", by_metric, conversion_result, conversion_result.explanation
            ),
            self._calculation_check(
                "profit_cash_divergence",
                by_metric,
                divergence_result,
                divergence_result.explanation,
            ),
            {
                "check_code": "one_off_contribution",
                "status": "unavailable",
                "fact_ids": [],
                "evidence_ids": [],
                "finding": "当前事实集没有一次性损益贡献字段, 未作推断。",
            },
            self._trend_check(
                "revenue_trend", "revenue", by_metric, previous_by_metric, trend_results
            ),
            self._trend_check(
                "profit_trend", "net_income", by_metric, previous_by_metric, trend_results
            ),
        )
        company = current[0]["company"]
        period = current[0]["period"]
        assert gross_margin_result.value is not None
        assert divergence_result.value is not None
        if conversion_result.value is None:
            conversion_value = "not_meaningful"
            conversion_display = "不适用(净利润为零或负数)"
        else:
            conversion_value = f"{conversion_result.value.quantize(Decimal('0.01'))}"
            conversion_display = f"{conversion_value}倍"
        context = {
            "company": company,
            "period_label": f"{period['fiscal_year']}{period['fiscal_period']}",
            "cash_conversion": conversion_value,
            "cash_conversion_display": conversion_display,
            "cash_conversion_status": conversion_result.status.value,
            "gross_margin": (
                f"{(gross_margin_result.value * Decimal(100)).quantize(Decimal('0.01'))}%"
            ),
            "divergence_triggered": divergence_result.value == Decimal(1),
            "operating_cash_flow": _decimal_text(value("operating_cash_flow")),
            "net_income": _decimal_text(value("net_income")),
            "accounts_receivable": _decimal_text(value("accounts_receivable")),
            "inventory": _decimal_text(value("inventory")),
            "one_off_contribution_available": False,
            "revenue_growth": self._trend_text(trend_results.get("revenue")),
            "profit_growth": self._trend_text(trend_results.get("net_income")),
            "real_disclosure_evidence": bool(loaded.evidence_chunks)
            and all(
                "SYNTHETIC PUBLIC EVIDENCE" not in str(chunk.get("text", ""))
                for chunk in loaded.evidence_chunks
            ),
        }
        return EarningsQualityAnalysis(
            current_facts=current,
            calculation_records=calculations,
            mandatory_checks=checks,
            context=context,
        )

    @staticmethod
    def _trend_text(result: CalculationResult | None) -> str:
        if result is None or result.value is None:
            return "unavailable"
        return f"{(result.value * Decimal(100)).quantize(Decimal('0.01'))}%"

    @staticmethod
    def _trend_check(
        code: str,
        metric: str,
        current: dict[str, dict[str, Any]],
        previous: dict[str, dict[str, Any]],
        results: dict[str, CalculationResult],
    ) -> dict[str, Any]:
        result = results.get(metric)
        if result is None or metric not in previous:
            return {
                "check_code": code,
                "status": "unavailable",
                "fact_ids": [current[metric]["fact_id"]],
                "evidence_ids": [],
                "finding": "当前请求没有较早同口径期间, 未生成趋势。",
            }
        return {
            "check_code": code,
            "status": (
                "performed" if result.status is CalculationStatus.CALCULATED else "unavailable"
            ),
            "fact_ids": [current[metric]["fact_id"], previous[metric]["fact_id"]],
            "evidence_ids": [],
            "finding": result.explanation,
        }

    @staticmethod
    def _fact_check(
        code: str,
        by_metric: dict[str, dict[str, Any]],
        finding: str,
    ) -> dict[str, Any]:
        return {
            "check_code": code,
            "status": "performed",
            "fact_ids": [by_metric[code]["fact_id"]],
            "evidence_ids": [],
            "finding": finding,
        }

    @staticmethod
    def _calculation_check(
        code: str,
        by_metric: dict[str, dict[str, Any]],
        result: CalculationResult,
        finding: str,
    ) -> dict[str, Any]:
        metric_map = {
            "gross_margin": ("revenue", "operating_cost"),
            "cash_conversion": ("operating_cash_flow", "net_income"),
            "profit_cash_divergence": ("net_income", "operating_cash_flow"),
        }
        return {
            "check_code": code,
            "status": (
                "performed"
                if result.status is CalculationStatus.CALCULATED
                else "not_applicable"
                if result.status is CalculationStatus.NOT_MEANINGFUL
                else "unavailable"
            ),
            "fact_ids": [by_metric[metric]["fact_id"] for metric in metric_map[code]],
            "evidence_ids": [],
            "finding": finding,
        }
