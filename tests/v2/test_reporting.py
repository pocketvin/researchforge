"""Run-bound report contracts must prevent writer-created provenance."""

from __future__ import annotations

from researchforge.v2.reporting import (
    _public_prose,
    bound_report_schema,
    build_safe_dossier_report,
)


def context() -> dict:
    return {
        "request": {
            "company_query": "Synthetic Co",
            "research_question": "Can the filing support a categorical conclusion?",
        },
        "dossier": {
            "stop_reason": "evidence_exhausted",
            "direct_answer": "cannot_determine",
            "summary": (
                "The filing supports a 5.11% deterministic measure "
                "(calc_capex_ratio), but no filing-linked classification threshold exists."
            ),
            "evidence_ids": ["view_capex", "view_sales"],
            "remaining_uncertainties": [
                "No explicit filing threshold or peer benchmark is available."
            ],
            "why_stop": "Additional filing search cannot supply an external classification rule.",
        },
        "working": {
            "objectives": [
                {
                    "objective_id": "obj_category",
                    "question": "Can the filing support a categorical conclusion?",
                    "priority": "required",
                    "status": "limited",
                    "evidence_ids": ["view_capex", "calc_capex_ratio"],
                    "conclusion": (
                        "The filing supports calc_capex_ratio, but the categorical label "
                        "cannot be determined from the filing alone."
                    ),
                    "remaining_uncertainty": "No filing-linked classification threshold exists.",
                }
            ]
        },
        "evidence": [
            {"artifact_id": "view_capex", "text": "CAPEX is disclosed in the filing."},
            {"artifact_id": "view_sales", "text": "Revenue is disclosed in the filing."},
        ],
        "financial_facts": [
            {
                "fact_id": "fact_revenue",
                "metric_code": "revenue",
                "value": "100",
            }
        ],
        "calculations": [
            {
                "calculation_id": "calc_capex_ratio",
                "formula_code": "ratio_percent",
                "measurement_unit": "PERCENT",
                "value": "5.11",
            }
        ],
    }


def test_public_prose_localizes_internal_status_words_in_chinese_copy() -> None:
    text = "本目标只能标为 limited，并以 evidence_exhausted 提交。"
    assert _public_prose(text) == "本目标只能标为 有边界结论，并以 当前财报已无更多有效信息 提交。"


def test_public_prose_removes_punctuation_only_internal_id_shells() -> None:
    assert (
        _public_prose("The comparison is supported by filing excerpts (view_one, view_two).")
        == "The comparison is supported by filing excerpts."
    )
    assert _public_prose("现金流数据见（view_one、view_two）。") == "现金流数据见。"
    assert _public_prose("净利润为100万元（上年同期90万元，view_one）。") == (
        "净利润为100万元（上年同期90万元）。"
    )


def test_bound_report_schema_only_accepts_run_owned_source_ids_and_direct_answer() -> None:
    schema = bound_report_schema(context())
    finding = schema["$defs"]["Finding"]["properties"]
    assert finding["evidence_ids"]["items"]["enum"] == ["view_capex", "view_sales"]
    assert finding["fact_ids"]["items"]["enum"] == ["fact_revenue"]
    assert finding["calculation_ids"]["items"]["enum"] == ["calc_capex_ratio"]
    numeric = schema["$defs"]["NumericAssertion"]["properties"]["source_id"]["enum"]
    assert numeric == ["calc_capex_ratio", "fact_revenue"]
    assert schema["properties"]["direct_answer"] == {
        "type": "string",
        "const": "cannot_determine",
    }


