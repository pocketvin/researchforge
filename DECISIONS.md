# ResearchForge Decision Log

This file records decisions that materially affect scope, architecture, data, evaluation, cost, or delivery. Chat history is not a durable decision record.

## Status Legend

- **ACCEPTED**: binding until replaced by a later decision.
- **PROPOSED**: preferred option, awaiting implementation evidence or owner confirmation.
- **REJECTED**: considered and intentionally not used.
- **SUPERSEDED**: replaced by another decision.

## Decision Index

| ID | Decision | Status | Date | Blocks |
|---|---|---|---|---|
| RF-001 | Contract-first implementation | ACCEPTED | 2026-08-29 | — |
| RF-002 | Staged personal-success ladder | ACCEPTED | 2026-08-29 | — |
| RF-003 | Portfolio MVP before full V1.3 breadth | ACCEPTED | 2026-08-29 | — |
| RF-004 | Structured and filing data sources | PROPOSED | 2026-08-29 | G0 |
| RF-005 | Evidence persistence and pgvector timing | ACCEPTED | 2026-08-30 | — |
| RF-006 | Initial company universe | SUPERSEDED | 2026-08-29 | — |
| RF-007 | Bounded LangGraph orchestration | ACCEPTED | 2026-08-30 | — |
| RF-008 | Upgrade the active scope to V1.3 | ACCEPTED | 2026-08-30 | — |
| RF-009 | Upgrade the active scope to V1.4 | ACCEPTED | 2026-08-30 | — |
| RF-010 | Replace the human pilot with labeled simulations | ACCEPTED | 2026-08-30 | — |
| RF-011 | OpenAI model and USD 20 budget boundary | ACCEPTED | 2026-08-30 | — |
| RF-012 | Primary and contingency experiment suites | ACCEPTED | 2026-08-30 | G0 evidence |

## RF-001 — Contract-First Implementation

Status: **ACCEPTED**

Decision:

Persisted artifacts and APIs must conform to the versioned schemas and semantic contracts before feature breadth is added.

Why:

Financial-period mistakes, benchmark leakage, unverifiable claims, and silent scope expansion are more expensive to repair after the UI and orchestration are built.

Consequence:

The first runtime work is deterministic data/financial tooling and a vertical slice, not the final interface.

## RF-002 — Staged Personal-Success Ladder

Status: **ACCEPTED**

Decision:

Treat L1 Resume Ready, L2 Demo Ready, L3 Differentiated, and L4 Full V1.3 as independently valuable delivery levels.

Why:

A solo project can fail because all value is deferred until the hardest research claim. Earlier honest milestones preserve motivation and produce usable interview evidence.

Consequence:

Each level must be demonstrable and truthfully describable without claiming later capabilities.

## RF-003 — Portfolio MVP Before Full Product Breadth

Status: **ACCEPTED**

Decision:

Build one earnings-quality company-research thin slice first. It may use frozen local evidence packages and a CLI or single API endpoint. The five task modes and two-page UI remain required for full V1.3, not for L1.

Why:

This sequence validates data normalization, deterministic tools, citations, and the Research Procedure before investing in broad UI and infrastructure.

Consequence:

No task mode is deleted from V1.3; it is only sequenced later.

## RF-004 — Data Sources

Status: **PROPOSED**

Preferred direction:

- structured facts from one provider that passes `data-source-acceptance.md`;
- filings from an official exchange/company source;
- frozen local packages for Benchmark and repeatable public demos.

Open evidence:

- licensing and redistribution rights;
- historical publication timestamps;
- A-share YTD/discrete semantics;
- metric coverage, cost, and reliability.

Decision rule:

Do not accept a provider from feature lists alone. Run the two-company/four-period spike first.

## RF-005 — Evidence Persistence and pgvector Timing

Status: **ACCEPTED**

Preferred direction:

1. L1/L2 use immutable file-backed source documents, evidence chunks, and run artifacts with deterministic retrieval.
2. Full V1.3 may map five core records plus `source_documents`, `evidence_chunks`, and `run_artifacts` to PostgreSQL/object storage.
3. pgvector is an optional index on `evidence_chunks` only after a frozen retrieval evaluation demonstrates value.

Reason:

This prevents database work from blocking the first useful report while making evidence persistence explicit. It resolves the V1.2 five-object ambiguity without turning retrieval infrastructure into a product goal.

Escalation:

Any further logical record requires an explicit decision and migration evidence. Do not hide a scope change behind an ORM migration.

## RF-006 — Initial Company Universe

