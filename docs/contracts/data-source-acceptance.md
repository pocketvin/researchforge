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
| Identity and access | SZSE/CNInfo official announcement links; public web/direct PDF access | Tushare registered account/token and at least 2,000-point statement permissions |
| License/redistribution | Full PDFs excluded; normalized facts, documented short evidence, hashes, locators and official links only | Personal, non-transferable, non-commercial, revocable and personal-viewing-only terms fail public/runtime use |
| Metric and company coverage | G0 evidence covers CATL and EVE, four periods each and six metrics per filing; later Benchmark expansion remains separately gated | Required income, balance-sheet and cash-flow fields documented; API call intentionally unnecessary after rights rejection |
| Period/scope metadata | CAS consolidated, frozen source-label mapping version `1.0.0`; 48/48 facts carry complete period and restatement semantics | Announcement date, actual publication date, period, report type and company type documented |
| Publication-time history | Official disclosure timestamps required and retained | Historical announcement fields documented, but not relied upon by the product |
| Filing locators | Official URL, file hash, page/section/table/row/column required | Provider field plus official filing back-reference would be required for optional local comparison |
| Numeric reconciliation | 48/48 official cells match after unit conversion; 0 unresolved mismatches; representative 20-fact sample signed | No provider payload needed; numeric authority remains the manually checked filing sample |
| Missing/correction behavior | Never coerce to zero; preserve old hashes and correction lineage | Update flag exists, but provider guarantees are insufficient and values cannot replace official lineage |
| Latency/cost/rate limits | Offline after package freeze | Permission/account cost and service dependency avoided |
| Final outcome and scope | `FIXTURE-ONLY` accepted for the stated two-company/four-period scope; no live or full-market claim | `REJECT` for runtime, committed demo, redistribution and public package |

Evidence and links for this scorecard are recorded in `docs/evidence/g0-source-spike.md`.

## Fallback

If no candidate passes within the time box, create content-hashed fixtures from official, redistribution-safe material with manual reconciliation evidence. Continue L1 as an offline research prototype and disclose that live ingestion remains unresolved.
