// Test-only clone: change transport configuration, never the routing or result mapping code.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
const workflow = JSON.parse(readFileSync(new URL('./researchforge-v1.7.workflow.json', import.meta.url)));
workflow.id = 'rfTransportTest';
workflow.name = '[TEST ONLY] ResearchForge transport failure checks';
const webhook = workflow.nodes.find((node) => node.name === 'Research webhook');
webhook.parameters.path = 'researchforge-runtime-test';
webhook.webhookId = 'researchforge-runtime-test';
// Keep the failure fixture transport-only and avoid colliding with the production form path.
workflow.nodes = workflow.nodes.filter((node) => node.name !== 'Research form');
delete workflow.connections['Research form'];
const prepare = workflow.nodes.find((node) => node.name === 'Prepare request');
prepare.parameters.jsCode = prepare.parameters.jsCode
  .replace("backend_url: 'http://api:8000'", "backend_url: 'http://n8n-failure-fixture:8018'")
  .replace('max_polls: 60', 'max_polls: 3');
const dir = new URL('../../artifacts/n8n-runtime-fixture/', import.meta.url);
mkdirSync(dir, { recursive: true });
writeFileSync(new URL('workflow.json', dir), JSON.stringify(workflow, null, 2) + '\n');
console.log('Generated ignored test-only workflow; no financial truth supplied.');
