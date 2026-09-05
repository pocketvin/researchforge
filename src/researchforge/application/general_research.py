"""Question routing, research planning and deterministic filing-evidence retrieval for V1.7."""

# ruff: noqa: RUF001 -- user-facing Chinese questions intentionally use Chinese punctuation.

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar, Literal

JsonObject = dict[str, Any]
ResearchSkill = Literal[
    "company_overview",
    "earnings_change",
    "growth_analysis",
    "financial_health",
    "risk_analysis",
    "business_analysis",
]


@dataclass(frozen=True, slots=True)
class ResearchIntent:
    skill: ResearchSkill
    label: str
    search_terms: tuple[str, ...]
    preferred_sections: tuple[str, ...]

    def artifact_value(self) -> JsonObject:
        return {
            "skill": self.skill,
            "label": self.label,
            "search_terms": list(self.search_terms),
            "preferred_sections": list(self.preferred_sections),
        }


_SKILLS: dict[ResearchSkill, ResearchIntent] = {
    "company_overview": ResearchIntent(
        "company_overview",
        "完整公司分析",
        (
            "business",
            "segment",
            "revenue",
            "profit",
            "cash flow",
            "risk",
            "outlook",
            "业务",
            "分部",
            "收入",
            "利润",
            "现金流",
            "风险",
            "展望",
        ),
        (
            "Business and segments",
            "Growth drivers",
            "Management discussion",
            "Financial statements",
            "Liquidity and capital",
            "Customers and suppliers",
            "Risk factors",
            "Outlook",
        ),
    ),
    "earnings_change": ResearchIntent(
        "earnings_change",
        "业绩变化",
        (
            "revenue",
            "profit",
            "margin",
            "expense",
            "change",
            "increase",
            "decrease",
            "收入",
            "利润",
            "毛利",
            "费用",
            "增长",
            "下降",
            "变动原因",
        ),
        ("Management discussion", "Growth drivers", "Financial statements"),
    ),
    "growth_analysis": ResearchIntent(
        "growth_analysis",
        "增长来源",
        (
            "growth",
            "demand",
            "segment",
            "customer",
            "market",
            "revenue",
            "增长",
            "需求",
            "分部",
            "客户",
            "市场",
            "收入",
        ),
        ("Growth drivers", "Business and segments", "Management discussion"),
    ),
    "financial_health": ResearchIntent(
        "financial_health",
        "财务健康",
        (
            "cash flow",
            "liquidity",
            "debt",
            "inventory",
            "receivable",
            "margin",
            "资本",
            "现金流",
            "债务",
            "存货",
            "应收",
            "毛利",
            "流动性",
        ),
        ("Liquidity and capital", "Financial statements", "Management discussion"),
    ),
    "risk_analysis": ResearchIntent(
        "risk_analysis",
        "风险分析",
        (
            "risk",
            "uncertainty",
            "competition",
            "customer",
            "supplier",
            "regulation",
            "风险",
            "不确定",
            "竞争",
            "客户",
            "供应商",
            "监管",
        ),
        ("Risk factors", "Customers and suppliers", "Management discussion"),
    ),
    "business_analysis": ResearchIntent(
        "business_analysis",
        "业务结构",
        (
            "business",
            "segment",
            "product",
            "service",
            "geographic",
            "customer",
            "业务",
            "分部",
            "产品",
            "服务",
            "地区",
            "客户",
        ),
        ("Business and segments", "Customers and suppliers", "Management discussion"),
    ),
}


