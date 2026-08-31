# G0 Controlled Filing Read Plan

Prepared: `2026-08-30`  
Status: `COMPLETED_WITH_OWNER_AUTHORIZATION`  
Filesystem scope: `data/raw/g0/` only (Git-ignored)

## Purpose and Limits

Read exactly eight official filing PDFs to construct the G0 reconciliation sample. No home-directory scan, recursive Workspace scan, provider login, Tushare call, OCR upload, external message, file deletion, or raw-PDF commit is permitted.

The expected local download is less than approximately 40 MB. Risks are limited to network bandwidth, potentially imperfect PDF text extraction and accidental inclusion of copyrighted filing text. Mitigations are exact URLs, SHA-256 hashes, page-level visual checks, ignored raw storage and a public package containing normalized facts/locators rather than full PDFs.

## Frozen Filing List

| Company | Period | Published/corrected | Official filing |
|---|---|---|---|
| CATL (`300750.SZ`) | 2023Q3 | 2023-10-20 | [2023 third-quarter report](https://static.cninfo.com.cn/finalpage/2023-10-20/1218095874.PDF) |
| CATL (`300750.SZ`) | 2023FY | 2024-03-16 | [2023 annual report](https://static.cninfo.com.cn/finalpage/2024-03-16/1219313047.PDF) |
| CATL (`300750.SZ`) | 2024Q1 | 2024-04-16 | [2024 first-quarter report](https://static.cninfo.com.cn/finalpage/2024-04-16/1219619642.PDF) |
| CATL (`300750.SZ`) | 2024H1 | 2024-07-26 | [2024 half-year report](https://disc.static.szse.cn/disc/disk03/finalpage/2024-07-26/6d9c1c9e-239e-4946-a477-84ea91313086.PDF) |
| EVE Energy (`300014.SZ`) | 2023Q3 | 2023-10-26 | [2023 third-quarter report](https://static.cninfo.com.cn/finalpage/2023-10-26/1218149368.PDF) |
| EVE Energy (`300014.SZ`) | 2023FY | 2024-04-19 | [2023 annual report](https://static.cninfo.com.cn/finalpage/2024-04-19/1219668064.PDF) |
| EVE Energy (`300014.SZ`) | 2024Q1 | 2024-04-25 | [2024 first-quarter report](https://static.cninfo.com.cn/finalpage/2024-04-25/1219791452.PDF) |
| EVE Energy (`300014.SZ`) | 2024H1 | corrected 2024-09-03 | [corrected 2024 half-year report](https://static.cninfo.com.cn/finalpage/2024-09-03/1221114672.PDF) |

The corrected EVE Energy half-year report is the active statement for a research time after `2024-09-03`. The original `2024-08-23` filing remains referenced in the source evidence as superseded and must not be silently mixed with the corrected values.

## Extraction and Review Procedure

1. Download the eight PDFs into `data/raw/g0/` with deterministic names; reject non-PDF content and failed HTTP responses.
2. Record byte count and SHA-256 before parsing.
3. Extract layout-preserving text locally and locate the consolidated income statement, balance sheet and cash-flow statement.
4. For every document, capture six reported values: `revenue`, `operating_cost`, attributable `net_income`, `operating_cash_flow`, `accounts_receivable` and `inventory`.
5. Normalize all currency values to CNY base units using `Decimal`; retain reported scale, sign, period basis, scope, CAS standard, restatement status, published/retrieved times and page/table/row/column locators.
6. Render only the relevant statement pages and visually compare each selected cell against the PDF. Text extraction alone is not acceptance evidence.
7. Produce 48 reported facts plus deterministic gross-profit, gross-margin, growth/comparison and divergence records where meaningful. Missing values remain unavailable and do not reduce the disclosed denominator silently.
8. Validate every public artifact against V1.4 schemas, freeze hashes, and present a compact sample/signoff record to the owner.

## Planned Golden Cases

- CATL 2024Q1 earnings quality;
- EVE Energy 2024Q1 earnings quality, including negative operating cash flow;
- CATL versus EVE Energy 2024H1 peer evidence, using the corrected EVE filing.

These are manual/deterministic G0 cases, not model-generated investment analysis and not formal Benchmark runs.

## Completion Record

The owner authorized this exact bounded read. All eight files were downloaded into the ignored directory, verified as PDFs, hashed, locally extracted, and visually reconciled. The public-safe output contains 8 Source Documents, 48 Financial Facts and 3 deterministic golden cases; no raw PDF or extracted full text is committed. Exact denominators, hashes and limitations are recorded in [`g0-reconciliation.md`](g0-reconciliation.md).
