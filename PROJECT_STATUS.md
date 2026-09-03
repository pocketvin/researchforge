# ResearchForge Project Status

Last updated: 2026-09-04
Machine-readable mirror: [`project-status.json`](project-status.json)

Contract package: 1.5.0
Current gate: GENERALIZATION
Scope: V1.5 active productization

## Current Position

- Active product direction: **V1.5 Productization — independently accepted**.
- V1.5 productization label: **V1.5 Product Ready**.
- Product thesis: **Direction Ready**.
- Real-data vertical slice: **verified; six metrics now originate from deterministic PDF recovery**.
- Research UX and Quality Lab: **verified in unit, E2E and live-browser runs**.
- Legacy Web-only pilot kit: **implemented but not executed; 0 real-human sessions**.
- Human usefulness: **UNVALIDATED; formal Web+n8n evaluation is deferred to final Phase 6**.
- Local engineering gate: **passed**.
- Published GitHub CI: **passed** on commit `b96c4b0` in run
  [33731347766](https://github.com/pocketvin/researchforge/actions/runs/33731347766).
- Final independent V1.5 acceptance: **VERDICT: PASS**.
- Current product boundary: CATL `2024H1`, CATL `2024FY` and BYD `2024H1`, `filing_analysis`,
  strict `product` namespace, one shared deterministic extractor and Research backend.
- Phase 3 local checkpoint: **passed; public CI for these changes is pending publication**.
- Public repository: [pocketvin/researchforge](https://github.com/pocketvin/researchforge).

The current authority is
[`docs/product/researchforge-v1.5-product-thesis.md`](docs/product/researchforge-v1.5-product-thesis.md).
The frozen remaining delivery order is
[`docs/product/researchforge-final-delivery-roadmap.md`](docs/product/researchforge-final-delivery-roadmap.md).
V1.5 success does not depend on a supported Evolution hypothesis.

## Implemented V1.5 Evidence

### Product narrative and contracts

- README, Portfolio, demo and product docs lead with Company + Period + Research Question.
- V1.5 schemas cover product requests, ingestion manifests, pilot records and checkpoints.
- The primary user journey contains no Candidate, Validation or Final Test terminology.

### Real public disclosure

- Allowlisted official SZSE CATL 2024H1 PDF acquired and hash-checked.
- Source PDF: 1,684,794 bytes; SHA-256
  `2a690cb2471c1f0d4539d909a9f068c03710a838ddd35313175790169e85eab1`.
- Derived package: one Source Document, six deterministically recovered Financial Facts and eight page-located
  Evidence Chunks; package hash
  `2207187bd5d466d8c79a09863703bb373ec1890829f84505fc994c5e071669de`.
- Product, fixture and Benchmark namespaces are explicit; mismatch refuses fallback.
- The filing registry contains document identity only; it supplies no fact value, page locator or
  evidence text to the extractor.
- Hash, byte-count, PDF-magic, missing/duplicate row, unresolved period column, conflicting unit or
  missing native text causes abstention.

### Phase 2 reusable extraction

- One company-independent extractor supports exactly revenue, operating cost, attributable net
  income, operating cash flow, accounts receivable and inventory.
- It detects consolidated statement boundaries, joins wrapped rows, carries cash-flow context
  across a page boundary, resolves period columns and units, and normalizes with `Decimal`.
- Every promoted value has raw token, source page/lines, table, row, column, unit, evidence hash,
  page-text hash and canonical recovery hash in the ingestion manifest.
- The CATL 2024H1 package and nine focused ingestion tests pass locally. The full Phase 2
  engineering gate and GitHub CI passed; independent acceptance is intentionally deferred to the
  one final project-wide Phase 7 review.

### Phase 3 generalization

- All three official PDFs reproduce the published package and recovery hashes with the same
  extractor: 18 facts, 22 evidence chunks, 12 calculations and three successful Research Results.
- CATL 2024FY and BYD 2024H1 identities are configuration only; no expected numbers or source
  pages are fed into extraction. Missing/ambiguous values abstain.
- A hash-checked product index exposes the three cases while preserving the original CATL H1
  package and all frozen V1.4 data. Stale or tampered product artifacts are refused.
- All three cases passed the deterministic Verifier, live-backend Web E2E and Docker/PostgreSQL
  smoke before and after an Alembic down/up round-trip.
- [Generalization evidence](docs/evidence/v1.5-generalization/README.md) includes source identities,
  every recovered metric and locator, actual calculations, results, limitations and monitoring.
- CATL annual counter-evidence status is honestly `not_found`; annual results do not inherit an
  unsupported unaudited-interim limitation.

### Original CATL H1 research result

- The real-data cash-conversion path completed through all ten LangGraph stages.
- Net income: CNY `22,864,987,400.00`; operating cash flow: CNY
  `44,708,954,600.00`; deterministic cash conversion: `1.96x` displayed.
- Material claims resolve to exact fact and evidence IDs.
- Filing-based counter evidence covers non-recurring-profit context and unaudited status.
- Result includes limitations, monitoring trigger and a sanitized trace.
- A bounded model-backed smoke passed the Verifier with all main metrics at `1.0`; request cost
  was USD `0.0012008`.

### Core product UX

- Research begins with Company, Period, Question and Start Research.
- Output order is Executive Conclusion, Key Findings, Financial Facts, Calculations, Supporting
  Evidence, Counter Evidence, Risks & Limitations, Monitoring Plan and Research Trace.
- Facts, calculations, evidence and trace use keyboard-accessible progressive disclosure.
- Skill Lab is renamed **Quality Lab**, marked experimental/read-only and treated as secondary.

### Pilot and demo

- A privacy notice, participant task sheet, facilitator guide, observation rubric and schema-valid
  session template exist as legacy Web-only preparation assets. They are not the final dual-surface
  evaluation protocol and must not be run as the formal project Pilot.
- A real-data three-to-five-minute demo script and exact evidence record are present.
- Formal participants are not recruited until reusable extraction, generalization, n8n, UX and
  demo hardening are complete and the Web+n8n acceptance rules are frozen.

## Preserved V1.4 Baseline

The frozen Quality Lab result remains:

```text
RESEARCH_HYPOTHESIS_UNSUPPORTED_AFTER_TWO_EXPERIMENTS
```

- Primary result hash:
  `60d7620ca0f620e926c99f22a091d7305097dd787c28d89270977cb8a6c735ed`
- Contingency result hash:
  `dadd29917979b53a2b47ed66e7bfa9deae6ba8486802acc12bdba38ab3a3877f`
- Combined outcome hash:
  `bdc0c1aed55e930312f01ecaebee8969e96e7ff625b27b735b940fcff8a1d2af`
- Aggregate OpenAI spend after V1.5 smoke: USD `0.1547530 / 20.00`.
- No Candidate, Validation or Final Test was created or consumed.
- No further formal Evolution experiment is authorized.

V1.2–V1.4 schemas, historical scopes, fixture/Benchmark packages, thresholds and hashes are not
rewritten by V1.5.

## Phase 1 Closure Evidence

1. Local backend, frontend, migration, Docker and safety gates passed.
2. Current published commit passed all GitHub Actions jobs.
3. The independent read-only completion reviewer returned `VERDICT: PASS` with no required
   findings.
4. The share-safe Codex review file records the closure evidence.

Phase 1 remains closed. Phase 2 is closed as an engineering checkpoint. Phase 3 generalization is
active. Formal real-human evaluation remains deferred until Phase 6, and the next independent
review occurs only once at the final Phase 7 release gate.

## Honest Non-Claims

- Coverage is three filings across two companies, not the full A-share market.
- No real-human pilot has occurred; usefulness and market demand are unvalidated.
- Simulated usability evidence is not human evidence.
- ResearchForge is not a self-evolving or multi-agent system.
- The Evolution research hypothesis remains unsupported.
- The product does not provide investment advice, price prediction or trade execution.

## Single Next Action

Publish Phase 3 through green GitHub CI, then proceed directly to Phase 4's importable n8n
workflow over the same backend. No intermediate independent acceptance is required.

## Fast Resume

Read, in order:

1. `docs/product/researchforge-v1.5-product-thesis.md`
2. `docs/product/researchforge-final-delivery-roadmap.md`
3. `PROJECT_STATUS.md`
4. `docs/demo/v1.5-demo-evidence.md`
5. `docs/evidence/v1.5-phase2-financial-fact-extraction.md`
6. `DECISIONS.md`

Then run:

```bash
uv run python scripts/validate_contracts.py
git status --short
```