Status: **SUPERSEDED** by RF-012

Preferred direction:

- Thin slice: two same-market, same-currency companies with comparable reporting periods and text-readable official filings.
- Formal Benchmark: expand to 4–6 companies only after G0 data and formula tests pass.

Candidate pair:

CATL and EVE Energy are suitable narrative candidates from the frozen demo, but they are not approved until source availability and metric reconciliation pass.

RF-012 replaces this open-ended proposal with fixed primary and contingency suites. G0 still decides whether each fixed company has sufficient source/provenance evidence; it does not choose a different universe silently.

## RF-007 — Bounded LangGraph Orchestration

Status: **ACCEPTED**

Decision:

Keep LangGraph in L1 and the full product as the one Research Agent's workflow engine. Use it for typed state, stable stages, conditional degradation, checkpoint/resume, one bounded structure-repair route, and audit events.

Do not use it for financial formulas, period semantics, retrieval algorithms, verifier policy, storage meaning, multiple agents, or the Evolution pipeline.

Why:

This preserves a relevant agent-engineering technology and makes a genuinely conditional workflow inspectable, while keeping domain logic portable and easy to test.

Consequence:

The graph is versioned and pinned. Graph nodes remain thin adapters around plain application/domain services. Base, Seed, and Candidate comparisons use the same graph version so orchestration cannot confound the experiment.

## RF-008 — Upgrade the Active Scope to V1.3

Status: **ACCEPTED**

Decision:

Supersede the V1.2 frozen scope with `docs/product/researchforge-v1.3-scope.md` and contract package 1.3.0. Preserve V1.2 scope and schemas as immutable historical evidence.

V1.3 formalizes staged product success, the G0 data-source decision, bounded LangGraph orchestration, a Workflow Trace artifact, explicit supporting evidence storage, conditional pgvector adoption, product-usefulness evidence, and schema-valid project resumption.

Why:

These changes directly improve feasibility, portfolio value, usefulness, completeness, and solo recoverability without adding a new research task or widening the Evolution target.

Consequence:

New artifacts use `schema_version: 1.3.0` and `schemas/v1.3/`. V1.2 artifacts are never silently interpreted as V1.3; any later migration creates a new artifact and preserves original provenance.

## RF-009 — Upgrade the Active Scope to V1.4

Status: **ACCEPTED**

Decision:

Supersede V1.3 with the active V1.4 scope and contract package `1.4.0`. Preserve the V1.3 scope, schemas, examples, and Git baseline as immutable history.

Reason:

The owner changed both the success-evidence meaning and the project completion rule. This is a minor contract change, not a clarification.

Consequence:

New artifacts use `schema_version: 1.4.0`. Any migration creates a new artifact and retains the V1.3 source hash.

## RF-010 — Labeled Simulations Instead of a Human Pilot

Status: **ACCEPTED**

Decision:

G4 requires exactly three isolated simulated-usability sessions. Every record uses `evidence_label: SIMULATED` and `human_user_value_validated: false`.

Reason:

The owner explicitly removed real-user recruitment from the project.

Consequence:

The final engineering label is `V1.4 Full Engineering Product Ready`. Documentation MUST state that human usefulness and market demand were not validated.

## RF-011 — OpenAI Model and Budget Boundary

Status: **ACCEPTED**

Decision:

Use the OpenAI Responses API with `store: false`, Structured Outputs, no built-in tools, `gpt-5.6-luna`, medium reasoning, and a USD 20 aggregate cap. `gpt-5.4-mini` is allowed only as a pre-formal-run fallback.

Budget:

- USD 1 calibration;
- USD 9 primary experiment;
- USD 6 contingency reserve;
- USD 2 simulations;
- USD 2 safety reserve.

Consequence:

A real request is rejected before dispatch if its worst-case estimate would breach the aggregate cap. Model/configuration changes after formal runs begin invalidate the experiment.

## RF-012 — Primary and Contingency Experiment Suites

Status: **ACCEPTED**

Decision:

- Primary V1.4: CATL and EVE Energy for Evolution, Gotion High-Tech for Validation, and Sunwoda for Final Test.
- Contingency V1.5: Great Power, Farasis Energy, BYD, and Zhuhai CosMX in a wholly disjoint pre-frozen suite.
- Six target reports per company: 2023Q3, 2023FY, 2024Q1, 2024H1, 2024Q3, and 2024FY.

Consequence:

Company inclusion still must pass G0 source/provenance evidence. Replacing a company or report period requires a new decision before any formal run. At most one contingency experiment may run after an unsupported primary result.
