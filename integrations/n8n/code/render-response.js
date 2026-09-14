// Render only persisted V2 artifacts. This node does not create research content.
const incoming = $input.first().json;
const transport = { ...incoming };
delete transport.surface;
const escape = (value) => String(value ?? '')
  .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;').replaceAll("'", '&#39;');
const safeUrl = (value) => /^https?:\/\//.test(String(value ?? '')) ? escape(value) : '#';
const list = (items) => items.length > 0 ? `<ul>${items.map((item) => `<li>${item}</li>`).join('')}</ul>` : '<p>无可呈现项目。</p>';
let content;
if (transport.status !== 'succeeded') {
  content = `<header><p class="eyebrow">BOUNDED FAILURE</p><h1>研究未生成</h1></header>
    <section class="failure"><p><strong>${escape(transport.code)}</strong> — ${escape(transport.message)}</p>
    <p>ResearchForge 在输入、来源、状态或产物无法确认时停止，不由 n8n 补写结论。</p>
    ${transport.links?.status ? `<p><a href="${safeUrl(transport.links.status)}">检查后端运行状态</a></p>` : ''}</section>`;
} else {
  const findings = transport.findings.map((finding) => `<strong>${escape(finding.title)}</strong><br>${escape(finding.text)}`);
  const analysis = transport.analysis_sections.map((section) => `<strong>${escape(section.title)}</strong><br>${escape(section.text)}`);
  const facts = transport.financial_facts.map((fact) => `<strong>${escape(fact.metric_code)}</strong>: ${escape(fact.value)} ${escape(fact.currency ?? '')}`);
  const calculations = transport.calculations.map((item) => `<strong>${escape(item.formula_code)}</strong>: ${escape(item.value ?? '不适用')}`);
  const hypotheses = transport.hypotheses.map((item) => `<strong>${escape(item.status)}</strong>: ${escape(item.statement)}`);
  const followUps = transport.follow_up_questions.map(escape);
  const evidence = transport.supporting_evidence.slice(0, 20).map((item) => `${escape(item.text ?? item.title ?? item.artifact_id)}`);
  content = `<header><p class="eyebrow">SAME V2 BACKEND · VERIFIED PIPELINE</p><h1>ResearchForge 研究完成</h1><span class="status">SUCCEEDED</span></header>
    <section class="conclusion"><h2>研究结论</h2><p>${escape(transport.conclusion)}</p>${transport.direct_answer && transport.direct_answer !== 'not_applicable' ? `<small>直接答案：${escape(transport.direct_answer)}</small>` : ''}</section>
    <details open><summary>关键发现</summary>${list(findings)}</details>
    <details open><summary>深入分析</summary>${list(analysis)}</details>
    <details><summary>财务事实</summary>${list(facts)}</details>
    <details><summary>确定性计算</summary>${list(calculations)}</details>
    <details><summary>已观察证据</summary>${list(evidence)}</details>
    <details><summary>假设与反向检验</summary>${list(hypotheses)}</details>
    <details><summary>限制与证据边界</summary>${list([...(transport.limitations || []), ...(transport.extraction_gaps || [])].map(escape))}</details>
    ${followUps.length ? `<details open><summary>进一步研究</summary>${list(followUps)}</details>` : ''}
    <nav><a href="${safeUrl(transport.links.result)}">完整 V2 Result</a><a href="${safeUrl(transport.links.trace)}">完整 V2 Trace</a><a href="${safeUrl(transport.links.workspace)}">完整 V2 Workspace</a></nav>
    <footer>${escape(transport.trust_boundary)}</footer>`;
}
const formPage = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ResearchForge V2 研究结果</title><style>
:root{font-family:Inter,system-ui,sans-serif;color:#dce4eb;background:#071015}*{box-sizing:border-box}body{margin:0;background:#071015}main{max-width:920px;margin:auto;padding:44px 22px 70px}.eyebrow{color:#43d6a3;font:11px ui-monospace,monospace;letter-spacing:.14em}header{position:relative;margin-bottom:22px}h1{margin:8px 0;color:#fff}.status{position:absolute;right:0;top:15px;color:#72e7bd}.conclusion,details,.failure{margin:12px 0;padding:18px;border:1px solid #23343e;border-radius:12px;background:#0d1921}.conclusion{border-left:3px solid #43d6a3}.conclusion p{font:17px/1.85 Georgia,serif}.conclusion small,li{color:#9eb0b9}summary{cursor:pointer;font-weight:650}li{margin:9px 0;line-height:1.65}a{color:#71d7b2}nav{display:flex;gap:12px;flex-wrap:wrap;margin-top:18px}nav a{padding:10px 12px;border:1px solid #285846;border-radius:8px;text-decoration:none}footer{margin-top:20px;color:#657d88;font:10px/1.7 ui-monospace,monospace}.failure{border-color:#663b3b;color:#ffaaa4}</style></head><body><main>${content}</main></body></html>`;
return [{ json: { transport, formPage } }];
