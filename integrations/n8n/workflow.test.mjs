import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import assert from 'node:assert/strict';

const workflow = JSON.parse(readFileSync(new URL('./researchforge-v1.6.workflow.json', import.meta.url)));
const runId = 'run_' + 'a'.repeat(32);
const request = { company_query: 'NVDA', market_hint: 'US', requested_period_label: null, research_question: '最新报告期利润是否转化成经营现金流？' };
function execute(name, input, references = {}, runIndex = 0) {
  const node = workflow.nodes.find((item) => item.name === name);
  const output = vm.runInNewContext(`(function(){${node.parameters.jsCode}\n})()`, {
    $input: { first: () => ({ json: input }) }, $execution: { id: 'test-12345' }, $runIndex: runIndex,
    $: (label) => ({ first: () => ({ json: references[label] }) }),
  });
  return JSON.parse(JSON.stringify(output[0].json));
}
const config = execute('Prepare request', { body: request });
const refs = { 'Prepare request': config, 'Accept submission': {
  run_id: runId, path: `/v1/research-runs/${runId}`, links: { status: 'http://127.0.0.1:8000/status' },
} };

test('workflow is portable, unpinned, bounded and all IF outputs are wired', () => {
  assert.equal(workflow.active, false);
  assert.deepEqual(workflow.pinData, {});
  assert.equal(workflow.settings.executionTimeout, 300);
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
      assert(!node.parameters.url.includes('$json.body'));
    }
  }
  for (const edges of Object.values(workflow.connections)) {
    for (const branch of edges.main) for (const edge of branch) assert(names.has(edge.node));
  }
});
test('native form and webhook enter the same bounded backend request path', () => {
  const form = execute('Prepare request', {
    'Company / 公司或股票代码': 'NVDA',
    'Market / 市场': '美股',
    'Period / 报告期（可选）': '',
    'Research Question / 研究问题': request.research_question,
    submittedAt: '2026-09-04T00:00:00Z', formMode: 'production',
  });
  assert.equal(config.surface, 'webhook');
  assert.equal(form.surface, 'form');
  assert.equal(form.ok, true);
  assert.equal(form.request.company_query, config.request.company_query);
  assert.equal(form.request.market_hint, config.request.market_hint);
  assert.equal(form.request.requested_period_label, config.request.requested_period_label);
  assert.equal(form.request.research_question, config.request.research_question);
  assert.deepEqual(workflow.connections['Research webhook'].main[0], [{ node: 'Prepare request', type: 'main', index: 0 }]);
  assert.deepEqual(workflow.connections['Research form'].main[0], [{ node: 'Prepare request', type: 'main', index: 0 }]);
});
test('minimum input maps to the same backend request, no namespace override', () => {
  assert.equal(config.ok, true);
  assert.equal(config.request.company_query, 'NVDA');
  assert.equal(config.request.market_hint, 'US');
  assert.equal(config.request.requested_period_label, null);
  assert.equal(config.request.idempotency_key, 'n8n-run-test-12345');
  assert.equal(config.backend_url, 'http://api:8000');
  for (const body of [null, [], {}, { ...request, backend_url: 'http://evil' },
    { ...request, data_namespace: 'fixture' }, { ...request, research_question: '' },
    { ...request, idempotency_key: 'retry-123' }, { ...request, research_time: 'yesterday' },
    { ...request, company_query: '' }, { ...request, market_hint: 'CRYPTO' },
    { ...request, requested_period_label: '2025Q5' }]) {
    assert.equal(execute('Prepare request', { body }).code, 'INVALID_INPUT');
  }
});
test('cross-execution retry preserves all immutable input including cutoff', () => {
  const body = { ...request, idempotency_key: 'retry-123', research_time: '2026-09-03T00:00:00Z' };
  assert.deepEqual(execute('Prepare request', { body }).request, execute('Prepare request', { body }).request);
});
test('backend readiness is checked before autonomous submission', () => {
  for (const response of [{ error: 'secret exception' }, { statusCode: 500 },
    { statusCode: 200, body: { status: 'starting', version: '1.6.0' } },
    { statusCode: 200, body: { status: 'ok', version: '1.5.0' } }]) {
    const result = execute('Check backend', response, refs);
    assert.equal(result.code, 'BACKEND_UNAVAILABLE_OR_UNSAFE');
    assert(!JSON.stringify(result).includes('secret exception'));
  }
  assert.equal(execute('Check backend', { statusCode: 200, body: { status: 'ok', version: '1.6.0' } }, refs).ok, true);
});
test('submission accepts only safe IDs and does not follow response-supplied URLs', () => {
  const response = execute('Accept submission', { statusCode: 202,
    body: { run_id: runId, links: { status: 'http://evil' } } }, refs);
  assert.equal(response.ok, true);
  assert(!JSON.stringify(response).includes('evil'));
  for (const [statusCode, code] of [[409, 'IDEMPOTENCY_CONFLICT'], [422, 'UNSUPPORTED_OR_INVALID_INPUT'],
    [500, 'SUBMISSION_UNCONFIRMED']]) {
    assert.equal(execute('Accept submission', { statusCode }, refs).code, code);
  }
  assert.equal(execute('Accept submission', { statusCode: 202, body: { run_id: '../../secret' } }, refs).ok, false);
});
test('queued/running poll; each terminal outcome has an explicit branch', () => {
  for (const state of ['queued', 'running', 'succeeded', 'insufficient_data', 'cancelled', 'failed', 'timed_out', 'alien']) {
    const output = execute('Classify status', { statusCode: 200,
      body: { run_id: runId, lifecycle_state: state } }, refs);
    assert.equal(output.route, ['queued', 'running'].includes(state) ? 'waiting' :
      state === 'succeeded' ? 'completed' : 'error');
    if (output.route === 'error') assert.equal(output.status, 'error');
  }
});
test('poll count, elapsed time, mismatched ID and network error stop safely', () => {
  const response = { statusCode: 200, body: { run_id: runId, lifecycle_state: 'running' } };
  assert.equal(execute('Classify status', response, refs, 59).code, 'POLL_LIMIT_EXCEEDED');
  assert.equal(execute('Classify status', response, { ...refs,
    'Prepare request': { ...config, started_at_ms: 0 } }).code, 'POLL_LIMIT_EXCEEDED');
  assert.equal(execute('Classify status', { error: 'internal secret' }, refs).code, 'STATUS_UNAVAILABLE');
  assert.equal(execute('Classify status', { statusCode: 200, body: { run_id: 'wrong' } }, refs).code, 'STATUS_UNAVAILABLE');
});
test('mapped fields equal backend artifacts without numerical or prose generation', () => {
  const result = JSON.parse(readFileSync(new URL('../../docs/evidence/v1.5-generalization/byd-2024h1/research-result.json', import.meta.url)));
  const caseRefs = { ...refs, 'Accept submission': { ...refs['Accept submission'], run_id: result.run_id } };
  const values = [result, [{ value: '123.4500' }], [{ value: '1.04012' }], [{ evidence_id: 'evidence' }],
    { run_id: result.run_id, stages: [] }];
  ['result', 'facts', 'calculations', 'evidence', 'trace'].forEach((kind, i) => {
    caseRefs[`Fetch ${kind}`] = { statusCode: 200, body: values[i] };
  });
  const output = execute('Map verified output', {}, caseRefs);
  assert.equal(output.status, 'succeeded');
  assert.equal(output.conclusion, result.executive_summary);
  assert.deepEqual(output.findings, result.claims);
  assert.deepEqual(output.research_result, result);
  assert.deepEqual(output.financial_facts, values[1]);
  assert.deepEqual(output.calculations, values[2]);
  assert.deepEqual(output.monitoring, result.monitoring_items);
  assert.deepEqual(output.limitations, result.limitations);
  for (const kind of ['result', 'facts', 'calculations', 'evidence', 'trace']) {
    assert.equal(execute('Map verified output', {}, { ...caseRefs,
      [`Fetch ${kind}`]: { statusCode: 500 } }).code, 'RESULT_ARTIFACTS_UNAVAILABLE');
  }
});
test('form response escapes backend text and transport response remains unchanged', () => {
  const success = {
    status: 'succeeded', conclusion: '<script>alert(1)</script>', findings: [],
    financial_facts: [], calculations: [], supporting_evidence: [], counter_evidence: [],
    limitations: ['<b>limit</b>'], monitoring: [], links: { result: 'http://example/result', trace: 'http://example/trace' },
    trust_boundary: 'same backend',
  };
  const rendered = execute('Render surface response', success, { 'Prepare request': config });
  assert.deepEqual(rendered.transport, success);
  assert(!rendered.formPage.includes('<script>alert'));
  assert(rendered.formPage.includes('&lt;script&gt;'));
  assert(rendered.formPage.includes('完整 Research Trace'));
  const failure = execute('Render surface response', { status: 'error', code: 'RUN_FAILED', message: '<failure>', links: null }, { 'Prepare request': config });
  assert(failure.formPage.includes('研究未生成'));
  assert(!failure.formPage.includes('<failure>'));
});