def test_safe_dossier_report_reuses_only_existing_research_state_and_lineage() -> None:
    report = build_safe_dossier_report(context())
    assert report.direct_answer == "cannot_determine"
    assert report.executive_summary == (
        "The cited filing evidence supports only a bounded answer: the missing inputs or "
        "comparison basis do not support a stronger conclusion. The verified facts and "
        "evidence boundaries are stated below."
    )
    assert "left unresolved" not in report.executive_summary
    assert "safe report" not in report.executive_summary.casefold()
    assert "calc_capex_ratio" not in report.executive_summary
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.kind == "limitation"
    assert finding.title.startswith("Evidence limitation:")
    assert finding.evidence_ids == ["view_capex"]
    assert finding.calculation_ids == ["calc_capex_ratio"]
    assert finding.fact_ids == []
    assert finding.numeric_assertions == []
    assert "cannot be determined reliably" in finding.text
    assert "calc_capex_ratio" not in finding.text
    assert report.sections[0].title == "Evidence boundary"
    assert report.sections[0].evidence_ids == ["view_capex", "view_sales"]
    assert "calc_capex_ratio" not in report.sections[0].text
    serialized = report.model_dump_json()
    assert "made_up" not in serialized
    assert "fact_revenue" not in serialized


def test_safe_report_deduplicates_limited_summary_and_humanizes_snake_case() -> None:
    payload = context()
    original = payload["working"]["objectives"][0]
    payload["working"]["objectives"] = [
        original,
        {
            **original,
            "objective_id": "obj_second_limit",
            "question": "Does the filing support an industry-relative classification?",
            "remaining_uncertainty": "No peer_benchmark was established in the cited evidence.",
        },
    ]
    report = build_safe_dossier_report(payload)
    assert report.executive_summary == (
        "The cited filing evidence supports only a bounded answer: the missing inputs or "
        "comparison basis do not support a stronger conclusion. The verified facts and "
        "evidence boundaries are stated below."
    )
    assert "This part cannot be determined reliably" not in report.executive_summary
    assert "peer_benchmark" not in report.model_dump_json()
    assert any("peer benchmark" in item for item in report.limitations)


def test_safe_report_does_not_copy_wrong_language_limited_state() -> None:
    payload = context()
    payload["working"]["objectives"][0]["conclusion"] = (
        "当前已引用证据没有建立行业相对分类所需的可比阈值，因此不能作更强结论。"
    )
    payload["working"]["objectives"][0]["remaining_uncertainty"] = "当前证据没有建立同业比较基准。"
    report = build_safe_dossier_report(payload)
    public = "\n".join(
        [
            report.title,
            report.executive_summary,
            *[
                finding.title + "\n" + finding.text + "\n" + finding.uncertainty
                for finding in report.findings
            ],
            *report.limitations,
        ]
    )
    assert "当前" not in public
    assert "证据" not in public
    assert "the cited filing evidence does not establish" in report.findings[0].text
    assert "The cited evidence does not establish" in report.findings[0].uncertainty


def test_safe_report_softens_global_absence_and_analyst_superlatives() -> None:
    payload = context()
    payload["dossier"]["direct_answer"] = "not_applicable"
    payload["working"]["objectives"][0].update(
        {
            "status": "answered",
            "conclusion": (
                "Net interest income is the dominant revenue line and its increase is the "
                "largest single positive operating swing. The filing does not state a primary "
                "driver, and noninterest income was led by loan-sale gains."
            ),
            "remaining_uncertainty": (
                "The filing contains no formal primary-driver sentence in the reviewed material."
            ),
        }
    )
    report = build_safe_dossier_report(payload)
    public = report.model_dump_json().casefold()
    assert "the filing does not state" not in public
    assert "the filing contains no" not in public
    assert "dominant revenue line" not in public
    assert "largest single positive operating swing" not in public
    assert " led by " not in public
    assert "major revenue line" in public
    assert "material positive operating swing" in public
    assert "the cited evidence does not establish" in public
    assert "where the filing does not explicitly" not in public
    assert "where the cited evidence does not establish explicit attribution" in public


