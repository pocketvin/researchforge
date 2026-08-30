# Product Success Metrics

Contract version: `1.3.0`

Product usefulness and Research/Evolution success are separate. Better benchmark metrics do not prove that a user receives a useful report, and user preference does not prove financial correctness.

## Golden-Case Correctness

On the frozen thin-slice fixtures:

- 100% of persisted artifacts validate against their V1.3 schemas;
- 100% of expected deterministic calculations and period classifications pass fixture assertions;
- 100% of material numeric claims resolve to facts/calculations;
- 100% of cited evidence IDs resolve to point-in-time-valid sources;
- every required counter-evidence search has a result or explicit `not_found` record;
- every unsupported required input produces a safe insufficient-data outcome rather than a guessed value.

Counts and denominators MUST be reported. These are acceptance checks on bounded fixtures, not claims about all public-company research.

## Reliability and Efficiency

Run at least 20 fixed thin-slice executions across the accepted companies/cases. Report:

- successful schema-valid runs / attempted runs, with a G1 target of at least 90%;
- failure counts by code and retry status;
- p50 and p95 end-to-end latency;
- p50 and p95 token usage and estimated cost;
- model/configuration, graph version, dataset hash, and run IDs.

Cost and latency caps are resolved before each batch and stored in Run Manifests; this contract does not invent a provider-independent price target.

## Target-User Pilot

Before Product Usefulness is marked Green:

- at least three target users complete the same bounded research task without project-owner coaching;
- at least two of three rate both usefulness and auditability at 4/5 or higher;
- users can locate the key change, supporting evidence, counter-evidence/limitation, and monitoring item within ten minutes;
- every material factual error and usability blocker is recorded, including dissenting feedback.

Three users are a portfolio pilot, not evidence of market demand.

## Fair Baseline Comparison

If ResearchForge is compared with a bare-model call, both conditions MUST use the same:

- model snapshot and parameters;
- research question, data/evidence access, and research-time cutoff;
- token/tool/time budget;
- evaluation cases and verifier version.

Only the explicit Research Procedure/orchestration condition may differ. Report all exclusions and do not cherry-pick fluent examples.

## Gate Evidence

- L1/G1 thin slice: golden-case correctness plus one exported trace and report.
- Formal G1: reliability batch and acceptance coverage across all five task modes.
- G4: target-user pilot, reproducible demo startup, and UI behavior evidence.

No metric in this file supports an investment-performance, alpha, return, production-readiness, or broad-market accuracy claim.

