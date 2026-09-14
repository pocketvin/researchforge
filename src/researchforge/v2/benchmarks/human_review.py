# ruff: noqa: E501,RUF001
"""Private, choice-only human acceptance presentation for V2 held-out suites.

The product/benchmark runners do the research and automatic checks. This module only normalizes
finished reports into a blind, implementation-neutral card and records one human choice per case.
No hidden reference answer, evidence label, reviewer rationale or manual number audit is required.
"""

from __future__ import annotations

import hashlib
import html
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from researchforge.v2.benchmarks.heldout import (
    HeldOutHumanJudgment,
    HeldOutRuntimeCase,
    HeldOutSuiteSeal,
    validate_human_judgments,
)


class ReviewContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CandidateResultRef(ReviewContract):
    case_id: str = Field(min_length=1)
    candidate_key: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    result_path: str = Field(min_length=1)


class BlindCandidate(ReviewContract):
    run_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=240)
    direct_answer: str | None = None
    executive_summary: str = Field(min_length=1, max_length=12000)
    findings: list[str] = Field(max_length=24)
    sections: list[str] = Field(max_length=16)
    limitations: list[str] = Field(max_length=24)


class BlindReviewCase(ReviewContract):
    case_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    review_mode: Literal["pairwise_preference", "meets_standard"]
    candidate_a: BlindCandidate | None = None
    candidate_b: BlindCandidate | None = None
    evaluated_candidate: BlindCandidate | None = None

    @model_validator(mode="after")
    def shape_matches_mode(self) -> BlindReviewCase:
        if self.review_mode == "pairwise_preference":
            if self.candidate_a is None or self.candidate_b is None:
                raise ValueError("pairwise review card requires A and B candidates")
            if self.evaluated_candidate is not None:
                raise ValueError("pairwise review card cannot expose a threshold candidate")
            return self
        if self.evaluated_candidate is None:
            raise ValueError("meets-standard review card requires one evaluated candidate")
        if self.candidate_a is not None or self.candidate_b is not None:
            raise ValueError("meets-standard review card cannot expose pairwise candidates")
        return self


class BlindReviewPackage(ReviewContract):
    schema_version: Literal["2.0.0"] = "2.0.0"
    suite_id: str = Field(min_length=1)
    bundle_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_mode: Literal["pairwise_preference", "meets_standard"]
    reviewer_id: str = Field(default="owner", min_length=1)
    generated_at: datetime
    cases: list[BlindReviewCase] = Field(min_length=1)


class HumanJudgmentFile(ReviewContract):
    schema_version: Literal["2.0.0"] = "2.0.0"
    suite_id: str = Field(min_length=1)
    bundle_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_mode: Literal["pairwise_preference", "meets_standard"]
    judgments: list[HeldOutHumanJudgment] = Field(min_length=1)


class HumanAcceptanceSummary(ReviewContract):
    schema_version: Literal["2.0.0"] = "2.0.0"
    suite_id: str
    bundle_hash: str
    review_mode: Literal["pairwise_preference", "meets_standard"]
    total_cases: int
    verdict_counts: dict[str, int]
    candidate_preference_counts: dict[str, int] | None = None
    decisive_pairwise_cases: int | None = None
    meets_standard_cases: int | None = None
    cannot_judge_cases: int
    note: str


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"candidate result must be a JSON object: {path}")
    return value


def _string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def normalize_result(payload: dict[str, Any], *, question: str, run_id: str) -> BlindCandidate:
    """Normalize V1/V2 result shapes so presentation does not reveal implementation identity."""
    report = payload.get("report")
    if isinstance(report, dict):
        direct_answer = _string(report.get("direct_answer")) or None
        if direct_answer == "not_applicable":
            direct_answer = None
        findings = []
        for item in report.get("findings", []):
            if not isinstance(item, dict):
                continue
            title = _string(item.get("title"))
            text = _string(item.get("text"))
            findings.append(f"{title}: {text}" if title else text)
        sections = []
        for item in report.get("sections", []):
            if not isinstance(item, dict):
                continue
            title = _string(item.get("title"))
            text = _string(item.get("text"))
            sections.append(f"{title}\n{text}" if title else text)
        return BlindCandidate(
            run_id=run_id,
            title="Research Result",
            direct_answer=direct_answer,
            executive_summary=_string(report.get("executive_summary")),
            findings=[item for item in findings if item],
            sections=[item for item in sections if item],
            limitations=[_string(item) for item in report.get("limitations", []) if _string(item)],
        )

    # Preserved V1.x research-result shape.
    findings = [
        _string(item.get("text"))
        for item in payload.get("claims", [])
        if isinstance(item, dict) and _string(item.get("text"))
    ]
    sections = []
    for item in payload.get("analysis_sections", []) or []:
        if not isinstance(item, dict):
            continue
        title = _string(item.get("title"))
        text = _string(item.get("text"))
        sections.append(f"{title}\n{text}" if title else text)
    overall = payload.get("overall_judgment")
    direct_answer = None
    if isinstance(overall, dict):
        direct_answer = _string(overall.get("label")) or None
    return BlindCandidate(
        run_id=run_id,
        title="Research Result",
        direct_answer=direct_answer,
        executive_summary=_string(payload.get("executive_summary")) or question,
        findings=findings,
        sections=[item for item in sections if item],
        limitations=[_string(item) for item in payload.get("limitations", []) if _string(item)],
    )