def test_safe_report_softens_indirect_filing_wide_negative_clause() -> None:
    payload = context()
    payload["dossier"]["direct_answer"] = "not_applicable"
    payload["working"]["objectives"][0].update(
        {
            "status": "answered",
            "conclusion": "Management provides an explicit year-over-year bridge.",
            "remaining_uncertainty": (
                "The filing notes the effect but does not quantify it as a separate bridge item."
            ),
        }
    )
    report = build_safe_dossier_report(payload)
    public = report.model_dump_json().casefold()
    assert "the filing notes" not in public
    assert (
        "the cited evidence notes the effect but does not establish it as a separate bridge item"
    ) in public


def test_cash_flow_safe_report_neutralizes_unbenchmarked_degree_words() -> None:
    payload = context()
    payload["request"]["research_question"] = "分析现金流是否健康"
    payload["dossier"].update(
        {
            "direct_answer": "mixed",
            "stop_reason": "sufficient_evidence",
            "summary": "经营强、整体承压。",
            "remaining_uncertainties": ["投资流出构成仍需细分。"],
        }
    )
    base = payload["working"]["objectives"][0]
    payload["working"]["objectives"] = [
        {
            **base,
            "objective_id": "obj_ocf",
            "question": "经营现金创造如何？",
            "status": "answered",
            "conclusion": (
                "经营现金创造与利润现金转换在本期均较强，经营现金流/净利润比值为1.96，"
                "其中相当部分来自经营性应收项目的回收。"
            ),
            "remaining_uncertainty": "应收回收的精确贡献比例未拆分。",
        },
        {
            **base,
            "objective_id": "obj_liquidity",
            "question": "净现金与流动性如何？",
            "status": "answered",
            "conclusion": (
                "现金及现金等价物净增加额为-110.996亿元，期末现金余额与未使用授信"
                "仍构成较厚的流动性缓冲。"
            ),
            "remaining_uncertainty": "受限资金影响未量化。",
        },
        {
            **base,
            "objective_id": "obj_investing",
            "question": "投资与筹资现金流如何？",
            "status": "answered",
            "conclusion": (
                "投资与筹资活动均形成显著净流出，是现金净流出的主要来源；短期偿付安排规模可观。"
            ),
            "remaining_uncertainty": "投资流出性质仍需细分。",
        },
    ]
    report = build_safe_dossier_report(payload)
    public = report.model_dump_json(ensure_ascii=False)
    assert report.direct_answer == "mixed"
    assert "1.96" in public
    assert "-110.996" in public
    for phrase in ("较强", "相当部分", "较厚", "主要来源", "可观", "显著净流出"):
        assert phrase not in public
    assert "经营活动现金流同比增长" in public
    assert "已披露的流动性来源" in public
    assert "现金变动的负向贡献项" in public
    assert "其中其中" not in public
    assert "主要是" not in public
    assert "明显支撑" not in public
    assert "重要正向来源" not in public
    assert "利润现金转换大于1" not in public
    assert "mixed" in report.direct_answer
    assert "混合判断" in report.executive_summary


def test_safe_report_answered_objectives_ignore_wrong_language_dossier_limitations() -> None:
    payload = context()
    payload["dossier"]["direct_answer"] = "not_applicable"
    payload["dossier"]["remaining_uncertainties"] = [
        "财报未量化两个驱动因素的各自金额贡献。",
        "市场级运营表的列定义未完全确认。",
    ]
    payload["working"]["objectives"][0].update(
        {
            "status": "answered",
            "conclusion": "The cited evidence supports the requested filing-grounded conclusion.",
            "remaining_uncertainty": (
                "The filing excerpt does not provide a full reconciliation of every line-item change."
            ),
        }
    )
    report = build_safe_dossier_report(payload)
    public = report.model_dump_json()
    assert "财报" not in public
    assert "未量化" not in public
    assert "The filing excerpt does not provide" not in public
    assert "the cited evidence does not establish" in public.casefold()
    assert report.limitations == [
        "the cited evidence does not establish a full reconciliation of every line-item change."
    ]
