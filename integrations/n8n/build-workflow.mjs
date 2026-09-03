// Produce one portable import artifact; keep Code nodes separately reviewable and testable.
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
node('Research webhook', 'webhook', 2.1, { httpMethod: 'POST', path: 'researchforge-v15',
  responseMode: 'responseNode', options: {} }, [0, 0], { webhookId: 'researchforge-v15' });
node('Research form', 'formTrigger', 2.1, {
  path: 'researchforge-v15-form',
  formTitle: 'ResearchForge · 可核验 A 股基本面研究',
  formDescription: '输入公司、报告期和研究问题。支持：宁德时代 2024H1/2024FY、比亚迪 2024H1。结果来自与 Web 相同的后端、确定性计算和证据验证链路。',
  formFields: { values: [
    { fieldLabel: 'Company / 公司', fieldType: 'dropdown', requiredField: true,
      fieldOptions: { values: [{ option: '宁德时代 · 300750.SZSE' }, { option: '比亚迪 · 002594.SZSE' }] } },
    { fieldLabel: 'Period / 报告期', fieldType: 'dropdown', requiredField: true,
      fieldOptions: { values: [{ option: '2024H1' }, { option: '2024FY' }] } },
    { fieldLabel: 'Research Question / 研究问题', fieldType: 'textarea', requiredField: true,
      placeholder: '例如：2024 年上半年利润是否真正转化成了经营现金流？' },
  ] },
  responseMode: 'responseNode',
  options: { buttonLabel: 'Start Research / 开始研究', appendAttribution: false },
}, [0, 180], { webhookId: 'researchforge-v15-form' });
code('Prepare request', 'prepare.js', [220, 0]);
check('Input valid', '={{ String($json.ok) }}', 'true', [440, 0]);
http('Check product backend', `={{ ${backend} + '/v1/catalog' }}`, [660, 0]);
code('Check catalog', 'check-catalog.js', [880, 0]);
check('Backend ready', '={{ String($json.ok) }}', 'true', [1100, 0]);
http('Create run', `={{ ${backend} + '/v1/research-runs' }}`, [1320, 0], true);
code('Accept submission', 'accept-submission.js', [1540, 0]);
check('Submission accepted', '={{ String($json.ok) }}', 'true', [1760, 0]);
node('Wait before polling', 'wait', 1.1, { resume: 'timeInterval', amount: 2, unit: 'seconds' }, [1980, 0]);
http('Poll status', `={{ ${backend} + ${runPath} }}`, [2200, 0]);
code('Classify status', 'classify-status.js', [2420, 0]);
check('Run completed', '={{ $json.route }}', 'completed', [2640, 0]);
check('Keep waiting', '={{ $json.route }}', 'waiting', [2640, 260]);
['result', 'facts', 'calculations', 'evidence', 'trace'].forEach((kind, index) => {
  http(`Fetch ${kind}`, `={{ ${backend} + ${runPath} + '/${kind}' }}`, [2860 + index * 220, 0]);
});
code('Map verified output', 'map-result.js', [3960, 0]);
code('Render surface response', 'render-response.js', [4180, 0]);
check('Form surface', "={{ $('Prepare request').first().json.surface }}", 'form', [4400, 0]);
node('Respond form', 'respondToWebhook', 1.4, { respondWith: 'text', responseBody: '={{ $json.formPage }}',
  options: { responseCode: 200 } }, [4620, -100]);
node('Respond webhook', 'respondToWebhook', 1.4, { respondWith: 'json', responseBody: '={{ $json.transport }}',
  options: { responseCode: '={{ $json.transport.http_status }}' } }, [4620, 100]);
const chain = ['Research webhook', 'Prepare request', 'Input valid', 'Check product backend',
  'Check catalog', 'Backend ready', 'Create run', 'Accept submission', 'Submission accepted',
  'Wait before polling', 'Poll status', 'Classify status', 'Run completed',
  'Fetch result', 'Fetch facts', 'Fetch calculations', 'Fetch evidence', 'Fetch trace',
  'Map verified output', 'Render surface response', 'Form surface'];
for (let i = 0; i < chain.length - 1; i++) connect(chain[i], chain[i + 1]);
connect('Research form', 'Prepare request');
for (const name of ['Input valid', 'Backend ready', 'Submission accepted']) connect(name, 'Render surface response', 1);
connect('Run completed', 'Keep waiting', 1);
connect('Keep waiting', 'Wait before polling');
connect('Keep waiting', 'Render surface response', 1);
connect('Form surface', 'Respond form');
connect('Form surface', 'Respond webhook', 1);
node('Read me', 'stickyNote', 1, { width: 640, height: 280,
  content: '## ResearchForge × n8n\nCompany + Period + Research Question → verified research.\n\n**Local-only.** Configure trusted backend/public URLs in Prepare request, never in user input.\n\nWait: 2s; ≤60 polls / 150s. Failure output never invents research. n8n timeout does not cancel backend.\n\nAll facts, calculations, evidence and conclusions come from the SAME backend as Web. No LLM, finance formula or verifier lives here.\n\nSee integrations/n8n/README.md for import, demo, retries and failures. Human usefulness UNVALIDATED.',
}, [0, -380]);
const workflow = { id: 'researchforgeV15', name: 'ResearchForge — Verified Company Research',
  active: false, nodes, connections, pinData: {},
  settings: { executionOrder: 'v1', executionTimeout: 300,
    saveDataSuccessExecution: 'all', saveDataErrorExecution: 'all' }, tags: [] };
const path = join(root, 'researchforge.workflow.json');
const serialized = JSON.stringify(workflow, null, 2) + '\n';
if (process.argv.includes('--check')) {
  if (readFileSync(path, 'utf8') !== serialized) throw new Error('Workflow JSON is stale; regenerate it.');
  console.log('Portable n8n workflow matches source.');
} else {
  writeFileSync(path, serialized);
  console.log('Generated integrations/n8n/researchforge.workflow.json');
}
