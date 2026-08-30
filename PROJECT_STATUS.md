# ResearchForge Project Status

Last updated: 2026-08-30

Machine-readable mirror: [`project-status.json`](project-status.json)

## Current Position

- Scope: V1.3 active baseline (V1.2 retained as history)
- Contract package: 1.3.0
- Completed gate: C0 Contract Readiness
- Current gate: G0 Research Skill and Financial Foundations
- Runtime status: not started
- Work in progress: none
- V1.3 independent review: PASS
- LangGraph decision: retained as bounded single-agent orchestration (RF-007)

## Resume in Five Minutes

1. Read this file.
2. Read [`docs/product/researchforge-v1.3-scope.md`](docs/product/researchforge-v1.3-scope.md).
3. Read [`DECISIONS.md`](DECISIONS.md), especially open decisions RF-004 and RF-006.
4. Run `python3 scripts/validate_contracts.py`.
5. Open [`docs/contracts/data-source-acceptance.md`](docs/contracts/data-source-acceptance.md) and start only the single next action below.

## Single Next Action

Run a time-boxed data-source feasibility spike and complete the Candidate A/B scorecard in `data-source-acceptance.md`.

Expected evidence:

- one structured financial-data candidate;
- one official filing source;
- two candidate companies with four comparable periods;
- sampled metric reconciliation against official filings;
- licensing, cost, latency, and point-in-time notes;
- an explicit ACCEPT / REJECT / FIXTURE-ONLY decision.

Do not start FastAPI, LangGraph runtime code, PostgreSQL, pgvector, React, or visual design before this decision. Data feasibility is the current critical path. After G0 source acceptance, LangGraph enters at L1 under `research-workflow.md`.

## Open Blockers

| ID | Blocker | Blocks | Required owner action |
|---|---|---|---|
| B-001 | Structured financial-data source and license are not selected | G0 | Run the source spike and choose/reject a provider |
| B-002 | First company universe is not frozen | Golden cases | Select two thin-slice companies, then expand to 4–6 for Benchmark |

RF-005 is resolved in V1.3: L1/L2 use immutable file artifacts; the full product has five core records plus `source_documents`, `evidence_chunks`, and `run_artifacts`, with pgvector conditional on retrieval evidence.

## Current Success Ladder

| Level | Outcome | Status |
|---|---|---|
| L0 Contract Ready | Scope, schemas, methods, experiment rules, validation | complete |
| L1 Resume Ready | Deterministic tools + one LangGraph CLI/API research report + tests | not started |
| L2 Demo Ready | Verifier + trace + replayable Skill Lab story | not started |
| L3 Differentiated | Controlled no-cluster/rejection/supported outcome | not started |
| L4 Full V1.3 | Five modes, two-page UI, Docker, CI, measured demo | not started |

Stopping at L1 or L2 still produces a legitimate portfolio artifact. It must not be described as completed self-evolution unless L3 evidence exists.

## Last Verification

```text
python3 scripts/validate_contracts.py
PASS: 11 current + 10 historical schemas, 252 references,
      4 current examples, historical V1.2 artifacts, project checkpoint,
      23 links, 30 required files, and insufficient-data regression

Independent completion reviewer
V1.3 upgrade review: PASS (Review 2; no required work remains)
Initial scaffold review: PASS
```

## End-of-Session Rule

Before stopping any future work session:

1. update this file and `project-status.json`;
2. record accepted/rejected choices in `DECISIONS.md`;
3. leave exactly one concrete next action;
4. record the last passing verification command;
5. create the Workspace-required Codex review file.
