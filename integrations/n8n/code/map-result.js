// Presentation aliases only. All research, evidence, facts and calculations are V2 backend-owned.
const run = $('Accept submission').first().json;
const config = $('Prepare request').first().json;
const resultResponse = $('Fetch result').first().json;
const workspaceResponse = $('Fetch workspace').first().json;
const traceResponse = $('Fetch trace').first().json;
const result = resultResponse.body;
const workspace = workspaceResponse.body;
const trace = traceResponse.body;
const valid = [resultResponse, workspaceResponse, traceResponse].every((response) => response.statusCode === 200) &&
  result?.run_id === run.run_id && workspace?.run_id === run.run_id && trace?.run_id === run.run_id &&
  result?.schema_version === '2.0.0' && typeof result?.report?.executive_summary === 'string' &&
  Array.isArray(result?.report?.findings) && Array.isArray(result?.report?.sections) &&
  Array.isArray(workspace?.facts) && Array.isArray(workspace?.calculations) && Array.isArray(trace?.events);
if (!valid) {
  return [{ json: {
    schema_version: '2.0.0', status: 'error', http_status: 502, run_id: run.run_id,
    links: run.links, code: 'RESULT_ARTIFACTS_UNAVAILABLE',
    message: 'V2 报告或工作区产物不可用/不匹配；未把缺失内容呈现为成功。',
  } }];
}
return [{ json: {
  schema_version: '2.0.0', status: 'succeeded', http_status: 200,
  run_id: run.run_id, links: run.links, request: config.request,
  direct_answer: result.report.direct_answer,
  conclusion: result.report.executive_summary,
  findings: result.report.findings,
  analysis_sections: result.report.sections,
  limitations: result.report.limitations,
  follow_up_questions: result.report.follow_up_questions,
  financial_facts: workspace.facts,
  calculations: workspace.calculations,
  supporting_evidence: workspace.observed_evidence || [],
  hypotheses: workspace.working?.hypotheses || [],
  stop_decision: workspace.stop_decision || null,
  extraction_gaps: workspace.gaps || [],
  semantic_review: result.semantic_review,
  validation: result.validation,
  research_result: result,
  research_trace: trace,
  trust_boundary: 'n8n 只编排并展示同一 V2 backend 的持久化产物，不生成研究结论、财务数字或第二套状态。',
} }];
