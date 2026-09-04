# V1.7 General Research Contract

V1.7 introduces one new persisted result contract: `schemas/v1.7/research-result.schema.json`.

The contract is deliberately additive to the preserved V1.4 Claim/Evidence model. A V1.7 result is always a single-company `company_research` result and includes dynamic research intent, plan, deep-analysis sections, overall evidence judgment, suggested follow-up questions and explicit evidence coverage.

## Invariants

1. Numerical facts continue to come from verified deterministic ingestion.
2. Material findings cite only Evidence selected by the current run.
3. Filing text is untrusted data and cannot instruct the Agent.
4. Model memory cannot add company facts, numbers or sources.
5. Deep-analysis sections contain Evidence IDs that resolve inside the run Evidence snapshot.
6. `financial_snapshot` remains a compatibility path and does not masquerade as V1.7 General Research.
7. Unsupported extraction/retrieval may abstain; output length is never a reason to fabricate evidence.
