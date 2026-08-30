# Implementation Blueprint

This blueprint sequences the active V1.3 architecture for a solo implementation. It does not replace the product scope or semantic contracts.

## Two Delivery Shapes

### Portfolio MVP — L1/L2

- Python domain and application services;
- one FastAPI endpoint plus CLI entry point;
- one single-agent LangGraph workflow;
- Pydantic validation at process boundaries;
- frozen facts/evidence packages and deterministic retrieval;
- exported JSON artifacts and traces;
- no database or UI required for L1.

### Full V1.3 — L4

- the same domain and workflow expanded to five task types;
- PostgreSQL for core records and supporting provenance/artifact records;
- pgvector only if retrieval evaluation justifies it;
- React/TypeScript Research and Skill Lab pages;
- Docker Compose and CI.

The MVP is a staging point, not a different product architecture.

## Target Repository Shape

```text
backend/
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
- `POST /v1/research-runs/{run_id}/cancel` — best-effort cancellation.

Skill Lab and Evolution endpoints are added only at G3/G4. Endpoint names are implementation guidance; artifact semantics remain governed by the schemas.

## Storage Strategy

L1/L2 use content-hashed directories for fixtures, run artifacts, and trace events. This makes the thin slice reproducible without inventing database tables.

Full V1.3 preserves five core product/experiment records:

```text
cases
runs
skill_versions
evolution_runs
evaluations
```

V1.3 adds three supporting provenance/artifact records:

```text
source_documents
evidence_chunks
run_artifacts
```

L1/L2 keep these in immutable file packages referenced by hash. Full V1.3 may persist them in PostgreSQL/object storage. An optional pgvector column/index belongs to `evidence_chunks` and is introduced only after retrieval evaluation.

## Complexity Decision Rules

Add a component only if all are true:

1. a current gate criterion cannot be met without it;
2. a smaller in-process or file-backed option was evaluated;
3. its owner, failure mode, test, and removal path are documented;
4. the decision is recorded in `DECISIONS.md`.

V1.3 explicitly avoids distributed queues, multiple agents, agent debate, dynamic graph mutation, open-ended prompt optimization, and a general observability platform.
