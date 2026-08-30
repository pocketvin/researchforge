# ResearchForge V1.3 — Active Product and Research Scope

## A Financial Research Agent with Verifiable Procedures and a Controlled Learning Experiment

- Status: **active V1.3 baseline**
- Contract package: **1.3.0**
- Supersedes: **V1.2 frozen scope**
Scope changes require an explicit decision and changelog entry; they are no longer blocked by the word “frozen.”

## 1. Product Definition

ResearchForge is a single-agent financial research system that:

1. answers bounded company fundamental-research questions using structured financial facts and filing evidence;
2. calculates important financial values with deterministic tools;
3. links material conclusions to point-in-time facts, evidence, counter-evidence searches, and limitations;
4. records a reproducible workflow trace;
5. tests whether repeated, verified earnings-quality omissions can produce a bounded Research Skill patch that improves held-out cases.

The product is research assistance, not investment advice. It does not predict prices, execute trades, optimize portfolios, or claim investment returns.

## 2. V1.3 Design Goals

V1.3 optimizes for:

- **feasibility:** disprove data and period-semantic risks before application infrastructure;
- **usefulness:** help a user understand what changed, why it matters, supporting and opposing evidence, and what remains unknown;
- **auditability:** every important claim resolves to immutable artifacts and a research-time cutoff;
- **career evidence:** each stage produces inspectable Python, agent, evaluation, or full-stack proof;
- **solo completion:** L1–L4 are independently valuable delivery levels;
- **controlled complexity:** one agent, one model, one core skill, one workflow graph, and one narrow Evolution target;
- **recoverability:** every work session ends with a schema-valid checkpoint and one next action.

## 3. Target User and Supported Context

Primary V1.3 users:

- finance learners and junior analysts who need an auditable company-research walkthrough;
- technical reviewers/interviewers evaluating agent, data, and experimentation engineering;
- the project owner running a local or controlled single-user demo.

V1.3 is not designed for professional trading desks, real-time market monitoring, broad consumer investing, or unattended production decisions.

## 4. Product and Research Success Are Separate

### Product Success

The system produces a useful, evidence-grounded company-research result under the contracts and measured product-success criteria.

### Research Success

A repeated verified earnings-quality failure produces a bounded skill patch that passes paired Validation guardrails and improves the sealed Final Test target without catastrophic regression.

### Honest Negative Outcome

If no genuine repeated cluster exists or a candidate is rejected, the product/portfolio stages may still pass. The project reports a negative research result and MUST NOT claim completed self-improvement.

This separation is intentional: a research hypothesis may fail without making the engineering project a failure.

## 5. Product Task Scope

Full V1.3 supports the same five bounded research tasks:

1. **Company Fundamental Research** — revenue, profit, margins, cash flow, working capital, CapEx, debt/cash, changes, risks, and outlook limitations.
2. **Earnings/Filing Analysis** — material period changes, management explanations, contradictory evidence, and monitoring items.
3. **Peer Comparison** — two comparable companies using the same framework, periods, scope, and currency treatment.
4. **Thesis Investigation** — supporting evidence, counter evidence, alternative explanations, conclusion, uncertainty, and confidence.
5. **Risk/Anomaly Detection** — explainable signals such as profit/cash divergence, receivables/inventory growth, margin deterioration, CapEx acceleration, debt deterioration, and one-off contributions.

The implementation sequence starts with one earnings-quality thin slice. This sequences scope; it does not remove the other modes from full V1.3.

## 6. Delivery Levels

| Level | Required outcome | Claim unlocked |
|---|---|---|
| L0 Contract Ready | V1.3 scope, schemas, semantic contracts, validator, and checkpoint | Designed an auditable agent/experiment architecture |
| L1 Resume Ready | One LangGraph-orchestrated earnings-quality flow, deterministic tools, schema-valid report, tests | Built a working evidence-grounded research slice |
| L2 Demo Ready | Deterministic/coverage verifier, trace inspection, replayable failure | Built evaluation and auditable failure analysis |
| L3 Differentiated | Controlled outcome: no eligible cluster, rejected candidate, or supported sealed result | Claim self-improvement only if adoption/final-test criteria pass |
| L4 Full Product | Five modes, Research and Skill Lab pages, storage, Docker, CI, user pilot | Shipped the complete V1.3 controlled demo |

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

