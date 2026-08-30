# ResearchForge V1.4 — Active Product and Research Scope

## A Financial Research Agent with Verifiable Procedures and a Controlled Learning Experiment

- Status: **active V1.4 baseline**
- Contract package: **1.4.0**
- Supersedes: **V1.3 active baseline**
- Historical baselines: **V1.2 and V1.3 remain immutable**

Scope changes require an explicit decision and changelog entry. V1.4 implements the owner-approved completion plan: A-share frozen evidence, one OpenAI model, a hard USD 20 API cap, a public-safe repository, bounded LangGraph orchestration, and simulated rather than human usability evidence.

## 1. Product Definition

ResearchForge is a single-agent financial research system that:

1. answers bounded company fundamental-research questions using structured financial facts and filing evidence;
2. calculates important financial values with deterministic tools;
3. links material conclusions to point-in-time facts, evidence, counter-evidence searches, and limitations;
4. records a reproducible workflow trace;
5. tests whether repeated, verified earnings-quality omissions can produce a bounded Research Skill patch that improves held-out cases.

The product is research assistance, not investment advice. It does not predict prices, execute trades, optimize portfolios, or claim investment returns.

## 2. V1.4 Design Goals

V1.4 optimizes for:

- **feasibility:** disprove data and period-semantic risks before application infrastructure;
- **usefulness:** help a user understand what changed, why it matters, supporting and opposing evidence, and what remains unknown;
- **auditability:** every important claim resolves to immutable artifacts and a research-time cutoff;
- **career evidence:** each stage produces inspectable Python, agent, evaluation, or full-stack proof;
- **solo completion:** L1–L4 are independently valuable delivery levels;
- **controlled complexity:** one agent, one model, one core skill, one workflow graph, and one narrow Evolution target;
- **recoverability:** every work session ends with a schema-valid checkpoint and one next action.

V1.4 deliberately changes one V1.3 success rule. Three isolated AI simulations replace the three-person target-user pilot. These records MUST be labeled `SIMULATED`; they prove only an engineering usability check and MUST NOT be described as human validation or market demand.

## 3. Target User and Supported Context

Primary V1.4 users:

- finance learners and junior analysts who need an auditable company-research walkthrough;
- technical reviewers/interviewers evaluating agent, data, and experimentation engineering;
- the project owner running a local or controlled single-user demo.

V1.4 is not designed for professional trading desks, real-time market monitoring, broad consumer investing, or unattended production decisions.

## 4. Product and Research Success Are Separate

### Product Success

The system produces a useful, evidence-grounded company-research result under the contracts and measured product-success criteria.

V1.4 Product Success is an engineering label. Real target-user value remains unvalidated until a future human pilot is completed.

### Research Success

A repeated verified earnings-quality failure produces a bounded skill patch that passes paired Validation guardrails and improves the sealed Final Test target without catastrophic regression.

### Research Completion Requirement

The owner-selected project completion standard requires a `SUPPORTED` result. If the primary V1.4 experiment produces no eligible cluster or a rejected Candidate, all evidence is frozen and one V1.5 experiment MAY run against the pre-frozen, disjoint contingency suite. After two unsupported experiments, engineering work may be complete but the project is honestly blocked against its research completion target.

No threshold may be relaxed and no unsealed Final Test may be reused to manufacture success.

## 5. Product Task Scope

Full V1.4 supports the same five bounded research tasks:

1. **Company Fundamental Research** — revenue, profit, margins, cash flow, working capital, CapEx, debt/cash, changes, risks, and outlook limitations.
2. **Earnings/Filing Analysis** — material period changes, management explanations, contradictory evidence, and monitoring items.
3. **Peer Comparison** — two comparable companies using the same framework, periods, scope, and currency treatment.
4. **Thesis Investigation** — supporting evidence, counter evidence, alternative explanations, conclusion, uncertainty, and confidence.
5. **Risk/Anomaly Detection** — explainable signals such as profit/cash divergence, receivables/inventory growth, margin deterioration, CapEx acceleration, debt deterioration, and one-off contributions.