class QuestionRouter:
    """Map an ordinary-language research question onto one bounded research skill."""

    _rules: tuple[tuple[ResearchSkill, tuple[str, ...]], ...] = (
        ("risk_analysis", ("风险", "隐患", "风险点", "risk", "uncertainty")),
        ("growth_analysis", ("增长来源", "增长主要", "增长点", "growth", "driver", "driven by")),
        (
            "earnings_change",
            (
                "为什么",
                "原因",
                "变化",
                "变动",
                "下降",
                "增长",
                "why",
                "change",
                "increase",
                "decrease",
            ),
        ),
        (
            "financial_health",
            (
                "现金流",
                "财务健康",
                "偿债",
                "负债",
                "存货",
                "应收",
                "cash flow",
                "liquidity",
                "debt",
                "inventory",
                "receivable",
            ),
        ),
        (
            "business_analysis",
            (
                "业务结构",
                "业务分部",
                "哪块业务",
                "产品结构",
                "segment",
                "business mix",
                "business structure",
            ),
        ),
    )

    def route(self, question: str) -> ResearchIntent:
        lowered = question.casefold()
        # Broad/comprehensive requests must win before any single-dimension marker.
        # A prompt such as "覆盖业绩、增长、业务结构、风险和管理层展望" contains
        # many narrower keywords, but the product intent is still a full company review.
        if any(
            term in lowered
            for term in (
                "完整分析",
                "全面分析",
                "整体分析",
                "完整研究",
                "综合分析",
                "系统分析",
                "覆盖业绩",
                "analyze the company",
                "company overview",
                "full analysis",
                "comprehensive analysis",
            )
        ):
            return _SKILLS["company_overview"]
        if any(
            marker in lowered
            for marker in (
                "业务结构",
                "主要业务",
                "业务分部",
                "分部结构",
                "哪块业务",
                "business structure",
                "business mix",
                "segment structure",
            )
        ):
            return _SKILLS["business_analysis"]
        if any(
            marker in lowered
            for marker in ("增长来源", "增长主要", "增长点", "growth driver", "driven by")
        ):
            return _SKILLS["growth_analysis"]
        if any(
            marker in lowered
            for marker in ("盈利能力", "毛利率", "利润率", "profitability", "gross margin")
        ):
            return _SKILLS["financial_health"]
        if any(
            marker in lowered for marker in ("管理层", "展望", "未来增长", "outlook", "guidance")
        ):
            return _SKILLS["business_analysis"]
        scores: dict[ResearchSkill, int] = {skill: 0 for skill in _SKILLS}
        for skill, markers in self._rules:
            scores[skill] += sum(3 for marker in markers if marker.casefold() in lowered)
        for skill, intent in _SKILLS.items():
            scores[skill] += sum(1 for term in intent.search_terms if term.casefold() in lowered)
        winner = max(scores, key=scores.__getitem__)
        return _SKILLS[winner] if scores[winner] else _SKILLS["company_overview"]


class ResearchPlanner:
    """Produce an explicit, inspectable plan from the routed research intent."""

    _steps: ClassVar[dict[ResearchSkill, tuple[str, ...]]] = {
        "company_overview": (
            "识别公司业务与主要分部",
            "核对核心财务表现与现金转化",
            "寻找主要增长驱动",
            "读取管理层讨论与未来展望",
            "扫描重要风险与反向信号",
            "形成综合判断与后续问题",
        ),
        "earnings_change": (
            "确认本期收入、利润与盈利能力变化",
            "检索管理层对变动原因的解释",
            "定位业务/产品结构变化",
            "检查费用、现金流与营运资本是否支持解释",
            "搜索相反证据并形成因果边界",
        ),
        "growth_analysis": (
            "确认总收入和利润表现",
            "定位业务分部/产品增长来源",
            "检索需求、客户和市场驱动",
            "检查增长是否伴随盈利与现金流改善",
            "扫描增长持续性的主要风险",
            "形成增长来源排序",
        ),
        "financial_health": (
            "核对利润、经营现金流和毛利",
            "检查应收与存货",
            "检索流动性、债务和资本开支信息",
            "寻找一次性或口径限制",
            "形成财务健康判断与监控项",
        ),
        "risk_analysis": (
            "读取官方风险因素",
            "检查财务风险信号",
            "定位客户、供应链、竞争和监管风险",
            "检索管理层对风险的缓释说明",
            "按证据强度和潜在影响排序风险",
            "列出需要继续验证的风险",
        ),
        "business_analysis": (
            "识别主要业务/产品分部",
            "比较各分部的重要性和变化",
            "检索地区、客户与市场结构",
            "结合财务表现判断业务组合变化",
            "读取管理层对业务结构的解释",
            "形成业务结构结论",
        ),
    }

    def plan(self, run_id: str, intent: ResearchIntent) -> list[JsonObject]:
        return [
            {
                "step_id": f"step_{run_id}_research_{index}",
                "description": description,
                "status": "completed",
            }
            for index, description in enumerate(self._steps[intent.skill], start=1)
        ]


