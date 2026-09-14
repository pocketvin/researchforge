# V2 filing-research contracts

These schemas are versioned separately from V1.8.5 and historical V1.x artifacts.
They describe actual Pydantic boundaries in `src/researchforge/v2/contracts.py`
and the reference-backed evaluator in `src/researchforge/v2/quality.py`.

- Product requests must not contain hidden reference labels or benchmark answers.
- Tool arguments are validated before dispatch; source IDs resolve only inside the current run.
- Model output confidence and notebook completeness are not measured benchmark scores.
- Tables/images are preserved as candidates until numeric/semantic verification supports promotion.
- Partial, unsupported, unverifiable and failed states must remain distinct from verified success.
- No private hidden reasoning/encrypted reasoning items are serialized into a public artifact.
- A schema-valid result alone is not proof of financial correctness.

## Exports

- `schemas/v2/research-request.schema.json`
- `schemas/v2/search-input.schema.json`
- `schemas/v2/read-input.schema.json`
- `schemas/v2/image-input.schema.json`
- `schemas/v2/facts-input.schema.json`
- `schemas/v2/calculate-input.schema.json`
- `schemas/v2/counter-input.schema.json`
- `schemas/v2/series-extract-input.schema.json`
- `schemas/v2/series-calculate-input.schema.json`
- `schemas/v2/hypothesis.schema.json`
- `schemas/v2/open-question.schema.json`
- `schemas/v2/research-objective.schema.json`
- `schemas/v2/working-state.schema.json`
- `schemas/v2/submission.schema.json`
- `schemas/v2/numeric-assertion.schema.json`
- `schemas/v2/finding.schema.json`
- `schemas/v2/analysis-section.schema.json`
- `schemas/v2/research-report.schema.json`
- `schemas/v2/claim-review.schema.json`
- `schemas/v2/semantic-review.schema.json`
- `schemas/v2/trace-event.schema.json`
- `schemas/v2/numeric-reference.schema.json`
- `schemas/v2/evidence-alternative.schema.json`
- `schemas/v2/evidence-requirement.schema.json`
- `schemas/v2/finding-requirement.schema.json`
- `schemas/v2/requirement-assessment.schema.json`
- `schemas/v2/quality-case.schema.json`
- `schemas/v2/semantic-annotations.schema.json`
- `schemas/v2/benchmark-atomic-claim-assessment.schema.json`
- `schemas/v2/benchmark-semantic-assessment-draft.schema.json`
- `schemas/v2/benchmark-suite-manifest.schema.json`
- `schemas/v2/benchmark-suite-execution.schema.json`
- `schemas/v2/heldout-document.schema.json`
- `schemas/v2/heldout-human-judgment.schema.json`
- `schemas/v2/heldout-candidate-result-ref.schema.json`
- `schemas/v2/heldout-blind-candidate.schema.json`
- `schemas/v2/heldout-blind-review-case.schema.json`
- `schemas/v2/heldout-blind-review-package.schema.json`
- `schemas/v2/heldout-human-judgment-file.schema.json`
- `schemas/v2/heldout-human-acceptance-summary.schema.json`
- `schemas/v2/heldout-runtime-case.schema.json`
- `schemas/v2/heldout-acceptance-attempt.schema.json`
- `schemas/v2/heldout-bundle-manifest.schema.json`
- `schemas/v2/heldout-suite-seal.schema.json`
- `schemas/v2/development-issuer-alias-group.schema.json`
- `schemas/v2/development-issuer-exclusion-manifest.schema.json`
- `schemas/v2/development-exposure-snapshot.schema.json`

The committed V2 schemas are generated from the live Pydantic contracts by
`scripts/export_v2_schemas.py`; `tests/v2/test_schema_exports.py` fails on drift.

Quality references distinguish `provided`, `verified`, and `suspect` integrity. Imported
benchmark gold labels are not automatically trusted as verified truth. A suspect label may
still be used to measure document/evidence observation and runtime efficiency, but it is
excluded from automatic reference-answer scalar measurement and cannot support a product
quality claim.
The tracked `docs/contracts/v2/benchmarks/financebench-public-development-10-v1.json`
is a public **development/canary** suite, not validation or held-out evidence. Its selection
manifest contains only question/company/document/reasoning metadata, pins the FinanceBench
commit/source SHA and carries a canonical suite hash. Gold answer/justification/evidence fields
are deliberately absent from the tracked suite manifest.
Held-out quality acceptance is governed by `docs/contracts/v2/heldout-quality-protocol.md`.
Acceptance-v2 freezes unseen runtime questions/source bytes but requires no human-authored reference
answers or evidence labels. Human input is choice-only after the Runs finish: blind A/B preference
or a meets-standard decision. `scripts/build_v2_heldout_review.py` renders the finished Runs into a
private offline `review.html` with implementation-neutral A/B cards; the last click automatically
downloads a judgment file and `scripts/summarize_v2_heldout_review.py` restores the hidden candidate
identity and aggregates the choices. The default owner suite is 8 cases / 4 issuer groups / 4 strata,
so a complete acceptance requires at most eight human choices.
Before a seal is created, ResearchForge also freezes a private `development-exposures.json`
snapshot. It combines the tracked issuer exclusions, the public development suite, the complete
locally cached FinanceBench public source when present, and persisted V2 run requests. The snapshot
stores exact question hashes rather than question text and is content-bound by the public seal.
Held-out sealing rejects both issuer overlap and exact normalized-question overlap. The tracked
issuer exclusion manifest covers the entire 32-issuer FinanceBench public universe, not just cases
that happened to be executed during development.
No held-out acceptance seal is currently committed; the presence of these schemas is not evidence
that an independent held-out evaluation has been performed.
