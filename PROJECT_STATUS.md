# ResearchForge Project Status

Last updated: 2026-09-03
Machine-readable mirror: [`project-status.json`](project-status.json)

Contract package: 1.5.0
Current gate: V15_PRODUCT
Scope: V1.5 active productization

## Current Position

- Active product direction: **V1.5 Productization**.
- Product thesis: **Direction Ready**.
- Real-data vertical slice: **verified**.
- Research UX and Quality Lab: **verified in unit, E2E and live-browser runs**.
- Legacy Web-only pilot kit: **implemented but not executed; 0 real-human sessions**.
- Human usefulness: **UNVALIDATED; formal Web+n8n evaluation is deferred to final Phase 6**.
- Local engineering gate: **passed**.
- Published GitHub CI: **passed** on commit `9a0feb1` in run
  [33690111534](https://github.com/pocketvin/researchforge/actions/runs/33690111534).
- Final independent V1.5 acceptance: **pending**.
- Current product boundary: CATL `2024H1`, `filing_analysis`, strict `product` namespace.
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
- Derived package: one Source Document, six reviewed Financial Facts and eight page-located
  Evidence Chunks; package hash
  `fdd6cc077607144b46b741aae3fe713eae09ca7c54c00bfbc43960847be45765`.
- Product, fixture and Benchmark namespaces are explicit; mismatch refuses fallback.
- Hash, byte-count, PDF-magic or reviewed-cell mismatch causes abstention.

### Research result

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

## Remaining Gate Work

1. Run the one final independent read-only V1.5 completion review.
2. Require `VERDICT: PASS`; retain any non-PASS result and correct only required issues.
3. Record the share-safe Codex review file.

After Phase 1 passes, Phase 2 is reusable deterministic extraction for exactly six financial
metrics. Formal real-human evaluation remains deferred until Phase 6.

## Honest Non-Claims

- Coverage is one company and one reporting period, not the full A-share market.
- No real-human pilot has occurred; usefulness and market demand are unvalidated.
- Simulated usability evidence is not human evidence.
- ResearchForge is not a self-evolving or multi-agent system.
- The Evolution research hypothesis remains unsupported.
- The product does not provide investment advice, price prediction or trade execution.

## Single Next Action

Run the final independent read-only V1.5 acceptance review against the already-published,
CI-green implementation and the Phase 1 documentation correction.

## Fast Resume

Read, in order:

1. `docs/product/researchforge-v1.5-product-thesis.md`
2. `docs/product/researchforge-final-delivery-roadmap.md`
3. `PROJECT_STATUS.md`
4. `docs/demo/v1.5-demo-evidence.md`
5. `DECISIONS.md`

Then run:

```bash
uv run python scripts/validate_contracts.py
git status --short
```
