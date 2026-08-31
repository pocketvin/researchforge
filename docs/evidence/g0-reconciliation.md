# G0 Filing Reconciliation Evidence

Evidence date: `2026-08-31`  
Package: `g0_catl_eve_2023q3_to_2024h1`  
Status: `INDEPENDENTLY_ACCEPTED`

## Outcome

The bounded eight-filing source spike produced 48 non-missing, base-unit CNY facts. Every selected cell was visually compared with the corresponding consolidated financial-statement page. All artifacts validate against the V1.4 Source Document and Financial Fact schemas.

| Measure | Exact result | Contract threshold |
|---|---:|---:|
| Source documents | 8/8 | 8 planned |
| Reviewed facts | 48/48 | at least 20 |
| Complete semantic records | 48/48 (100%) | 100% |
| Numeric agreement after unit conversion | 48/48 (100%) | at least 98% |
| Visual cell matches | 48/48 (100%) | no unexplained mismatch |
| Unresolved mismatches | 0/48 (0%) | 0 at this sample size |
| Raw PDFs committed | 0 | 0 |

The package contains 8 schema-valid Source Documents, 48 schema-valid Financial Facts, one custom-validated golden-case fixture, 57 artifact hashes, and a deterministic package hash. The owner-signed package hash is `56fd99ae6be655dc878d93a8c99f4bd3d6ba60feffaf2f21ffc81da2d180d58d`.

## Frozen Source Set

| Filing | Published/effective | Bytes | SHA-256 |
|---|---|---:|---|
| CATL 2023Q3 | 2023-10-20 | 839,227 | `7681bd022913880699d1c58c404ae8c5a526f891f4275851b09b5da19f82cad3` |
| CATL 2023FY | 2024-03-16 | 5,986,207 | `6081f0377617dddb82f900569d6458c278a7ab26697b34c87684188eac083471` |
| CATL 2024Q1 | 2024-04-16 | 325,466 | `7be8765c33298b96a1010e61a7bcac3212db7f58dc3d360888548cfd11424265` |
| CATL 2024H1 | 2024-07-26 | 1,684,794 | `2a690cb2471c1f0d4539d909a9f068c03710a838ddd35313175790169e85eab1` |
| EVE 2023Q3 | 2023-10-26 | 576,992 | `dafbcdf7980cbfcb154a9c4dc1a9456ce04dc32066ca92a59653ceeeb4148f49` |
| EVE 2023FY | 2024-04-19 | 6,280,048 | `959d6d51d529fd5129c829d1358ad41d384c95560ef2f8dc23caedd91e01f33e` |
| EVE 2024Q1 | 2024-04-25 | 658,022 | `7427e016767527a676a9ebe20fcf23df4d4ee786edd10e231fe6791416d47019` |
| EVE 2024H1 corrected | 2024-09-03 | 5,248,825 | `28f193e0c8f4d19b4868d451d29ad47d52f0c4ba8d3bf3f34705e5f8b885e652` |

The EVE 2024H1 facts retain `restatement_status: restated`. They are eligible only at a research time on or after the corrected filing became available. The earlier filing is not mixed into this package.

## Review Procedure

1. Verified each local payload starts with a PDF signature and matches the frozen SHA-256.
2. Extracted text locally only to locate statement rows.
3. Rendered the 34 relevant pages and visually checked all 48 cells, including units, signs, statement scope, row, column and period.
4. Normalized CATL's reported `万元` values by `10,000` and EVE's reported `元` values by `1` using `Decimal`.
5. Stored physical PDF-page locators, official links, publication/retrieval times, source hashes and correction lineage.
6. Recomputed three golden cases with the production formula module and validated every public artifact and package hash.

The CATL 2023 annual-report income-statement cells are on physical PDF page 120, whose printed footer is page 119. The locator intentionally uses physical PDF page numbering so automated rendering is reproducible.

## Decision Boundary

- Official SZSE/CNInfo-derived material passes the technical requirements for the narrowly scoped `FIXTURE-ONLY` outcome: CATL and EVE, four periods each, six metrics per filing.
- This does not establish live ingestion reliability, broad A-share coverage, redistribution rights for full filings, or real-user value.
- Tushare remains `REJECT` for runtime, committed demo, redistribution and public-package use because its documented license boundary is incompatible with those uses.
- Raw PDFs, extracted full text and rendered pages remain local and Git-ignored. The public package contains normalized factual cells, metadata, hashes, locators and official links only.

The owner signed the representative 20-fact sample in [`g0-owner-signoff.md`](g0-owner-signoff.md). The independent completion reviewer returned `VERDICT: PASS` after verifying the package and the adjacent-year YoY regression correction; G0 has no remaining findings.

## Reproduction

```bash
uv run python scripts/build_g0_fixtures.py
uv run python scripts/validate_contracts.py
uv run pytest -q tests/domain/test_g0_fixtures.py tests/domain/test_finance.py
```

All three commands passed before this record was prepared.
