# G3 Primary Benchmark Data Signoff

Status: `PREPARED_AWAITING_OWNER_SIGNOFF`

This is the second of three intentionally small owner signoffs required by the V1.4
protocol. It authorizes the already frozen data package for the primary experiment; it
does not claim that the research hypothesis is supported and it does not unseal Final
Test.

## Frozen package

- Package ID: `package_v1_4_primary_battery_earnings_quality`
- Package SHA-256: `3638eb1ca7b8192cb6a901f4b0d51c8373ccaff1e776758605f1d4b975cb1c3f`
- Pre-registered suite SHA-256:
  `2c112ff26cbbf0488a40db029c6a849b11ee35ffbc3353ffbf1e6f61282311c0`
- Public contents: 24 Source Documents, 144 normalized Financial Facts, 24 synthetic
  Evidence Chunks, and 24 Benchmark Cases.
- Split: 12 Evolution cases (CATL and EVE), 6 Validation cases (Gotion), and 6 sealed
  Final Test cases (Sunwoda).
- Required metrics per report: revenue, operating cost, net income, operating cash flow,
  accounts receivable, and inventory.
- Raw announcement PDFs and verifier-only ground truth are not committed. Their hashes,
  official links, publication times, and physical-page locators are retained.
- `formal_run_authorized` remains `false` until the owner explicitly signs this package.

The machine-readable package is
[`data/fixtures/v1.4-primary/manifest.json`](../../data/fixtures/v1.4-primary/manifest.json).

## Verification performed

- The 16 newly acquired filings were downloaded from official CNInfo artifact URLs and
  matched against their frozen SHA-256 values.
- All 96 newly normalized metric cells were found on their declared physical PDF pages.
- The 48 previously signed G0 facts were copied without changing their source artifacts.
- Four representative statement pages were rendered and visually checked:
  CATL 2024FY page 119, EVE 2024Q3 page 11, Gotion 2024H1 page 71, and Sunwoda 2024FY
  page 129.
- Contract validation rechecks schema validity, referential integrity, point-in-time
  cutoffs, company split isolation, Final Test sealing, public file hashes, and package
  hash stability without opening private ground truth.

## Minimal owner sample

The sample below covers every target report once. Values are normalized CNY revenue;
page numbers are physical PDF pages. The remaining five metrics for each row carry the
same source document and can be inspected through the case manifest.

| Ticker | Period | Revenue (CNY) | PDF page | Document ID |
|---|---:|---:|---:|---|
| 002074 | 2023FY | 31,605,490,020.32 | 122 | `doc_v14_gotion_2023fy` |
| 002074 | 2023Q3 | 21,778,492,192.22 | 7 | `doc_v14_gotion_2023q3` |
| 002074 | 2024FY | 35,391,817,095.44 | 132 | `doc_v14_gotion_2024fy` |
| 002074 | 2024H1 | 16,793,872,660.65 | 71 | `doc_v14_gotion_2024h1` |
| 002074 | 2024Q1 | 7,507,913,610.08 | 7 | `doc_v14_gotion_2024q1` |
| 002074 | 2024Q3 | 25,174,850,704.11 | 8 | `doc_v14_gotion_2024q3` |
| 300014 | 2023FY | 48,783,587,175.86 | 99 | `doc_g0_eve_2023fy` |
| 300014 | 2023Q3 | 35,528,837,484.66 | 11 | `doc_g0_eve_2023q3` |
| 300014 | 2024FY | 48,614,556,525.09 | 97 | `doc_v14_eve_2024fy` |
| 300014 | 2024H1 | 21,659,398,588.08 | 62 | `doc_g0_eve_2024h1_corrected` |
| 300014 | 2024Q1 | 9,317,321,354.65 | 10 | `doc_g0_eve_2024q1` |
| 300014 | 2024Q3 | 34,049,276,929.36 | 11 | `doc_v14_eve_2024q3` |
| 300207 | 2023FY | 47,862,226,994.24 | 133 | `doc_v14_sunwoda_2023fy` |
| 300207 | 2023Q3 | 34,318,739,236.58 | 10 | `doc_v14_sunwoda_2023q3` |
| 300207 | 2024FY | 56,020,634,117.81 | 129 | `doc_v14_sunwoda_2024fy` |
| 300207 | 2024H1 | 23,918,383,157.44 | 67 | `doc_v14_sunwoda_2024h1` |
| 300207 | 2024Q1 | 10,974,999,651.78 | 9 | `doc_v14_sunwoda_2024q1` |
| 300207 | 2024Q3 | 38,278,680,524.37 | 10 | `doc_v14_sunwoda_2024q3` |
| 300750 | 2023FY | 400,917,044,900.00 | 120 | `doc_g0_catl_2023fy` |
| 300750 | 2023Q3 | 294,677,250,600.00 | 10 | `doc_g0_catl_2023q3` |
| 300750 | 2024FY | 362,012,554,000.00 | 119 | `doc_v14_catl_2024fy` |
| 300750 | 2024H1 | 166,766,833,600.00 | 69 | `doc_g0_catl_2024h1` |
| 300750 | 2024Q1 | 79,770,778,600.00 | 8 | `doc_g0_catl_2024q1` |
| 300750 | 2024Q3 | 259,044,748,600.00 | 9 | `doc_v14_catl_2024q3` |

## Owner decision

Pending. The owner should confirm that this 24-report sample, company grouping, and
public-data treatment may be used for the primary experiment. On confirmation, the
manifest and this evidence record will be changed to `SIGNED`, while Final Test remains
sealed until the protocol reaches that stage.

## Limitations

- Public Evidence Chunks are clearly labeled synthetic normalized summaries, not filing
  quotations.
- This package covers four battery-sector companies and does not establish full-market
  generalization.
- No real-user value has been validated.
- No formal model experiment has been run and no `SUPPORTED` conclusion is recorded.
