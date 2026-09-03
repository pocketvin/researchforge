# ResearchForge × n8n Integration Contract

Version: `1.5.0`. Phase 4 is an engineering checkpoint, not independent acceptance.

## Ownership and input

n8n owns input transport, bounded waiting, status routing and presentation aliases only. It MUST
call the same ResearchForge backend as Web. It MUST NOT calculate financial values, generate a
conclusion, select evidence truth, run verifier policy or replace LangGraph. No core rewrite is
required. Existing financial artifacts retain their unchanged V1.4 schemas.

The webhook accepts `company_id`, `period`, `research_question`; optional `research_time` and
`idempotency_key` support reproducible retries. Additional keys are rejected. Capabilities are read
from `/v1/catalog`, which MUST advertise the `product` namespace. Unsupported company/period
pairs are refused before POST; fixtures and Benchmark are never substitutes.

The trusted backend URL is operator configuration in the workflow, never user input. Run IDs
are validated before constructing paths. Backend-returned links are not followed; redirects are
disabled. This local single-user integration is not an authenticated public service.

## Lifecycle and limits

- POST exactly the existing `filing_analysis` request contract; accept only a valid HTTP 202.
- HTTP nodes use 5-second timeouts and at most three transport attempts. POST retries retain the
  exact input and idempotency key. HTTP refusals are routed, not retried as new research runs.
- Wait two seconds between polls, at most 60 polls and 150 seconds of elapsed polling budget.
  The elapsed bound is checked after each response; an in-flight bounded HTTP attempt can add
  time. The workflow has an outer 300-second timeout.
- Only backend `succeeded` permits result fetching. `queued`/`running` may wait. All other states,
  unknown states, transport failures and missing artifacts have explicit error outputs.
- Poll exhaustion is not backend cancellation. Preserve run/status/trace/cancel links and state
  that the backend may still be running. Cancellation remains an explicit POST to the backend.
- An n8n process crash or outer execution timeout may terminate the webhook without the custom
  JSON envelope. This is a transport failure, never a successful research result.

## Output and replay

Output validates against `schemas/v1.5/n8n-research-output.schema.json`. Success includes the
unchanged Research Result, Financial Facts, Calculation Records, Evidence Chunks and Workflow
Trace. Conclusion, findings, limitations and monitoring are exact aliases of backend fields.
Counter-evidence mapping retains the backend's `found`/`not_found`/`not_applicable` state.

For cross-execution retries, preserve both the original `research_time` and `idempotency_key`.
Changing either input under an existing key returns a conflict. No global workflow-static mutable
state is used for poll counters or per-user requests.

## Evidence boundary

Three real-filing webhook runs must match the corresponding backend artifacts exactly. Test-only
transport fixtures may exercise waiting/failure branches but MUST NOT serve synthetic finance or
count as real-filing evidence. Human usefulness remains unvalidated until final Phase 6 Web+n8n
evaluation. No simulated persona or engineering smoke is a human participant.