def _terms(text: str) -> set[str]:
    lowered = text.casefold()
    output = set(re.findall(r"[a-z0-9][a-z0-9&.-]{1,}", lowered))
    for sequence in re.findall(r"[\u4e00-\u9fff]{2,}", lowered):
        output.add(sequence)
        output.update(sequence[index : index + 2] for index in range(len(sequence) - 1))
    return output


_RETRIEVAL_SIGNALS: dict[ResearchSkill, tuple[str, ...]] = {
    "company_overview": (
        "segment",
        "revenue",
        "driven by",
        "risk",
        "outlook",
        "业务",
        "收入",
        "风险",
    ),
    "earnings_change": (
        "driven by",
        "increased",
        "decreased",
        "year over year",
        "year-over-year",
        "margin",
        "expense",
        "变动",
        "增长",
        "下降",
    ),
    "growth_analysis": (
        "driven by",
        "year over year",
        "year-over-year",
        "sequentially",
        "revenue by",
        "segment",
        "demand",
        "increased",
        "grew",
        "ramp",
        "增长",
        "需求",
        "分部",
    ),
    "financial_health": (
        "cash flow",
        "liquidity",
        "debt",
        "inventory",
        "receivable",
        "capital expenditure",
        "现金流",
        "流动性",
        "债务",
        "存货",
        "应收",
    ),
    "risk_analysis": (
        "risk",
        "uncertainty",
        "competition",
        "regulation",
        "restriction",
        "concentration",
        "风险",
        "不确定",
        "竞争",
        "监管",
    ),
    "business_analysis": (
        "segment",
        "revenue by",
        "business",
        "product",
        "service",
        "geographic",
        "customer",
        "market platform",
        "业务",
        "分部",
        "产品",
        "地区",
        "客户",
    ),
}

_RISK_LANGUAGE = (
    "risk",
    "uncertainty",
    "restriction",
    "export control",
    "regulation",
    "could negatively",
    "material adverse",
    "风险",
    "不确定",
    "限制",
    "监管",
    "负面影响",
)


