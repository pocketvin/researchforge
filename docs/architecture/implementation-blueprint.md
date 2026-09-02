# Implementation Blueprint

This blueprint sequences the active V1.4 architecture for a solo implementation. It does not replace the product scope or semantic contracts.

## Two Delivery Shapes

### Portfolio MVP — L1/L2

- Python domain and application services;
- one FastAPI endpoint plus CLI entry point;
- one single-agent LangGraph workflow;
- Pydantic validation at process boundaries;
- frozen facts/evidence packages and deterministic retrieval;
- exported JSON artifacts and traces;
- no database or UI required for L1.

### Full V1.4 — L4

- the same domain and workflow expanded to five task types;
- PostgreSQL for core records and supporting provenance/artifact records;
- pgvector only if retrieval evaluation justifies it;
- React/TypeScript Research and Skill Lab pages;
- Docker Compose and CI.

The MVP is a staging point, not a different product architecture.

## Target Repository Shape

```text
src/
  researchforge/
    domain/          # facts, periods, formulas, claims; no framework imports
    application/     # use cases, ports, limits, artifact assembly
    workflow/        # LangGraph topology, typed state, node adapters
    adapters/        # data, filing, model, storage implementations
    api/             # FastAPI transport
tests/
frontend/            # introduced after the core evidence exists
skills/
  fundamental-research/
benchmarks/
infra/
examples/
schemas/
```

## Dependency Boundaries

```text
API / CLI
   ↓
Application use case
   ↓
LangGraph orchestration ──→ ports/interfaces
   ↓                          ↓
Plain domain services      external adapters
   ↓
Schema-valid artifacts
```

- Domain code MUST NOT import FastAPI, LangGraph, database clients, or model SDKs.
- Workflow nodes MUST be thin adapters around application/domain services.
- Model output MUST cross a structured validation boundary before it changes graph state.
- Retrieval, calculations, and verification MUST be callable and testable without running the graph.
- Persist only artifact IDs and concise audit summaries in graph state; licensed raw documents and hidden reasoning do not belong there.

## LangGraph's Exact Role

LangGraph remains a visible part of the project because the workflow has conditional degradation, cancellation/limits, one controlled output-repair loop, and an auditable stage trace. It is not used to create multiple agents.

The graph follows the stable stages in `research-workflow.md`:

```text
understand → plan → load facts → retrieve evidence → calculate
→ cross-check → counter-evidence → synthesize → validate → finish
```

Each run records explicit workflow engine, graph, and checkpoint schema versions and links a Workflow Trace. The Evolution pipeline remains ordinary Python as required by the product scope.

## Minimal API

The first runtime needs only:

- `POST /v1/research-runs` — validate and create one immutable run;
- `GET /v1/research-runs/{run_id}` — lifecycle, progress, limits, and failure;
- `GET /v1/research-runs/{run_id}/result` — schema-valid result after success;
- `GET /v1/research-runs/{run_id}/trace` — sanitized Workflow Trace after the run starts;
- `GET /v1/research-runs/{run_id}/facts` — normalized facts used by the run;
- `GET /v1/research-runs/{run_id}/evidence` — persisted evidence chunks referenced by claims;
- `GET /v1/research-runs/{run_id}/calculations` — deterministic calculation records;
- `POST /v1/research-runs/{run_id}/cancel` — best-effort cancellation;
- `GET /v1/catalog` — allowlisted companies, periods, and task capabilities.

`POST /v1/research-runs` accepts task type, question, one or two company IDs, requested period labels, research time, and an idempotency key. It returns `202` plus status/result/trace links. Audit resources are immutable after a successful run and are consumed by the Research page without reconstructing values in the browser. A pending result returns `425`; a terminal state without a Research Result returns `409` and the structured failure. Reusing a key with different input returns `409`.

Evolution is started only through a controlled CLI. Skill Lab reads:

- `GET /v1/evolution-experiments/{experiment_id}`;
- `GET /v1/evolution-experiments/{experiment_id}/artifacts/{kind}`.

Skill Lab and Evolution endpoints are added only at G3/G4. Endpoint names are implementation guidance; artifact semantics remain governed by the schemas.

## Storage Strategy

L1/L2 use content-hashed directories for fixtures, run artifacts, and trace events. This makes the thin slice reproducible without inventing database tables.

Full V1.4 preserves five core product/experiment records:

```text
cases
runs
skill_versions
evolution_runs
evaluations
```

V1.4 adds three supporting provenance/artifact records:

```text
source_documents
evidence_chunks
run_artifacts
```

L1/L2 keep these in immutable file packages referenced by hash. Full V1.4 may persist them in PostgreSQL/object storage. An optional pgvector column/index belongs to `evidence_chunks` and is introduced only after retrieval evaluation.

Semantic retrieval is adopted only when frozen evidence shows Recall@5 improves by at least `0.10`, introduces zero new citation mismatches, and keeps p95 latency at or below `2×` the deterministic baseline. Otherwise deterministic section/keyword retrieval remains final.

## Model and Cost Boundary

- OpenAI Responses API only; `store: false` and JSON Schema Structured Outputs.
- `gpt-5.6-luna`, medium reasoning, no built-in tools, 4,000 output-token cap.
- A formal run configuration is immutable; `gpt-5.4-mini` is a pre-formal-run-only availability fallback.
- Calibration/primary/contingency/simulation/safety allocations are USD 1/9/6/2/2.
- The adapter reserves worst-case request cost atomically and refuses dispatch if aggregate reserved plus spent cost could exceed USD 20.

## Complexity Decision Rules

Add a component only if all are true:

1. a current gate criterion cannot be met without it;
2. a smaller in-process or file-backed option was evaluated;
3. its owner, failure mode, test, and removal path are documented;
4. the decision is recorded in `DECISIONS.md`.

V1.4 explicitly avoids distributed queues, multiple agents, agent debate, dynamic graph mutation, open-ended prompt optimization, and a general observability platform.
