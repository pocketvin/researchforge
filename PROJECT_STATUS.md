# ResearchForge Project Status

**Updated:** 2026-09-05
**Contract package:** 1.5.0
**Product scope:** V1.7.1 synthesis correction over V1.7 General Company Research
**Scope: V1.7 general company research**

Contract package: 1.5.0
Current gate: RELEASE_FREEZE
Scope: V1.7 general company research

## Current milestone

**V1.7.1 Engineering Complete — READY FOR OWNER RE-ACCEPTANCE**

The first V1.7 Owner Acceptance failed on synthesis quality: the running demo had inherited deterministic mode and presented verified filing excerpts too much like a finished analyst report. V1.7.1 corrects that failure without weakening the evidence boundary.

The active flow is now:

`Company / Ticker → Official Filing → Verified Facts + Full-text Evidence → Question Routing → Research Plan → Research Synthesis → Claim Verification → Evidence-on-demand Report → Trace`

General Research explicitly records `synthesis_mode=model` or `synthesis_mode=evidence_summary_fallback`. A fallback is labeled as a Verified Evidence Summary and is never presented as AI research synthesis.

## V1.7.1 owner-feedback correction

- Comprehensive questions now route to `company_overview` before narrower keyword matches.
- Model-backed Findings carry analytical title, Claim type, epistemic status, confidence, direction, Evidence IDs and only relevant Fact IDs.
- Company Overview requires evidence-backed breadth: at least 5 Findings and 5 analytical sections when the model path succeeds.
- Raw source-section headings, table/check-box noise and long filing excerpts are rejected from the primary model report.
- The one structure repair now receives safe validation feedback instead of blindly repeating the same request.
- Web is analysis-first/evidence-on-demand and visibly distinguishes `MODEL SYNTHESIS` from `EVIDENCE SUMMARY FALLBACK`.
- Packaged demo startup actively sets `RESEARCHFORGE_REASONING_MODE=auto`; deterministic remains explicit for CI/reproducible smoke only.

## Real-model verification

Official-source model synthesis succeeded across all three supported markets:

- 贵州茅台 comprehensive analysis → `company_overview`, **8 Claims / 5 analytical sections**.
- NVIDIA growth analysis → `growth_analysis`, **6 Claims / 5 analytical sections**.
- 腾讯 business-structure analysis → `business_analysis`, **6 Claims / 5 analytical sections**.

All three runs reported `synthesis_mode=model`; none reproduced the old “官方披露在该部分记录” template or `√适用 / □不适用` PDF noise in the primary report.

## Full engineering gate — PASS

Verified on the V1.7.1 working tree:

- `uv lock --check`, Ruff format/check and strict mypy: PASS; mypy checked **105 source files**.
- `pytest -q`: **210 passed**.
- Contract validation: PASS; V1.7 result schemas remain compatible while historical V1.4/V1.5 contracts are preserved.
- Frontend: typecheck/lint/unit/build + **5 unit tests + 3 mocked E2E + 3 live-backend E2E**: PASS.
- n8n source: generated workflow check + **11 Node tests**: PASS.
- Fresh Docker API/frontend build + PostgreSQL/API/Web health + **3 Docker smoke cases**: PASS.
- Actual n8n 2.37.9 V1.7.1 runtime: **3 success cases**, same five backend artifact families, idempotent replay, native form checks and five HTTP failure checks: PASS.
- Actual n8n transport-only fixture: **5/5 bounded failure scenarios PASS** and no research truth supplied.

## Release boundary

`RELEASE_FREEZE` remains **in progress only for owner re-acceptance**. Automation cannot convert green engineering tests into human product acceptance. There is no six-person Human Pilot requirement.

Owner re-acceptance should confirm:

1. A representative arbitrary-company request returns a useful `MODEL SYNTHESIS` report rather than a filing summary.
2. Findings/Deep Analysis answer “what happened / why it matters / what could contradict it”.
3. Fact and Evidence links are relevant and understandable when expanded.
4. A fallback is clearly labeled as evidence summary, and an unsupported case stops without a plausible fake report.
5. Remaining UX/prompt limitations are fixed or explicitly accepted as non-blocking.

## Known bounded limitations

- CN/US/HK official-source adapters are supported; universal listed-company/layout coverage is not claimed.
- Six deterministic financial facts remain required for the current numerical backbone.
- Latest BYD, Xiaomi and Alibaba examples expose parser/layout boundaries and safely abstain in the extended regression.
- V1.7.1 does not include real-time news, broker research, price targets, trading, portfolio management or unrestricted multi-agent debate.
- Human usefulness, analyst productivity improvement and investment performance remain unvalidated claims.

## Resume here

Read first: [README.md](README.md), [DECISIONS.md](DECISIONS.md), the [V1.7.1 change note](docs/product/v1.7-to-v1.7.1-synthesis-change-note.md), the [final delivery roadmap](docs/product/researchforge-final-delivery-roadmap.md), and [PORTFOLIO.md](PORTFOLIO.md).

Primary checks:

```bash
uv run python scripts/start_demo.py --no-build
RESEARCHFORGE_REASONING_MODE=deterministic uv run python scripts/autonomous_regression.py --all
uv run python scripts/validate_contracts.py
git diff --check
git status --short
```