def _pairwise_order(
    bundle_hash: str, case_id: str, refs: list[CandidateResultRef]
) -> list[CandidateResultRef]:
    ordered = sorted(refs, key=lambda item: (item.candidate_key, item.run_id))
    if len(ordered) != 2:
        raise ValueError("pairwise review requires exactly two candidate results per case")
    digest = hashlib.sha256(f"{bundle_hash}:{case_id}".encode()).digest()
    return ordered if digest[0] % 2 == 0 else list(reversed(ordered))


def build_review_package(
    seal: HeldOutSuiteSeal,
    runtime_cases: list[HeldOutRuntimeCase],
    result_refs: list[CandidateResultRef],
    *,
    reviewer_id: str = "owner",
    generated_at: datetime,
) -> BlindReviewPackage:
    runtimes = {case.case_id: case for case in runtime_cases}
    if {_opaque_case(case_id) for case_id in runtimes} != set(seal.opaque_case_hashes):
        raise ValueError("review package runtime cases do not match held-out seal")
    grouped: dict[str, list[CandidateResultRef]] = defaultdict(list)
    for ref in result_refs:
        if ref.case_id not in runtimes:
            raise ValueError("candidate result references a case outside the held-out seal")
        grouped[ref.case_id].append(ref)
    if set(grouped) != set(runtimes):
        raise ValueError("candidate results must cover every held-out case exactly")

    cards: list[BlindReviewCase] = []
    for case_id in sorted(runtimes):
        runtime = runtimes[case_id]
        refs = grouped[case_id]
        if seal.review_mode == "pairwise_preference":
            refs = _pairwise_order(seal.bundle_hash, case_id, refs)
            candidates = [
                normalize_result(
                    _read_json(Path(ref.result_path).resolve()),
                    question=runtime.research_question,
                    run_id=ref.run_id,
                )
                for ref in refs
            ]
            cards.append(
                BlindReviewCase(
                    case_id=case_id,
                    question=runtime.research_question,
                    review_mode=seal.review_mode,
                    candidate_a=candidates[0],
                    candidate_b=candidates[1],
                )
            )
            continue
        if len(refs) != 1:
            raise ValueError("meets-standard review requires exactly one candidate result per case")
        candidate = normalize_result(
            _read_json(Path(refs[0].result_path).resolve()),
            question=runtime.research_question,
            run_id=refs[0].run_id,
        )
        cards.append(
            BlindReviewCase(
                case_id=case_id,
                question=runtime.research_question,
                review_mode=seal.review_mode,
                evaluated_candidate=candidate,
            )
        )
    return BlindReviewPackage(
        suite_id=seal.suite_id,
        bundle_hash=seal.bundle_hash,
        review_mode=seal.review_mode,
        reviewer_id=reviewer_id,
        generated_at=generated_at,
        cases=cards,
    )


def _opaque_case(case_id: str) -> str:
    return hashlib.sha256(("researchforge-heldout-v2:" + case_id).encode()).hexdigest()


