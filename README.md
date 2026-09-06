# ResearchForge

[![CI](https://github.com/pocketvin/researchforge/actions/workflows/ci.yml/badge.svg)](https://github.com/pocketvin/researchforge/actions/workflows/ci.yml)

> **Auditable autonomous financial research for public companies.**

ResearchForge is an auditable AI Research Agent for users who want a fast first-pass company study without trusting a financial chatbot's black box. V1.8.5 adds a measured Agent-engineering layer—evaluation, failure analysis, retrieval benchmarking, MCP interoperability and explicit security gates—without weakening the existing evidence-first research boundary.

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

## V1.8.5 product boundary

| Market | Company resolution | Official source | Numerical truth path |
|---|---|---|---|
| CN | ticker / Chinese name | CNINFO / official exchange disclosure | verified native-text PDF |
| US | ticker / issuer name | SEC EDGAR | SEC Company Facts/XBRL tied to filing accession |
| HK | ticker / English / traditional / simplified Chinese name | HKEXnews | verified native-text IFRS annual-report PDF |

V1.8.5 keeps the V1.7 General Research truth boundary and V1.7.3 lifecycle semantics: six comparable financial facts—revenue, operating cost, net income, operating cash flow, accounts receivable and inventory—remain the deterministic numerical backbone, while General Research retrieves full-filing narrative Evidence and distinguishes model synthesis from an explicit evidence-summary fallback. Unsupported document layouts fail closed. V1.8 engineering artifacts use their own `1.8.0` schemas rather than rewriting persisted Research Runs.

## Current status

- Active package: **V1.8.5 Agent Engineering Hardening** over the preserved V1.7 General Company Research scope.
- Product research truth remains evidence-first and fail-closed; V1.8 does not turn ResearchForge into a multi-agent, trading or open-ended RAG system.
- Security baseline refreshed: LangGraph 1.x, current pypdf/test tooling, `pip-audit` + `npm audit` CI, default-disabled FastAPI docs and explicit browser security headers.
- `researchforge eval` runs a frozen Router/Retrieval suite and can evaluate persisted Runs for routing, plan completion, grounding, citation validity, structured output and ten-stage trajectory completion.
- `researchforge failure-analyze` maps persisted failures to fourteen deterministic failure classes; real historical `OUTPUT_SCHEMA_INVALID` evidence is frozen as a regression candidate.
- Retrieval benchmark currently measures lexical Recall@10 **0.8125**, TF-IDF **0.8542** and RRF **0.8750**; the precision trade-off and small sample do **not** yet justify pgvector/dense retrieval.
- MCP exposes seven bounded tools over the same backend; stdio is default, optional Streamable HTTP binds to localhost.
- V1.8 contract validation currently covers four new schemas/examples alongside preserved V1.7.3/V1.7/V1.5/V1.4 history.
- V1.7 Golden Regression remains **PASS** — 6 trusted successes + 3 explicit safe abstentions; V1.7.3 Owner-path model evidence remains preserved.
- Owner re-acceptance found no product blocker. A final public-CI rerun exposed and locally fixed a low-probability same-digest content-addressed-store race; Release Freeze remains open only until that reliability fix passes remote CI.

See [PROJECT_STATUS.md](PROJECT_STATUS.md), the [V1.8.5 engineering note](docs/product/v1.8.5-agent-engineering-hardening.md), the [V1.8.5 architecture](docs/architecture/v1.8.5-agent-engineering.md), and [DECISIONS.md](DECISIONS.md).

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
| MCP | seven bounded interoperability tools over the same backend; no second research engine |
| Agent Eval / Failure | artifact-grounded component/run/thread evaluation and deterministic failure classification |
| 方法与实验 archive | preserved historical Quality Lab/evaluation evidence, secondary to normal research |

ResearchForge uses Python 3.12, FastAPI, Pydantic 2, LangGraph, SQLAlchemy/Alembic, PostgreSQL, React, TypeScript and Vite. Immutable JSON artifacts use content-addressed storage.

## Agent engineering and evaluation

Run the zero-provider-call component evaluation:

```bash
uv run researchforge eval
```

Evaluate persisted product Runs through a live backend:

```bash
uv run researchforge eval --api-base http://127.0.0.1:8000 --run-id <RUN_ID>
uv run researchforge failure-analyze <FAILED_RUN_ID> --api-base http://127.0.0.1:8000
```

Start the MCP interface locally:

```bash
uv run researchforge-mcp
# optional localhost Streamable HTTP
uv run researchforge-mcp --transport streamable-http --host 127.0.0.1 --port 8001
```

Measured V1.8 evidence and the retrieval decision are documented in [docs/evidence/v1.8/README.md](docs/evidence/v1.8/README.md).

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
n8n V1.8.5 presentation (stable V17 route): `http://127.0.0.1:5678/form/researchforge-v17-form`

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

- `GET /v1/research-runs?limit=20` — recent persisted General Research runs for workspace restore
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

When an explicit company+period matches a reviewed V1.5 product package, compatibility `financial_snapshot` runs may reuse that immutable cache. V1.7 General Research uses separate versioned full-text Evidence packages so stale six-fact-only packages cannot satisfy a deep-research run. General Research Result schema remains `1.7.0`; autonomous lifecycle manifests remain `1.7.3`; the current product/API package is V1.8.5 and new engineering-evaluation artifacts use schema `1.8.0`.

## Historical evidence

V1.4 and V1.5 contracts, experiments, reviewed filing packages, screenshots and old Human Pilot templates remain in the repository for auditability. They are not silently rewritten to claim V1.7 results.

The V1.4 formal evolution hypothesis ended honestly at:

```text
RESEARCH_HYPOTHESIS_UNSUPPORTED_AFTER_TWO_EXPERIMENTS
```

The V1.5 three-filing evidence remains documented in [docs/evidence/v1.5-generalization/README.md](docs/evidence/v1.5-generalization/README.md). The previous V1.5 product thesis is historical context; RF-032 through RF-044 and the active roadmap define the current V1.8.5 package over the preserved V1.7 research direction.

## Start here

1. [PROJECT_STATUS.md](PROJECT_STATUS.md) — current milestone and release gate.
2. [Final delivery roadmap](docs/product/researchforge-final-delivery-roadmap.md) — V1.8.5 frozen release scope and acceptance evidence.
3. [V1.8.5 Agent engineering hardening](docs/product/v1.8.5-agent-engineering-hardening.md) — security, Eval, Failure, Retrieval and MCP scope.
4. [V1.8.5 architecture](docs/architecture/v1.8.5-agent-engineering.md) — technology ownership and closed-loop design.
5. [V1.7.2 → V1.7.3 reliability/audit hardening note](docs/product/v1.7.2-to-v1.7.3-reliability-audit-hardening-change-note.md) — Run-first lifecycle, restart/concurrency safety and source/package hardening.
6. [V1.7.3 Owner runtime isolation hotfix](docs/product/v1.7.3-owner-runtime-isolation-hotfix.md) — prevents deterministic test-stack contamination and binds model Evidence/Fact IDs to the current run.
7. [V1.7.1 → V1.7.2 workspace UX change note](docs/product/v1.7.1-to-v1.7.2-workspace-ux-change-note.md) — continuous research, history restore, audit hierarchy and Quality Lab demotion.
8. [V1.7 → V1.7.1 synthesis change note](docs/product/v1.7-to-v1.7.1-synthesis-change-note.md) — why the first V1.7 Owner Acceptance failed and how synthesis/fallback are separated.
9. [DECISIONS.md](DECISIONS.md) — product and architecture decisions, including RF-032 through RF-044.
10. [n8n integration](integrations/n8n/README.md) — V1.8.5 presentation on the stable V17 workflow route.
11. [PORTFOLIO.md](PORTFOLIO.md) — project positioning and historical evidence.

## Non-goals

V1.8.5 does not provide trading, order execution, price targets, portfolio optimization, real-time market-data infrastructure, Bloomberg-scale proprietary coverage, unrestricted global-market support, open-ended self-modification or investment recommendations.