The implementation sequence starts with one earnings-quality thin slice. This sequences scope; it does not remove the other modes from full V1.4.

## 6. Delivery Levels

| Level | Required outcome | Claim unlocked |
|---|---|---|
| L0 Contract Ready | V1.4 scope, schemas, semantic contracts, validator, and checkpoint | Designed an auditable agent/experiment architecture |
| L1 Resume Ready | One LangGraph-orchestrated earnings-quality flow, deterministic tools, schema-valid report, tests | Built a working evidence-grounded research slice |
| L2 Demo Ready | Deterministic/coverage verifier, trace inspection, replayable failure | Built evaluation and auditable failure analysis |
| L3 Research Supported | Candidate adopted on Validation and improved the one sealed Final Test without catastrophic regression | Claim the bounded research hypothesis is supported for the frozen suite |
| L4 Full Engineering Product | Five modes, Research and Skill Lab pages, storage, Docker, CI, and three labeled simulations | Shipped the complete controlled engineering demo; human value remains unvalidated |

Each completed level remains usable if later work stops.

## 7. Portfolio MVP (L1)

L1 is deliberately small:

- one earnings-quality question;
- two source-compatible companies and four comparable periods;
- one accepted structured source or frozen reconciled fixture package;
- one official filing source;
- one CLI command and one FastAPI research-run resource (create/read/result/cancel);
- one single-agent LangGraph workflow;
- deterministic period normalization and financial tools;
- section/keyword evidence retrieval over immutable chunks;
- one Research Result, Run Manifest, Workflow Trace, and audit export;
- unit, schema, and thin-slice integration tests.

No React UI, PostgreSQL, pgvector, distributed queue, or Evolution implementation blocks L1.

## 8. Unified Single-Agent Workflow

All five task modes reuse one Research Procedure:

```text
understanding_question
→ planning
→ loading_financial_data
→ retrieving_evidence
→ calculating
→ cross_checking
→ searching_counter_evidence
→ forming_conclusion
→ validating_output
→ completed
```

Task configuration controls mandatory checks; it does not create five separate agents.

## 9. LangGraph Scope

LangGraph is retained as the Research workflow engine because the run has typed state, conditional degradation, cancellation/limits, checkpoint/resume, a bounded output-repair path, and an auditable stage trace.

LangGraph owns:

- stable stage transitions and conditional edges;
- graph checkpoint/resume and lifecycle coordination;
- calls to application services;
- sanitized progress and Workflow Trace events;
- one structured-output repair attempt inside the original budget.

LangGraph does not own:

- financial formulas or reporting-period semantics;
- data-provider normalization or retrieval ranking;
- verifier/evaluation policy;
- database meaning;
- skill mutation or the Evolution pipeline;
- hidden chain-of-thought;
- Planner/Researcher/Critic/Reviewer agents or agent debate.

Graph nodes remain thin, typed, independently testable adapters. The graph version is pinned and held constant in Base/Seed/Candidate comparisons.

## 10. Financial Correctness

Important calculations are deterministic and versioned. At minimum:

- unit/currency/scale normalization;
- reported versus derived facts;
- YTD-to-discrete-quarter derivation with parent provenance;
- growth, margin, cash conversion, working-capital, divergence, and peer-alignment checks;
- zero/negative/missing/incompatible period behavior;
- restatement and statement-scope handling.

The model may interpret calculated artifacts. It must not replace them with mental arithmetic or fill missing facts from memory.

## 11. Data and Evidence

G0 must choose `ACCEPT`, `FIXTURE-ONLY`, or `REJECT` through the data-source acceptance contract.

The default V1.4 outcome is `FIXTURE-ONLY`. Public packages contain normalized derived facts, short evidence only when publication is documented, hashes, locators, and official links. Full filing PDFs and uncertain-license payloads are not committed.

Every source records identity, license, retrieval time, publication time, point-in-time availability, content hash, company, period, statement scope, accounting standard, restatement state, currency/unit, and stable locator.

External filings are untrusted data. Instructions inside retrieved content cannot modify prompts, skills, tools, permissions, benchmarks, or policies.

