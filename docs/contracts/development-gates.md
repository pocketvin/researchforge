# Development and Acceptance Gates

Contract version: `1.3.0`

The V1.3 baseline keeps gates G0–G4, adds a prerequisite Contract Gate, and separates a thin vertical slice from full G1 breadth so the hardest assumptions are tested early.

Recommended working order:

```text
C0 → G0 → G1 thin slice → G2 ─┬→ G3 controlled experiment ─┐
                                └→ complete G1 breadth ───────┴→ G4
```

G1 is not formally passed until all five product modes meet its exit criteria.

## C0 — Contract Readiness

Required evidence:

- active V1.3 scope and V1.2→V1.3 change note stored in the project;
- contract catalog and all V1.3 JSON schemas;
- financial methodology, task matrix, benchmark protocol, evolution policy, and run lifecycle;
- data-source, product-success, and single-agent LangGraph workflow contracts;
- human-readable and schema-valid machine project checkpoints;
- a V1.3 Workflow Trace schema and valid example;
- contract validator passes;
- at least one schema-valid benchmark-case example.

No application feature may persist an artifact before its schema and semantic contract exist.

## G0 — Research Skill and Financial Foundations

Required evidence:

- an ACCEPT or FIXTURE-ONLY source decision under `data-source-acceptance.md`;
- Seed `fundamental-research` skill with immutable version/hash;
- deterministic implementations for normalization, period derivation, growth, margin, comparison, and divergence detection;
- versioned source-line mapping for the chosen data provider;
- 2–3 manually reviewed earnings-quality golden cases;
- unit tests for positive, zero, negative, missing, YTD, restated, and incompatible-period inputs;
- manual end-to-end review demonstrating no model mental arithmetic for important figures.

## G1 — Useful Research Agent

### Thin-slice checkpoint

Before broad implementation, one earnings-quality case MUST run through:

```text
question → plan → facts → filing retrieval → deterministic calculations
→ cross-check → structured result → trace
```

The result and Run Manifest must validate against V1.3 schemas. The single-agent workflow MUST use the bounded LangGraph contract in `research-workflow.md`; domain and formula behavior remains independently testable plain Python.

This checkpoint is L1 Resume Ready only when the golden-case correctness requirements in `product-success-metrics.md` pass and the exported trace/report support the claims in `PORTFOLIO.md`.

### Formal G1 exit

Each of the five modes has at least one frozen acceptance case satisfying `task-capability-matrix.md`. In addition:

- all modes use the same core workflow;
- Peer Comparison uses the same framework for both companies;
- Thesis Investigation can reject or remain uncertain rather than confirm by default;
- Risk Detection explains signals rather than treating them as proof;
- unsupported/missing-data requests degrade safely;
- material claims resolve to facts/evidence and point-in-time-valid sources.
- the fixed-run reliability batch in `product-success-metrics.md` is reported with exact denominators.

## G2 — Financial Verifier

Required evidence:

- deterministic checks for numbers, calculations, periods, schema, tools, citation existence, and point-in-time validity;
- coverage checks for OCF, receivables, inventory, cash conversion, profit/cash divergence, and counter-evidence search;
- failure taxonomy with specific signatures;
- verifier fixtures containing both passing and failing examples;
- 100% expected outcomes on deterministic verifier fixtures;
- comparison against human ground truth on all golden cases, with disagreements documented;
- LLM qualitative judge clearly marked advisory-only.

Evolution work MUST NOT begin until G2 evidence shows stable detection of the target failure.

## G3 — Controlled Evolution

Common required evidence:

- frozen Evolution/Validation/Final Test manifests with non-overlapping group keys;
- exact counts, denominators, exclusions, costs, and limitations reported.

G3 completes with one of these honest outcomes:

1. **NO_ELIGIBLE_CLUSTER** — all eligible Evolution evidence is processed, no cluster meets the pre-registered support threshold, no Candidate is generated, and Validation/Final Test remain sealed.
2. **REJECTED_VALIDATION** — a real cluster, experience, and bounded Candidate exist, but paired identical-configuration Validation rejects it; Final Test remains sealed.
3. **REJECTED_FINAL** — Validation adopts the frozen Candidate, one sealed Final Test is run, and the target/generalization guardrail fails; operational rollback is proven.
4. **SUPPORTED** — Validation adopts the Candidate and one sealed Final Test improves the target metric without catastrophic regression; skill history and rollback are proven.

Metrics come from immutable evaluation records and all automatic decisions follow `evolution-adoption-policy.md`. Outcomes 1–3 prove honest experimental engineering but do **not** satisfy the V1.3 Research Hypothesis Supported label. Product/portfolio levels remain valid.

## G4 — Productization

Required evidence:

- Research and Skill Lab pages render persisted artifacts, not hard-coded demo values;
- asynchronous progress, cancellation, errors, and insufficient-data states work;
- Docker Compose starts the supported local demo from documented steps;
- migrations and seed/golden data loading are repeatable;
- CI runs formatting, lint, type-check, unit, schema, integration, and smoke checks;
- README documents setup, supported scope, data licensing, costs, limitations, and financial-research disclaimer;
- demo video follows the actual system and measured results.
- the bounded target-user pilot in `product-success-metrics.md` is complete and dissenting feedback is retained.
- Skill Lab renders the actual G3 outcome, including no-cluster and rejection states.

## Completion Evidence Format

Every gate record SHOULD include:

- commit or artifact hashes;
- exact verification commands and exit codes;
- test/run IDs;
- screenshots or exported JSON where relevant;
- known limitations;
- reviewer and date.

Passing a later gate does not waive an earlier failed gate.