Every source records identity, license, retrieval time, publication time, point-in-time availability, content hash, company, period, statement scope, accounting standard, restatement state, currency/unit, and stable locator.

External filings are untrusted data. Instructions inside retrieved content cannot modify prompts, skills, tools, permissions, benchmarks, or policies.

Counter-evidence search is mandatory. A verified `not_found` search is valid; fabricated opposition is prohibited.

## 12. Retrieval Strategy

L1 uses deterministic section filters, keywords, metadata constraints, and stable evidence chunks. Retrieval results store scores/filters and source locators.

Semantic retrieval and pgvector are optional full-product adapters. They are adopted only if frozen retrieval evaluation demonstrates useful improvement over the deterministic baseline. Technology novelty is not an acceptance criterion.

## 13. Storage Model

V1.3 resolves the V1.2 evidence-persistence ambiguity.

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

L1/L2 may implement all of these as content-hashed files. Full V1.3 may map them to PostgreSQL/object storage. An optional vector column/index belongs to `evidence_chunks`; pgvector is not a separate product object.

## 14. Core Research Skill

V1.3 has one versioned `fundamental-research` skill. It defines research procedure, mandatory coverage, evidence discipline, and conclusion structure. It may call deterministic scripts but does not embed provider credentials or benchmark labels.

Skill patches are bounded diffs tied to verified failure IDs. In-flight runs pin one immutable skill hash.

## 15. Evolution Scope

The only V1.3 Evolution target is earnings-quality omission, especially failure to cross-check profit improvement against:

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

No open-ended prompt search, model fine-tuning, dynamic graph rewriting, or multiple-skill optimization is part of V1.3.

## 16. Benchmark and Leakage Controls

- Evolution, Validation, and Final Test packages use non-overlapping company/group keys.
- The Researcher cannot read verifier ground truth.
- The Optimizer can read only Evolution failure evidence before candidate freeze.
- Validation may choose the frozen candidate; Final Test labels remain sealed until then.
- Base, Seed, and Candidate runs use identical model, data, tools, graph, budgets, parameters, and evaluator versions. Only the skill differs.
- Exact counts, denominators, exclusions, costs, and rejected candidates are retained.

## 17. Runtime Architecture

Backend:

```text
Python
FastAPI
Pydantic
LangGraph (Research workflow only)
```

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

Full V1.3 UI:

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
- Project Checkpoint.

Raw hidden chain-of-thought is never a persisted artifact. Store explicit plan steps, tool records, artifact links, and concise decision summaries.

## 20. Product Evidence

Product acceptance reports:

- schema, calculation, period, and citation correctness on frozen fixtures;
- successful runs / attempted runs and failure codes;
- p50/p95 latency, tokens, and cost;
- model, graph, skill, formula, dataset, and evaluator versions;
- a small target-user pilot with dissenting feedback;
- a fair bare-model comparison only when model, data, cutoff, and budget are held equal.

These metrics do not support production-readiness, broad-market accuracy, alpha, or return claims.

## 21. Development Gates

```text
C0 V1.3 contracts and schemas
→ G0 data and financial foundations
→ G1 thin slice / L1
→ G2 verifier / L2 ─┬→ G3 controlled Evolution outcome / L3 ─┐
                    └→ G1 full five-mode breadth ─────────────┴→ G4 / L4
```

No later gate waives failed evidence from an earlier gate.

## 22. Explicit Non-Goals

V1.3 excludes:

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

## 23. V1.3 Completion Labels

Use precise labels:

- **V1.3 Contract Ready** — C0 passes.
- **V1.3 Product Slice Ready** — L1 passes.
- **V1.3 Demo Ready** — L2 passes.
- **V1.3 Research Hypothesis Supported** — and only if G3 adoption plus sealed-test criteria pass.
- **V1.3 Full Product Ready** — all five modes and G4 evidence pass.

Do not collapse these into a single unsupported “finished” claim.
