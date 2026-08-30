# Data-Source Acceptance Contract

Contract version: `1.4.0`

A data source is accepted only after evidence shows it can support correct, point-in-time research. A feature list or successful API call is insufficient.

## Mandatory Source Record

For each structured-data and filing candidate, record:

- provider/source identity and authoritative URL;
- access method, authentication needs, rate limits, latency, and cost;
- license, redistribution, caching, and derived-artifact restrictions;
- supported markets, companies, metrics, periods, currencies, accounting standards, statement scopes, restatements, and publication timestamps;
- stable source/document/section/page locators;
- missing-value and correction behavior;
- retrieval timestamp and evidence cutoff behavior.

Unknown license or redistribution terms mean `REJECT` for committed demo data.

## Time-Boxed Spike

Maximum effort: two person-days before an explicit decision.

Use:

- two candidate companies from the same market and reporting convention;
- four comparable reporting periods per company;
- revenue, net income, operating cash flow, receivables, inventory, and one margin input where reported;
- the corresponding official filings available at the recorded research time.

The V1.4 spike compares an official-filing-derived frozen package with one structured-data reconciliation candidate. It MUST NOT start application infrastructure.

The intended runtime outcome is `FIXTURE-ONLY`: public artifacts include normalized facts, short evidence only when the publication basis is documented, hashes, source locators, and official links. Full filing PDFs and uncertain-license raw provider payloads MUST NOT be committed.

## Reconciliation Protocol

Build a manually reviewed sample of at least 20 non-missing facts across companies, periods, and metrics.

Acceptance requires:

1. 100% of sampled facts carry period start/end, period basis, currency, unit/scale, statement scope, accounting standard, restatement status, publication time, and a source locator.
2. At least 98% of sampled numeric values agree with the official filing after documented unit conversion and deterministic derivation.
3. Every disagreement is classified as provider error, source restatement, scope mismatch, period mismatch, derivation, or unresolved.
4. No missing or ambiguous value is silently converted to zero.
5. YTD-to-discrete derivations follow `financial-methodology.md` and retain parent fact IDs.
6. A later correction does not overwrite the point-in-time value used by a historical case.

With a 20-fact minimum, the 98% threshold effectively permits no unexplained mismatch. Larger samples use the stated denominator and exact count.

## Decision Outcomes

- **ACCEPT** — suitable for the stated companies/metrics/product use, with recorded restrictions.
- **FIXTURE-ONLY** — suitable only to create frozen, manually reconciled, redistribution-safe packages; no live-data reliability claim.
- **REJECT** — unsuitable due to correctness, semantics, licensing, provenance, cost, or operational limits.

The decision record MUST state its scope. Acceptance for two A-share companies does not imply full-market coverage.

## Candidate Scorecard

| Check | Official-derived frozen package | Structured reconciliation candidate |
|---|---|---|
| Identity and access | CNInfo/SSE official filing links; extraction workflow pending | Provider identity/account pending G0 spike |
| License/redistribution | Derived facts, documented short evidence, hashes, and links only | Terms and caching/derived-artifact rights pending |
| Metric and company coverage | Eight named A-share companies; source validation pending | Same-company reconciliation coverage pending |
| Period/scope metadata | CAS consolidated, six target reports; mapping pending | Publication/period/report-type fields pending |
| Publication-time history | Official disclosure timestamps required | Historical announcement timestamps required |
| Filing locators | Page/section/table locators required | Source-line and official filing back-reference required |
| Numeric reconciliation | At least 20 non-missing facts pending | Compared against the same official facts |
| Missing/correction behavior | Never coerce to zero; preserve old hashes | Provider correction/restatement behavior pending |
| Latency/cost/rate limits | Offline after package freeze | Recorded but not a runtime dependency for V1.4 |
| Final outcome and scope | Expected `FIXTURE-ONLY`, not yet accepted | ACCEPT/REJECT for reconciliation use only |

## Fallback

If no candidate passes within the time box, create content-hashed fixtures from official, redistribution-safe material with manual reconciliation evidence. Continue L1 as an offline research prototype and disclose that live ingestion remains unresolved.
