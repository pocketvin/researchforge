# G3 V1.5 Contingency Package Freeze

Status: `FROZEN_CONTINGENCY_SEALED`

The one permitted fallback experiment is prepared before any formal V1.4 provider run.
It is an inactive contingency, not a second chance to tune against the primary result.

## Immutable commitment

- Package ID: `package_v1_5_contingency_battery_earnings_quality`
- Package SHA-256:
  `ba95986b94d416e7c5d3960749d253463d61161ca081b3454c4428b6344c93f4`
- Pre-registered suite SHA-256:
  `2a5381ce526c961773aad69bf28a9b9c21d1735fa5d132d3e5d356f4aaeef755`
- Public package: 24 Source Documents, 144 Financial Facts, 24 explicitly synthetic
  Evidence Chunks, and 24 Benchmark Cases.
- Raw PDFs and verifier-only ground truth remain in Git-ignored directories.
- `formal_run_authorized` and `contingency_activation_authorized` are both `false`.
- Activation is permitted only if the primary Validation rejects its Candidate.

Machine-readable commitments:
[`suite`](../../benchmark/suites/v1.5-contingency-preregistered.json) and
[`package`](../../data/fixtures/v1.5-contingency/manifest.json).

## Frozen grouping

| Split | Companies | Cases |
|---|---|---:|
| Evolution | 鹏辉能源 (`300438`), 孚能科技 (`688567`) | 12 |
| Validation | 比亚迪 (`002594`) | 6 |
| Final Test | 珠海冠宇 (`688772`) | 6 |

Every company contributes the same six periods: `2023Q3`, `2023FY`, `2024Q1`,
`2024H1`, `2024Q3`, and `2024FY`. The four company groups have zero overlap with each
other and with the V1.4 primary suite.

## Verification evidence

- All 24 official CNInfo PDFs match frozen SHA-256 values.
- Every one of the 144 normalized values is present on its declared physical PDF page.
- Every case binds exactly one company-report pair, six facts, one synthetic evidence
  chunk, one source document, a publication cutoff, and a verifier-only truth hash.
- Public evidence is synthetic normalized factual text and is never represented as a
  filing quotation.
- Package and public-artifact hashes reproduce deterministically.
- Four statement pages were rendered and visually checked for scope, units, columns,
  values, and signs:
  - 鹏辉能源 2024FY page 84;
  - 孚能科技 2023FY page 131;
  - 比亚迪 2024H1 page 84, whose statement unit is CNY thousands;
  - 珠海冠宇 2024FY page 124.

## Stop conditions

This package remains sealed when the primary Candidate is adopted and passes its Final
Test. If the primary experiment is unsupported, its complete negative record is frozen
before this package can be activated as V1.5. The second formal experiment is final: an
unsupported result must be reported as an unmet research objective rather than changed
or rerun.

No OpenAI request was used to prepare or validate this package. Spend remains USD 0.
