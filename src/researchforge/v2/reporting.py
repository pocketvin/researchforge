# ruff: noqa: RUF001 -- Chinese product fallback copy intentionally uses Chinese punctuation.
"""Run-bound report contracts and a conservative renderer for validated research dossiers."""

from __future__ import annotations

import copy
import re

from researchforge.v2.contracts import Json, ResearchReport, strict_schema

_ID_RE = re.compile(r"\b(?:calc|fact)_[A-Za-z0-9_.:-]+\b")
_PUBLIC_PROSE_ID_RE = re.compile(
    r"\b(?:view|page|table|series|calc|fact|doc|run)_[A-Za-z0-9_.:-]+\b",
    re.IGNORECASE,
)
_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_SNAKE_CASE_RE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")


def _public_prose(text: str) -> str:
    """Remove run-internal implementation language and keep fallback claims epistemically scoped."""
    value = _PUBLIC_PROSE_ID_RE.sub("", str(text))
    if _CJK_RE.search(value):
        for internal, public in (
            ("evidence_exhausted", "当前财报已无更多有效信息"),
            ("sufficient_evidence", "现有证据已足够"),
            ("not_answerable_from_filings", "仅凭财报无法回答"),
            ("needs_attention", "需要处理"),
            ("not_applicable", "不适用"),
            ("answerable", "已有足够信息形成结论"),
            ("investigating", "仍在研究"),
            ("limited", "有边界结论"),
        ):
            value = re.sub(rf"\b{re.escape(internal)}\b", public, value, flags=re.IGNORECASE)
    value = _SNAKE_CASE_RE.sub(lambda match: match.group(0).replace("_", " "), value)
    # A conservative renderer must never upgrade a dossier's missing-observation wording into a
    # whole-filing nonexistence claim. Rewrite filing-wide negatives into the actual epistemic
    # boundary owned by this fallback: what the cited evidence establishes.
    value = re.sub(
        r"\b(?:the|this) filing(?:\s+(?:excerpt|evidence|text|section))? "
        r"(?:does not|doesn't) "
        r"(?:explicitly\s+)?(?:state|label|contain|provide|disclose|report|present|show|include|quantify|establish|attribute|rank)\b",
        "the cited evidence does not establish",
        value,
        flags=re.IGNORECASE,
    )
    # The validator deliberately rejects filing-wide negatives even when a short clause sits
    # between the filing subject and the negative verb (for example ``the filing notes X but
    # does not quantify Y``). Safe fallback must normalize the same shape rather than emitting
    # wording that its own deterministic gate will reject. Preserve the observed positive clause
    # and narrow only the negative half to what the cited evidence establishes.
    value = re.sub(
        r"\b(?:the|this) (?:filing|annual report)(?P<middle>[^.!?]{0,40}?)"
        r"\bdoes\s+not\s+(?:explicitly\s+)?(?:contain|provide|disclose|report|present|show|include|state|label|quantify|establish|attribute|rank)\b",
        r"the cited evidence\g<middle>does not establish",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\b(?:the|this) filing (?:contains|provides|has) no\b",
        "the cited evidence does not establish",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\bno ([^.\n]{1,160}?) (?:is|are) present in the filing\b",
        r"no \1 is present in the cited evidence",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"\bno ([^.\n]{1,160}?) exists? in the filing\b",
        r"no \1 was established in the cited evidence",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"财报(?:中)?未披露", "当前引用证据未建立", value)
    value = re.sub(r"财报(?:中)?没有", "当前引用证据未显示", value)
    # Safe fallback is deliberately more conservative than the model writer. If the notebook
    # contains an analyst-created ranking that already failed semantic review, preserve the
    # underlying fact while dropping the unsupported hierarchy instead of asking the fallback
    # reviewer to adjudicate another superlative.
    for pattern, replacement in (
        (
            r"\bis the largest single positive operating swing\b",
            "is a material positive operating swing",
        ),
        (r"\bis the largest single revenue-side swing\b", "is a material revenue-side swing"),
        (r"\bis the largest contributor\b", "is a material contributor"),
        (r"\bis the dominant revenue line\b", "is a major revenue line"),
        (r"\bsingle largest driver\b", "major driver among the cited line items"),
        (r"\bled by\b", "including"),
    ):
        value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
    # Removing internal IDs can leave punctuation-only reference shells such as ``(, , )``.
    # Collapse those shells completely before normal spacing cleanup.
    value = re.sub(r"[（(]\s*(?:[,，;；:/：、-]\s*)*[）)]", "", value)
    value = re.sub(
        r"([（(][^）)]*?)[,，;；:/：、-]+\s*([）)])",
        r"\1\2",
        value,
    )
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    value = re.sub(r"[ \t]{2,}", " ", value)
    value = re.sub(r" \n", "\n", value)
    return value.strip(" \t,;:-")


