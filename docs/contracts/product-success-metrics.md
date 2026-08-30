# Product Success Metrics

Contract version: `1.4.0`

Product usefulness and Research/Evolution success are separate. Better benchmark metrics do not prove that a user receives a useful report, and user preference does not prove financial correctness.

## Golden-Case Correctness

On the frozen thin-slice fixtures:

- 100% of persisted artifacts validate against their V1.4 schemas;
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

## Simulated Usability Evidence

V1.4 does not claim a real-user pilot. Before Full Engineering Product Ready is marked Green:

- exactly three isolated AI-simulated personas inspect the same persisted report and UI evidence under fresh contexts;
- every record uses `evidence_label: SIMULATED` and `human_user_value_validated: false`;
- at least two of three assign both usefulness and auditability scores of 4/5 or higher;
- every session locates the key change, supporting evidence, counter-evidence/limitation, and monitoring item;
- every material factual error and usability blocker is retained, including dissenting findings.

Simulated evidence tests presentation and artifact navigation only. It is not a user study, cannot validate market demand, and cannot justify a claim that target users find the product useful.

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
- G4: three labeled simulations, reproducible demo startup, and UI behavior evidence.

No metric in this file supports an investment-performance, alpha, return, production-readiness, or broad-market accuracy claim.
