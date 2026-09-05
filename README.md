# ResearchForge

[![CI](https://github.com/pocketvin/researchforge/actions/workflows/ci.yml/badge.svg)](https://github.com/pocketvin/researchforge/actions/workflows/ci.yml)

> **Auditable autonomous financial research for public companies.**

ResearchForge is an AI Research Agent for users who want a fast first-pass company study without trusting a financial chatbot's black box.

Give it:

```text
Company name / ticker + optional market + optional period + research question
```

For example:

```text
贵州茅台 + Auto + Latest + “当前最值得关注的三个经营风险是什么？”
NVDA + US + Latest + “Where is recent growth coming from, and which drivers matter most?”
腾讯 + HK + 2025FY + “主要业务和分部结构发生了哪些重要变化？”
```

ResearchForge then performs:

```text
Entity Resolution → Official Filing Discovery → Verified Extraction
→ Question Routing → Research Plan → Full-filing Evidence Retrieval
→ Deterministic Calculations → Counter Evidence → Claims / Deep Analysis → Trace
```

## Why it is different

ResearchForge is not primarily a filing summarizer. Its core promise is that successful research is inspectable and failed research is explicit.

- Important arithmetic is deterministic Python, not model memory.
- Material claims reference stored Facts and Evidence.
- Dynamic run inputs are snapshotted so historical runs do not drift after later downloads.
- Official-source identity, publication time, retrieval time, hashes and locators are retained.
- Ambiguous company resolution or unreliable extraction causes an explicit abstention instead of invented data.
- The same authoritative backend serves Web and n8n.
- Historical evaluation/Quality Lab evidence remains preserved but is not the normal user journey.

## V1.7.1 market boundary

| Market | Company resolution | Official source | Numerical truth path |
|---|---|---|---|
| CN | ticker / Chinese name | CNINFO / official exchange disclosure | verified native-text PDF |
| US | ticker / issuer name | SEC EDGAR | SEC Company Facts/XBRL tied to filing accession |
| HK | ticker / English / traditional / simplified Chinese name | HKEXnews | verified native-text IFRS annual-report PDF |

V1.7.1 keeps six comparable financial facts—revenue, operating cost, net income, operating cash flow, accounts receivable and inventory—as the deterministic numerical backbone, while General Research retrieves full-filing narrative Evidence and distinguishes model synthesis from an explicit evidence-summary fallback. Unsupported document layouts fail closed.

## Current status

- Active direction: **V1.7.1 Research Synthesis & Report UX** over the V1.7 General Company Research scope.
- V1.7 first Owner Acceptance: **FAILED** — retrieval breadth passed, but deterministic evidence excerpts were incorrectly presented as research synthesis. RF-035 records the correction.
- V1.7 Golden Regression remains **PASS** — quick CN/US/HK success; extended nine-company set produced **6 trusted successes + 3 explicit safe abstentions**.
- V1.7.1 real model smoke: 贵州茅台 `company_overview` 8 Claims / 5 sections; NVIDIA `growth_analysis` 6 / 5; 腾讯 `business_analysis` 6 / 5.
- Web and n8n expose `synthesis_mode`; model-backed research and evidence-summary fallback are visibly different. Historical V1.4/V1.5/V1.6 evidence remains preserved.
- V1.7.1 engineering gate: **PASS** — 210 pytest tests, strict mypy over 105 source files, 5 frontend unit tests, 3 mocked + 3 live E2E, fresh Docker smoke, 11 n8n Node tests, 3 actual n8n success cases and 5/5 failure-fixture routes.
- Current gate: **RELEASE_FREEZE in progress — engineering complete, owner re-acceptance pending**.
- Six-person Human Pilot: **removed from the active release criteria by RF-032**.
- Investment advice, order execution and price prediction: not provided.

See [PROJECT_STATUS.md](PROJECT_STATUS.md), the [final delivery roadmap](docs/product/researchforge-final-delivery-roadmap.md) and [DECISIONS.md](DECISIONS.md) for current authority.

## Product architecture

| Layer | Owns |
|---|---|
| Discovery | company resolution and official filing discovery |
| Ingestion | acquisition, immutable identity, parsing and normalized facts/evidence |
| Deterministic Python | Decimal formulas, period semantics and financial calculations |
| Evidence System | source identity, locators and claim traceability |
| LangGraph | bounded research workflow, checkpoint/recovery, cancellation and sanitized trace |
| Model adapter | bounded language synthesis over supplied evidence/calculations |
| n8n | optional external workflow entry; no finance calculation or second research engine |
| Quality Lab | preserved historical evaluation evidence, separate from product use |

ResearchForge uses Python 3.12, FastAPI, Pydantic 2, LangGraph, SQLAlchemy/Alembic, PostgreSQL, React, TypeScript and Vite. Immutable JSON artifacts use content-addressed storage.

## Run locally

Install/sync:

```bash
uv sync --frozen --all-groups
npm ci --prefix frontend
```

Start API and Web separately:

```bash
RESEARCHFORGE_REASONING_MODE=auto \
uv run uvicorn researchforge.api.app:create_app --factory --reload

npm run dev --prefix frontend
```

Or start the packaged stack:

```bash
uv run python scripts/start_demo.py
```

Web: `http://127.0.0.1:4173/`
n8n V1.7.1 form: `http://127.0.0.1:5678/form/researchforge-v17-form`

## Autonomous API

Primary creation resource:

```text
POST /v1/autonomous-research-runs
```

Input fields:

```text
company_query
market_hint: CN | US | HK | null
requested_period_label: 2025FY / 2025H1 / 2025Q1 ... | null
research_question
research_time
idempotency_key
```

The created run then uses the ordinary immutable resources:

- `GET /v1/research-runs/{run_id}`
- `GET /v1/research-runs/{run_id}/result`
- `GET /v1/research-runs/{run_id}/facts`
- `GET /v1/research-runs/{run_id}/evidence`
- `GET /v1/research-runs/{run_id}/calculations`
- `GET /v1/research-runs/{run_id}/trace`
- `POST /v1/research-runs/{run_id}/cancel`

## Golden Company Regression

The release regression deliberately distinguishes trusted success from safe abstention. Quick mode requires at least one real successful run in each supported market:

```bash
RESEARCHFORGE_REASONING_MODE=deterministic \
uv run python scripts/autonomous_regression.py
```

Extended mode adds more unfamiliar companies:

```bash
RESEARCHFORGE_REASONING_MODE=deterministic \
uv run python scripts/autonomous_regression.py --all
```

A successful case must contain exactly the six required facts, valid Claim→Fact/Evidence references, a completed Trace and an allowlisted official source. An unsupported filing may abstain; it may not produce a partial fabricated report.

## Data safety

Product data comes from public official disclosures. Raw downloaded filing bytes remain ignored by Git. Derived artifacts retain provenance and hashes. `fixture` and `benchmark` namespaces never silently substitute for missing product data.

When an explicit company+period matches a reviewed V1.5 product package, compatibility `financial_snapshot` runs may reuse that immutable cache. V1.7/V1.7.1 General Research uses separate versioned full-text Evidence packages so stale six-fact-only packages cannot satisfy a deep-research run. General Research Result schema remains `1.7.0`; product/API package version is `1.7.1`.

## Historical evidence

V1.4 and V1.5 contracts, experiments, reviewed filing packages, screenshots and old Human Pilot templates remain in the repository for auditability. They are not silently rewritten to claim V1.7 results.

The V1.4 formal evolution hypothesis ended honestly at:

```text
RESEARCH_HYPOTHESIS_UNSUPPORTED_AFTER_TWO_EXPERIMENTS
```

The V1.5 three-filing evidence remains documented in [docs/evidence/v1.5-generalization/README.md](docs/evidence/v1.5-generalization/README.md). The previous V1.5 product thesis is historical context; RF-032 through RF-035 and the active roadmap define the current V1.7.1 direction.

## Start here

1. [PROJECT_STATUS.md](PROJECT_STATUS.md) — current milestone and release gate.
2. [Final delivery roadmap](docs/product/researchforge-final-delivery-roadmap.md) — V1.7.1 completion and owner re-acceptance sequence.
3. [V1.7 → V1.7.1 synthesis change note](docs/product/v1.7-to-v1.7.1-synthesis-change-note.md) — why the first V1.7 Owner Acceptance failed and how synthesis/fallback are separated.
4. [DECISIONS.md](DECISIONS.md) — product and architecture decisions, including RF-032 through RF-035.
5. [n8n integration](integrations/n8n/README.md) — V1.7.1 external workflow entry.
6. [PORTFOLIO.md](PORTFOLIO.md) — project positioning and historical evidence.

## Non-goals

V1.7.1 does not provide trading, order execution, price targets, portfolio optimization, real-time market-data infrastructure, Bloomberg-scale proprietary coverage, unrestricted global-market support, open-ended self-modification or investment recommendations.
