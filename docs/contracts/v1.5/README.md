# ResearchForge V1.5 Productization Contracts

These contracts implement the active direction in
[`researchforge-v1.5-product-thesis.md`](../../product/researchforge-v1.5-product-thesis.md).
They extend the product boundary without changing any frozen V1.4 artifact, benchmark or
experiment contract.

## Contract map

| Contract | Governs |
|---|---|
| [`real-data-ingestion.md`](real-data-ingestion.md) | Official-disclosure discovery, deterministic six-metric extraction, provenance, isolation and abstention |
| [`product-research-run.md`](product-research-run.md) | The Company + Period + Question product boundary and non-fallback rule |
| [`human-usability-pilot.md`](human-usability-pilot.md) | Preparation and evidence rules for real human pilot sessions |

Machine-readable schemas live in `schemas/v1.5/`. Existing research artifacts produced by the
bounded V1.4 workflow continue to validate against `schemas/v1.4/`; their content hashes and
semantics must not be rewritten.

## Version boundary

- Active product direction and new productization records: `1.5.0`.
- Preserved workflow, research-result and experiment artifacts: `1.4.0`.
- The historical fixture folder named `v1.5-contingency` is a frozen V1.4 experiment input, not
  a V1.5 product data namespace.

The contract package remains narrow: CATL 2024H1, CATL 2024FY and BYD 2024H1 use the same
six-metric extractor. `product-package-index.schema.json` binds the three child packages by hash
without mixing fixtures or Benchmark data. OCR, broader metrics, model-selected numbers and
general document parsing remain outside this boundary.
