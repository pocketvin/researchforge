# ruff: noqa: RUF001 -- Chinese product copy intentionally uses Chinese punctuation.
"""Capability boundary: model requests are validated against one run-
owned filing universe."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import cast

from pydantic import BaseModel, ValidationError

from researchforge.adapters.storage import payload_sha256
from researchforge.v2.compute import FORMULAS, calculate
from researchforge.v2.contracts import (
    CalculateInput,
    Contract,
    CounterInput,
    FactsInput,
    ImageInput,
    Json,
    ReadInput,
    ResearchRequest,
    SearchInput,
    SeriesCalculateInput,
    SeriesExtractInput,
    Submission,
    WorkingState,
    strict_schema,
)
from researchforge.v2.documents import render_page, search_objects, terms
from researchforge.v2.numeric_provenance import unsupported_percentages
from researchforge.v2.preparation import FilingPreparer
from researchforge.v2.series import (
    SERIES_FORMULAS,
    SERIES_METRICS,
    calculate_series_metric,
    extract_statement_series,
)
from researchforge.v2.storage import ResearchRepository


class EmptyInput(Contract):
    pass


class AddFilingInput(Contract):
    period_label: str


TOOL_MODELS: dict[str, tuple[type[BaseModel], str, str]] = {
    "list_filings": (
        EmptyInput,
        "List all loaded official filings and their extraction limitations; no open web.",
        "查看财报目录",
    ),
    "search_filing": (
        SearchInput,
        (
            "Search complete loaded documents by lexical query at "
            "page/section/table/evidence granularity. Returns previews, not the"
            " whole universe. Broaden/rephrase a query or inspect an original "
            "when evidence is insufficient."
        ),
        "检索财报内容",
    ),
    "read_filing": (
        ReadInput,
        (
            "Read a document, page, table, figure descriptor, footnote or "
            "evidence by artifact_id. offset/max_chars permit full-document "
            "access without silent truncation. Cite the returned evidence_id."
        ),
        "阅读原文与表格",
    ),
    "inspect_page_image": (
        ImageInput,
        (
            "View the actual PDF page image, including vector charts, merged "
            "headers and footnotes. Image interpretations are not automatically"
            " verified financial facts."
        ),
        "核查财报页面图像",
    ),
    "get_financial_facts": (
        FactsInput,
        (
            "Read only native-verified financial facts, preserving "
            "currency/period/scope. Empty filters mean all. The response "
            "explicitly reports missing requested period labels; use add_filing "
            "when a comparison period is not loaded. Missing metrics are "
            "unavailable; never invent them."
        ),
        "读取规范财务事实",
    ),
    "calculate_metric": (
        CalculateInput,
        (
            "Compute with two verified fact IDs. For changes: current then "
            "prior, same metric and fiscal basis. gross_profit/gross_margin: "
            "revenue then operating_cost. cash_conversion: operating_cash_flow "
            "then net_income. Uses local Decimal rules, not model arithmetic."
        ),
        "执行确定性财务计算",
    ),
    "extract_statement_series": (
        SeriesExtractInput,
        (
            "Deterministically extract a multi-year numeric row from one native-text filing "
            "page or native HTML table. Supply the exact artifact_id returned by search/read, "
            "the exact visible row label, and its financial metric; never invent a page ID. "
            "The system—not the model—maps fiscal-year headers, signs and scale, creates a "
            "run-owned verified series, and returns precise source evidence. Use this when "
            "the value exists in a statement table but is not already a canonical fact."
        ),
        "从财报原页核验多期数值",
    ),
    "calculate_series_metric": (
        SeriesCalculateInput,
        (
            "Run deterministic arithmetic over verified statement-series IDs. Arguments are "
            "exactly formula, series_ids, round_decimals and period_label; do not use legacy "
            "metric/numerator_series_id/denominator_series_id names. ratio_percent expects "
            "series_ids=[numerator, denominator] plus a period_label when multiple periods are "
            "present. average_ratio_percent uses series_ids=[numerator, denominator] and averages "
            "matching period ratios; period_label must be null. flow_to_average_balance_percent "
            "expects [flow, balance] (for ROA, net_income then total_assets). "
            "average_balance_to_flow_percent expects [balance, flow] and is used for capital-"
            "intensity measures such as average net PP&E / revenue or average total assets / "
            "revenue. average/sum expect one series. Currency/scale compatibility is enforced. "
            "Never pass raw model numbers. A formula + series_ids + period_label tuple is one "
            "semantic calculation: changing only round_decimals reuses the existing calculation "
            "instead of creating precision variants. Use the returned unrounded_value when more "
            "precision is needed; do not repeatedly call the tool at different rounding levels."
        ),
        "对核验数值序列做确定性计算",
    ),
    "search_counter_evidence": (
        CounterInput,
        (
            "Search for a specific hypothesis's alternatives/counter-evidence "
            "in the full filing universe. Supply a targeted query, not just "
            "generic risk words. Search results do not by themselves prove a "
            "contradiction."
        ),
        "寻找相反证据与替代解释",
    ),
    "update_research_state": (
        WorkingState,
        (
            "Replace the explicit public research notebook: hypotheses, "
            "support/against evidence, open questions and a short action "
            "summary. No hidden reasoning. References must be observed "
            "evidence/facts/calculations."
        ),
        "更新研究假设与待查问题",
    ),
    "add_filing": (
        AddFilingInput,
        (
            "Load another period's official financial filing of the SAME "
            "issuer, under the SAME cutoff. Use a label such as 2024FY or "
            "2025H1. No news or external research."
        ),
        "补充同公司其他报告期",
    ),
    "submit_research": (
        Submission,
        (
            "End research when evidence is sufficient or filing evidence is "
            "exhausted. evidence_ids normally contain observed evidence IDs. When a "
            "conclusion comes from a run-owned verified fact, statement series, or "
            "calculation, that lineage ID may also be supplied; ResearchForge resolves "
            "it deterministically to the actually observed source evidence and rejects "
            "unknown or unresolvable references. Explain why further research is "
            "unlikely to change the answer, and explicitly preserve unresolved"
            " limitations. For a binary user question, set direct_answer to yes/no/mixed or "
            "cannot_determine. For every non-binary question (amount/date/entity/why/what/how), "
            "direct_answer MUST be not_applicable; put the actual amount/date/textual answer in "
            "summary instead. Use mixed only when material evidence genuinely supports both "
            "sides; do not use it merely to avoid making the requested yes/no judgment. This is "
            "a dossier submission, not the final prose report. Keep summary <= 4000 characters "
            "(prefer roughly 1000-2500): summarize the required conclusions and evidence boundary "
            "rather than restating every table row. If the tool returns summary:string_too_long, "
            "retry submit_research with a shorter summary; do not perform more research merely to "
            "repair the submission shape."
        ),
        "提交研究成果",
    ),
}

# Public-state mutation is owned by the Runtime reflection node, not the ordinary model Tool Loop.
# Keep update_research_state for recovery/tests, but never advertise it as an Agent Tool.
AGENT_TOOL_NAMES = frozenset(TOOL_MODELS) - {"update_research_state"}


def tool_definitions(allowed_names: set[str] | None = None) -> list[Json]:
    return [
        {
            "type": "function",
            "name": name,
            "description": description,
            "parameters": strict_schema(model),
            "strict": True,
        }
        for name, (model, description, _label) in TOOL_MODELS.items()
        if allowed_names is None or name in allowed_names
    ]


def _analytical_question(question: str) -> bool:
    probe = question.casefold()
    return any(
        marker in probe
        for marker in (
            "为什么",
            "分析",
            "原因",
            "风险",
            "驱动",
            "匹配",
            "why",
            "explain",
            "cause",
            "risk",
            "driver",
            "drove",
            "driven",
            "driving",
            "contribution",
            "contributed",
            "quality",
            "healthy",
            "assess",
            "assessment",
            "evaluate",
            "evaluation",
            "interpret",
            "interpretation",
            "评估",
            "评价",
            "解读",
            "capital-intensive",
            "capital intensive",
            "是否",
        )
    )


def _cash_flow_health_question(question: str) -> bool:
    probe = question.casefold()
    cash_flow = any(marker in probe for marker in ("cash flow", "cashflow", "现金流"))
    health = any(
        marker in probe
        for marker in (
            "healthy",
            "health",
            "quality",
            "健康",
            "质量",
            "是否健康",
            "是否良好",
        )
    )
    return cash_flow and health


def _soften_limited_absence_language(text: str) -> str:
    """Keep evidence-limited notebook prose from turning non-observation into nonexistence.

    This runs only on objectives already marked ``limited``. It does not manufacture a finding or
    change a positive factual assertion; it narrows global absence wording to the epistemic scope
    that the runtime actually knows: the evidence cited/observed in this run.
    """

    value = str(text)
    replacements: tuple[tuple[str, str], ...] = (
        (
            r"\bthe filing does not (?:disclose|report|present|contain|provide|include|show)\b",
            "the cited evidence does not establish",
        ),
        (r"\bthe filing contains no\b", "the cited evidence does not establish"),
        (r"\bthe filing provides no\b", "the cited evidence does not establish"),
        (r"\bthe filing has no\b", "the cited evidence does not establish"),
        (
            r"\bno ([^.\n]{1,140}?) (?:is|are) present in the filing\b",
            r"the cited evidence does not establish \1",
        ),
        (
            r"\bno ([^.\n]{1,140}?) exists? in the filing\b",
            r"the cited evidence does not establish \1",
        ),
        (r"财报(?:中)?未披露", "当前引用证据未建立"),
        (r"财报(?:中)?没有", "当前引用证据未显示"),
        (r"财报(?:中)?不存在", "当前引用证据未建立"),
        (r"整份财报(?:中)?没有", "当前引用证据未显示"),
        (r"整份财报(?:中)?不存在", "当前引用证据未建立"),
    )
    for pattern, replacement in replacements:
        value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
    return value


def _focused_question_does_not_request_percentage(question: str) -> bool:
    """Whether an unsupported percentage is ancillary to a focused extraction request."""

    probe = question.casefold()
    percentage_markers = (
        "%",
        "percent",
        "percentage",
        "ratio",
        "rate",
        "growth",
        "change",
        "margin",
        "同比",
        "增长率",
        "变化率",
        "比率",
        "比例",
        "利润率",
    )
    return not _analytical_question(question) and not any(
        marker in probe for marker in percentage_markers
    )


def _drop_sentences_with_unsupported_percentages(text: str, unsupported: list[str]) -> str:
    """Delete only sentence-level convenience arithmetic that lacks provenance.

    This never manufactures a replacement number. It is used only after an answered objective
    already links at least one valid deterministic calculation, so removing an extra unsupported
    restatement (for example, a registered 116.12% ratio rewritten as "about 16% above") keeps
    the supported answer while preventing a writing defect from sending the Agent back to tools.
    """

    tokens = {token.casefold() for token in unsupported if token}
    if not tokens:
        return text
    parts = re.split(r"(?<=[.!?。！？])\s+", str(text).strip())
    kept = [
        part
        for part in parts
        if part.strip() and not any(token in part.casefold() for token in tokens)
    ]
    return " ".join(kept).strip()


def binary_question(question: str) -> bool:
    probe = question.strip().casefold()
    english_starts = (
        "is ",
        "are ",
        "was ",
        "were ",
        "do ",
        "does ",
        "did ",
        "has ",
        "have ",
        "can ",
        "could ",
        "should ",
        "would ",
        "will ",
    )
    chinese_markers = ("是否", "是不是", "能否", "会不会", "有没有", "有无")
    return (
        probe.startswith(english_starts)
        or any(marker in question for marker in chinese_markers)
        or question.rstrip().endswith("吗")
    )


def _metric_alias_matches(question: str) -> dict[str, tuple[str, ...]]:
    question_terms = terms(question)
    matches: dict[str, tuple[str, ...]] = {}
    for metric_code, definition in SERIES_METRICS.items():
        aliases = tuple(str(alias) for alias in definition["aliases"])
        if any(
            (alias_terms := terms(alias)) and alias_terms <= question_terms for alias in aliases
        ):
            matches[metric_code] = aliases
    return matches


def _statement_context_queries(question: str) -> list[str]:
    probe = question.casefold()
    contexts: list[str] = []
    if any(
        marker in probe
        for marker in (
            "cash flow statement",
            "statement of cash flow",
            "statement of cash flows",
            "cash flows",
            "现金流量表",
        )
    ):
        contexts.append("consolidated statement cash flows cash flow statement 现金流量表")
    if any(
        marker in probe
        for marker in (
            "balance sheet",
            "statement of financial position",
            "资产负债表",
        )
    ):
        contexts.append("consolidated balance sheet statement financial position 资产负债表")
    if any(
        marker in probe
        for marker in (
            "income statement",
            "statement of income",
            "statement of earnings",
            "profit and loss",
            "利润表",
            "损益表",
        )
    ):
        contexts.append("consolidated statement income earnings profit loss 利润表")
    return contexts


def bootstrap_evidence_candidates(
    objects: dict[str, Json], question: str, *, limit: int = 6
) -> tuple[list[Json], list[str]]:
    """Seed retrieval with question text plus deterministic financial-metric aliases.

    This is only a cold-start accelerator. It does not restrict the Agent's later full-document
    search and it never marks a metric as found merely because an alias matched.
    """
    candidates: dict[str, tuple[int, float, Json]] = {}

    def add(item: Json, *, priority: int, source: str, metric_code: str | None = None) -> None:
        identifier = str(item["artifact_id"])
        enriched = {**item, "bootstrap_source": source}
        if metric_code is not None:
            enriched["bootstrap_metric_code"] = metric_code
        score = float(item.get("score", 0.0))
        previous = candidates.get(identifier)
        if previous is None or (priority, score) > (previous[0], previous[1]):
            candidates[identifier] = (priority, score, enriched)

    for item in search_objects(objects, question, "evidence")[: max(limit * 3, 12)]:
        add(item, priority=1, source="question")

    metric_matches = _metric_alias_matches(question)
    statement_contexts = _statement_context_queries(question)
    years = re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", question)
    year_context = " ".join(dict.fromkeys(years))
    for metric_code, aliases in metric_matches.items():
        for alias in aliases:
            for item in search_objects(objects, alias, "evidence")[:4]:
                add(
                    item,
                    priority=2,
                    source="financial_metric_alias",
                    metric_code=metric_code,
                )
            for statement_context in statement_contexts:
                combined_query = " ".join(
                    part for part in (alias, statement_context, year_context) if part
                )
                for item in search_objects(objects, combined_query, "evidence")[:4]:
                    add(
                        item,
                        priority=3,
                        source="financial_metric_alias_and_statement",
                        metric_code=metric_code,
                    )

    ranked = [
        item
        for _priority, _score, item in sorted(
            candidates.values(),
            key=lambda candidate: (-candidate[0], -candidate[1], candidate[2]["artifact_id"]),
        )
    ]
    # First maximize page/location diversity, then fill remaining slots with additional chunks.
    selected: list[Json] = []
    deferred: list[Json] = []
    seen_locations: set[str] = set()
    for item in ranked:
        location = str(item.get("page_id") or item["artifact_id"])
        if location in seen_locations:
            deferred.append(item)
            continue
        selected.append(item)
        seen_locations.add(location)
        if len(selected) == limit:
            break
    if len(selected) < limit:
        selected.extend(deferred[: limit - len(selected)])
    return selected[:limit], sorted(metric_matches)


class FilingTools:
    def __init__(
        self,
        repository: ResearchRepository,
        run_id: str,
        request: ResearchRequest,
        environment: Json,
        check: Callable[[], None],
        *,
        snapshot: Json | None = None,
    ) -> None:
        self.repository, self.run_id, self.request = repository, run_id, request
        self.environment, self.check = environment, check
        snapshot = snapshot or {}
        self.working = WorkingState.model_validate(snapshot.get("working", {}))
        self.observed: dict[str, Json] = snapshot.get("observed", {})
        self.calculations: dict[str, Json] = snapshot.get("calculations", {})
        self.verified_series: dict[str, Json] = snapshot.get("verified_series", {})
        self.receipts: dict[str, Json] = snapshot.get("receipts", {})
        self.counter_searches: list[Json] = snapshot.get("counter_searches", [])
        self.dossier: Json | None = snapshot.get("dossier")
        self.feedback: list[str] = snapshot.get("feedback", [])
        self.last_reflection_progress_key: str | None = snapshot.get("last_reflection_progress_key")
        self.state_baseline_receipt_count = int(snapshot.get("state_baseline_receipt_count", 0))
        self.state_baseline_evidence_count = int(snapshot.get("state_baseline_evidence_count", 0))
        self.state_baseline_calculation_count = int(
            snapshot.get("state_baseline_calculation_count", 0)
        )
        self.stagnant_plateau_reflections = int(snapshot.get("stagnant_plateau_reflections", 0))

    def save(self) -> None:
        self.repository.attach(self.run_id, "environment", self.environment)
        self.repository.attach(self.run_id, "research_state", self.snapshot())

    def snapshot(self) -> Json:
        return {
            "working": self.working.model_dump(mode="json"),
            "observed": self.observed,
            "calculations": self.calculations,
            "verified_series": self.verified_series,
            "receipts": self.receipts,
            "counter_searches": self.counter_searches,
            "dossier": self.dossier,
            "feedback": self.feedback,
            "last_reflection_progress_key": self.last_reflection_progress_key,
            "state_baseline_receipt_count": self.state_baseline_receipt_count,
            "state_baseline_evidence_count": self.state_baseline_evidence_count,
            "state_baseline_calculation_count": self.state_baseline_calculation_count,
            "stagnant_plateau_reflections": self.stagnant_plateau_reflections,
        }

    def _latest_receipt_position(self, name: str) -> int | None:
        latest: int | None = None
        for position, receipt in enumerate(self.receipts.values()):
            if receipt.get("name") == name:
                latest = position
        return latest

    def _capital_intensity_question(self) -> bool:
        probe = self.request.research_question.casefold()
        return any(
            marker in probe
            for marker in (
                "capital-intensive",
                "capital intensive",
                "capital intensity",
                "资本密集",
                "重资产",
            )
        )

    def _calculation_metric_signature(self, calculation: Json) -> tuple[str, ...]:
        signature: list[str] = []
        for series_id in calculation.get("input_series_ids", []):
            series = self.verified_series.get(str(series_id))
            if series is None:
                return ()
            signature.append(str(series.get("metric_code")))
        return tuple(signature)

    def _research_period_label(self) -> str | None:
        if self.request.requested_period_label:
            return self.request.requested_period_label
        labels = {
            str(document.get("period_label"))
            for document in self.environment.get("documents", {}).values()
            if document.get("period_label")
        }
        return next(iter(labels)) if len(labels) == 1 else None

    def _dimension_calculation_candidates(
        self, *, formula: str, signature: tuple[str, ...]
    ) -> list[tuple[str, ...]]:
        groups = [
            sorted(
                series_id
                for series_id, series in self.verified_series.items()
                if series.get("metric_code") == metric_code
            )
            for metric_code in signature
        ]
        if any(not group for group in groups):
            return []
        candidates: list[tuple[str, ...]] = []
        for left in groups[0]:
            right_ids = groups[1] if len(groups) > 1 else [None]
            for right in right_ids:
                series_ids = [left] if right is None else [left, right]
                period_label = (
                    self._research_period_label()
                    if formula
                    in {
                        "ratio_percent",
                        "flow_to_average_balance_percent",
                        "average_balance_to_flow_percent",
                    }
                    else None
                )
                try:
                    calculate_series_metric(
                        SeriesCalculateInput.model_validate(
                            {
                                "formula": formula,
                                "series_ids": series_ids,
                                "period_label": period_label,
                                "round_decimals": 4,
                            }
                        ),
                        self.verified_series,
                    )
                except ValueError:
                    continue
                candidates.append(tuple(series_ids))
        return candidates

    def _capital_intensity_classification_evidence_ids(self) -> list[str]:
        if not self._capital_intensity_question():
            return []
        linked = {
            identifier
            for objective in self.working.objectives
            if objective.priority == "required"
            for identifier in objective.evidence_ids
            if identifier in self.observed
        }
        pattern = re.compile(r"\bcapital[- ]intensive\b|资本密集|重资产", re.IGNORECASE)
        return sorted(
            identifier
            for identifier in linked
            if pattern.search(str(self.observed[identifier].get("text", "")))
        )

    def _methodology_checks(self) -> list[Json]:
        if _cash_flow_health_question(self.request.research_question):
            return [
                {
                    "methodology_id": "cash_flow_health_multidimensional_v1",
                    "status": "assessment_required",
                    "classification_status": "not_applicable",
                    "dimensions": [
                        {
                            "dimension": "operating_cash_generation",
                            "instruction": (
                                "Assess operating cash-flow level/trend and profit-to-cash "
                                "conversion; distinguish recurring earnings from working-capital "
                                "release when the filing permits."
                            ),
                        },
                        {
                            "dimension": "net_cash_and_liquidity",
                            "instruction": (
                                "Assess net change in cash/cash equivalents together with the "
                                "available liquidity buffer; a strong OCF alone is not the whole "
                                "cash-flow health judgment."
                            ),
                        },
                        {
                            "dimension": "investing_and_financing",
                            "instruction": (
                                "Assess investing/financing cash-flow pressure and material "
                                "capital outflows when available; do not treat every investment "
                                "automatically unhealthy without context."
                            ),
                        },
                        {
                            "dimension": "working_capital_and_one_offs",
                            "instruction": (
                                "Check working-capital release and one-off cash effects. "
                                "Receivable factoring/discounting may affect quality only when "
                                "actually links its accounting cash-flow treatment to OCF."
                            ),
                        },
                    ],
                    "direct_answer_rule": (
                        "Use yes/no only when material evidence across the available dimensions "
                        "points consistently one way. Use mixed when material positive and "
                        "negative cash-flow evidence coexist. Use cannot_determine only when "
                        "cannot support a responsible overall judgment."
                    ),
                    "instruction": (
                        "Cash-flow health is a multidimensional filing-based assessment, not a "
                        "single-ratio threshold. A cash-conversion ratio above 1 or rising OCF can "
                        "support operating cash quality, but cannot by itself establish overall "
                        "cash-flow health when material cash depletion, investing pressure, or "
                        "working-capital/one-off effects point the other way."
                    ),
                }
            ]
        if not self._capital_intensity_question():
            return []
        dimensions = [
            {
                "dimension": "investment_intensity",
                "label": "当期再投资强度：CAPEX / Revenue",
                "formula": "ratio_percent",
                "signature": ("capital_expenditures", "revenue"),
            },
            {
                "dimension": "fixed_asset_intensity",
                "label": "固定资产资本强度：Average Net PP&E / Revenue",
                "formula": "average_balance_to_flow_percent",
                "signature": ("fixed_assets", "revenue"),
            },
            {
                "dimension": "total_asset_intensity",
                "label": "整体资产资本强度：Average Total Assets / Revenue",
                "formula": "average_balance_to_flow_percent",
                "signature": ("total_assets", "revenue"),
            },
        ]
        observed: list[Json] = []
        for dimension in dimensions:
            matches = [
                calculation_id
                for calculation_id, calculation in self.calculations.items()
                if calculation.get("formula_code") == dimension["formula"]
                and self._calculation_metric_signature(calculation) == dimension["signature"]
                and calculation.get("status") == "valid"
            ]
            candidates = (
                []
                if matches
                else self._dimension_calculation_candidates(
                    formula=str(dimension["formula"]),
                    signature=tuple(dimension["signature"]),
                )
            )
            status = (
                "complete" if matches else "ready_to_calculate" if candidates else "missing_inputs"
            )
            observed.append(
                {
                    "dimension": dimension["dimension"],
                    "label": dimension["label"],
                    "status": status,
                    "calculation_ids": matches,
                    "ready_series_ids": [list(candidate) for candidate in candidates],
                }
            )
        missing = [item["dimension"] for item in observed if item["status"] != "complete"]
        ready = [item["dimension"] for item in observed if item["status"] == "ready_to_calculate"]
        missing_inputs = [
            item["dimension"] for item in observed if item["status"] == "missing_inputs"
        ]
        classification_evidence = self._capital_intensity_classification_evidence_ids()
        methodology_status = (
            "complete" if not missing else "calculation_pending" if ready else "incomplete"
        )
        return [
            {
                "methodology_id": "capital_intensity_direct_v2",
                "status": methodology_status,
                "dimensions": observed,
                "missing_dimensions": missing,
                "ready_to_calculate_dimensions": ready,
                "missing_input_dimensions": missing_inputs,
                "classification_status": (
                    "explicit_filing_characterization"
                    if classification_evidence
                    else "absolute_metrics_only"
                ),
                "classification_evidence_ids": classification_evidence,
                "instruction": (
                    "Measure direct capital demand with CAPEX/revenue, average net PP&E/revenue, "
                    "and average total assets/revenue. ROA may be reported separately as return "
                    "context but is not a capital-intensity definition. Without an explicit filing "
                    "characterization or comparable benchmark/threshold, report the absolute "
                    "metrics but mark the categorical capital-intensive label limited rather than "
                    "inventing high/medium/low cutoffs."
                ),
            }
        ]

    def _sufficient_evidence_blockers(self) -> list[tuple[str, str]]:
        blockers: list[tuple[str, str]] = []
        analytical = _analytical_question(self.request.research_question)
        if (
            self.working.core_question_status != "answerable"
            or self.working.expected_value_of_more_research != "low"
        ):
            blockers.append(
                (
                    "state_not_answerable_low",
                    "mark the core question answerable and remaining research value low before "
                    "sufficient_evidence submission",
                )
            )
        required_objectives = [
            objective for objective in self.working.objectives if objective.priority == "required"
        ]
        if not required_objectives or any(
            objective.status == "open" for objective in required_objectives
        ):
            blockers.append(
                (
                    "required_objectives_incomplete",
                    "all user-required research objectives must be answered or limited before "
                    "sufficient_evidence submission",
                )
            )
        for objective in required_objectives:
            if objective.status != "answered" or not objective.conclusion.strip():
                continue
            # This research-state gate answers one narrow question: did the model invent a
            # percentage that is absent from every verified source/calculation in this run? Exact
            # claim-to-evidence linkage is enforced later by validate_report. Keeping those layers
            # separate prevents a missing notebook citation from trapping an otherwise answerable
            # run in more research, while still refusing unsupported model arithmetic.
            missing_percentages = unsupported_percentages(
                objective.conclusion,
                calculations=list(self.calculations.values()),
                facts=list(self.environment["facts"].values()),
                evidence=list(self.observed.values()),
            )
            if missing_percentages:
                blockers.append(
                    (
                        "derived_percentage_calculation_missing",
                        (
                            f"required objective {objective.objective_id} contains derived "
                            f"percentage(s) {', '.join(missing_percentages)} absent from every "
                            "verified percentage fact, reported source percentage, or "
                            "CalculationRecord in this run; use deterministic calculation tools "
                            "instead of model arithmetic"
                        ),
                    )
                )
        if not analytical and any(
            question.status == "open" and question.priority in {"high", "medium"}
            for question in self.working.open_questions
        ):
            blockers.append(
                (
                    "focused_verification_question_open",
                    "focused research cannot submit while a medium/high verification question "
                    "is open",
                )
            )
        if analytical and not self.working.hypotheses:
            blockers.append(
                (
                    "analytical_hypothesis_missing",
                    "analytical research requires an explicit hypothesis state",
                )
            )
        required_answered = any(objective.status == "answered" for objective in required_objectives)
        unresolved_major = (
            analytical
            and required_answered
            and any(
                hypothesis.materiality == "major"
                and hypothesis.status in {"investigating", "unresolved"}
                for hypothesis in self.working.hypotheses
            )
        )
        if unresolved_major:
            blockers.append(
                (
                    "major_hypothesis_unresolved",
                    "an answered analytical objective cannot submit while a major hypothesis is "
                    "still investigating or unresolved",
                )
            )
        resolved_major = (
            analytical
            and required_answered
            and any(
                hypothesis.materiality == "major"
                and hypothesis.status in {"supported", "mixed", "rejected"}
                for hypothesis in self.working.hypotheses
            )
        )
        latest_counter = self._latest_receipt_position("search_counter_evidence")
        if resolved_major and latest_counter is None:
            blockers.append(
                (
                    "counter_evidence_missing",
                    "a resolved major analytical conclusion requires one targeted counter-evidence "
                    "search against the final verdict before submission",
                )
            )
        if latest_counter is not None and latest_counter >= self.state_baseline_receipt_count:
            blockers.append(
                (
                    "counter_reflection_pending",
                    "counter-evidence results must be reflected into public research state before "
                    "submission",
                )
            )
        methodology_checks = self._methodology_checks()
        if required_answered and methodology_checks:
            methodology = methodology_checks[0]
            if methodology["status"] == "calculation_pending":
                ready = ", ".join(methodology["ready_to_calculate_dimensions"])
                blockers.append(
                    (
                        "capital_intensity_calculation_pending",
                        "capital-intensity source inputs are already verified for direct "
                        f"dimension(s): {ready}; run calculate_series_metric before submission",
                    )
                )
            elif methodology["status"] == "incomplete":
                missing = ", ".join(methodology["missing_input_dimensions"])
                blockers.append(
                    (
                        "capital_intensity_methodology_incomplete",
                        "capital-intensity analysis is still missing verified filing inputs for "
                        f"dimension(s): {missing}; recover them when available, or mark the "
                        "required objective limited with an explicit filing-data limitation",
                    )
                )
            elif methodology["classification_status"] == "absolute_metrics_only":
                blockers.append(
                    (
                        "capital_intensity_classification_boundary",
                        "the filing supports absolute capital-intensity metrics but provides no "
                        "linked explicit capital-intensive characterization or comparison "
                        "benchmark/threshold; mark the required classification objective limited "
                        "and use evidence_exhausted/cannot_determine instead of inventing a "
                        "categorical yes/no threshold",
                    )
                )
        return blockers

    def _evidence_exhausted_blockers(self) -> list[tuple[str, str]]:
        blockers: list[tuple[str, str]] = []
        required_objectives = [
            objective for objective in self.working.objectives if objective.priority == "required"
        ]
        if not required_objectives or any(
            objective.status == "open" for objective in required_objectives
        ):
            blockers.append(
                (
                    "required_objectives_unclosed",
                    "evidence_exhausted requires every user-required objective to be answered "
                    "or explicitly limited",
                )
            )
        methodology_checks = self._methodology_checks()
        if methodology_checks and methodology_checks[0]["status"] == "calculation_pending":
            ready = ", ".join(methodology_checks[0]["ready_to_calculate_dimensions"])
            blockers.append(
                (
                    "capital_intensity_calculation_pending",
                    "verified filing inputs already exist for direct capital-demand dimension(s): "
                    f"{ready}; evidence_exhausted cannot skip deterministic calculations",
                )
            )
        return blockers

    def _required_before_submit(self) -> list[str]:
        if self.working.core_question_status == "evidence_exhausted":
            if self.working.expected_value_of_more_research != "low":
                return []
            blockers = self._evidence_exhausted_blockers()
            if not blockers:
                return ["submit_research"]
            if {code for code, _message in blockers} == {"capital_intensity_calculation_pending"}:
                return ["calculate_series_metric"]
            return []
        blockers = self._sufficient_evidence_blockers()
        if not blockers:
            return ["submit_research"]
        if {code for code, _message in blockers} == {"counter_evidence_missing"}:
            return ["search_counter_evidence"]
        return []

    def _progress_key(self) -> str:
        return payload_sha256(
            {
                "observed_evidence_ids": sorted(self.observed),
                "calculation_ids": sorted(self.calculations),
            }
        )

    def _semantic_state_signature(self, state: WorkingState | None = None) -> str:
        current = state or self.working
        return payload_sha256(
            {
                "objectives": [
                    {
                        "objective_id": item.objective_id,
                        "status": item.status,
                        "evidence_ids": sorted(item.evidence_ids),
                        "conclusion": item.conclusion,
                        "remaining_uncertainty": item.remaining_uncertainty,
                    }
                    for item in current.objectives
                ],
                "hypotheses": [
                    {
                        "hypothesis_id": item.hypothesis_id,
                        "status": item.status,
                        "evidence_for": sorted(item.evidence_for),
                        "evidence_against": sorted(item.evidence_against),
                        "unknowns": item.unknowns,
                    }
                    for item in current.hypotheses
                ],
                "open_questions": [
                    {
                        "question_id": item.question_id,
                        "status": item.status,
                        "evidence_ids": sorted(item.evidence_ids),
                        "explanation": item.explanation,
                    }
                    for item in current.open_questions
                ],
                "core_question_status": current.core_question_status,
                "expected_value_of_more_research": current.expected_value_of_more_research,
            }
        )

    def _reflection_query_terms(self) -> set[str]:
        prompts = [self.request.research_question]
        prompts.extend(
            objective.question
            for objective in self.working.objectives
            if objective.priority == "required"
        )
        prompts.extend(
            question.question
            for question in self.working.open_questions
            if question.status == "open" and question.priority in {"high", "medium"}
        )
        prompts.extend(
            hypothesis.statement
            for hypothesis in self.working.hypotheses
            if hypothesis.materiality == "major"
        )
        return terms(" ".join(prompts))

    @staticmethod
    def _evidence_excerpt(text: str, query_terms: set[str], max_chars: int = 720) -> str:
        if len(text) <= max_chars:
            return text
        lowered = text.casefold()
        positions = [
            lowered.find(term.casefold())
            for term in sorted(query_terms, key=len, reverse=True)
            if len(term) >= 2 and lowered.find(term.casefold()) >= 0
        ]
        if not positions:
            return text[:max_chars]
        center = min(positions)
        start = max(0, center - max_chars // 3)
        end = min(len(text), start + max_chars)
        start = max(0, end - max_chars)
        prefix = "…" if start else ""
        suffix = "…" if end < len(text) else ""
        return prefix + text[start:end] + suffix

    def _reflection_evidence_memory(self, limit: int = 18) -> list[Json]:
        """Keep a bounded semantic memory for Reflection, not the ordinary action context."""
        query_terms = self._reflection_query_terms()
        linked: set[str] = set()
        for objective in self.working.objectives:
            linked.update(
                identifier for identifier in objective.evidence_ids if identifier in self.observed
            )
        for hypothesis in self.working.hypotheses:
            linked.update(
                identifier for identifier in hypothesis.evidence_for if identifier in self.observed
            )
            linked.update(
                identifier
                for identifier in hypothesis.evidence_against
                if identifier in self.observed
            )
        for question in self.working.open_questions:
            linked.update(
                identifier for identifier in question.evidence_ids if identifier in self.observed
            )
        for fact in self.environment["facts"].values():
            identifier = fact.get("observed_evidence_id")
            if isinstance(identifier, str) and identifier in self.observed:
                linked.add(identifier)

        ranked: list[tuple[int, int, int, str, Json]] = []
        observed_items = list(self.observed.items())
        for recency, (identifier, item) in enumerate(observed_items):
            text = str(item.get("text", ""))
            overlap = len(query_terms & terms(text)) if text else 0
            is_linked = 1 if identifier in linked else 0
            if not is_linked and not overlap and recency < max(0, len(observed_items) - 6):
                continue
            ranked.append((is_linked, overlap, recency, identifier, item))
        ranked.sort(key=lambda row: (-row[0], -row[1], -row[2], row[3]))
        output: list[Json] = []
        seen_sources: set[tuple[object, object]] = set()
        for is_linked, overlap, _recency, identifier, item in ranked:
            source_key = (item.get("source_artifact_id"), item.get("page_number"))
            if source_key in seen_sources and not is_linked and overlap == 0:
                continue
            seen_sources.add(source_key)
            output.append(
                {
                    "evidence_id": identifier,
                    "source_artifact_id": item.get("source_artifact_id"),
                    "source_kind": item.get("source_kind"),
                    "page_number": item.get("page_number"),
                    "relevance_terms": overlap,
                    "already_linked_to_public_state": bool(is_linked),
                    "text_excerpt": self._evidence_excerpt(str(item.get("text", "")), query_terms),
                }
            )
            if len(output) >= limit:
                break
        return output

    def reflection_decision(self) -> Json:
        progress_key = self._progress_key()
        progress_changed = progress_key != self.last_reflection_progress_key
        progress = self._recent_progress()
        first_research_notebook = bool(
            not self.working.objectives and (self.observed or self.calculations)
        )
        missing_analytical_hypothesis = bool(
            _analytical_question(self.request.research_question)
            and self.working.objectives
            and not self.working.hypotheses
        )
        since_state = list(self.receipts.values())[self.state_baseline_receipt_count :]
        research_since_state = [
            receipt
            for receipt in since_state
            if receipt.get("name") not in {"update_research_state", "submit_research"}
        ]
        evidence_gain = max(0, len(self.observed) - self.state_baseline_evidence_count)
        calculation_gain = max(0, len(self.calculations) - self.state_baseline_calculation_count)
        deliberate_reads = sum(
            receipt.get("name") in {"read_filing", "inspect_page_image"}
            and bool(receipt.get("new_observed_count"))
            for receipt in research_since_state
        )
        open_required_objectives = any(
            objective.priority == "required" and objective.status == "open"
            for objective in self.working.objectives
        )
        open_material_questions = any(
            question.status == "open" and question.priority in {"high", "medium"}
            for question in self.working.open_questions
        )
        objective_research_update = bool(
            open_required_objectives
            and (evidence_gain >= 1 or calculation_gain >= 1 or deliberate_reads >= 1)
        )
        question_research_update = bool(
            open_material_questions
            and (evidence_gain >= 1 or calculation_gain >= 1 or deliberate_reads >= 1)
        )
        material_research_update = bool(
            self.working.hypotheses
            and (evidence_gain >= 6 or calculation_gain >= 2 or deliberate_reads >= 2)
        )
        latest_counter = self._latest_receipt_position("search_counter_evidence")
        counter_evidence_update = bool(
            latest_counter is not None and latest_counter >= self.state_baseline_receipt_count
        )
        # A new deterministic calculation is itself a notebook-state update worth reflecting.
        # Checking blockers *after* the calculation is too late: the calculation may have already
        # cleared the numeric-provenance blocker that motivated it.
        numeric_provenance_update = calculation_gain >= 1
        plateau_since_state = len(research_since_state) >= 5 and not any(
            bool(receipt.get("new_observed_count")) or bool(receipt.get("new_calculation_count"))
            for receipt in research_since_state[-5:]
        )
        exhaustion_review_required = bool(
            self.stagnant_plateau_reflections >= 1
            and open_required_objectives
            and plateau_since_state
        )
        reason = "none"
        if exhaustion_review_required:
            reason = "research_exhaustion_review"
        elif first_research_notebook:
            reason = (
                "first_analytical_evidence"
                if _analytical_question(self.request.research_question)
                else "first_research_evidence"
            )
        elif missing_analytical_hypothesis:
            reason = "missing_analytical_hypothesis"
        elif counter_evidence_update:
            # A targeted counter-search is itself a research result even when it
            # returns zero new chunks; the public hypothesis state must record it.
            reason = "counter_evidence_update"
        elif numeric_provenance_update:
            reason = "numeric_provenance_update"
        elif progress_changed and material_research_update:
            reason = "material_research_update"
        elif progress_changed and objective_research_update:
            reason = "open_objective_research_update"
        elif progress_changed and question_research_update:
            reason = "open_question_research_update"
        elif plateau_since_state:
            reason = "research_plateau"
        return {
            "needed": reason != "none",
            "reason": reason,
            "progress_changed_since_reflection": progress_changed,
            "has_hypotheses": bool(self.working.hypotheses),
            "has_objectives": bool(self.working.objectives),
            "missing_analytical_hypothesis": missing_analytical_hypothesis,
            "open_required_objectives": open_required_objectives,
            "open_material_questions": open_material_questions,
            "objective_research_update": objective_research_update,
            "question_research_update": question_research_update,
            "analytical_question": _analytical_question(self.request.research_question),
            "observed_evidence_count": len(self.observed),
            "receipt_count": len(self.receipts),
            "recent_plateau": progress["plateau_detected"],
            "plateau_since_state": plateau_since_state,
            "evidence_gain_since_state": evidence_gain,
            "calculation_gain_since_state": calculation_gain,
            "deliberate_reads_since_state": deliberate_reads,
            "counter_evidence_update": counter_evidence_update,
            "numeric_provenance_update": numeric_provenance_update,
            "stagnant_plateau_reflections": self.stagnant_plateau_reflections,
            "research_exhaustion_review_required": exhaustion_review_required,
        }

    def reflection_needed(self) -> bool:
        return bool(self.reflection_decision()["needed"])

    def mark_reflected(self) -> None:
        self.last_reflection_progress_key = self._progress_key()
        self.state_baseline_receipt_count = len(self.receipts)
        self.state_baseline_evidence_count = len(self.observed)
        self.state_baseline_calculation_count = len(self.calculations)
        self.save()

    def reference_registry(self) -> Json:
        evidence = list(self.observed.values())[-80:]
        return {
            "evidence": [
                {
                    "evidence_id": item["artifact_id"],
                    "source_artifact_id": item.get("source_artifact_id"),
                    "source_kind": item.get("source_kind"),
                    "page_number": item.get("page_number"),
                }
                for item in evidence
            ],
            "facts": [
                {
                    "fact_id": fact_id,
                    "metric_code": fact.get("metric_code"),
                    "period_label": self.environment["documents"][fact["document_id"]].get(
                        "period_label"
                    ),
                }
                for fact_id, fact in self.environment["facts"].items()
            ],
            "verified_series": [
                {
                    "series_id": series_id,
                    "metric_code": series.get("metric_code"),
                    "page_number": series.get("page_number"),
                    "evidence_id": series.get("evidence_id"),
                }
                for series_id, series in self.verified_series.items()
            ],
            "calculations": [
                {
                    "calculation_id": calculation_id,
                    "formula_code": calculation.get("formula_code"),
                }
                for calculation_id, calculation in self.calculations.items()
            ],
            "rule": (
                "Only the exact evidence_id/fact_id/series_id/calculation_id values in this "
                "registry are "
                "valid WorkingState references. Page/table labels are locations, not IDs."
            ),
        }

    def _objective_relevant_evidence_ids(self, question: str, limit: int = 6) -> list[str]:
        query_terms = terms(question + " " + self.request.research_question)
        ranked: list[tuple[int, int, str]] = []
        for recency, (identifier, item) in enumerate(self.observed.items()):
            text = str(item.get("text", ""))
            overlap = len(query_terms & terms(text)) if text else 0
            if overlap:
                ranked.append((overlap, recency, identifier))
        ranked.sort(key=lambda row: (-row[0], -row[1], row[2]))
        return [identifier for _overlap, _recency, identifier in ranked[:limit]]

    def _apply_semantic_exhaustion_fallback(self, payload: Json, corrections: list[Json]) -> None:
        """Close only epistemic state after repeated zero-gain plateau; never invent a finding."""
        note = "连续研究窗口未获得可改变该目标结论的新证据；当前财报范围的边际信息增益已耗尽。"
        for objective in payload["objectives"]:
            if objective["priority"] != "required" or objective["status"] != "open":
                continue
            objective["status"] = "limited"
            if not objective["evidence_ids"]:
                objective["evidence_ids"] = self._objective_relevant_evidence_ids(
                    str(objective["question"])
                )
            if not str(objective["conclusion"]).strip():
                objective["conclusion"] = "当前财报范围内无法形成更强的可验证结论。"
            uncertainty = str(objective["remaining_uncertainty"]).strip()
            objective["remaining_uncertainty"] = (
                (uncertainty + " " + note).strip() if uncertainty else note
            )[:1600]
            corrections.append(
                {
                    "subject": objective["objective_id"],
                    "correction": "semantic_plateau_objective_limited",
                }
            )
        for question in payload["open_questions"]:
            if question["status"] != "open" or question["priority"] not in {"high", "medium"}:
                continue
            question["status"] = "not_answerable_from_filings"
            explanation = str(question["explanation"]).strip()
            question["explanation"] = ((explanation + " " + note).strip() if explanation else note)[
                :2000
            ]
            corrections.append(
                {
                    "subject": question["question_id"],
                    "correction": "semantic_plateau_question_exhausted",
                }
            )
        payload["core_question_status"] = "evidence_exhausted"
        payload["expected_value_of_more_research"] = "low"
        summary = str(payload["decision_summary"]).strip()
        stop_note = "当前财报范围连续无新增高价值证据，公开研究状态收敛为 evidence_exhausted。"
        payload["decision_summary"] = (
            (summary + " " + stop_note).strip() if summary else stop_note
        )[:1200]
        corrections.append(
            {
                "subject": "research_state",
                "correction": "semantic_plateau_evidence_exhausted",
            }
        )

    def apply_working_state(
        self, parsed: WorkingState, *, trigger_reason: str | None = None
    ) -> Json:
        allowed = (
            set(self.observed)
            | set(self.environment["facts"])
            | set(self.verified_series)
            | set(self.calculations)
        )
        payload = parsed.model_dump(mode="json")
        corrections: list[Json] = []
        existing_required = {
            objective.objective_id: objective.model_dump(mode="json")
            for objective in self.working.objectives
            if objective.priority == "required"
        }
        if existing_required:
            proposed_ids = {str(item["objective_id"]) for item in payload["objectives"]}
            for objective in payload["objectives"]:
                objective_id = str(objective["objective_id"])
                previous = existing_required.get(objective_id)
                if previous is not None:
                    if objective["question"] != previous["question"]:
                        corrections.append(
                            {
                                "subject": objective_id,
                                "correction": "required_objective_question_locked",
                            }
                        )
                    objective["question"] = previous["question"]
                    objective["priority"] = "required"
                elif objective["priority"] == "required":
                    objective["priority"] = "supporting"
                    corrections.append(
                        {
                            "subject": objective_id,
                            "correction": "new_required_objective_downgraded_to_supporting",
                        }
                    )
            for objective_id, previous in existing_required.items():
                if objective_id not in proposed_ids:
                    payload["objectives"].append(previous)
                    corrections.append(
                        {
                            "subject": objective_id,
                            "correction": "missing_required_objective_restored",
                        }
                    )
        research_receipts = [
            receipt
            for receipt in self.receipts.values()
            if receipt.get("name") not in {"update_research_state", "submit_research"}
            and (
                bool(receipt.get("new_observed_count"))
                or bool(receipt.get("new_calculation_count"))
                or bool(cast(Json, receipt.get("result", {})).get("facts"))
                or bool(cast(Json, receipt.get("result", {})).get("new_documents"))
            )
        ]
        first_objective_initialization = bool(not existing_required and payload["objectives"])
        if first_objective_initialization and not research_receipts:
            maturity_note = (
                "首次状态只锁定研究目标；至少完成一次针对性财报研究动作后，"
                "才能将 required objective 标记为 answered/limited。"
            )
            for objective in payload["objectives"]:
                if objective["priority"] == "required" and objective["status"] != "open":
                    objective["status"] = "open"
                    objective["remaining_uncertainty"] = (
                        (objective["remaining_uncertainty"] + " " + maturity_note).strip()
                    )[:1600]
                    corrections.append(
                        {
                            "subject": objective["objective_id"],
                            "correction": "first_reflection_requires_active_research",
                        }
                    )
            payload["core_question_status"] = "investigating"
            if payload["expected_value_of_more_research"] == "low":
                payload["expected_value_of_more_research"] = "medium"
        for objective in payload["objectives"]:
            if objective["status"] == "limited":
                for field in ("conclusion", "remaining_uncertainty"):
                    original_text = str(objective[field])
                    softened_text = _soften_limited_absence_language(original_text)
                    if softened_text != original_text:
                        objective[field] = softened_text
                        corrections.append(
                            {
                                "subject": objective["objective_id"],
                                "field": field,
                                "correction": "limited_global_absence_softened_to_observed_boundary",
                            }
                        )
            if objective["status"] == "answered":
                linked_calculation_ids = [
                    identifier
                    for identifier in objective["evidence_ids"]
                    if identifier in self.calculations
                    and self.calculations[identifier].get("status") == "valid"
                ]
                focused_ancillary_percentage = _focused_question_does_not_request_percentage(
                    self.request.research_question
                ) and bool(objective["evidence_ids"])
                if linked_calculation_ids or focused_ancillary_percentage:
                    unsupported = unsupported_percentages(
                        str(objective["conclusion"]),
                        calculations=list(self.calculations.values()),
                        facts=list(self.environment["facts"].values()),
                        evidence=list(self.observed.values()),
                    )
                    if unsupported:
                        original_conclusion = str(objective["conclusion"])
                        pruned = _drop_sentences_with_unsupported_percentages(
                            original_conclusion, unsupported
                        )
                        if pruned and pruned != original_conclusion:
                            objective["conclusion"] = pruned
                            corrections.append(
                                {
                                    "subject": objective["objective_id"],
                                    "unsupported_percentages": sorted(set(unsupported)),
                                    "linked_calculation_ids": linked_calculation_ids,
                                    "focused_ancillary_percentage": focused_ancillary_percentage,
                                    "correction": (
                                        "unsupported_convenience_percentage_removed_from_answered_objective"
                                    ),
                                }
                            )
            explicit_support_ids = re.findall(
                r"\b(?:calc|series)_[A-Za-z0-9_.:-]+\b",
                objective["conclusion"] + " " + objective["remaining_uncertainty"],
            )
            recovered = [
                identifier
                for identifier in explicit_support_ids
                if identifier in allowed and identifier not in objective["evidence_ids"]
            ]
            room = max(0, 30 - len(objective["evidence_ids"]))
            recovered = recovered[:room]
            if recovered:
                objective["evidence_ids"].extend(recovered)
                corrections.append(
                    {
                        "subject": objective["objective_id"],
                        "recovered_reference_ids": recovered,
                        "correction": "explicit_support_reference_recovered_from_objective_text",
                    }
                )
            original = list(objective["evidence_ids"])
            objective["evidence_ids"] = [
                identifier for identifier in original if identifier in allowed
            ]
            dropped_objective = [identifier for identifier in original if identifier not in allowed]
            if dropped_objective:
                corrections.append(
                    {
                        "subject": objective["objective_id"],
                        "dropped_reference_ids": sorted(set(dropped_objective)),
                    }
                )
            if objective["status"] == "answered" and not objective["evidence_ids"]:
                objective["status"] = "open"
                objective["remaining_uncertainty"] = (
                    objective["remaining_uncertainty"]
                    + " 支撑引用无法映射到本 Run，目标重新标记为 open。"
                )[:1600]
        for hypothesis in payload["hypotheses"]:
            dropped: list[str] = []
            for field in ("evidence_for", "evidence_against"):
                original = list(hypothesis[field])
                hypothesis[field] = [identifier for identifier in original if identifier in allowed]
                dropped.extend(identifier for identifier in original if identifier not in allowed)
            if dropped:
                corrections.append(
                    {
                        "subject": hypothesis["hypothesis_id"],
                        "dropped_reference_ids": sorted(set(dropped)),
                    }
                )
            if hypothesis["status"] == "supported" and not hypothesis["evidence_for"]:
                hypothesis["status"] = "unresolved"
                hypothesis["confidence"] = "low"
                note = "支持引用无法映射到本 Run 的合法证据，状态已降级为 unresolved。"
                if note not in hypothesis["unknowns"] and len(hypothesis["unknowns"]) < 10:
                    hypothesis["unknowns"].append(note)
        for question in payload["open_questions"]:
            original = list(question["evidence_ids"])
            question["evidence_ids"] = [
                identifier for identifier in original if identifier in allowed
            ]
            dropped_question = [identifier for identifier in original if identifier not in allowed]
            if dropped_question:
                corrections.append(
                    {
                        "subject": question["question_id"],
                        "dropped_reference_ids": sorted(set(dropped_question)),
                    }
                )
            if question["status"] == "answered" and not question["evidence_ids"]:
                question["status"] = "open"
                question["explanation"] = (
                    question["explanation"]
                    + " 已移除无法映射到本 Run 的引用，因此该问题重新标记为 open。"
                )[:2000]
            if question["status"] != "open" and not question["explanation"].strip():
                raise ValueError("closed question needs an explicit explanation")
        sanitized = WorkingState.model_validate(payload)
        required_objectives = [
            objective for objective in sanitized.objectives if objective.priority == "required"
        ]
        if required_objectives and all(
            objective.status == "limited" for objective in required_objectives
        ):
            limited_payload = sanitized.model_dump(mode="json")
            changed = False
            if limited_payload["core_question_status"] != "evidence_exhausted":
                limited_payload["core_question_status"] = "evidence_exhausted"
                changed = True
            if limited_payload["expected_value_of_more_research"] != "low":
                limited_payload["expected_value_of_more_research"] = "low"
                changed = True
            if changed:
                corrections.append(
                    {
                        "subject": "research_state",
                        "correction": "all_required_limited_requires_evidence_exhausted",
                    }
                )
                sanitized = WorkingState.model_validate(limited_payload)
        required_still_open = any(
            objective.priority == "required" and objective.status == "open"
            for objective in sanitized.objectives
        )
        material_question_still_open = any(
            question.status == "open" and question.priority in {"high", "medium"}
            for question in sanitized.open_questions
        )
        research_progress_since_state = bool(
            len(self.observed) > self.state_baseline_evidence_count
            or len(self.calculations) > self.state_baseline_calculation_count
        )
        if trigger_reason == "research_plateau":
            # A Reflection rewrite is not research progress. Count a plateau whenever the model
            # still leaves material research open; only new observed evidence/calculations or
            # genuinely closing the research question can clear this counter.
            if required_still_open or material_question_still_open:
                self.stagnant_plateau_reflections += 1
            else:
                self.stagnant_plateau_reflections = 0
        elif trigger_reason == "research_exhaustion_review":
            if required_still_open or material_question_still_open:
                fallback_payload = sanitized.model_dump(mode="json")
                self._apply_semantic_exhaustion_fallback(fallback_payload, corrections)
                sanitized = WorkingState.model_validate(fallback_payload)
            self.stagnant_plateau_reflections = 0
        elif research_progress_since_state:
            self.stagnant_plateau_reflections = 0
        self.working = sanitized
        self.last_reflection_progress_key = self._progress_key()
        self.state_baseline_receipt_count = len(self.receipts)
        self.state_baseline_evidence_count = len(self.observed)
        self.state_baseline_calculation_count = len(self.calculations)
        if corrections:
            self.repository.emit(
                self.run_id,
                "research_state_reference_correction",
                "research_state",
                "移除无法映射到本次研究的引用，并保守降级相关状态",
                "needs_attention",
                data={"corrections": corrections},
            )
        return {
            "working_state": sanitized.model_dump(mode="json"),
            "completeness": self.completeness(),
            "reference_corrections": corrections,
        }

    def _recent_progress(self) -> Json:
        receipts = list(self.receipts.values())
        recent = receipts[-8:]
        informative = sum(
            bool(item.get("new_observed_count"))
            or bool(item.get("new_calculation_count"))
            or bool(item.get("state_changed"))
            for item in recent
        )
        research_actions = [
            item
            for item in recent
            if item.get("name") not in {"update_research_state", "submit_research"}
        ]
        plateau = len(research_actions) >= 5 and not any(
            bool(item.get("new_observed_count")) or bool(item.get("new_calculation_count"))
            for item in research_actions[-5:]
        )
        return {
            "window_size": len(recent),
            "informative_actions": informative,
            "redundant_actions": sum(bool(item.get("reused")) for item in recent),
            "plateau_detected": plateau,
            "recent_actions": [
                {
                    "name": item.get("name"),
                    "new_evidence": item.get("new_observed_count", 0),
                    "new_calculations": item.get("new_calculation_count", 0),
                    "state_changed": bool(item.get("state_changed")),
                    "reused": bool(item.get("reused")),
                }
                for item in recent
            ],
        }

    def completeness(self, *, include_required: bool = True) -> Json:
        hypotheses = self.working.hypotheses
        questions = self.working.open_questions
        required_objectives = [
            objective for objective in self.working.objectives if objective.priority == "required"
        ]
        output = {
            "assessment_source": "model_notebook_plus_reference_checks_not_ground_truth",
            "required_objectives_total": len(required_objectives),
            "required_objectives_open": sum(
                objective.status == "open" for objective in required_objectives
            ),
            "required_objectives_answered": sum(
                objective.status == "answered" for objective in required_objectives
            ),
            "required_objectives_limited": sum(
                objective.status == "limited" for objective in required_objectives
            ),
            "major_hypotheses": sum(h.materiality == "major" for h in hypotheses),
            "unresolved_major_hypotheses": sum(
                h.materiality == "major" and h.status in {"investigating", "unresolved"}
                for h in hypotheses
            ),
            "high_priority_open_questions": sum(
                q.priority == "high" and q.status == "open" for q in questions
            ),
            "observed_evidence_count": len(self.observed),
            "counter_searches_performed": len(self.counter_searches),
            "loaded_filing_count": len(self.environment["documents"]),
            "extraction_limitations": self.environment["gaps"],
            "core_question_status": self.working.core_question_status,
            "expected_value_of_more_research": self.working.expected_value_of_more_research,
            "recent_research_progress": self._recent_progress(),
            "methodology_checks": self._methodology_checks(),
        }
        if include_required:
            reflection = self.reflection_decision()
            blockers = (
                self._evidence_exhausted_blockers()
                if self.working.core_question_status == "evidence_exhausted"
                else self._sufficient_evidence_blockers()
            )
            output["submission_blockers"] = [code for code, _message in blockers]
            output["submission_blocker_details"] = [
                {"code": code, "message": message} for code, message in blockers
            ]
            output["required_state_refresh"] = (
                ["runtime_reflection"] if reflection["needed"] else []
            )
            output["state_refresh_reason"] = reflection["reason"]
            output["required_before_submit"] = self._required_before_submit()
        return output

    def catalog(self) -> Json:
        return {
            "documents": list(self.environment["documents"].values()),
            "object_counts": {
                kind: sum(obj["kind"] == kind for obj in self.environment["objects"].values())
                for kind in ("page", "section", "table", "figure", "footnote", "evidence")
            },
            "available_metrics": sorted(
                {f["metric_code"] for f in self.environment["facts"].values()}
            ),
            "formula_registry": {**FORMULAS, **SERIES_FORMULAS},
            "statement_series_metrics": sorted(SERIES_METRICS),
            "gaps": self.environment["gaps"],
            "whole_documents_accessible": True,
            "extraction_is_lossless": False,
        }

    def _observe(self, obj: Json, text: str, offset: int = 0) -> str:
        identifier = (
            "view_"
            + payload_sha256({"source": obj["artifact_id"], "text": text, "offset": offset})[:24]
        )
        self.observed[identifier] = {
            "artifact_id": identifier,
            "kind": "evidence",
            "document_id": obj["document_id"],
            "source_artifact_id": obj["artifact_id"],
            "source_kind": obj["kind"],
            "page_id": obj.get("page_id")
            or (obj["artifact_id"] if obj["kind"] == "page" else None),
            "page_number": obj.get("page_number"),
            "text": text,
            "char_start": offset,
            "char_end": offset + len(text),
            "source_uri": obj["source_uri"],
            "published_at": obj["published_at"],
            "text_hash": payload_sha256(text),
            "content_role": "untrusted_source",
        }
        return identifier

    def bootstrap(self) -> Json:
        ranked, metric_hints = bootstrap_evidence_candidates(
            self.environment["objects"], self.request.research_question, limit=6
        )
        evidence = []
        for item in ranked:
            obj = self.environment["objects"][item["artifact_id"]]
            identifier = self._observe(obj, item["snippet"])
            evidence.append({**item, "evidence_id": identifier})
        # Fact-source snippets remain available even when the narrative query has poor recall.
        facts = list(self.environment["facts"].values())
        for fact in facts:
            source = self.environment["objects"][fact["evidence_id"]]
            fact["observed_evidence_id"] = self._observe(source, source["text"])
        self.save()
        focused_hint = (
            {
                "metric_codes": metric_hints,
                "instruction": (
                    "这是聚焦事实抽取题。若最高排名 initial_evidence 已包含目标报表行/期间，"
                    "优先用 read_filing 或 extract_statement_series 核验该来源；只有核验失败"
                    "再扩大 search_filing，不要先做泛化检索。"
                ),
            }
            if metric_hints and not _analytical_question(self.request.research_question)
            else None
        )
        return {
            "request": self.request.model_dump(mode="json"),
            "catalog": self.catalog(),
            "initial_evidence": evidence,
            "initial_facts": facts[:24],
            "metric_hints": metric_hints,
            "focused_verification_hint": focused_hint,
            "notice": (
                "初始召回不是全部信息；标准财务指标会使用本地别名词典扩展种子召回，"
                "但仍须搜索/阅读原文确认，必要时查看原页图像。"
            ),
        }

    @staticmethod
    def _fact_digest(fact: Json) -> Json:
        return {
            key: fact.get(key)
            for key in (
                "fact_id",
                "metric_code",
                "value",
                "currency",
                "measurement_unit",
                "period",
                "observed_evidence_id",
            )
            if fact.get(key) is not None
        }

    @classmethod
    def _result_digest(cls, result: Json) -> Json:
        if result.get("reused_cached_result"):
            return {
                key: result.get(key)
                for key in (
                    "reused_cached_result",
                    "research_progress",
                    "previous_call_id",
                    "previous_evidence_ids",
                    "calculation_id",
                    "message",
                )
                if result.get(key) is not None
            }
        output: Json = {
            key: result.get(key)
            for key in (
                "error",
                "message",
                "evidence_id",
                "artifact_id",
                "kind",
                "page_id",
                "page_number",
                "next_offset",
                "calculation_id",
                "series_id",
                "formula_code",
                "input_fact_ids",
                "input_series_ids",
                "metric_code",
                "value",
                "measurement_unit",
                "status",
                "explanation",
                "requested_kind",
                "fallback_applied",
                "fallback_from_kind",
                "loaded_period_labels",
                "unavailable_period_labels",
                "unavailable_metrics",
                "next_action_hint",
            )
            if result.get(key) is not None
        }
        if isinstance(result.get("facts"), list):
            output["facts"] = [
                cls._fact_digest(fact) for fact in result["facts"][:24] if isinstance(fact, dict)
            ]
        if isinstance(result.get("results"), list):
            output["results"] = [
                {
                    key: item.get(key)
                    for key in (
                        "artifact_id",
                        "evidence_id",
                        "kind",
                        "page_id",
                        "page_number",
                        "title",
                        "score",
                    )
                    if item.get(key) is not None
                }
                | {"snippet": str(item.get("snippet", ""))[:300]}
                for item in result["results"][:4]
                if isinstance(item, dict)
            ]
        if isinstance(result.get("content"), str):
            output["content_excerpt"] = result["content"][:1000]
        return output

    def _research_digest(self) -> list[Json]:
        receipts = [
            receipt
            for receipt in self.receipts.values()
            if receipt.get("name") not in {"update_research_state", "submit_research"}
        ][-6:]
        return [
            {
                "call_id": receipt.get("call_id"),
                "name": receipt.get("name"),
                "arguments": receipt.get("arguments"),
                "result": self._result_digest(cast(Json, receipt.get("result", {}))),
                "new_observed_count": receipt.get("new_observed_count", 0),
                "new_calculation_count": receipt.get("new_calculation_count", 0),
                "reused": bool(receipt.get("reused")),
            }
            for receipt in receipts
        ]

    def context_state(self) -> Json:
        return {
            "working": self.working.model_dump(mode="json"),
            "completeness": self.completeness(),
            "observed_evidence_ids": list(self.observed),
            "verified_series": [
                {
                    "series_id": item.get("series_id"),
                    "metric_code": item.get("metric_code"),
                    "page_number": item.get("page_number"),
                    "periods": [value.get("period_label") for value in item.get("values", [])],
                    "evidence_id": item.get("evidence_id"),
                }
                for item in self.verified_series.values()
            ],
            "calculation_ids": list(self.calculations),
            "calculation_summary": [
                {
                    "calculation_id": item.get("calculation_id"),
                    "formula_code": item.get("formula_code"),
                    "input_fact_ids": item.get("input_fact_ids"),
                    "input_series_ids": item.get("input_series_ids"),
                    "status": item.get("status"),
                    "value": item.get("value"),
                    "measurement_unit": item.get("measurement_unit"),
                }
                for item in self.calculations.values()
            ],
            "research_evidence_digest": self._research_digest(),
            "reflection_evidence_memory": self._reflection_evidence_memory(),
            "reference_registry": self.reference_registry(),
            "validation_feedback": self.feedback,
        }

    def _normalize_tool_arguments(self, name: str, arguments: Json) -> tuple[Json, Json | None]:
        """Normalize only unambiguous historical argument shapes at the capability boundary.

        This is protocol compatibility, not financial inference: values and series identities are
        preserved exactly. Ambiguous/unknown shapes still fail strict Pydantic validation.
        """
        if name == "extract_statement_series" and "artifact_id" not in arguments:
            if "page_id" in arguments and set(arguments) <= {"page_id", "row_label", "metric_code"}:
                migrated_arguments = {**arguments, "artifact_id": arguments["page_id"]}
                migrated_arguments.pop("page_id", None)
                return migrated_arguments, {
                    "from": "series_extract_page_id_v1",
                    "to": "series_extract_artifact_id_v2",
                    "original_keys": sorted(arguments),
                }
            return arguments, None
        if name != "calculate_series_metric" or "formula" in arguments or "series_ids" in arguments:
            return arguments, None
        legacy_keys = {
            "metric",
            "numerator_series_id",
            "denominator_series_id",
            "round_decimals",
            "period_label",
        }
        if not set(arguments) <= legacy_keys:
            return arguments, None
        metric = arguments.get("metric")
        numerator = arguments.get("numerator_series_id")
        denominator = arguments.get("denominator_series_id")
        if not all(isinstance(item, str) and item for item in (metric, numerator, denominator)):
            return arguments, None
        normalized: Json = {
            "formula": metric,
            "series_ids": [numerator, denominator],
            "round_decimals": arguments.get("round_decimals", 4),
            "period_label": arguments.get("period_label"),
        }
        migration = {
            "from": "legacy_series_pair_v1",
            "to": "series_calculate_input_v2",
            "original_keys": sorted(arguments),
        }
        return normalized, migration

    def execute(self, call_id: str, name: str, arguments: Json, parent: str | None = None) -> Json:
        self.check()
        if call_id in self.receipts:
            receipt = self.receipts[call_id]
            if receipt["name"] != name or receipt["arguments"] != arguments:
                raise ValueError("a tool call ID cannot be rebound to different arguments")
            return cast(Json, receipt["result"])
        prior = next(
            (
                receipt
                for receipt in reversed(list(self.receipts.values()))
                if (
                    receipt["name"] == name
                    and receipt["arguments"] == arguments
                    and not receipt.get("reused", False)
                    and "error" not in cast(Json, receipt.get("result", {}))
                )
            ),
            None,
        )
        if prior is not None and name not in {"update_research_state", "submit_research"}:
            prior_result = cast(Json, prior["result"])
            result = {
                "reused_cached_result": True,
                "research_progress": "no_new_information",
                "previous_call_id": prior["call_id"],
                "message": (
                    "相同参数的工具结果已经返回过；本次没有新信息。"
                    "请使用之前的结果，或改用新的搜索/阅读策略。"
                ),
            }
            if prior_result.get("calculation_id"):
                result["calculation_id"] = prior_result["calculation_id"]
            if isinstance(prior_result.get("results"), list):
                result["previous_evidence_ids"] = [
                    item.get("evidence_id")
                    for item in prior_result["results"]
                    if isinstance(item, dict) and item.get("evidence_id")
                ]
            self.receipts[call_id] = {
                "call_id": call_id,
                "name": name,
                "arguments": arguments,
                "result": result,
                "new_observed_count": 0,
                "new_calculation_count": 0,
                "state_changed": False,
                "reused": True,
            }
            self.save()
            self.repository.emit(
                self.run_id,
                "tool_result",
                name,
                "复用已有研究结果",
                "succeeded",
                data={
                    "call_id": call_id,
                    "result": result,
                    "new_observed_evidence_ids": [],
                    "new_observed_count": 0,
                    "reused": True,
                },
            )
            return result
        before = set(self.observed)
        before_calculations = set(self.calculations)
        before_state = self.working.model_dump(mode="json")
        definition = TOOL_MODELS.get(name)
        label = definition[2] if definition else "拒绝未知工具"
        normalized_arguments, protocol_migration = self._normalize_tool_arguments(name, arguments)
        span_data: Json = {"arguments": arguments, "call_id": call_id}
        if protocol_migration is not None:
            span_data["normalized_arguments"] = normalized_arguments
            span_data["protocol_migration"] = protocol_migration
        with self.repository.span(
            self.run_id,
            name,
            label,
            parent=parent,
            data=span_data,
        ) as span:
            try:
                if definition is None:
                    raise ValueError("tool is not in the filing-only registry")
                parsed = definition[0].model_validate(normalized_arguments)
                result = self._dispatch(name, parsed)
                if protocol_migration is not None and "error" not in result:
                    result = {**result, "protocol_migration": protocol_migration}
                    self.repository.emit(
                        self.run_id,
                        "tool_protocol_migrated",
                        name,
                        "兼容旧版工具参数并按当前契约执行",
                        "succeeded",
                        parent_span_id=span,
                        data={
                            "call_id": call_id,
                            "migration": protocol_migration,
                            "normalized_arguments": normalized_arguments,
                        },
                    )
            except ValidationError as exc:
                details: list[str] = []
                observed_lengths: Json = {}
                for error in exc.errors()[:8]:
                    location = ".".join(map(str, error["loc"]))
                    detail = location + ": " + str(error["type"])
                    if error["type"] == "string_too_long":
                        field = str(error["loc"][0]) if error["loc"] else ""
                        value = normalized_arguments.get(field)
                        context = error.get("ctx")
                        max_length = (
                            context.get("max_length") if isinstance(context, dict) else None
                        )
                        if isinstance(value, str):
                            observed_lengths[field] = len(value)
                        if max_length is not None:
                            detail += f" (max_length={max_length}"
                            if isinstance(value, str):
                                detail += f", actual_length={len(value)}"
                            detail += ")"
                    details.append(detail)
                result = {
                    "error": "INVALID_TOOL_ARGUMENTS",
                    "details": details,
                }
                if name == "submit_research":
                    result.update(
                        {
                            "field_limits": {
                                "summary_max_chars": 4000,
                                "why_stop_max_chars": 4000,
                                "remaining_uncertainty_max_chars_each": 4000,
                            },
                            "observed_lengths": observed_lengths,
                            "required_action": (
                                "Retry submit_research only. Compress summary to <= 4000 "
                                "characters (prefer 1000-2500), keep the required conclusions "
                                "and evidence boundary, and do not perform additional research "
                                "just to repair this contract error."
                            ),
                        }
                    )
            except (ValueError, KeyError) as exc:
                result = {"error": "TOOL_INPUT_REJECTED", "message": str(exc)[:800]}
            self.receipts[call_id] = {
                "call_id": call_id,
                "name": name,
                "arguments": arguments,
                "normalized_arguments": normalized_arguments
                if normalized_arguments != arguments
                else None,
                "result": result,
                "new_observed_count": len(set(self.observed) - before),
                "new_calculation_count": len(set(self.calculations) - before_calculations),
                "state_changed": self.working.model_dump(mode="json") != before_state,
                "reused": False,
            }
            self.save()
            self.repository.emit(
                self.run_id,
                "tool_result",
                name,
                label,
                "failed" if "error" in result else "succeeded",
                parent_span_id=span,
                data={
                    "call_id": call_id,
                    "result": result,
                    "new_observed_evidence_ids": sorted(set(self.observed) - before),
                    "new_observed_count": len(set(self.observed) - before),
                    "new_calculation_count": len(set(self.calculations) - before_calculations),
                    "state_changed": self.working.model_dump(mode="json") != before_state,
                    "reused": False,
                },
            )
        self.check()
        return result

    def _resolve_submission_evidence(self, references: list[str]) -> tuple[list[str], list[Json]]:
        """Resolve run-owned calculation/series/fact lineage to observed evidence.

        The persisted dossier always contains actual observed evidence IDs. This lets the
        research model cite a calculation it just produced without forcing it to reconstruct
        internal lineage identifiers, while unknown or unobserved sources remain fail-closed.
        """
        resolved: list[str] = []
        resolutions: list[Json] = []

        def append_evidence(evidence_id: object, *, source_id: str, source_kind: str) -> None:
            if not isinstance(evidence_id, str) or evidence_id not in self.observed:
                raise ValueError(
                    f"{source_kind} {source_id} does not resolve to evidence observed in this run"
                )
            if evidence_id not in resolved:
                resolved.append(evidence_id)
            resolutions.append(
                {
                    "input_reference_id": source_id,
                    "input_reference_kind": source_kind,
                    "resolved_evidence_id": evidence_id,
                }
            )

        def resolve_series(series_id: str, *, source_id: str, source_kind: str) -> None:
            series = self.verified_series.get(series_id)
            if series is None:
                raise ValueError(f"unknown verified statement series reference: {series_id}")
            append_evidence(series.get("evidence_id"), source_id=source_id, source_kind=source_kind)

        def resolve_fact(fact_id: str, *, source_id: str, source_kind: str) -> None:
            fact = self.environment["facts"].get(fact_id)
            if fact is None:
                raise ValueError(f"unknown verified financial fact reference: {fact_id}")
            append_evidence(
                fact.get("observed_evidence_id"), source_id=source_id, source_kind=source_kind
            )

        for reference in references:
            if reference in self.observed:
                append_evidence(reference, source_id=reference, source_kind="evidence")
                continue
            if reference in self.verified_series:
                resolve_series(reference, source_id=reference, source_kind="statement_series")
                continue
            if reference in self.environment["facts"]:
                resolve_fact(reference, source_id=reference, source_kind="financial_fact")
                continue
            calculation = self.calculations.get(reference)
            if calculation is None:
                raise ValueError(
                    "submission support reference is not observed evidence or a run-owned "
                    f"fact/series/calculation: {reference}"
                )
            input_series_ids = calculation.get("input_series_ids", [])
            input_fact_ids = calculation.get("input_fact_ids", [])
            if not input_series_ids and not input_fact_ids:
                raise ValueError(f"calculation {reference} has no resolvable source lineage")
            for series_id in input_series_ids:
                resolve_series(
                    str(series_id), source_id=reference, source_kind="calculation_series_lineage"
                )
            for fact_id in input_fact_ids:
                resolve_fact(
                    str(fact_id), source_id=reference, source_kind="calculation_fact_lineage"
                )
        if not resolved:
            raise ValueError("submission must resolve to at least one observed evidence item")
        return resolved, resolutions

    def _dispatch(self, name: str, parsed: BaseModel) -> Json:
        if name == "list_filings":
            return self.catalog()
        if name in {"search_filing", "search_counter_evidence"}:
            if isinstance(parsed, CounterInput):
                query, kind, document_id, offset, limit = parsed.query, "all", None, 0, 8
            else:
                assert isinstance(parsed, SearchInput)
                query, kind, document_id, offset, limit = (
                    parsed.query,
                    parsed.kind,
                    parsed.document_id,
                    parsed.offset,
                    parsed.limit,
                )
            if document_id and document_id not in self.environment["documents"]:
                raise ValueError("document is outside this research run")
            ranked = search_objects(self.environment["objects"], query, kind, document_id)
            fallback_from_kind: str | None = None
            if not ranked and kind not in {"all", "evidence", "page"}:
                fallback_from_kind = kind
                broad = search_objects(self.environment["objects"], query, "all", document_id)
                useful_kinds = {"page", "evidence", "table", "section", "footnote"}
                deduped: list[Json] = []
                seen_locations: set[tuple[str, object]] = set()
                for item in broad:
                    if item["kind"] not in useful_kinds:
                        continue
                    location: tuple[str, object]
                    if item.get("page_number") is not None:
                        location = (str(item["document_id"]), item["page_number"])
                    else:
                        location = (str(item["document_id"]), item["artifact_id"])
                    if location in seen_locations:
                        continue
                    seen_locations.add(location)
                    deduped.append(item)
                ranked = deduped
            results = []
            for item in ranked[offset : offset + limit]:
                obj = self.environment["objects"][item["artifact_id"]]
                results.append({**item, "evidence_id": self._observe(obj, item["snippet"])})
            output = {
                "results": results,
                "total_matches": len(ranked),
                "next_offset": offset + limit if offset + limit < len(ranked) else None,
                "not_found_does_not_prove_absence": True,
                "requested_kind": kind,
                "fallback_applied": fallback_from_kind is not None,
                "fallback_from_kind": fallback_from_kind,
                "fallback_scope": (
                    "page_evidence_table_section_footnote"
                    if fallback_from_kind is not None
                    else None
                ),
            }
            if isinstance(parsed, CounterInput):
                self.counter_searches.append(
                    {
                        "hypothesis": parsed.hypothesis,
                        "query": query,
                        "evidence_ids": [item["evidence_id"] for item in results],
                    }
                )
            return output
        if isinstance(parsed, ReadInput):
            obj = self.environment["objects"].get(parsed.artifact_id) or self.observed.get(
                parsed.artifact_id
            )
            if obj is None:
                raise ValueError("artifact is not in this run's filing environment")
            text = obj["text"]
            if parsed.offset > len(text):
                raise ValueError("offset is outside the source text")
            excerpt = text[parsed.offset : parsed.offset + parsed.max_chars]
            identifier = self._observe(obj, excerpt, parsed.offset)
            result = {
                "artifact_id": parsed.artifact_id,
                "evidence_id": identifier,
                "kind": obj["kind"],
                "content": excerpt,
                "text_length": len(text),
                "next_offset": parsed.offset + len(excerpt)
                if parsed.offset + len(excerpt) < len(text)
                else None,
                "page_id": obj.get("page_id"),
                "page_number": obj.get("page_number"),
                "extraction_status": obj.get("extraction_status"),
                "related_table_ids": obj.get("table_ids", []),
                "footnote_ids": obj.get("footnote_ids", []),
            }
            if obj["kind"] == "table":
                result.update(
                    {
                        "row_count": obj["row_count"],
                        "column_count": obj["column_count"],
                        "unit_candidates": obj.get("unit_candidates", []),
                        "header_status": obj["header_status"],
                        "table_notice": (
                            "单元格结构可在原表查看；提取候选不是已核验财务事实，"
                            "表头/单位/脚注不可省略。"
                        ),
                    }
                )
            return result
        if isinstance(parsed, ImageInput):
            page = self.environment["objects"].get(parsed.page_id)
            if page is None or page["kind"] != "page":
                raise ValueError("page is not in this run")
            image_blob_id = render_page(self.repository, page)
            identifier = (
                "visual_" + payload_sha256({"page": parsed.page_id, "image": image_blob_id})[:24]
            )
            self.observed[identifier] = {
                **page,
                "artifact_id": identifier,
                "source_artifact_id": parsed.page_id,
                "kind": "evidence",
                "source_kind": "page_image",
                "image_blob_id": image_blob_id,
                "page_id": parsed.page_id,
                "visual_interpretation_verified": False,
            }
            return {
                "evidence_id": identifier,
                "page_id": parsed.page_id,
                "image_blob_id": image_blob_id,
                "notice": "查看实际页面图像；视觉读数不能自动作为确定性计算输入。",
            }
        if isinstance(parsed, FactsInput):
            found = [
                f
                for f in self.environment["facts"].values()
                if (not parsed.metrics or f["metric_code"] in parsed.metrics)
                and (
                    not parsed.period_labels
                    or self.environment["documents"][f["document_id"]]["period_label"]
                    in parsed.period_labels
                )
            ]
            loaded_periods = {
                source["period_label"] for source in self.environment["documents"].values()
            }
            requested_periods = set(parsed.period_labels)
            coverage_by_period = {
                period: sorted(
                    {
                        fact["metric_code"]
                        for fact in found
                        if self.environment["documents"][fact["document_id"]]["period_label"]
                        == period
                    }
                )
                for period in sorted(requested_periods or loaded_periods)
            }
            missing_periods = sorted(requested_periods - loaded_periods)
            return {
                "facts": found,
                "unavailable_metrics": sorted(
                    set(parsed.metrics) - {f["metric_code"] for f in found}
                ),
                "loaded_period_labels": sorted(loaded_periods),
                "unavailable_period_labels": missing_periods,
                "coverage_by_period": coverage_by_period,
                "next_action_hint": (
                    "Use add_filing for the missing period before period comparison."
                    if missing_periods
                    else None
                ),
            }
        if isinstance(parsed, CalculateInput):
            result = calculate(parsed, self.environment["facts"])
            self.calculations[result["calculation_id"]] = result
            return result
        if isinstance(parsed, SeriesExtractInput):
            source = self.environment["objects"].get(parsed.artifact_id)
            if source is None or source.get("kind") not in {"page", "table"}:
                raise ValueError("series extraction artifact is outside this research run")
            document = self.environment["documents"].get(source["document_id"])
            if document is None:
                raise ValueError("series extraction document is outside this research run")
            result = extract_statement_series(parsed, source, document)
            excerpt = str(result["source_excerpt"])
            offset = max(0, str(source.get("text", "")).find(excerpt))
            evidence_id = self._observe(source, excerpt, offset)
            result["evidence_id"] = evidence_id
            self.verified_series[result["series_id"]] = result
            return result
        if isinstance(parsed, SeriesCalculateInput):
            semantic_match = next(
                (
                    calculation
                    for calculation in self.calculations.values()
                    if calculation.get("status") == "valid"
                    and calculation.get("formula_code") == parsed.formula
                    and list(calculation.get("input_series_ids", [])) == list(parsed.series_ids)
                    and calculation.get("period_label") == parsed.period_label
                ),
                None,
            )
            if semantic_match is not None:
                return {
                    **semantic_match,
                    "semantic_reuse": True,
                    "requested_round_decimals": parsed.round_decimals,
                    "message": (
                        "相同公式、输入序列和期间已经有确定性计算；不同显示精度不创建新的 "
                        "CalculationRecord。请复用已有 calculation_id / unrounded_value。"
                    ),
                }
            result = calculate_series_metric(parsed, self.verified_series)
            self.calculations[result["calculation_id"]] = result
            return result
        if isinstance(parsed, WorkingState):
            return self.apply_working_state(parsed)
        if isinstance(parsed, AddFilingInput):
            if len(self.environment["documents"]) >= 6:
                raise ValueError("six-filing resource boundary reached; preserve this limitation")
            if any(
                source["period_label"] == parsed.period_label
                for source in self.environment["documents"].values()
            ):
                return {"already_loaded": True, "catalog": self.catalog()}
            package = FilingPreparer(self.repository).prepare(
                self.request,
                self.run_id,
                self.check,
                period_label=parsed.period_label,
                expected_company_id=self.environment["entity"]["company_id"],
            )
            for key in ("documents", "objects", "facts"):
                self.environment[key].update(package[key])
            self.environment["gaps"] = list(
                dict.fromkeys(self.environment["gaps"] + package["gaps"])
            )
            return {
                "new_documents": list(package["documents"].values()),
                "new_fact_ids": list(package["facts"]),
                "gaps": package["gaps"],
            }
        if isinstance(parsed, Submission):
            if binary_question(self.request.research_question):
                if parsed.direct_answer == "not_applicable":
                    raise ValueError("binary research question requires an explicit direct_answer")
                if (
                    parsed.stop_reason == "evidence_exhausted"
                    and parsed.direct_answer != "cannot_determine"
                ):
                    raise ValueError(
                        "evidence_exhausted binary research requires direct_answer=cannot_determine"
                    )
                if (
                    parsed.stop_reason == "sufficient_evidence"
                    and parsed.direct_answer == "cannot_determine"
                ):
                    raise ValueError(
                        "sufficient_evidence binary research cannot use "
                        "direct_answer=cannot_determine"
                    )
            elif parsed.direct_answer != "not_applicable":
                raise ValueError(
                    "non-binary research question requires direct_answer=not_applicable"
                )
            resolved_evidence_ids, resolutions = self._resolve_submission_evidence(
                parsed.evidence_ids
            )
            if parsed.stop_reason == "sufficient_evidence":
                blockers = self._sufficient_evidence_blockers()
                if blockers:
                    raise ValueError(blockers[0][1])
            if parsed.stop_reason == "evidence_exhausted" and not parsed.remaining_uncertainties:
                raise ValueError("evidence exhaustion must preserve its remaining uncertainties")
            if parsed.stop_reason == "evidence_exhausted" and (
                self.working.core_question_status != "evidence_exhausted"
                or self.working.expected_value_of_more_research != "low"
            ):
                raise ValueError(
                    "evidence_exhausted submission requires matching research state and low "
                    "expected value of further filing research"
                )
            if parsed.stop_reason == "evidence_exhausted":
                blockers = self._evidence_exhausted_blockers()
                if blockers:
                    raise ValueError(blockers[0][1])
            self.dossier = {
                **parsed.model_dump(mode="json"),
                "evidence_ids": resolved_evidence_ids,
            }
            lineage_changed = resolved_evidence_ids != parsed.evidence_ids
            if lineage_changed:
                self.repository.emit(
                    self.run_id,
                    "submission_lineage_resolved",
                    "submit_research",
                    "已将计算或数值序列引用解析为实际查看过的财报证据",
                    "succeeded",
                    data={
                        "input_reference_ids": parsed.evidence_ids,
                        "resolved_evidence_ids": resolved_evidence_ids,
                        "resolutions": resolutions,
                    },
                )
            return {
                ("accepted"): True,
                ("dossier"): self.dossier,
                ("completeness"): self.completeness(),
                ("support_reference_resolution"): resolutions,
            }
        raise ValueError("unsupported tool input")

    def synthesis_context(self) -> Json:
        if not self.dossier:
            raise ValueError("research has not been submitted")
        question = self.request.research_question
        presentation_language = "zh-CN" if re.search(r"[\u3400-\u9fff]", question) else "en"
        return {
            "request": self.request.model_dump(mode="json"),
            "presentation_contract": {
                "language": presentation_language,
                "instruction": (
                    "All user-facing report prose must match the research_question language; "
                    "research notebook prose in another language is source material to translate, "
                    "not a signal to change the report language."
                ),
            },
            "dossier": self.dossier,
            "working": self.working.model_dump(mode="json"),
            "evidence": [self.observed[key] for key in self.dossier["evidence_ids"]],
            "financial_facts": list(self.environment["facts"].values()),
            "verified_statement_series": list(self.verified_series.values()),
            "calculations": list(self.calculations.values()),
            "extraction_gaps": self.environment["gaps"],
            "validation_feedback": self.feedback,
        }

    def consecutive_invalid_submission_count(self) -> int:
        """Bound writer-contract repair loops without confusing them with research progress."""

        count = 0
        for receipt in reversed(list(self.receipts.values())):
            if receipt.get("name") != "submit_research":
                break
            result = cast(Json, receipt.get("result", {}))
            if result.get("error") not in {"INVALID_TOOL_ARGUMENTS", "TOOL_INPUT_REJECTED"}:
                break
            count += 1
        return count

    def observation_messages(self, calls: list[Json]) -> list[Json]:
        return [
            {
                "call_id": call["call_id"],
                "name": call["name"],
                "arguments": json.dumps(call["arguments"], ensure_ascii=False),
                "result": self.receipts[call["call_id"]]["result"],
            }
            for call in calls
            if call["call_id"] in self.receipts
        ]
