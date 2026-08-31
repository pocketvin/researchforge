# G1 Full-Breadth Reliability Evidence

Evidence date: `2026-09-01`

Status: `LOCAL_EXIT_EVIDENCE_COMPLETE_FINAL_ACCEPTANCE_DEFERRED`

## Outcome

All five allowlisted modes use the same ten-stage LangGraph and immutable artifact service. Frozen success cases cover Company Research, Filing Analysis, Peer Comparison, Thesis Investigation, and Risk Detection. A separate cutoff-driven case for each mode proves safe `insufficient_data` degradation with no Research Result.

## Fixed Reliability Batch

Command: `uv run python scripts/run_reliability_batch.py`

| Mode | Runs | Succeeded |
|---|---:|---:|
| Company Research | 4 | 4 |
| Filing Analysis | 4 | 4 |
| Peer Comparison | 4 | 4 |
| Thesis Investigation | 4 | 4 |
| Risk Detection | 4 | 4 |
| **Total** | **20** | **20** |

Success rate: `100%` (contract threshold: at least `90%`). Provider calls and OpenAI spend: `0`.

Observed local latency ranged from about 21 ms to 370 ms. This is development-machine evidence, not a production SLO. Later runs take longer because the durable single-user checkpoint file grows; PostgreSQL stores logical records, while immutable JSON remains the artifact source of truth.

## Mode-Specific Assertions

- Company Research calculates multi-period trend checks.
- Peer Comparison applies the same formula/tool path to exactly two companies.
- Thesis Investigation refuses investment advice and can return a mixed/uncertain result.
- Risk Detection emits explained risk claims rather than treating anomaly signals as proof.
- Every material result includes mandatory earnings-quality checks, counter-evidence status, sources, facts, calculations, limitations, and schema-valid Trace.

## Honest Boundary

This is frozen-fixture, single-user reliability. It does not prove live A-share coverage, model quality, Docker startup, human usefulness, or formal Evolution support. Independent G1 acceptance is deferred to the one final project review at the owner's request.
