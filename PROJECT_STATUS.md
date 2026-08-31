# ResearchForge Project Status

Last updated: 2026-08-31

Machine-readable mirror: [`project-status.json`](project-status.json)

## Current Position

- Scope: V1.4 active baseline (V1.2/V1.3 retained as history)
- Contract package: 1.4.0
- Historical completed gate: V1.3 C0 Contract Readiness
- Completed gate: C0 V1.4 Contract Readiness
- Completed gate: G0 Research Skill and Financial Foundations
- Current gate: G1_THIN / L1 Resume Ready
- Runtime status: deterministic financial domain and public-safe G0 fixture package accepted; application thin slice is starting
- Work in progress: content-addressed storage, bounded LangGraph workflow, CLI and asynchronous research API
- V1.4 C0 independent review: PASS
- V1.4 G0 independent review: PASS
- LangGraph decision: retained as bounded single-agent orchestration (RF-007)

## Resume in Five Minutes

1. Read this file.
2. Read [`docs/product/researchforge-v1.4-scope.md`](docs/product/researchforge-v1.4-scope.md).
3. Read [`docs/product/v1.3-to-v1.4-change-note.md`](docs/product/v1.3-to-v1.4-change-note.md) and [`DECISIONS.md`](DECISIONS.md).
4. Run `python3 scripts/validate_contracts.py`.
5. Open [`docs/contracts/research-workflow.md`](docs/contracts/research-workflow.md) and start only the single next action below.

## Single Next Action

Implement one earnings-quality case through the complete L1 path: deterministic fixture retrieval, calculations, one bounded LangGraph workflow, immutable file artifacts, CLI and asynchronous API.

Expected evidence:

- the same application services work without LangGraph in unit tests;
- one earnings-quality run reaches a schema-valid result from the frozen G0 fixture package;
- all immutable run artifacts are addressable by SHA-256 and the trace is replayable;
- CLI and API use the same workflow and return only persisted artifacts;
- the OpenAI adapter has an offline fake for tests and refuses calls that would exceed the budget.

Do not broaden to five modes, PostgreSQL or the UI until this vertical slice passes independently.

## Open Blockers

None. A rotated OpenAI key will be needed for later live-model calibration, but offline engineering is not blocked by it.

RF-005 is resolved in V1.4: L1/L2 use immutable file artifacts; the full product has five core records plus `source_documents`, `evidence_chunks`, and `run_artifacts`, with pgvector conditional on retrieval evidence.

## Current Success Ladder

| Level | Outcome | Status |
|---|---|---|
| L0 Contract Ready | V1.4 scope, 19 schemas, methods, experiment rules, validation | complete |
| L1 Resume Ready | Deterministic tools + one LangGraph CLI/API research report + tests | in progress |
| L2 Demo Ready | Verifier + trace + replayable Skill Lab story | not started |
| L3 Research Supported | Adopted Candidate plus supported sealed result | not started |
| L4 Full Engineering Product | Five modes, two-page UI, Docker, CI, three labeled simulations | not started |

Stopping at L1 or L2 still produces a legitimate portfolio artifact. It must not be described as completed self-evolution unless L3 evidence exists.

## Last Verification

```text
uv lock --check && uv run python scripts/build_g0_fixtures.py
PASS: 68 packages resolved; 8 Source Documents and 48 Financial Facts reproduced from hash-verified local filings

uv run ruff format --check . && uv run ruff check . && uv run mypy --strict src scripts tests && uv run pytest -q
PASS: 46 files formatted; lint and strict typing clean; 69 tests passed

uv run python scripts/validate_contracts.py && git diff --check
PASS: 19/11/10 schemas, 12/4/1 examples, Seed Skill hash, G0 8/48/3 package, 49 local links, 61 required files, and diff whitespace

secret-pattern scan and git-ignore check
PASS: no sk-proj pattern in project files; raw filing PDFs remain ignored

Independent completion reviewer
V1.4 G0 review: PASS — non-adjacent YoY correction independently verified; no remaining findings
V1.4 C0 review: PASS — no required corrections
V1.3 upgrade review: PASS
```

## End-of-Session Rule

Before stopping any future work session:

1. update this file and `project-status.json`;
2. record accepted/rejected choices in `DECISIONS.md`;
3. leave exactly one concrete next action;
4. record the last passing verification command;
5. create the Workspace-required Codex review file.
