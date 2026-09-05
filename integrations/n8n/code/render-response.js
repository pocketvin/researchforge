// Render backend-owned artifacts for the native form without creating research content.
const incoming = $input.first().json;
// `surface` is internal routing metadata and is never part of the public webhook contract.
const transport = { ...incoming };
delete transport.surface;
const escape = (value) => String(value ?? '')
  .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;').replaceAll("'", '&#39;');
const safeUrl = (value) => /^https?:\/\//.test(String(value ?? '')) ? escape(value) : '#';
const list = (items) => items.length > 0 ? `<ul>${items.map((item) => `<li>${item}</li>`).join('')}</ul>` : '<p>无可呈现项目。</p>';

let content;
if (transport.status !== 'succeeded') {
  content = `
    <header><p class="eyebrow">BOUNDED FAILURE</p><h1>研究未生成</h1></header>
    <section class="failure">
    <p><strong>${escape(transport.code)}</strong> — ${escape(transport.message)}</p>
    <p>ResearchForge 在输入、数据、状态或产物无法确认时会停止，不会补写结论或数字。</p>
    ${transport.links?.status ? `<p><a href="${safeUrl(transport.links.status)}">检查后端运行状态</a></p>` : ''}
    </section>`;
} else {
  const facts = transport.financial_facts.map((fact) => `<strong>${escape(fact.metric_code)}</strong>: ${escape(fact.value ?? 'ABSTAINED')} ${escape(fact.currency ?? fact.measurement_unit ?? '')} · P${escape(fact.source_locator?.page ?? '—')}`);
  const calculations = transport.calculations.map((calculation) => `<strong>${escape(calculation.formula_code)}</strong>: ${escape(calculation.value ?? '不适用')} · ${escape(calculation.explanation)}`);
  const findings = transport.findings.map((finding) => escape(finding.text));
  const plan = (transport.research_plan || []).map((step) => `<strong>${escape(step.description)}</strong> · ${escape(step.status)}`);
  const analysis = (transport.analysis_sections || []).map((section) => `<strong>${escape(section.title)}</strong><br>${escape(section.text)}`);
  const followUps = (transport.suggested_follow_ups || []).map(escape);
  const evidence = transport.supporting_evidence.map((chunk) => `<strong>${escape(chunk.section)} · P${escape(chunk.locator?.page_start ?? '—')}</strong><br>${escape(chunk.text)}<br><a href="${safeUrl(chunk.source_uri)}">打开官方披露</a>`);
  const counters = transport.counter_evidence.map((entry) => `<strong>${escape(entry.search?.result)}</strong>: ${escape(entry.search?.summary)}`);
  const monitoring = transport.monitoring.map((item) => `<strong>${escape(item.title)}</strong>: ${escape(item.rationale)} · 触发条件 ${escape(item.trigger)} · ${escape(item.next_review)}`);
  const isFallback = transport.synthesis_mode === 'evidence_summary_fallback';
  const fallbackNotice = isFallback
    ? `<section class="fallback"><strong>EVIDENCE SUMMARY FALLBACK · 未执行 AI 综合分析</strong><p>当前只展示已核验的证据与确定性财务事实，不把财报摘录包装成完整研究结论。</p></section>`
    : '';
  content = `
    <header><p class="eyebrow">SAME BACKEND · VERIFIED PIPELINE</p><h1>${isFallback ? 'ResearchForge 证据核验完成' : 'ResearchForge 研究完成'}</h1><span class="status ${isFallback ? 'fallback-status' : ''}">${isFallback ? 'EVIDENCE ONLY' : 'SUCCEEDED'}</span></header>
    ${fallbackNotice}
    <section class="conclusion"><h2>Executive Conclusion / 核心结论</h2><p>${escape(transport.conclusion)}</p></section>
    ${transport.research_intent && transport.overall_judgment ? `<section class="judgment"><h2>Research Intent / 研究意图</h2><p><strong>${escape(transport.research_intent.label)}</strong> · ${escape(transport.research_intent.skill)}</p><p>${escape(transport.overall_judgment.label)} — ${escape(transport.overall_judgment.rationale)}</p></section>` : ''}
    <details open><summary>Research Plan / 研究计划</summary>${list(plan)}</details>
    ${isFallback ? `<details open><summary>Evidence Inventory / 已核验证据</summary>${list(evidence)}</details>` : `<details open><summary>Key Findings / 关键发现</summary>${list(findings)}</details>`}
    ${!isFallback && analysis.length > 0 ? `<details open><summary>Deep Analysis / 深入分析</summary>${list(analysis)}</details>` : ''}
    <details><summary>Financial Facts / 财务事实</summary>${list(facts)}</details>
    <details><summary>Calculations / 确定性计算</summary>${list(calculations)}</details>
    <details><summary>Supporting Evidence / 支持证据</summary>${list(evidence)}</details>
    <details><summary>Counter Evidence & Limitations / 反证与限制</summary>${list([...counters, ...transport.limitations.map(escape)])}</details>
    <details><summary>下一份财报重点看什么</summary>${list(monitoring)}</details>
    ${followUps.length > 0 ? `<details open><summary>继续研究</summary>${list(followUps)}</details>` : ''}
    ${transport.evidence_coverage ? `<p class="coverage">Evidence coverage: ${escape(transport.evidence_coverage.selected_chunk_count)} selected / ${escape(transport.evidence_coverage.available_chunk_count)} available · sections ${escape((transport.evidence_coverage.sections || []).join(', '))}</p>` : ''}
    <nav><a href="${safeUrl(transport.links.result)}">完整 Research Result</a><a href="${safeUrl(transport.links.trace)}">完整 Research Trace</a></nav>
    <footer>${escape(transport.trust_boundary)}</footer>`;
}
const formPage = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ResearchForge 研究结果</title><style>
:root{font-family:Inter,system-ui,sans-serif;color:#dce4eb;background:#071015}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 75% -10%,#173d33 0,transparent 35%),#071015}main{max-width:920px;margin:auto;padding:44px 22px 70px}header{position:relative;margin-bottom:22px}.eyebrow{color:#43d6a3;font:11px ui-monospace,monospace;letter-spacing:.14em}h1{margin:8px 0;color:#fff;font-size:30px}.status{position:absolute;right:0;top:15px;padding:5px 9px;border:1px solid #2c8064;border-radius:99px;color:#72e7bd;font:10px ui-monospace,monospace}.conclusion,.judgment,details,.failure,.fallback{margin:12px 0;padding:18px;border:1px solid #23343e;border-radius:12px;background:#0d1921}.conclusion{border-left:3px solid #43d6a3}.judgment{border-left:3px solid #d4a85f}.judgment h2{margin:0 0 10px;color:#d4a85f;font-size:12px}.judgment p,.coverage{color:#9eb0b9;line-height:1.7}.conclusion h2{margin:0 0 10px;color:#8fa5b1;font-size:12px}.conclusion p{margin:0;color:#e3eaed;font:17px/1.85 Georgia,serif}summary{cursor:pointer;color:#c9d5da;font-weight:650}ul{margin:14px 0 0;padding-left:20px}li{margin:9px 0;color:#9eb0b9;line-height:1.65}a{color:#71d7b2}nav{display:flex;gap:12px;margin-top:18px}nav a{padding:10px 12px;border:1px solid #285846;border-radius:8px;text-decoration:none}footer{margin-top:20px;color:#657d88;font:10px/1.7 ui-monospace,monospace}.failure{border-color:#663b3b;color:#ffaaa4}.fallback{border-color:#725f36;color:#d8bc7c}.fallback p{color:#9f906d;line-height:1.7}.status.fallback-status{border-color:#725f36;color:#d8bc7c}@media(max-width:600px){main{padding:28px 14px}.status{position:static;display:inline-block}nav{flex-direction:column}}
</style></head><body><main>${content}</main></body></html>`;
return [{ json: { transport, formPage } }];