def summarize_human_acceptance(
    seal: HeldOutSuiteSeal,
    judgment_file: HumanJudgmentFile,
    result_refs: list[CandidateResultRef],
) -> HumanAcceptanceSummary:
    if judgment_file.suite_id != seal.suite_id or judgment_file.bundle_hash != seal.bundle_hash:
        raise ValueError("human judgment file does not belong to the frozen held-out seal")
    if judgment_file.review_mode != seal.review_mode:
        raise ValueError("human judgment review mode does not match the frozen held-out seal")
    validate_human_judgments(seal, judgment_file.judgments)
    verdict_counts: Counter[str] = Counter()
    for item in judgment_file.judgments:
        verdict = item.pairwise_verdict or item.threshold_verdict
        if verdict is not None:
            verdict_counts[verdict] += 1

    if seal.review_mode == "meets_standard":
        return HumanAcceptanceSummary(
            suite_id=seal.suite_id,
            bundle_hash=seal.bundle_hash,
            review_mode=seal.review_mode,
            total_cases=seal.case_count,
            verdict_counts=dict(sorted(verdict_counts.items())),
            meets_standard_cases=verdict_counts["meets_standard"],
            cannot_judge_cases=verdict_counts["cannot_judge"],
            note="Choice-only owner acceptance; automatic provenance/citation/trajectory checks are separate.",
        )

    run_to_candidate: dict[str, str] = {}
    for ref in result_refs:
        prior = run_to_candidate.get(ref.run_id)
        if prior is not None and prior != ref.candidate_key:
            raise ValueError("one run ID cannot represent two pairwise candidate identities")
        run_to_candidate[ref.run_id] = ref.candidate_key
    preferences: Counter[str] = Counter()
    decisive = 0
    for item in judgment_file.judgments:
        if item.pairwise_verdict == "a_better":
            decisive += 1
            preferences[run_to_candidate[item.candidate_a_run_id or ""]] += 1
        elif item.pairwise_verdict == "b_better":
            decisive += 1
            preferences[run_to_candidate[item.candidate_b_run_id or ""]] += 1
    return HumanAcceptanceSummary(
        suite_id=seal.suite_id,
        bundle_hash=seal.bundle_hash,
        review_mode=seal.review_mode,
        total_cases=seal.case_count,
        verdict_counts=dict(sorted(verdict_counts.items())),
        candidate_preference_counts=dict(sorted(preferences.items())),
        decisive_pairwise_cases=decisive,
        cannot_judge_cases=0,
        note="Blind pairwise owner preference; no human-authored reference answer or evidence labeling.",
    )


def render_review_html(package: BlindReviewPackage) -> str:
    """Return a self-contained offline page. The last human click downloads the judgment JSON."""
    payload = json.dumps(package.model_dump(mode="json"), ensure_ascii=False).replace("</", "<\\/")
    title = html.escape(package.suite_id)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>ResearchForge Blind Acceptance · {title}</title>
