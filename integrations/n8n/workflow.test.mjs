import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import assert from 'node:assert/strict';

const workflow = JSON.parse(readFileSync(new URL('./researchforge-v2.workflow.json', import.meta.url)));
const runId = 'run_' + 'a'.repeat(32);
const request = {
  company_query: 'NVDA', market_hint: 'US', requested_period_label: null,
  research_question: '最近增长主要来自哪里？哪些业务贡献最大？',
};
function execute(name, input, references = {}, runIndex = 0) {
  const node = workflow.nodes.find((item) => item.name === name);
  assert(node, `missing node ${name}`);
  const output = vm.runInNewContext(`(function(){${node.parameters.jsCode}\n})()`, {
    $input: { first: () => ({ json: input }) }, $execution: { id: 'test-12345' }, $runIndex: runIndex,
    $: (label) => ({ first: () => ({ json: references[label] }) }),
  });
  return JSON.parse(JSON.stringify(output[0].json));
}
const config = execute('Prepare request', { body: request });
const refs = { 'Prepare request': config, 'Accept submission': {
  run_id: runId, path: `/v2/research-runs/${runId}`,
  links: { status: `http://127.0.0.1:8000/v2/research-runs/${runId}` },
} };

test('workflow is portable, unpinned and V2-only', () => {
  assert.equal(workflow.active, false);
  assert.deepEqual(workflow.pinData, {});
  assert.equal(workflow.settings.executionTimeout, 300);
  const serialized = JSON.stringify(workflow);
  assert(serialized.includes('/v2/research-runs'));
  assert(!serialized.includes('/v1/'));
  assert(!serialized.includes('research_mode'));
  const names = new Set(workflow.nodes.map((node) => node.name));
  assert.equal(names.size, workflow.nodes.length);
  const allowed = ['webhook', 'formTrigger', 'code', 'if', 'httpRequest', 'wait', 'respondToWebhook', 'stickyNote'];
  for (const node of workflow.nodes) {
    assert(allowed.includes(node.type.replace('n8n-nodes-base.', '')));
    assert.equal(node.credentials, undefined);
    if (node.type.endsWith('.if')) assert.equal(workflow.connections[node.name].main.length, 2);
    if (node.type.endsWith('.httpRequest')) {
      assert.equal(node.parameters.options.timeout, 5000);
      assert.equal(node.maxTries, 3);
      assert.equal(node.onError, 'continueRegularOutput');
      assert.equal(node.parameters.options.redirect.redirect.followRedirects, false);
    }
  }
});

test('native form and webhook produce the same V2 request shape', () => {
  const form = execute('Prepare request', {
    'Company / 公司或股票代码': 'NVDA', 'Market / 市场': '美股',
    'Period / 报告期（可选）': '', 'Research Question / 研究问题': request.research_question,
    submittedAt: '2026-09-14T00:00:00Z', formMode: 'production',
  });
  assert.equal(config.surface, 'webhook');
  assert.equal(form.surface, 'form');
  assert.equal(form.ok, true);
  assert.equal(form.request.company_query, config.request.company_query);
  assert.equal(form.request.market_hint, config.request.market_hint);
  assert.equal(form.request.requested_period_label, config.request.requested_period_label);
  assert.equal(form.request.research_question, config.request.research_question);
  assert.equal(form.request.research_mode, undefined);
});

test('invalid transport input fails before backend submission', () => {
  for (const body of [null, [], {}, { ...request, backend_url: 'http://evil' },
    { ...request, data_namespace: 'fixture' }, { ...request, research_question: '' },
    { ...request, company_query: '' }, { ...request, market_hint: 'CRYPTO' },
    { ...request, requested_period_label: '2025Q5' }, { ...request, research_mode: 'general' }]) {
    assert.equal(execute('Prepare request', { body }).code, 'INVALID_INPUT');
  }
});