def sanitize_public_prose(text: str) -> str:
    """Sanitize user-facing prose while leaving structured provenance IDs untouched."""
    return _public_prose(text)


def _cash_flow_health_question(context: Json) -> bool:
    question = str(context.get("request", {}).get("research_question", "")).casefold()
    return any(marker in question for marker in ("cash flow", "cashflow", "现金流")) and any(
        marker in question for marker in ("healthy", "health", "quality", "健康", "质量")
    )


def _cash_flow_safe_prose(text: str) -> str:
    """Neutralize unsupported degree/causal wording in cash-flow-health fallback prose."""
    value = _public_prose(text)
    replacements: tuple[tuple[str, str], ...] = (
        (
            r"经营现金创造与利润现金转换在本期均较强",
            "本期经营活动现金流同比增长，且经营现金流/净利润比值高于1",
        ),
        (r"经营现金创造较强", "经营活动现金流为正且同比增长"),
        (r"利润现金转换较强", "经营现金流/净利润比值高于1"),
        (r"现金创造能力较强", "经营活动现金流为正且同比增长"),
        (r"其中相当部分来自", "其中包含"),
        (r"相当部分来自", "包含来自"),
        (r"较厚的流动性缓冲", "已披露的流动性来源"),
        (r"流动性缓冲较厚", "存在已披露的流动性来源"),
        (r"流动性缓冲充足", "披露了现金余额与可用授信等流动性来源"),
        (r"投资与筹资活动均形成显著净流出", "投资与筹资活动均为净流出"),
        (r"投资与筹资活动均为大额净流出", "投资与筹资活动均为净流出"),
        (r"投资与筹资现金流出压力在本期明显加大", "投资与筹资现金流净流出较上年增加"),
        (
            r"期末金融负债到期结构显示短期偿付安排(?:规模)?可观",
            "期末金融负债到期结构披露了多项一年以内到期的项目",
        ),
        (
            r"本期OCF质量受营运资金释放（主要是应收回收）明显支撑",
            "本期经营现金流包含营运资金变动的正向贡献（包括应收回收）",
        ),
        (r"主要是应收回收", "包括应收回收"),
        (r"明显支撑", "提供正向贡献"),
        (r"是现金净流出的主要来源", "构成现金变动的负向贡献项"),
        (r"现金净流出的主要来源", "现金变动的负向贡献项"),
        (r"短期偿付安排(?:规模)?可观", "存在多项一年以内到期的偿付安排"),
        (r"显著正向贡献", "正向贡献"),
        (r"明显正向贡献", "正向贡献"),
        (r"重要正向来源", "正向贡献项"),
        (r"利润现金转换大于1", "经营现金流/净利润比值高于1"),
    )
    for pattern, replacement in replacements:
        value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
    return _public_prose(value)