Counter-evidence search is mandatory. A verified `not_found` search is valid; fabricated opposition is prohibited.

## 12. Retrieval Strategy

L1 uses deterministic section filters, keywords, metadata constraints, and stable evidence chunks. Retrieval results store scores/filters and source locators.

Semantic retrieval and pgvector are optional full-product adapters. They are adopted only if frozen retrieval evaluation demonstrates useful improvement over the deterministic baseline. Technology novelty is not an acceptance criterion.

## 13. Storage Model

V1.4 resolves the V1.2 evidence-persistence ambiguity.

Core experiment/product records:

```text
cases
runs
skill_versions
evolution_runs
evaluations
```

Supporting provenance/artifact records:

```text
source_documents
evidence_chunks
run_artifacts
```

L1/L2 may implement all of these as content-hashed files. Full V1.4 may map them to PostgreSQL/object storage. An optional vector column/index belongs to `evidence_chunks`; pgvector is not a separate product object.

The machine contract also defines Source Document, Calculation Record, Tool Record, Skill Version, Experience, Evolution Experiment, Retrieval Evaluation, and Simulated Usability Evaluation artifacts.

## 14. Core Research Skill

V1.4 has one versioned `fundamental-research` skill. It defines research procedure, mandatory coverage, evidence discipline, and conclusion structure. It may call deterministic scripts but does not embed provider credentials or benchmark labels.

Skill patches are bounded diffs tied to verified failure IDs. In-flight runs pin one immutable skill hash.

## 15. Evolution Scope

The only V1.4 Evolution target is earnings-quality omission, especially failure to cross-check profit improvement against:

- operating cash flow;
- receivables;
- inventory;
- cash-conversion behavior;
- plausible counter evidence.

Evolution remains ordinary Python:

```text
immutable traces
→ deterministic/coverage verifier
→ repeated failure cluster
  ├→ none eligible: NO_ELIGIBLE_CLUSTER and stop sealed
  └→ experience artifact
     → bounded skill candidate
     → paired Validation
       ├→ REJECTED_VALIDATION and keep Final Test sealed
       └→ ADOPTED → one sealed Final Test → SUPPORTED or REJECTED_FINAL
```

No open-ended prompt search, model fine-tuning, dynamic graph rewriting, or multiple-skill optimization is part of V1.4.

## 16. Benchmark and Leakage Controls

### Primary suite

- Evolution companies: CATL (`300750.SZ`) and EVE Energy (`300014.SZ`).
- Validation company: Gotion High-Tech (`002074.SZ`).
- Final Test company: Sunwoda (`300207.SZ`).

### Contingency suite

- Companies: Great Power (`300438.SZ`), Farasis Energy (`688567.SH`), BYD (`002594.SZ`), and Zhuhai CosMX (`688772.SH`).
- The suite is frozen before the primary experiment and remains sealed unless a versioned V1.5 retry is authorized by the primary terminal outcome.

Each company contributes six target reports: `2023Q3`, `2023FY`, `2024Q1`, `2024H1`, `2024Q3`, and `2024FY`. Each suite contains 24 cases and uses whole-company split isolation.

- Evolution, Validation, and Final Test packages use non-overlapping company/group keys.
- The Researcher cannot read verifier ground truth.
- The Optimizer can read only Evolution failure evidence before candidate freeze.
- Validation may choose the frozen candidate; Final Test labels remain sealed until then.
- Base, Seed, and Candidate runs use identical model, data, tools, graph, budgets, parameters, and evaluator versions. Only the skill differs.
- Exact counts, denominators, exclusions, costs, and rejected candidates are retained.
- The project owner signs the reconciled 20-fact sample, split manifest hashes, and final public package.

## 17. Runtime Architecture

Backend:

```text
Python
FastAPI
Pydantic
LangGraph (Research workflow only)
OpenAI Responses API (`store: false`, Structured Outputs)
```

The default formal model is `gpt-5.6-luna` with `reasoning_effort=medium`, no built-in tools, and a 4,000 output-token cap. A formal experiment cannot change its resolved model/configuration. `gpt-5.4-mini` is a pre-experiment-only fallback if the preferred model is unavailable.

