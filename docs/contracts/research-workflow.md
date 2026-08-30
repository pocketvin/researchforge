# Research Workflow and LangGraph Contract

Contract version: `1.3.0`

ResearchForge uses one LangGraph workflow to make the versioned single-agent Research Procedure explicit, auditable, and recoverable. LangGraph is an orchestration boundary, not a second source of product or financial semantics.

## Allowed Responsibilities

LangGraph MAY manage:

- typed run state and stable stage transitions;
- conditional routing for insufficient data, cancellation, limits, and validation failure;
- checkpoint/resume for asynchronous runs;
- one controlled structured-output repair attempt within the existing run budget;
- sanitized progress and trace events;
- calls to plain application/domain services.

LangGraph MUST NOT:

- implement formulas, period normalization, retrieval ranking, verifier rules, or storage policy inside graph topology;
- create Planner, Critic, Reviewer, or debate agents;
- dynamically rewrite its topology or the active skill during a run;
- orchestrate the Evolution pipeline;
- store hidden chain-of-thought or unrestricted filing payloads.

## Stable Stages

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

The implementation may combine pure pass-through functions, but user-visible progress names and artifact semantics remain stable.

## Conditional Routes

```text
invalid/unsupported request ───────────────→ failed
missing mandatory facts after loading ────→ insufficient_data
no credible counter evidence found ───────→ continue with recorded not_found
schema-invalid structured output ─────────→ one bounded repair → revalidate
second validation failure ─────────────────→ failed
cancellation or limit exceeded ────────────→ terminal lifecycle state
```

A repair fixes structure only. It cannot introduce new facts, evidence, calculations, or citations that were not produced earlier in the run.

## Graph State Boundary

The typed graph state MUST include or reference:

- run/case/task identifiers and research time;
- immutable configuration, limits, attempt, and `graph_version`;
- current stage and sanitized progress summary;
- explicit plan steps;
- financial fact, calculation, evidence, and claim IDs;
- counter-evidence search status;
- structured failure and validation issues;
- result/manifest artifact IDs and usage totals.

State SHOULD carry identifiers instead of duplicate payloads. The persisted Run Manifest remains the authority for lifecycle and reproducibility.

## Node Contract

Every node MUST:

1. have one named responsibility and typed input/output;
2. call an injectable service through an application port;
3. be independently testable with fake adapters;
4. emit artifact IDs, status, latency, and a concise decision summary;
5. respect the immutable run configuration and remaining budget;
6. be idempotent or document its idempotency boundary;
7. map expected failures to the codes in `run-lifecycle.md`.

Model-facing nodes must validate structured output. Tool-facing nodes must not ask the model to perform important arithmetic.

## Versioning and Reproducibility

- Pin the LangGraph dependency when runtime implementation begins.
- Research runs record `engine`, `graph_version`, and `checkpoint_schema_version` in Run Manifest `configuration.workflow`; ordinary-Python patch-generation runs record `workflow: null`.
- Persist sanitized stage events against `workflow-trace.schema.json` and link the trace from the Run Manifest.
- Every Research run that reaches `running` or a terminal state has a non-null Workflow Trace ID; patch-generation runs have no LangGraph trace.
- Topology/routing changes increment `graph_version` and require trace fixtures.
- Base, Seed, and Candidate comparisons use the same graph version. Only the skill differs.
- Checkpoint serialization changes require a migration or explicit incompatibility note; silent resume failure is prohibited.

## Acceptance Evidence

L1 requires tests or trace fixtures proving:

- the happy path visits each required stage in order;
- insufficient data terminates without a fabricated report;
- `not_found` counter-evidence continues honestly;
- output repair is capped at one and cannot add evidence;
- cancellation/limits produce the contracted terminal state;
- rerunning a completed idempotency key does not duplicate work;
- domain/formula tests run without importing or executing LangGraph.
