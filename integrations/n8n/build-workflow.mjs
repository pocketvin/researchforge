// Build the one n8n transport over the canonical V2 ResearchForge runtime.
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = dirname(fileURLToPath(import.meta.url));
const nodes = [];
const connections = {};
function node(name, type, version, parameters, position, extras = {}) {
  nodes.push({ id: name.toLowerCase().replaceAll(' ', '-'), name, type: `n8n-nodes-base.${type}`,
    typeVersion: version, position, parameters, ...extras });
}
function code(name, file, position) {
  node(name, 'code', 2, { jsCode: readFileSync(join(root, 'code', file), 'utf8') }, position);
}
function connect(from, to, output = 0) {
  connections[from] ??= { main: [] };
  while (connections[from].main.length <= output) connections[from].main.push([]);
  connections[from].main[output].push({ node: to, type: 'main', index: 0 });
}
function check(name, expression, value, position) {
  node(name, 'if', 2.2, { conditions: {
    options: { caseSensitive: true, leftValue: '', typeValidation: 'strict', version: 2 },
    conditions: [{ id: 'route', leftValue: expression, rightValue: value,
      operator: { type: 'string', operation: 'equals' } }], combinator: 'and',
  }, options: {} }, position);
}
function http(name, url, position, post = false) {
  const parameters = { url, options: { timeout: 5000,
    redirect: { redirect: { followRedirects: false } },
    response: { response: { fullResponse: true, neverError: true, responseFormat: 'json' } },
  } };
  if (post) Object.assign(parameters, { method: 'POST', sendBody: true, specifyBody: 'json',
    jsonBody: "={{ $('Prepare request').first().json.request }}" });
  node(name, 'httpRequest', 4.2, parameters, position,
    { retryOnFail: true, maxTries: 3, waitBetweenTries: 1000, onError: 'continueRegularOutput' });
}

const backend = "$('Prepare request').first().json.backend_url";
const runPath = "$('Accept submission').first().json.path";
node('Research webhook', 'webhook', 2.1, { httpMethod: 'POST', path: 'researchforge-v2',
  responseMode: 'responseNode', options: {} }, [0, 0], { webhookId: 'researchforge-v2' });
node('Research form', 'formTrigger', 2.1, {
  path: 'researchforge-v2-form',
  formTitle: 'ResearchForge V2 · 财报研究',
  formDescription: '与 Web / MCP 共用同一个 V2 研究 Runtime、数据缓存、证据链和报告。',
  formFields: { values: [
    { fieldLabel: 'Company / 公司或股票代码', fieldType: 'text', requiredField: true,
      placeholder: '宁德时代 / NVDA / 00700' },
    { fieldLabel: 'Market / 市场', fieldType: 'dropdown', requiredField: true,
      fieldOptions: { values: [{ option: 'Auto / 自动识别' }, { option: 'A 股' }, { option: '美股' }, { option: '港股' }] } },
    { fieldLabel: 'Period / 报告期（可选）', fieldType: 'text', requiredField: false,
      placeholder: '留空 = Latest；例如 2024H1 / 2025FY' },
    { fieldLabel: 'Research Question / 研究问题', fieldType: 'textarea', requiredField: true,
      placeholder: '例如：经营现金流是否健康？为什么净利润同比变化？' },
  ] },
  responseMode: 'responseNode', options: { buttonLabel: '开始 V2 财报研究', appendAttribution: false },
}, [0, 180], { webhookId: 'researchforge-v2-form' });
code('Prepare request', 'prepare.js', [220, 0]);
check('Input valid', '={{ String($json.ok) }}', 'true', [440, 0]);
http('Check V2 backend', `={{ ${backend} + '/v2/capabilities' }}`, [660, 0]);
code('Check backend', 'check-backend.js', [880, 0]);
check('Backend ready', '={{ String($json.ok) }}', 'true', [1100, 0]);
http('Create run', `={{ ${backend} + '/v2/research-runs' }}`, [1320, 0], true);
code('Accept submission', 'accept-submission.js', [1540, 0]);
check('Submission accepted', '={{ String($json.ok) }}', 'true', [1760, 0]);
node('Wait before polling', 'wait', 1.1, { resume: 'timeInterval', amount: 2, unit: 'seconds' }, [1980, 0]);
http('Poll status', `={{ ${backend} + ${runPath} }}`, [2200, 0]);
code('Classify status', 'classify-status.js', [2420, 0]);
check('Run completed', '={{ $json.route }}', 'completed', [2640, 0]);
check('Keep waiting', '={{ $json.route }}', 'waiting', [2640, 260]);
http('Fetch result', `={{ ${backend} + ${runPath} + '/result' }}`, [2860, 0]);
http('Fetch workspace', `={{ ${backend} + ${runPath} + '/workspace' }}`, [3080, 0]);
http('Fetch trace', `={{ ${backend} + ${runPath} + '/trace' }}`, [3300, 0]);
code('Map verified output', 'map-result.js', [3520, 0]);
code('Render surface response', 'render-response.js', [3740, 0]);
check('Form surface', "={{ $('Prepare request').first().json.surface }}", 'form', [3960, 0]);
node('Respond form', 'respondToWebhook', 1.4, { respondWith: 'text', responseBody: '={{ $json.formPage }}',
  options: { responseCode: 200 } }, [4180, -100]);
node('Respond webhook', 'respondToWebhook', 1.4, { respondWith: 'json', responseBody: '={{ $json.transport }}',
  options: { responseCode: '={{ $json.transport.http_status }}' } }, [4180, 100]);

const chain = ['Research webhook', 'Prepare request', 'Input valid', 'Check V2 backend', 'Check backend',
  'Backend ready', 'Create run', 'Accept submission', 'Submission accepted', 'Wait before polling',
  'Poll status', 'Classify status', 'Run completed', 'Fetch result', 'Fetch workspace', 'Fetch trace',
  'Map verified output', 'Render surface response', 'Form surface'];
for (let i = 0; i < chain.length - 1; i++) connect(chain[i], chain[i + 1]);
connect('Research form', 'Prepare request');
for (const name of ['Input valid', 'Backend ready', 'Submission accepted']) connect(name, 'Render surface response', 1);
connect('Run completed', 'Keep waiting', 1);
connect('Keep waiting', 'Wait before polling');
connect('Keep waiting', 'Render surface response', 1);
connect('Form surface', 'Respond form');
connect('Form surface', 'Respond webhook', 1);
node('Read me', 'stickyNote', 1, { width: 640, height: 260,
  content: '## ResearchForge V2 × n8n\nOne runtime only: n8n submits and reads `/v2/research-runs`; it does not own retrieval, finance, prompts, state or validation.\n\nWeb, MCP and n8n share the same official filing discovery, document cache, Research State, report and Trace.\n\nFailure stays explicit; n8n never invents a result or reruns a failed task automatically.',
}, [0, -360]);
const workflow = { id: 'researchforgeV17', name: 'ResearchForge — Filing Research V2',
  active: false, nodes, connections, pinData: {},
  settings: { executionOrder: 'v1', executionTimeout: 300,
    saveDataSuccessExecution: 'all', saveDataErrorExecution: 'all' }, tags: [] };
const path = join(root, 'researchforge-v2.workflow.json');
const serialized = JSON.stringify(workflow, null, 2) + '\n';
if (process.argv.includes('--check')) {
  if (readFileSync(path, 'utf8') !== serialized) throw new Error('Workflow JSON is stale; regenerate it.');
  console.log('Portable V2 n8n workflow matches source.');
} else {
  writeFileSync(path, serialized);
  console.log('Generated integrations/n8n/researchforge-v2.workflow.json');
}