The aggregate OpenAI API spend cap is USD 20: USD 1 calibration, USD 9 primary experiment, USD 6 contingency reserve, USD 2 simulations, and USD 2 safety reserve. A request MUST be rejected before dispatch when its worst-case estimate would exceed the cap.

Data/full product:

```text
content-hashed fixture/artifact packages first
PostgreSQL when full persistence is required
pgvector only after retrieval evidence
JSON Benchmark packages
```

Frontend/full product:

```text
React
TypeScript
Vite
Tailwind
```

Engineering:

```text
pytest
Docker Compose
CI
structured logging
```

No general observability platform or distributed orchestration platform is required.

## 18. Minimal Product Surface

L1 API:

- create research run;
- read lifecycle/progress/failure;
- read completed result and audit artifacts;
- cancel a run.

Full V1.4 UI:

1. **Research** — question, progress, structured report, claims, facts, evidence, sources, limitations.
2. **Skill Lab** — actual no-cluster, candidate rejection, or supported outcome with the relevant failure, experience, diff, paired metrics, and sealed-test evidence.

Both pages render persisted artifacts. Illustrative metrics must be labeled and cannot appear as measured results.

## 19. Required Persisted Artifacts

- Financial Fact;
- Evidence Chunk;
- Claim;
- Research Result;
- Run Manifest with explicit workflow configuration;
- Workflow Trace;
- Benchmark Case;
- Evaluation Result;
- Skill Patch;
- Source Document;
- Calculation Record;
- Tool Record;
- Skill Version;
- Experience;
- Evolution Experiment;
- Retrieval Evaluation;
- Simulated Usability Evaluation;
- Project Checkpoint.

Raw hidden chain-of-thought is never a persisted artifact. Store explicit plan steps, tool records, artifact links, and concise decision summaries.

## 20. Product Evidence

Product acceptance reports:

- schema, calculation, period, and citation correctness on frozen fixtures;
- successful runs / attempted runs and failure codes;
- p50/p95 latency, tokens, and cost;
- model, graph, skill, formula, dataset, and evaluator versions;
- three isolated `SIMULATED` usability sessions with dissenting findings retained;
- an explicit `human_user_value_validated: false` disclosure;
- a fair bare-model comparison only when model, data, cutoff, and budget are held equal.

These metrics do not support production-readiness, broad-market accuracy, human-user usefulness, market demand, alpha, or return claims.

## 21. Development Gates

```text
C0 V1.4 contracts and schemas
→ G0 data and financial foundations
→ G1 thin slice / L1
→ G2 verifier / L2 ─┬→ G3 controlled Evolution outcome / L3 ─┐
                    └→ G1 full five-mode breadth ─────────────┴→ G4 / L4
```

No later gate waives failed evidence from an earlier gate.

## 22. Explicit Non-Goals

V1.4 excludes:

- trading, order execution, portfolio optimization, or investment advice;
- price targets, return prediction, or real-time news/market monitoring;
- full-market or macro research;
- multi-agent systems, agent debate, and role swarms;
- open-ended self-modification, fine-tuning, or autonomous code deployment;
- multiple models or model routing as a product feature;
- complex/general RAG platforms;
- OCR platform construction;
- mobile app, collaboration, multi-tenancy, or enterprise authorization;
- distributed queues, Kubernetes, and full observability stacks.

Future proposals require evidence and a versioned scope decision.

## 23. V1.4 Completion Labels

Use precise labels:

- **V1.4 Contract Ready** — C0 passes.
- **V1.4 Product Slice Ready** — L1 passes.
- **V1.4 Demo Ready** — L2 passes.
- **V1.4 Research Hypothesis Supported** — and only if G3 adoption plus sealed-test criteria pass.
- **V1.4 Full Engineering Product Ready** — all five modes, three labeled simulations, and G4 engineering evidence pass; real user value remains unvalidated.
- **ResearchForge Complete** — Full Engineering Product Ready and Research Hypothesis Supported both pass within the two-experiment limit, and the final independent Reviewer returns `PASS`.

Do not collapse these into a single unsupported “finished” claim.
