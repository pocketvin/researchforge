# ResearchForge V2 n8n Integration

n8n is a transport/presentation surface over the same canonical V2 ResearchForge runtime used by Web, CLI and MCP. It does not own filing discovery, retrieval, finance formulas, Research State, validation, or a second model workflow.

## Active workflow

Source-generated portable artifact:

```text
integrations/n8n/researchforge-v2.workflow.json
```

The persistent n8n workflow record ID remains `researchforgeV17` only so importing the V2 definition replaces the existing local record instead of creating a second active workflow. The product path/name/content are V2.

Historical `researchforge.workflow.json`, `researchforge-v1.6.workflow.json`, and `researchforge-v1.7.workflow.json` are frozen audit artifacts only. They are never imported by `scripts/start_demo.py`.

## User inputs

- Company / 公司或股票代码
- Market / 市场: Auto / A 股 / 美股 / 港股
- Period / 报告期（可选）: blank = Latest, or e.g. `2025FY`, `2024H1`
- Research Question / 研究问题

The workflow sends exactly the V2 request shape to `POST /v2/research-runs`, polls that same Run, then reads `/result`, `/workspace`, and `/trace`. Facts, calculations, observed evidence, hypotheses, stop state, validation and semantic review all come from the same persisted V2 run as the Web UI.

## Generate and test

```bash
node integrations/n8n/build-workflow.mjs
node integrations/n8n/build-workflow.mjs --check
node --test integrations/n8n/workflow.test.mjs
```

## Import and publish

```bash
docker compose -f docker-compose.yml -f integrations/n8n/compose.yml \
  --profile n8n run --rm --no-deps n8n \
  import:workflow --input=/files/researchforge-v2.workflow.json

docker compose -f docker-compose.yml -f integrations/n8n/compose.yml \
  --profile n8n run --rm --no-deps n8n \
  publish:workflow --id=researchforgeV17
```

## Entry points

Native form:

```text
http://127.0.0.1:5678/form/researchforge-v2-form
```

Webhook:

```text
http://127.0.0.1:5678/webhook/researchforge-v2
```

Example webhook body:

```json
{
  "company_query": "NVDA",
  "market_hint": "US",
  "requested_period_label": null,
  "research_question": "最近增长主要来自哪里？哪些业务或因素贡献最大？"
}
```

`research_time` and `idempotency_key` may be supplied for an exact retry; otherwise the workflow creates them once for the submission.

## Safety boundary

Input validation, bounded polling and HTML escaping remain in n8n. All research meaning remains in V2. An invalid input or failed/insufficient/cancelled/timed-out Run returns a bounded failure with no invented report. `scripts/n8n_smoke.py` deliberately checks only form/transport failure behavior and performs **zero provider calls**.