<style>
:root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:#f4f1ea; color:#20211f; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; }}
main {{ width:min(1480px, calc(100% - 32px)); margin:28px auto 80px; }}
header {{ display:flex; justify-content:space-between; gap:24px; align-items:flex-end; margin-bottom:22px; }}
h1 {{ margin:0; font-size:24px; }}
.muted {{ color:#6e7069; font-size:13px; }}
.question {{ background:#fffdf8; border:1px solid #ddd8cb; border-radius:16px; padding:20px 22px; margin-bottom:16px; font-size:18px; line-height:1.65; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
.card {{ background:#fff; border:1px solid #d8d4ca; border-radius:16px; min-width:0; overflow:hidden; }}
.card > h2 {{ margin:0; padding:16px 20px; background:#f8f7f2; border-bottom:1px solid #e5e2da; font-size:16px; }}
.content {{ padding:18px 20px 22px; }}
.content h3 {{ margin:20px 0 8px; font-size:13px; text-transform:uppercase; letter-spacing:.05em; color:#77776f; }}
.content h3:first-child {{ margin-top:0; }}
.content p, .content li {{ line-height:1.65; white-space:pre-wrap; }}
.content ul {{ margin:8px 0; padding-left:20px; }}
.direct {{ display:inline-block; padding:5px 9px; border-radius:999px; background:#ecebe5; font-size:12px; margin-bottom:8px; }}
.actions {{ position:sticky; bottom:14px; margin-top:18px; background:rgba(244,241,234,.95); backdrop-filter:blur(10px); border:1px solid #d8d2c4; border-radius:16px; padding:12px; display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }}
button {{ border:1px solid #aaa79e; border-radius:12px; background:#fff; padding:13px 12px; font:inherit; cursor:pointer; }}
button:hover {{ background:#f2f0e9; }}
button.primary {{ background:#20211f; color:#fff; border-color:#20211f; }}
.progress {{ font-variant-numeric:tabular-nums; }}
.done {{ text-align:center; background:#fff; border:1px solid #d8d4ca; border-radius:18px; padding:48px 24px; }}
@media (max-width:900px) {{ .grid {{ grid-template-columns:1fr; }} .actions {{ grid-template-columns:1fr 1fr; }} header {{ align-items:flex-start; flex-direction:column; }} }}
</style>
</head>
<body><main id="app"></main>
<script>
const PACK = {payload};
let index = 0;
const judgments = [];
const app = document.getElementById('app');
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
function candidateHtml(label, item) {{
  const findings = item.findings.length ? `<h3>关键发现</h3><ul>${{item.findings.map(x=>`<li>${{esc(x)}}</li>`).join('')}}</ul>` : '';
  const sections = item.sections.length ? `<h3>深入分析</h3>${{item.sections.map(x=>`<p>${{esc(x)}}</p>`).join('')}}` : '';
  const limitations = item.limitations.length ? `<h3>限制</h3><ul>${{item.limitations.map(x=>`<li>${{esc(x)}}</li>`).join('')}}</ul>` : '';
  const direct = item.direct_answer ? `<span class="direct">${{esc(item.direct_answer)}}</span>` : '';
  return `<article class="card"><h2>${{label}}</h2><div class="content"><h3>核心结论</h3>${{direct}}<p>${{esc(item.executive_summary)}}</p>${{findings}}${{sections}}${{limitations}}</div></article>`;
}}
function download() {{
  const body = {{schema_version:'2.0.0',suite_id:PACK.suite_id,bundle_hash:PACK.bundle_hash,review_mode:PACK.review_mode,judgments}};
  const blob = new Blob([JSON.stringify(body,null,2)+'\\n'], {{type:'application/json'}});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=`researchforge-heldout-judgments-${{PACK.suite_id}}.json`; a.click(); URL.revokeObjectURL(a.href);
}}
function choose(verdict) {{
  const c=PACK.cases[index]; const now=new Date().toISOString();
  if (PACK.review_mode==='pairwise_preference') judgments.push({{schema_version:'2.0.0',case_id:c.case_id,review_mode:PACK.review_mode,reviewer_id:PACK.reviewer_id,reviewed_at:now,candidate_a_run_id:c.candidate_a.run_id,candidate_b_run_id:c.candidate_b.run_id,evaluated_run_id:null,pairwise_verdict:verdict,threshold_verdict:null}});
  else judgments.push({{schema_version:'2.0.0',case_id:c.case_id,review_mode:PACK.review_mode,reviewer_id:PACK.reviewer_id,reviewed_at:now,candidate_a_run_id:null,candidate_b_run_id:null,evaluated_run_id:c.evaluated_candidate.run_id,pairwise_verdict:null,threshold_verdict:verdict}});
  index += 1;
  if (index === PACK.cases.length) {{ download(); render(); }} else render();
}}
function render() {{
  if (index >= PACK.cases.length) {{ app.innerHTML=`<section class="done"><h1>完成</h1><p>已自动下载判断文件。你不需要再写任何说明。</p><button class="primary" onclick="download()">再次下载</button></section>`; return; }}
  const c=PACK.cases[index];
  const header=`<header><div><h1>ResearchForge 盲评</h1><div class="muted">只判断结果本身，模型和版本身份已隐藏。</div></div><div class="progress">${{index+1}} / ${{PACK.cases.length}}</div></header>`;
  let body=''; let actions='';
  if (PACK.review_mode==='pairwise_preference') {{
    body=`<div class="grid">${{candidateHtml('A',c.candidate_a)}}${{candidateHtml('B',c.candidate_b)}}</div>`;
    actions=`<div class="actions"><button class="primary" onclick="choose('a_better')">A 更好</button><button class="primary" onclick="choose('b_better')">B 更好</button><button onclick="choose('tie')">差不多</button><button onclick="choose('neither')">都不行</button></div>`;
  }} else {{
    body=candidateHtml('研究结果',c.evaluated_candidate);
    actions=`<div class="actions" style="grid-template-columns:repeat(3,1fr)"><button class="primary" onclick="choose('meets_standard')">达标</button><button onclick="choose('does_not_meet_standard')">不达标</button><button onclick="choose('cannot_judge')">无法判断</button></div>`;
  }}
  app.innerHTML=header+`<section class="question"><strong>问题</strong><br>${{esc(c.question)}}</section>`+body+actions;
}}
render();
</script></body></html>"""