class EvidenceRetriever:
    """Small deterministic lexical retriever over already verified filing chunks."""

    def retrieve(
        self,
        chunks: tuple[JsonObject, ...],
        *,
        question: str,
        intent: ResearchIntent,
        limit: int = 18,
    ) -> tuple[JsonObject, ...]:
        query_terms = _terms(question) | _terms(" ".join(intent.search_terms))
        ranked: list[tuple[float, JsonObject]] = []
        for chunk in chunks:
            text = str(chunk.get("text", ""))
            section = str(chunk.get("section", ""))
            if section == "Risk factors" and intent.skill != "risk_analysis":
                continue
            terms = _terms(section + " " + text)
            overlap = len(query_terms & terms)
            if overlap == 0 and section not in intent.preferred_sections:
                continue
            score = float(overlap * 3)
            lowered_text = text.casefold()
            signal_hits = sum(
                1
                for marker in _RETRIEVAL_SIGNALS[intent.skill]
                if marker.casefold() in lowered_text
            )
            score += min(signal_hits, 4) * 2.0
            if section in intent.preferred_sections:
                score += 5.0 - intent.preferred_sections.index(section)
            if section == "Filing narrative":
                score -= 1.0
            if intent.skill != "risk_analysis" and any(
                marker.casefold() in lowered_text for marker in _RISK_LANGUAGE
            ):
                score -= 4.0
            if signal_hits == 0 and overlap <= 1:
                score -= 3.0
            if text.count(".") + text.count("。") >= 2:
                score += 0.5
            ranked.append((score, chunk))
        ranked.sort(
            key=lambda item: (
                -item[0],
                int(item[1].get("locator", {}).get("page_start", 1)),
                str(item[1].get("chunk_id", "")),
            )
        )
        selected: list[JsonObject] = []
        section_counts: dict[str, int] = {}
        page_counts: dict[int, int] = {}
        window_counts: dict[int, int] = {}
        for _, chunk in ranked:
            section = str(chunk.get("section", "Filing narrative"))
            locator = chunk.get("locator", {})
            page = int(locator.get("page_start", 1))
            source_uri = str(chunk.get("source_uri", "")).casefold()
            is_pdf = source_uri.split("?", 1)[0].endswith(".pdf")
            char_start = locator.get("char_start")
            window = int(char_start or 0) // 6000
            if section_counts.get(section, 0) >= 5:
                continue
            if is_pdf and page_counts.get(page, 0) >= 2:
                continue
            if not is_pdf and window_counts.get(window, 0) >= 3:
                continue
            selected.append(chunk)
            section_counts[section] = section_counts.get(section, 0) + 1
            if is_pdf:
                page_counts[page] = page_counts.get(page, 0) + 1
            else:
                window_counts[window] = window_counts.get(window, 0) + 1
            if len(selected) >= limit:
                break
        if len(selected) < min(2, limit):
            seen = {str(chunk["chunk_id"]) for chunk in selected}
            for chunk in chunks:
                if str(chunk["chunk_id"]) in seen:
                    continue
                if (
                    str(chunk.get("section", "")) == "Risk factors"
                    and intent.skill != "risk_analysis"
                ):
                    continue
                selected.append(chunk)
                if len(selected) >= min(2, limit):
                    break
        return tuple(selected)

    def counter_candidates(
        self,
        chunks: tuple[JsonObject, ...],
        selected: tuple[JsonObject, ...],
        *,
        limit: int = 4,
    ) -> tuple[JsonObject, ...]:
        selected_ids = {str(item["chunk_id"]) for item in selected}
        risk_terms = _terms(
            "risk uncertainty decline competition regulation 风险 不确定 下降 竞争 监管"
        )
        ranked = []
        for chunk in chunks:
            if str(chunk["chunk_id"]) in selected_ids:
                continue
            score = len(
                risk_terms
                & _terms(str(chunk.get("section", "")) + " " + str(chunk.get("text", "")))
            )
            if str(chunk.get("section")) == "Risk factors":
                score += 5
            if score:
                ranked.append((score, chunk))
        ranked.sort(key=lambda item: -item[0])
        return tuple(chunk for _, chunk in ranked[:limit])


def follow_up_templates(skill: ResearchSkill) -> list[str]:
    mapping: dict[ResearchSkill, list[str]] = {
        "company_overview": [
            "最近业绩变化的主要原因是什么？",
            "增长主要来自哪些业务？",
            "当前最值得关注的三个风险是什么？",
            "管理层对下一阶段增长怎么看？",
            "现金流和利润质量如何？",
        ],
        "earnings_change": [
            "哪些业务贡献了最大的业绩变化？",
            "毛利率变化由什么驱动？",
            "费用变化是否可持续？",
            "现金流是否支持利润变化？",
            "管理层如何解释本期变化？",
        ],
        "growth_analysis": [
            "增长最依赖哪个业务或客户群？",
            "增长是否伴随毛利率改善？",
            "增长需要多少资本开支？",
            "主要增长风险是什么？",
            "管理层对增长持续性怎么判断？",
        ],
        "financial_health": [
            "现金流为何与利润存在差异？",
            "应收和存货变化是否异常？",
            "债务与流动性压力如何？",
            "资本开支是否过于激进？",
            "下一期最值得监控哪些指标？",
        ],
        "risk_analysis": [
            "哪个风险最可能影响未来业绩？",
            "客户集中度风险如何？",
            "供应链或监管风险有什么证据？",
            "管理层采取了哪些缓释措施？",
            "哪些风险目前证据仍不足？",
        ],
        "business_analysis": [
            "哪个业务分部增长最快？",
            "业务组合变化如何影响利润率？",
            "地区结构发生了什么变化？",
            "主要客户或市场集中度如何？",
            "管理层未来重点投入哪些业务？",
        ],
    }
    return mapping[skill]
