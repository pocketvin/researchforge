# G2 Deterministic Verifier Evidence

Evidence date: `2026-09-01`

Status: `LOCAL_EXIT_EVIDENCE_COMPLETE_FINAL_ACCEPTANCE_DEFERRED`

## Implemented Checks

The Verifier is plain Python and can run without LangGraph or a provider. It independently recomputes gross profit, gross margin, cash conversion, profit/cash divergence, and trend growth. It validates run/result/trace identity, V1.4 shape, point-in-time publication, period compatibility, citation linkage, tool/calculation records, and mandatory coverage.

Coverage includes operating cash flow, receivables, inventory, cash conversion, profit/cash divergence, one-off contribution status, and counter-evidence search. `unavailable` is accepted only when it carries a reason and limitation.

## Fixed Fixtures

- Passing fixture: all metrics `1.0`, no failure events.
- Calculation corruption: stable `CALCULATION_ERROR` event.
- Missing mandatory procedure: stable `CRITICAL_OMISSION` event.
- Broken evidence link: stable `CITATION_ERROR` event.
- Publication cutoff/period defect: stable cutoff or period failure event.

Evaluation Results validate against `evaluation-result.schema.json`, persist through the artifact repository, and are linked from the Run Manifest. The CLI can replay verification with frozen expected calculations.

## Evolution Boundary

The failure cluster selector requires at least three exact-signature failures across at least two distinct cases and the pre-registered 20% support floor. Synthetic policy fixtures test adoption, rollback, and one-time Final Test semantics; they do not constitute formal G3 evidence.

## Remaining Formal Evidence

The current G0 golden cases are exercised by deterministic formula and Verifier tests, but the 24-case formal Benchmark ground truth is not complete. Independent G2 acceptance is deferred to final project review.
