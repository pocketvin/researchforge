# ResearchForge V2 — Filing Research Workspace

Status: ACTIVE PRODUCT RUNTIME; final held-out Owner Acceptance not established. Owner-authorized V2 scope began 2026-09-10.

## Product contract

Build a single research agent over complete official financial filings. The model chooses
search/read/inspect/calculate/hypothesis actions and decides when to submit findings.
Deterministic services own company identity, source/time boundaries, financial semantics,
calculations, evidence identity, persistence, and operational limits. A separate writing phase
uses the research dossier, then structural/financial checks and separately labeled semantic
review precede the web report. No model or validator guarantees universal correctness.

### Included

- Original PDF/HTML retained by hash; document, page, section, table, figure, footnote,
  text chunk, verified fact and calculation are independently addressable.
- Whole-document access through bounded reads; initial retrieval is only a seed.
- Tables retain cells/headers/units/footnote relations and bounding boxes where recovered.
  Native extraction first; page-image inspection is an explicit capability. Model-read numbers
  are candidates, not automatically verified canonical facts. Missing/ambiguous structure is
  exposed as a coverage issue, never silently discarded or fabricated.
- One LangGraph research loop with callable filing tools, an explicit hypothesis/evidence/
  open-question state, and a model-authored stop decision. Operational deadline/budget/context
  limits are abort safeguards, not routine step-count stopping rules.
- Financial formula registry owns period/scope/currency/restatement contracts. Existing
  Decimal formulas are reused before adding more. Verified Statement Series can promote a bounded
  native table row into run-owned multi-period numeric inputs without copying model arithmetic.
  Third-party arithmetic is never the authority for financial meaning. Missing inputs yield
  unavailable/not_meaningful/unreliable.
- Durable live events, genuine timed spans and source-linked outputs. Product timeline and
  developer audit are two views of the same records. No hidden chain-of-thought in public
  trace, logs or artifacts.
- Answer-first Web Report with source drawer, tables, hypotheses, limitations and live trace.
  No invented financial charts, confidence percentages, completion percentages or quality scores.
- Regression gates and quality acceptance are separate. Reference-backed coverage/accuracy remains
  available for development benchmarks, while held-out owner acceptance may be reference-free: unseen
  inputs are frozen and the human only makes a blind pairwise or meets-standard choice after Runs
  terminate. Model judgments remain fallible and are never promoted to hidden ground truth.

### Explicitly deferred or excluded

No external news/open-web/industry research; no Slides/PPT; no multi-agent debate, arbitrary
shell/Python/SQL tools, trading, recommendations, target prices, batch screening or universal
valuation engine. No new formal Evolution experiment. Research threads/monitoring are future
extensions, not implied by independent runs. Do not rewrite frozen V1 artifacts or claim V2
quality improvements until a fair benchmark supports them.

## Inputs and outputs

| Boundary | Input | Output |
| --- | --- | --- |
| Intake | company, market, period, question, cutoff, idempotency key | persisted queued Run |
| Resolve | query + cutoff | unique official issuer + permitted filing |
| Acquire | validated filing URL | bounded bytes + SHA-256 + publication/retrieval metadata |
| Environment | raw filing + source metadata | page/section/table/image/chunk catalog, verified facts, extraction gaps |
| Bootstrap | question + environment | catalog, alias/statement-aware seed evidence, facts, tool definitions; no final evidence restriction |
| Agent | compact state + recent tool observations | requested function calls or a submission dossier |
| Tool executor | validated arguments + run-owned environment | typed result, artifact IDs, event/span, state change |
| Synthesis | dossier + cited evidence/facts/calculations | strict report draft |
| Validation | draft + immutable source registry | per-check verdicts; failures or explicit limitations |
| Quality eval | frozen case/trajectory/report + separate labels | measured metrics or null/not_scored |
| Product | report + persisted events + source artifacts | report, research timeline, evidence drawer, audit data |

Every cited item remains readable after failures and restarts. Persistence is continuous,
not merely a final stage. SSE transports durable events with replay cursor; it does not own
truth or cancel work on browser disconnect. Final report persistence precedes terminal success.
Expensive benchmark/judge runs are separate from every user request's validation.

## Runtime and migration

V2 is now the sole live research runtime. `/` is the canonical Web surface, `/research/v2` is only
a Web alias, and all new research creation goes through `/v2/research-runs`. CLI, MCP and n8n are
thin clients/transports over that same service; no V1 ResearchRunService or second research engine
is started. Runtime source/cache/persistence live under `artifacts/v2/`. The product container no
longer carries PostgreSQL/Alembic or V1 reviewed-package/fixture/benchmark data.

The useful V1-era primitives were retained as shared modules: official issuer/filing discovery,
source security, PDF/HTML/XBRL extraction, deterministic finance/domain semantics, CAS/file locking
and durable checkpoints. Frozen V1 schemas, evidence, reviewed packages, old Runs and n8n workflow
JSON remain immutable audit history only; they are never product fallback data and no `/v1` live
research API is exposed.

Work directory: `/Users/yu0/Workspace/10-Projects/ResearchForge/artifacts/v2-implementation/work`.
Verification outputs: `/Users/yu0/Workspace/10-Projects/ResearchForge/artifacts/v2-implementation/outputs`.
Canonical project deliverables: source, tests, `docs/architecture`, `docs/product`, `schemas/v2`.

## Verification and incremental delivery

1. Versioned contracts + original document environment + durable trace/tool boundary.
2. Real provider-routed function calling inside checkpointed LangGraph; working objectives/
   hypotheses, semantic completion, visible provider fallback and repeatable tool observations.
3. Synthesis/validation/source-linked web report, SSE reconnect/history/cancel behavior.
4. Reference-backed evaluation suite: independent expected facts, evidence alternatives,
   key findings, counter-evidence and acceptable uncertainty; dev/validation/held-out isolation.
5. Harden multimodal table extraction, numerical promotion, context recovery and live quality.

All stages require actual tests and explicit remaining limitations. Stage names or test counts
alone are not evidence of research quality. Active V2 progress is maintained in PROJECT_STATUS.md
and the V2 implementation/benchmark artifacts; the frozen V1 `project-status.json` is not extended
with V2-only fields. Implementation may change while the historical V1 contract stays fixed.

## Technical references checked 2026-09-10

- OpenAI Responses function calling: https://developers.openai.com/api/docs/guides/function-calling
- LangGraph streaming: https://docs.langchain.com/oss/python/langgraph/streaming
- pypdf extraction limitations: https://pypdf.readthedocs.io/en/stable/user/extract-text.html