test('backend readiness requires the V2 capability surface', () => {
  for (const response of [{ statusCode: 500 },
    { statusCode: 200, body: { version: '2.0.0-alpha.1', agent_ready: false } },
    { statusCode: 200, body: { version: '1.8.5', agent_ready: true } }]) {
    assert.equal(execute('Check backend', response, refs).code, 'BACKEND_UNAVAILABLE_OR_UNSAFE');
  }
  assert.equal(execute('Check backend', { statusCode: 200,
    body: { version: '2.0.0-alpha.1', agent_ready: true } }, refs).ok, true);
});

test('submission accepts only safe V2 run IDs and local links', () => {
  const accepted = execute('Accept submission', { statusCode: 202,
    body: { run_id: runId, links: { status: 'http://evil' } } }, refs);
  assert.equal(accepted.path, `/v2/research-runs/${runId}`);
  assert(!JSON.stringify(accepted).includes('evil'));
  assert.equal(execute('Accept submission', { statusCode: 202,
    body: { run_id: '../../secret' } }, refs).ok, false);
});

test('polling handles every V2 terminal state explicitly', () => {
  for (const state of ['queued', 'running', 'succeeded', 'insufficient_data', 'cancelled', 'failed', 'timed_out', 'alien']) {
    const output = execute('Classify status', { statusCode: 200,
      body: { run_id: runId, lifecycle_state: state } }, refs);
    assert.equal(output.route, ['queued', 'running'].includes(state) ? 'waiting' :
      state === 'succeeded' ? 'completed' : 'error');
  }
});

test('V2 result mapping copies persisted artifacts without a second research model', () => {
  const result = {
    schema_version: '2.0.0', run_id: runId,
    report: {
      direct_answer: 'mixed', executive_summary: '经营现金流为正，但净现金下降。',
      findings: [{ claim_id: 'claim_1', title: '现金流', text: '混合信号。' }],
      sections: [{ title: '分析', text: '基于已引用财报证据。' }],
      limitations: ['未使用外部行业数据。'], follow_up_questions: ['下一期现金流如何？'],
    },
    semantic_review: { status: 'model_reviewed' }, validation: { passed: true },
  };
  const workspace = {
    run_id: runId, facts: [{ fact_id: 'fact_1' }], calculations: [{ calculation_id: 'calc_1' }],
    observed_evidence: [{ artifact_id: 'ev_1', text: 'cash evidence' }],
    working: { hypotheses: [{ statement: 'test', status: 'supported' }] },
    stop_decision: { stop_reason: 'sufficient_evidence' }, gaps: [],
  };
  const trace = { run_id: runId, events: [] };
  const output = execute('Map verified output', {}, { ...refs,
    'Fetch result': { statusCode: 200, body: result },
    'Fetch workspace': { statusCode: 200, body: workspace },
    'Fetch trace': { statusCode: 200, body: trace },
  });
  assert.equal(output.status, 'succeeded');
  assert.equal(output.conclusion, result.report.executive_summary);
  assert.deepEqual(output.financial_facts, workspace.facts);
  assert.deepEqual(output.research_result, result);
  assert.deepEqual(output.research_trace, trace);
});

test('form renderer escapes backend prose and preserves transport JSON', () => {
  const success = {
    status: 'succeeded', conclusion: '<script>alert(1)</script>', direct_answer: 'mixed',
    findings: [], analysis_sections: [], financial_facts: [], calculations: [], supporting_evidence: [],
    hypotheses: [], limitations: ['<b>limit</b>'], extraction_gaps: [], follow_up_questions: [],
    links: { result: 'http://example/result', trace: 'http://example/trace', workspace: 'http://example/workspace' },
    trust_boundary: 'same V2 backend',
  };
  const rendered = execute('Render surface response', success, { 'Prepare request': config });
  assert.deepEqual(rendered.transport, success);
  assert(!rendered.formPage.includes('<script>alert'));
  assert(rendered.formPage.includes('&lt;script&gt;'));
  assert(rendered.formPage.includes('完整 V2 Trace'));
});
