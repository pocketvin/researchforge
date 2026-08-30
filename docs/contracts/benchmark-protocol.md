# Evolution Benchmark Protocol

Contract version: `1.3.0`

The V1 formal benchmark is restricted to earnings-quality analysis. Its purpose is to test whether a repeated, verifier-confirmed omission can be reduced by a bounded research-skill patch without damaging other behavior.

## 1. Case Population

- Target size: 24–36 high-quality company-quarter cases.
- Company count: 4–6.
- Each case contains frozen financial facts, allowed filing evidence, reporting period, research time, verifier-only ground truth, and package hashes.
- Ground truth SHOULD be independently annotated by two reviewers and adjudicated when they disagree.
- Every case MUST pass point-in-time, period, source-locator, and package-integrity checks before freezing.

This dataset supports an engineering proof of concept. Results MUST NOT be presented as broad evidence across all companies, markets, or models.

## 2. Split Isolation

Cases are assigned to `evolution`, `validation`, or `final_test` before experiment runs.

- Split by `group_key`, normally company. A group MUST occur in only one split.
- If a pre-registered temporal grouping is used, adjacent periods sharing substantially the same filings MUST not cross splits.
- Duplicate facts, evidence chunks, ground-truth wording, or derived case variants MUST not cross splits.
- Final Test is sealed before the first Evolution run.

Recommended allocation is approximately 50% Evolution, 25% Validation, and 25% Final Test while preserving whole groups. Exact counts and group assignments are recorded in the experiment manifest before running.

## 3. Access Matrix

| Actor | Evolution input | Evolution labels | Validation input | Validation labels | Final input/labels |
|---|---:|---:|---:|---:|---:|
| Researcher | yes | no | during validation | no | only after candidate freeze; labels never |
| Optimizer | failures/feedback only | summarized verified failures | no | no | no |
| Deterministic Verifier | yes | yes | yes | yes | after unsealing |
| Human reviewer | as needed | yes | as needed | yes | only after unsealing |

Product ingestion and benchmark packages MUST use separate storage namespaces and credentials/access paths.

## 4. Compared Conditions

V1 compares:

1. `Base Agent`: same model, tools, retrieval, data, schema, budget, and orchestration, but no fundamental-research skill procedure.
2. `Seed Skill`: the frozen initial fundamental-research skill.
3. `Evolved Skill`: the adopted candidate skill.

Only the skill content/hash may differ between Seed and Evolved paired comparisons. Naive Reflection is optional and cannot block V1.

## 5. Repeated Runs

- Minimum repeats: 3 runs per case per compared condition.
- Use the same registered seed list where the provider supports seeds.
- Record model snapshot, temperature, token/tool/cost limits, prompt hashes, skill hash, tool versions, formula version, dataset hash, and evidence cutoff.
- A failed infrastructure run is retried according to the run lifecycle and excluded only with an explicit technical-failure record.
- A valid low-quality answer remains in the evaluation.

Counts, rates, and denominators MUST be reported. Confidence intervals MAY be reported but cannot compensate for leakage or very small group counts.

## 6. Case Package Boundary

A case manifest may expose IDs of allowed facts and evidence, but verifier ground truth remains in a verifier-only artifact. The runtime supplied to the Researcher MUST not include:

- expected conclusions;
- mandatory-check answers;
- failure labels;
- verifier prompts or scoring rules beyond public task instructions;
- Validation or Final Test feedback.

## 7. Pre-Registration

Before running Final Test, freeze and hash:

- case membership and group assignments;
- all package contents;
- initial and candidate skills;
- model and runtime configuration;
- verifier and formula versions;
- failure signatures;
- metric formulas and adoption thresholds;
- exclusion/retry rules.

The Final Test can be run once for the declared V1.3 result and only after Validation adoption. A failed Final Test cannot be silently reclassified as Validation or rerun after tuning.

## 8. Reporting

The report MUST separate:

- Validation evidence used for adoption;
- Final Test evidence used for generalization;
- deterministic failures;
- coverage failures;
- advisory qualitative judgments;
- infrastructure exclusions;
- case counts, run counts, and group counts.

Illustrative UI values such as `41% → 18%` are placeholders until replaced by computed results from immutable evaluation records.
