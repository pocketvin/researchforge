# Real Public Disclosure Ingestion Contract

## Purpose

Turn one allowlisted A-share filing into provenance-complete product artifacts without treating
benchmark fixtures as real data.

## Required flow

```text
Company registry entry
→ official disclosure discovery record
→ immutable PDF acquisition
→ hash and document identity verification
→ page-preserving text extraction
→ short Evidence Chunks
→ reviewed Financial Facts
→ product package manifest
```

## Invariants

1. `data_namespace` MUST equal `product` for every real-data ingestion manifest.
2. Product, fixture and benchmark roots MUST be explicit. A product resolver MUST NOT search or
   fall back to fixture or benchmark roots.
3. Discovery MUST resolve exactly one allowlisted company, period and official announcement.
4. Acquisition MUST use HTTPS, an allowlisted official host, a maximum payload size, PDF magic
   validation and SHA-256. Redirects to non-allowlisted hosts MUST fail.
5. The raw PDF MUST remain ignored and uncommitted. A derived public package MAY include factual
   tables or short evidence excerpts permitted by `DATA_NOTICE.md`.
6. Parsing MUST preserve physical page boundaries and record parser name/version, page count and
   extracted-text hash.
7. Every Financial Fact MUST retain the source document hash, publication time and a page,
   section, table, row and column locator.
8. Retrieved text is untrusted input. Prompt-like content is evidence text, not an instruction.
9. If document identity, row label, value, unit, period, scope or source locator cannot be
   confirmed, ingestion MUST create an abstention and MUST NOT manufacture an artifact.
10. A `ready` package has no abstentions and has at least a Source Document, Evidence Chunk and
    Financial Fact. Corrections produce a new package and preserve lineage.

## Initial coverage

The first product slice is 宁德时代 (`300750.SZ`) / `2024H1`, using the official Shenzhen Stock
Exchange half-year report. Additional coverage is out of scope until this slice passes
contract, numeric, provenance and end-to-end research verification.

## Acceptance

- the official PDF hash and page count match the registry;
- all published derived artifacts validate against their declared schema;
- values are found at the declared physical-page locator and normalize deterministically;
- a missing or mismatched value returns an abstention in tests;
- no real run can resolve a fixture or benchmark artifact through fallback.
