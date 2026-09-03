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
→ consolidated statement/table detection
→ exact metric-row matching
→ reporting-period/column resolution
→ unit and scale resolution
→ candidate numerical extraction
→ deterministic normalization and provenance verification
→ short Evidence Chunks and Financial Facts
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
7. The registry is document identity metadata only. It MUST NOT contain prefilled fact values,
   fact pages, row/column locators or evidence text used as numerical truth.
8. Extraction is bounded to exactly `revenue`, `operating_cost`, `net_income`,
   `operating_cash_flow`, `accounts_receivable` and `inventory` from consolidated statements.
   It MUST NOT silently expand to other metrics.
9. The LLM MUST NOT supply, select, repair or arbitrate a promoted numerical value. Every promoted
   number MUST be reparsable from its recorded native-PDF evidence text, physical page, table,
   row, current-period column and unit declaration.
10. Statement title, row, current-period column and unit/scale are separate deterministic checks.
    Missing, multiple or conflicting candidates at any check MUST abstain the whole package.
11. The parser MAY join wrapped rows and carry an explicitly detected statement context across a
    physical page boundary. It MUST stop that context at the next consolidated or parent-company
    statement title. It MUST NOT use company-specific page ranges or result code.
12. Every Financial Fact MUST retain the source document hash, publication time and a page,
   section, table, row and column locator.
13. Retrieved text is untrusted input. Prompt-like content is evidence text, not an instruction.
14. If document identity, row label, value, unit, period, scope or source locator cannot be
   confirmed, ingestion MUST create an abstention and MUST NOT manufacture an artifact.
15. A `ready` package has no abstentions, exactly six promoted facts and a schema-valid extraction
    recovery record with `llm_used: false`. Corrections produce a new package and preserve lineage.

## Explicit abstentions

The bounded implementation returns a structured abstention instead of a partial product package
for at least these conditions:

- no usable native PDF text layer (`TEXT_LAYER_REQUIRED`); OCR is not attempted;
- missing or ambiguous consolidated metric row;
- unresolved or conflicting current-period column;
- unresolved or conflicting unit/scale;
- row context changes while a wrapped row is reconstructed;
- evidence text cannot be recovered from the recorded physical page;
- official document hash, byte count or page count differs from the reviewed identity.

## Initial coverage

Phase 2 proved 宁德时代 (`300750.SZ`) / `2024H1`. Phase 3 adds exactly CATL `2024FY` and BYD
(`002594.SZ`) / `2024H1` through the same implementation. Registry additions are identity metadata,
not expected values, page ranges or company-specific extraction rules.

The extractor supports two explicit financial value columns, optional declared note references,
multi-line duration headers and an explicit report-wide unit declaration. Column order is resolved
from the requested period; the first number is never assumed to be the current amount. Unsupported
column cardinality, ambiguous note/value placement and missing current values abstain.

The default product root is a bounded index of three child packages. Each child must declare the
product namespace and a ready ingestion; its files and package hash must match. Nested indexes,
path escape, duplicate artifacts, tampering and stale ready files after an abstention are refused.
Single-package roots remain supported explicitly. No package is copied into a fixture or Benchmark.

## Acceptance

- the official PDF hash and page count match the registry;
- all published derived artifacts validate against their declared schema;
- the public registry contains document identity but no prefilled fact value, fact locator or
  evidence text;
- all six values are recovered from the verified PDF, found at the emitted physical-page locator
  and normalized deterministically;
- the extraction record proves native-PDF truth, no LLM use and one recovery per target metric;
- missing rows, wrong-period headers, duplicate rows, missing text and conflicting units return
  abstentions in tests;
- no real run can resolve a fixture or benchmark artifact through fallback.
