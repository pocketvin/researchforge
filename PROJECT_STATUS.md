# ResearchForge Project Status

Last updated: 2026-08-30

Machine-readable mirror: [`project-status.json`](project-status.json)

## Current Position

- Scope: V1.4 active baseline (V1.2/V1.3 retained as history)
- Contract package: 1.4.0
- Historical completed gate: V1.3 C0 Contract Readiness
- Completed gate: C0 V1.4 Contract Readiness
- Current gate: G0 Research Skill and Financial Foundations
- Runtime status: not started
- Work in progress: time-boxed data-source feasibility spike
- V1.4 C0 independent review: PASS
- LangGraph decision: retained as bounded single-agent orchestration (RF-007)

## Resume in Five Minutes

1. Read this file.
2. Read [`docs/product/researchforge-v1.4-scope.md`](docs/product/researchforge-v1.4-scope.md).
3. Read [`docs/product/v1.3-to-v1.4-change-note.md`](docs/product/v1.3-to-v1.4-change-note.md) and [`DECISIONS.md`](DECISIONS.md).
4. Run `python3 scripts/validate_contracts.py`.
5. Open [`docs/contracts/data-source-acceptance.md`](docs/contracts/data-source-acceptance.md) and start only the single next action below.

## Single Next Action

Complete the identity, access, license, and official-source rows for the fixed A-share source package, then reconcile the first 20-fact sample.

Expected evidence:

- one official filing source and one structured reconciliation candidate are documented;
- at least 20 facts carry complete period, scope, unit, publication-time, and locator semantics;
- numeric reconciliation meets the documented threshold with exact denominators;
- public packaging and redistribution limits are explicit;
- RF-004 records `ACCEPT`, `FIXTURE-ONLY`, or `REJECT` and the owner signs the sample.

Do not start application infrastructure until the source decision is recorded. The default intended result remains `FIXTURE-ONLY`; a provider is not accepted from feature claims alone.

## Open Blockers

| ID | Blocker | Blocks | Required owner action |
|---|---|---|---|
| B-002 | Selected companies and official-source packages are not yet reconciled | G0 | Run the source spike and record FIXTURE-ONLY/REJECT evidence |

RF-005 is resolved in V1.4: L1/L2 use immutable file artifacts; the full product has five core records plus `source_documents`, `evidence_chunks`, and `run_artifacts`, with pgvector conditional on retrieval evidence.

## Current Success Ladder

| Level | Outcome | Status |
|---|---|---|
| L0 Contract Ready | V1.4 scope, 19 schemas, methods, experiment rules, validation | complete |
| L1 Resume Ready | Deterministic tools + one LangGraph CLI/API research report + tests | not started |
| L2 Demo Ready | Verifier + trace + replayable Skill Lab story | not started |
| L3 Research Supported | Adopted Candidate plus supported sealed result | not started |
| L4 Full Engineering Product | Five modes, two-page UI, Docker, CI, three labeled simulations | not started |

Stopping at L1 or L2 still produces a legitimate portfolio artifact. It must not be described as completed self-evolution unless L3 evidence exists.

## Last Verification

```text
git show --stat --oneline HEAD
PASS: V1.3 accepted baseline preserved in commit 9532f2f

uv lock --check && uv run --no-sync python scripts/validate_contracts.py
PASS: 68 packages resolved; 19/11/10 schemas and 12/4/1 examples validated

uv run ruff format --check . && uv run ruff check . && uv run mypy src scripts && uv run pytest
PASS: format and lint clean; strict mypy clean; 4 tests passed

Independent completion reviewer
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
