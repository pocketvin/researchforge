# G1 Earnings-Quality Thin-Slice Evidence

Evidence date: `2026-08-31`

Status: `SUPERSEDED_BY_G1_FULL_LOCAL_EVIDENCE`

## Outcome

One zero-cost `filing_analysis` request for CATL 2024H1 now runs through the stable ten-stage LangGraph and produces a persisted V1.4 Run Manifest, Research Result, Workflow Trace, explicit plan and four Calculation Records. The default path uses a deterministic conclusion adapter and never reads an API key or contacts a provider.

## Implemented Boundaries

- Plain Python loads only owner-signed G0 facts available by `research_time`.
- `Decimal` formulas compute gross profit, gross margin, cash conversion and the frozen profit/cash divergence signal.
- LangGraph orchestrates the ten named stages and the insufficient-data/structured-output branches; it does not own formulas, storage or budget policy.
- Immutable JSON objects use canonical serialization and SHA-256 paths; mutable run and idempotency pointers contain only hashes and lifecycle linkage.
- CLI and FastAPI share `ResearchRunService` and return persisted artifacts.
- Same idempotency key plus same input returns the original run; a changed input returns `409`.
- One structure-only repair reuses the same analysis context; a second invalid output fails with `OUTPUT_SCHEMA_INVALID` and no Research Result.
- The OpenAI Responses adapter is present but not active in the zero-cost path. Its no-network tests assert `gpt-5.6-luna`, medium reasoning, `store: false`, no tools, strict JSON Schema output, and budget refusal before provider contact.

## Frozen Smoke Case

```text
task_type: filing_analysis
company_id: cn_300750
period: 2024H1
research_time: 2024-08-01T00:00:00+08:00
question: 2024年上半年利润是否转化为经营现金流?
```

The run loads six normalized facts and one source-document locator. It deterministically calculates cash conversion at approximately `1.96x`, gross margin at approximately `26.53%`, and no triggered frozen profit/cash divergence rule. It records that no additional counter-evidence was found in the bounded package and explicitly limits the result because announcement full text was not searched.

## Verification

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy --strict src scripts tests
uv run pytest -q
uv run python scripts/validate_contracts.py
```

Local result before independent review: 96 tests passed. Runtime tests validate generated Manifest, Result, Trace and Calculation Records against the V1.4 schemas.

## Superseding Evidence

Persistent checkpoint recovery, active cancellation, timeouts, deterministic verification, five-mode breadth, PostgreSQL indexing, UI, Docker/CI definitions, and controlled Evolution preregistration were implemented after this snapshot. See [`g1-full-reliability.md`](g1-full-reliability.md), [`g2-verifier.md`](g2-verifier.md), and [`g4-engineering-progress.md`](g4-engineering-progress.md). Product completion and final independent acceptance remain pending.