def _truncate_public(text: str, limit: int) -> str:
    value = _public_prose(text)
    if len(value) <= limit:
        return value
    probe = value[: max(1, limit - 1)].rstrip()
    boundary = max(probe.rfind(" "), probe.rfind("，"), probe.rfind(","), probe.rfind("；"))
    if boundary >= max(24, limit // 2):
        probe = probe[:boundary].rstrip(" ,，;；:-")
    return probe + "…"


def _chinese_question(context: Json) -> bool:
    question = str(context.get("request", {}).get("research_question", ""))
    return bool(_CJK_RE.search(question))


def _matches_presentation_language(text: str, *, chinese: bool) -> bool:
    has_cjk = bool(_CJK_RE.search(str(text)))
    return has_cjk if chinese else not has_cjk


def _limited_language_fallback(question: str, *, chinese: bool) -> str:
    if chinese:
        return (
            f"对于“{question}”，当前引用的财报证据没有建立作出更强结论所需的输入或比较基准；"
            "因此仅保留证据边界，不补作推断。"
        )
    return (
        f'For the objective "{question}", the cited filing evidence does not establish the '
        "inputs or comparison basis needed for a stronger conclusion; the result is therefore "
        "kept evidence-limited rather than filled with inference."
    )


def _enum_items(values: list[str], *, sentinel: str) -> Json:
    """Keep arrays empty-capable while making any non-empty item run-bound."""
    return {"type": "string", "enum": values or [sentinel]}


def bound_report_schema(context: Json) -> Json:
    """Bind every source-bearing report field to IDs that actually exist in this run."""
    schema = copy.deepcopy(strict_schema(ResearchReport))
    evidence_ids = sorted(
        {
            str(item["artifact_id"])
            for item in context.get("evidence", [])
            if isinstance(item, dict) and item.get("artifact_id")
        }
    )
    fact_ids = sorted(
        {
            str(item["fact_id"])
            for item in context.get("financial_facts", [])
            if isinstance(item, dict) and item.get("fact_id")
        }
    )
    calculation_ids = sorted(
        {
            str(item["calculation_id"])
            for item in context.get("calculations", [])
            if isinstance(item, dict) and item.get("calculation_id")
        }
    )
    finding = schema["$defs"]["Finding"]["properties"]
    finding["evidence_ids"]["items"] = _enum_items(evidence_ids, sentinel="__NO_RUN_EVIDENCE_ID__")
    finding["fact_ids"]["items"] = _enum_items(fact_ids, sentinel="__NO_RUN_FACT_ID__")
    finding["calculation_ids"]["items"] = _enum_items(
        calculation_ids, sentinel="__NO_RUN_CALCULATION_ID__"
    )
    schema["$defs"]["AnalysisSection"]["properties"]["evidence_ids"]["items"] = _enum_items(
        evidence_ids, sentinel="__NO_RUN_EVIDENCE_ID__"
    )
    schema["$defs"]["NumericAssertion"]["properties"]["source_id"] = _enum_items(
        sorted({*fact_ids, *calculation_ids}), sentinel="__NO_RUN_NUMERIC_SOURCE_ID__"
    )
    direct_answer = str(context.get("dossier", {}).get("direct_answer", "not_applicable"))
    schema["properties"]["direct_answer"] = {
        "type": "string",
        "const": direct_answer,
    }
    return schema


def _linked_ids(text: str, allowed: set[str], prefix: str) -> list[str]:
    return list(
        dict.fromkeys(
            identifier
            for identifier in _ID_RE.findall(text)
            if identifier.startswith(prefix) and identifier in allowed
        )
    )


def build_safe_dossier_report(context: Json) -> ResearchReport:
    """Render only already-public research state when model prose cannot satisfy report contracts.

    This is not a substitute research agent. It performs no inference or arithmetic: it surfaces
    the submitted dossier and objective conclusions with their existing run-owned source lineage.
    Semantic review still decides whether those claims are supportable.
    """
    dossier = context["dossier"]
    working = context.get("working", {})
    evidence_ids = {
        str(item["artifact_id"])
        for item in context.get("evidence", [])
        if isinstance(item, dict) and item.get("artifact_id")
    }
    fact_ids = {
        str(item["fact_id"])
        for item in context.get("financial_facts", [])
        if isinstance(item, dict) and item.get("fact_id")
    }
    calculation_ids = {
        str(item["calculation_id"])
        for item in context.get("calculations", [])
        if isinstance(item, dict) and item.get("calculation_id")
    }
    dossier_evidence = [
        str(identifier)
        for identifier in dossier.get("evidence_ids", [])
        if str(identifier) in evidence_ids
    ]
    if not dossier_evidence:
        raise ValueError("safe dossier report requires at least one observed dossier evidence ID")

    chinese = _chinese_question(context)
    public_prose = _cash_flow_safe_prose if _cash_flow_health_question(context) else _public_prose
    limited_copy = (
        "这部分无法仅凭当前财报证据可靠确定，因此不作进一步推断。"
        if chinese
        else "This part cannot be determined reliably from the filing evidence available here, so no stronger inference is made."
    )
    boundary_copy = (
        "其余要求无法仅凭当前财报证据可靠确定，因此保留为未知。"
        if chinese
        else "The remaining requirement cannot be determined reliably from the filing alone and is left unresolved."
    )
    objectives = [item for item in working.get("objectives", []) if isinstance(item, dict)]
    limited_objectives = [
        item
        for item in objectives
        if item.get("priority") == "required" and item.get("status") == "limited"
    ]
    findings: list[Json] = []
    required_summary_parts: list[str] = []
    for objective in objectives:
        if not isinstance(objective, dict) or not str(objective.get("conclusion", "")).strip():
            continue
        question = str(
            objective.get("question") or ("研究目标" if chinese else "Research objective")
        )
        conclusion = public_prose(str(objective["conclusion"]))
        limited = objective.get("status") == "limited"
        conclusion_language_ok = _matches_presentation_language(conclusion, chinese=chinese)
        if limited:
            safe_text = (
                conclusion
                if conclusion and conclusion_language_ok
                else _limited_language_fallback(question, chinese=chinese)
            )
            if limited_copy not in safe_text:
                safe_text = (safe_text + " " + limited_copy).strip()
        else:
            safe_text = conclusion
        if objective.get("priority") == "required":
            required_summary_parts.append(limited_copy if limited else safe_text)
        objective_evidence = [
            str(identifier)
            for identifier in objective.get("evidence_ids", [])
            if str(identifier) in evidence_ids
        ][:20]
        if not objective_evidence:
            objective_evidence = dossier_evidence[:20]
        objective_calc_ids = list(
            dict.fromkeys(
                [
                    str(identifier)
                    for identifier in objective.get("evidence_ids", [])
                    if str(identifier) in calculation_ids
                ]
                + _linked_ids(conclusion, calculation_ids, "calc_")
            )
        )[:20]
        objective_fact_ids = list(
            dict.fromkeys(
                [
                    str(identifier)
                    for identifier in objective.get("evidence_ids", [])
                    if str(identifier) in fact_ids
                ]
                + _linked_ids(conclusion, fact_ids, "fact_")
            )
        )[:20]
        objective_id = str(objective.get("objective_id", "objective"))
        limited_title = f"证据限制：{question}" if chinese else f"Evidence limitation: {question}"
        raw_uncertainty = public_prose(str(objective.get("remaining_uncertainty", "")))
        uncertainty = (
            raw_uncertainty
            if not raw_uncertainty
            or _matches_presentation_language(raw_uncertainty, chinese=chinese)
            else (
                "当前引用证据没有建立作出更强结论所需的缺失输入或比较基准。"
                if chinese
                else "The cited evidence does not establish the missing inputs or comparison basis needed for a stronger conclusion."
            )
        )
        findings.append(
            {
                "claim_id": f"claim_{objective_id}"[:255],
                "title": _truncate_public(limited_title if limited else question, 160),
                "text": safe_text[:4000],
                "kind": "limitation" if limited else "inference",
                "evidence_ids": objective_evidence,
                "fact_ids": objective_fact_ids,
                "calculation_ids": objective_calc_ids,
                "numeric_assertions": [],
                "confidence": "low" if objective.get("status") == "limited" else "medium",
                "uncertainty": uncertainty[:2000],
            }
        )

    if not findings:
        summary = public_prose(str(dossier["summary"]))
        findings.append(
            {
                "claim_id": "claim_submitted_research",
                "title": "已提交研究结论" if chinese else "Submitted filing conclusion",
                "text": summary[:4000],
                "kind": (
                    "limitation"
                    if dossier.get("direct_answer") == "cannot_determine"
                    else "inference"
                ),
                "evidence_ids": dossier_evidence[:20],
                "fact_ids": _linked_ids(summary, fact_ids, "fact_")[:20],
                "calculation_ids": _linked_ids(summary, calculation_ids, "calc_")[:20],
                "numeric_assertions": [],
                "confidence": (
                    "low" if dossier.get("direct_answer") == "cannot_determine" else "medium"
                ),
                "uncertainty": public_prose(
                    "; ".join(str(item) for item in dossier.get("remaining_uncertainties", []))
                )[:2000],
            }
        )

    # The fallback must reuse already-checked objective conclusions rather than the free-form
    # dossier summary. The latter can contain an unregistered convenience restatement (for
    # example turning a registered 116.12% ratio into an unregistered "about 16% above" claim).
    # Required objective conclusions are the research-state contract and retain their lineage in
    # the findings above; limited objectives use the fixed evidence-boundary copy.
    required_items = [item for item in objectives if item.get("priority") == "required"]
    answered_required = [item for item in required_items if item.get("status") == "answered"]
    all_required_limited = bool(required_items and len(limited_objectives) == len(required_items))
    if all_required_limited:
        dossier_summary = (
            "当前引用的财报证据只能支持有边界的回答；缺失的输入或比较基准不足以支持更强结论。具体已核验事实与边界见下方。"
            if chinese
            else "The cited filing evidence supports only a bounded answer: the missing inputs or comparison basis do not support a stronger conclusion. The verified facts and evidence boundaries are stated below."
        )
    elif answered_required:
        if _cash_flow_health_question(context) and dossier.get("direct_answer") == "mixed":
            dossier_summary = (
                "当前引用的财报证据支持混合判断：现金流不同维度同时存在正面与负面证据；"
                "具体事实与边界见下方。"
                if chinese
                else "The cited filing evidence supports a mixed cash-flow assessment: material "
                "positive and negative signals coexist across the assessed dimensions. The facts "
                "and evidence boundaries are stated below."
            )
        else:
            dossier_summary = (
                "当前引用的财报证据支持下方研究结论；凡财报未明确归因、量化或排序之处，报告均保留为分析边界而不补作推断。"
                if chinese
                else "The cited filing evidence supports the findings below. Where the cited evidence does not establish explicit attribution, quantification, or ranking, the report preserves that boundary rather than filling it with inference."
            )
    else:
        dossier_summary = public_prose(str(dossier["summary"]))[:900]
    if limited_objectives and not all_required_limited and boundary_copy not in dossier_summary:
        dossier_summary = " ".join([dossier_summary, boundary_copy]).strip()
    summary_calcs = _linked_ids(dossier_summary, calculation_ids, "calc_")
    summary_facts = _linked_ids(dossier_summary, fact_ids, "fact_")
    findings[0]["calculation_ids"] = list(
        dict.fromkeys([*findings[0]["calculation_ids"], *summary_calcs])
    )[:20]
    findings[0]["fact_ids"] = list(dict.fromkeys([*findings[0]["fact_ids"], *summary_facts]))[:20]

    if limited_objectives:
        uncertainties = [
            str(item.get("uncertainty", ""))[:4000]
            for item in findings
            if item.get("kind") == "limitation" and str(item.get("uncertainty", "")).strip()
        ]
        uncertainties = list(dict.fromkeys(uncertainties))
        uncertainties.append(
            "未观察到某项披露不等于证明它不存在。"
            if chinese
            else "Not observing a disclosure is not the same as proving that it does not exist."
        )
    else:
        # Prefer the sanitized objective-level uncertainty that already follows the public-state
        # language contract. Dossier prose is model-authored and can still be in another language
        # even when the final report must not be. Only fall back to dossier uncertainties whose
        # language matches the user's question.
        uncertainties = list(
            dict.fromkeys(
                str(item.get("uncertainty", ""))[:4000]
                for item in findings
                if str(item.get("uncertainty", "")).strip()
                and _matches_presentation_language(
                    str(item.get("uncertainty", "")), chinese=chinese
                )
            )
        )
        if not uncertainties:
            uncertainties = [
                cleaned[:4000]
                for item in dossier.get("remaining_uncertainties", [])
                if str(item).strip()
                and (cleaned := public_prose(str(item)))
                and _matches_presentation_language(cleaned, chinese=chinese)
            ]
    limitations = uncertainties or [
        (
            "未发现会改变上述结论的重大证据限制。"
            if chinese
            else "No material evidence limitation was identified that would change the conclusion above."
        )
    ]
    company = context.get("request", {}).get("company_query", "公司" if chinese else "Company")
    return ResearchReport.model_validate(
        {
            "schema_version": "2.0.0",
            "direct_answer": dossier.get("direct_answer", "not_applicable"),
            "title": _truncate_public(
                f"{company} 财报研究结论" if chinese else f"{company} filing research conclusion",
                200,
            ),
            "executive_summary": dossier_summary[:4000],
            "findings": findings[:16],
            "sections": [
                {
                    "title": "证据边界" if chinese else "Evidence boundary",
                    "text": (
                        "本报告仅依据上方引用的财报证据；未把未观察到的信息当作不存在。"
                        if chinese
                        else "This report is limited to the filing evidence cited above; an unobserved disclosure is not treated as proof that it does not exist."
                    ),
                    "evidence_ids": dossier_evidence[:30],
                }
            ],
            "limitations": limitations[:3],
            "follow_up_questions": [],
        }
    )
