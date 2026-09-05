// Presentation aliases only: never calculate finance or generate a conclusion here.
const run = $('Accept submission').first().json;
const config = $('Prepare request').first().json;
const responses = ['Fetch result', 'Fetch facts', 'Fetch calculations', 'Fetch evidence', 'Fetch trace']
  .map((name) => $(name).first().json);
const [result, facts, calculations, evidence, trace] = responses.map((response) => response.body);
const snapshotMode = config.request.research_mode === 'financial_snapshot';
const baseValid = responses.every((response) => response.statusCode === 200) &&
  result?.run_id === run.run_id && result?.status === 'completed' &&
  trace?.run_id === run.run_id && Array.isArray(trace?.stages) &&
  typeof result?.executive_summary === 'string' && Array.isArray(result?.claims) &&
  Array.isArray(result?.limitations) && Array.isArray(result?.monitoring_items) &&
  Array.isArray(result?.research_plan) && Array.isArray(facts) &&
  Array.isArray(calculations) && Array.isArray(evidence);
const contractValid = snapshotMode
  ? result?.schema_version === '1.4.0' && result?.task_type === 'filing_analysis'
  : result?.schema_version === '1.7.0' && result?.task_type === 'company_research' &&
    !!result?.research_intent && Array.isArray(result?.analysis_sections) &&
    !!result?.overall_judgment && Array.isArray(result?.suggested_follow_ups) &&
    !!result?.evidence_coverage;
if (!baseValid || !contractValid) {
  return [{ json: { schema_version: '1.7.0', status: 'error', http_status: 502,
    run_id: run.run_id, links: run.links, code: 'RESULT_ARTIFACTS_UNAVAILABLE',
    message: '后端报告或审计产物不可用/不匹配；未把缺失内容呈现为成功。请检查结果和 Trace 链接。',
  } }];
}
const output = {
  schema_version: '1.7.0', status: 'succeeded', http_status: 200, data_namespace: 'product',
  run_id: run.run_id, links: run.links, request: config.request,
  conclusion: result.executive_summary, findings: result.claims,
  research_plan: result.research_plan,
  financial_facts: facts, calculations, supporting_evidence: evidence,
  counter_evidence: result.claims.map((claim) => ({
    claim_id: claim.claim_id, search: claim.counter_evidence_search,
  })),
  limitations: result.limitations, monitoring: result.monitoring_items,
  research_result: result, research_trace: trace,
  trust_boundary: 'n8n 只编排并转交 ResearchForge 产物，不生成结论或计算财务数字。失败时不生成伪结论。',
};
if (!snapshotMode) Object.assign(output, {
  research_intent: result.research_intent,
  analysis_sections: result.analysis_sections,
  overall_judgment: result.overall_judgment,
  suggested_follow_ups: result.suggested_follow_ups,
  evidence_coverage: result.evidence_coverage,
});
return [{ json: output }];
