# Run Lifecycle Contract

Contract version: `1.3.0`

Research and patch-generation calls are asynchronous jobs. The API and UI MUST use the same lifecycle semantics.

## States

```text
queued → running → succeeded
                 → insufficient_data
                 → failed
                 → timed_out
                 → cancelled
queued           → cancelled
```

Terminal states are immutable. A retry creates a new run ID with the same idempotency family and incremented attempt; it does not reopen a terminal run.

## State Requirements

| State | Required behavior |
|---|---|
| `queued` | Configuration is resolved and immutable; no provider call has begun |
| `running` | `started_at` exists; progress may advance; cancellation is best effort |
| `succeeded` | Schema-valid result and usage record exist; no failure object exists |
| `insufficient_data` | Required facts/evidence are unavailable; no result exists; a non-retryable structured `INSUFFICIENT_DATA` record explains the gap |
| `failed` | Structured error and `finished_at` exist; partial prose is not a valid result |
| `timed_out` | Timeout error is recorded; late provider responses are discarded |
| `cancelled` | Cancellation time/reason are recorded outside the immutable input; no further tools may execute |

## Immutable Configuration

After entering `queued`, a run MUST NOT change:

- task input and research time;
- model ID/snapshot/parameters;
- skill version/hash;
- prompt hashes;
- formula/tool versions;
- dataset package/hash;
- evidence cutoff;
- token, tool-call, time, and cost limits.

## Idempotency

- A client supplies or receives an idempotency key.
- Repeating the same request with the same key returns the existing run.
- Reusing a key with different immutable input returns a conflict.
- Tool writes, if any are later introduced, require their own idempotency keys.

## Limits and Retries

- Default maximum attempts: 3 total (initial attempt plus at most two automatic retries).
- Retry only provider/network/transient-storage failures marked `retryable`.
- Do not retry schema-invalid model output indefinitely; one controlled repair attempt may occur inside the same run budget.
- Calculation, period, citation, and research-quality failures are evaluation outcomes, not infrastructure retries.
- `insufficient_data` is an honest terminal research outcome, not an infrastructure retry.
- Exceeding time, token, tool-call, or cost limits terminates the run honestly.

Exact default limits are environment configuration, but the resolved values MUST appear in every Run Manifest.

## Progress Events

The UI may display these stable stages:

```text
understanding_question
planning
loading_financial_data
retrieving_evidence
calculating
cross_checking
searching_counter_evidence
forming_conclusion
validating_output
completed
```

Progress is informational and MUST NOT expose hidden chain-of-thought. Messages describe actions and artifact counts, not private reasoning.

## Trace Artifacts

Persist:

- explicit research plan;
- tool name/version, sanitized input, output artifact IDs, status, latency, and error;
- financial fact IDs used;
- retrieved evidence IDs and retrieval scores/filters;
- claim-to-fact/evidence links;
- concise decision summaries;
- generated patch ID for successful patch-generation runs;
- verifier feedback and failure events;
- usage and cost.

Do not persist hidden chain-of-thought, secrets, provider credentials, or unrestricted raw provider payloads.

## Failure Codes

At minimum distinguish:

- `INVALID_INPUT`
- `UNSUPPORTED_COMPANY`
- `INSUFFICIENT_DATA`
- `PERIOD_ALIGNMENT_FAILED`
- `EVIDENCE_PARSE_FAILED`
- `PROVIDER_UNAVAILABLE`
- `TOOL_FAILED`
- `OUTPUT_SCHEMA_INVALID`
- `LIMIT_EXCEEDED`
- `CANCELLED_BY_USER`

User-facing messages must be safe and actionable; internal errors remain in structured logs without secrets.

## Retention

- Benchmark manifests, skill versions, patches, evaluations, and hashes are retained as immutable experiment evidence.
- Product traces default to 90 days in the controlled demo unless the project owner configures a shorter period.
- Licensed raw documents follow their license and may be referenced by hash/locator without being copied into the repository.
