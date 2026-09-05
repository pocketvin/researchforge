# ResearchForge Project Status

**Updated:** 2026-09-05
**Contract package:** 1.5.0
**Product scope:** V1.7.2 workspace UX closeout over V1.7 General Company Research
**Scope: V1.7 general company research**

Contract package: 1.5.0
Current gate: RELEASE_FREEZE
Scope: V1.7 general company research

## Current milestone

**V1.7.2 Engineering Complete — READY FOR OWNER RE-ACCEPTANCE**

V1.7.1 established evidence-constrained model synthesis. The latest owner test judged the research output broadly acceptable and identified workspace continuity/clarity issues rather than a new research-engine failure. V1.7.2 closes those UX gaps without changing the research truth boundary.

## V1.7.2 workspace closeout

- Suggested Follow-ups immediately start a new research run in the current company/market/period context.
- `GET /v1/research-runs` exposes a bounded recent General Research list; persisted reports reopen without model reruns.
- Research state stays mounted while visiting the demoted **方法与实验** archive and returning.
- Workspace title prioritizes company + research intent; Run ID is secondary audit metadata.
- Main reading remains Conclusion / Findings / Deep Analysis. Facts, Calculations, Supporting Evidence, Counter Evidence, future-review checklist and Trace are audit-on-demand.
- Monitoring is shown as **下一份财报重点看什么** with a clear “not an automatic alert” explanation; generic entries can be suppressed.
- Quality Lab historical assets are preserved but removed from primary navigation. Unloaded adoption steps have no fake arrow; loaded steps navigate to real sections.
- Technical Claim labels use readable Chinese presentation while raw values remain available for audit.

## Research-quality evidence retained

- V1.7 extended Golden Regression: **6 trusted successes + 3 explicit safe abstentions; PASS**.
- V1.7.1 real-model smoke: 贵州茅台 `company_overview` **8 Claims / 5 sections**; NVIDIA `growth_analysis` **6 / 5**; 腾讯 `business_analysis` **6 / 5**.
- Model synthesis and `evidence_summary_fallback` remain explicitly distinct.

## Full engineering gate — PASS

Verified on the V1.7.2 working tree:

- `uv lock --check`, Ruff format/check and strict mypy: PASS; mypy checked **105 source files**.
- `pytest -q`: **211 passed**.
- Contract validation: PASS; preserved historical contracts remain valid.
- Frontend: typecheck/lint/build + **7 unit tests + 3 mocked E2E + 3 live-backend E2E**: PASS.
- n8n source: generated workflow check + **11 Node tests**: PASS.
- Fresh Docker API/frontend build + PostgreSQL/API/Web health + **3 Docker smoke cases**: PASS.
- Packaged history endpoint returned persisted General Research runs and excluded reviewed-cache snapshot smoke runs.
- Actual n8n 2.37.9 V1.7.2 runtime: **3 success cases**, idempotent replay/native form checks and 5 HTTP failure checks: PASS.
- Actual n8n transport-only fixture: **5/5 bounded failure scenarios PASS**.

## Release boundary

`RELEASE_FREEZE` remains **in progress only for owner re-acceptance**. No six-person Human Pilot is required. The owner should now verify the continuous workflow: run research → click a follow-up → see the new run in history → reopen the prior report → visit 方法与实验 and return without losing state → confirm the collapsed audit hierarchy feels understandable.

## Known bounded limitations

- CN/US/HK official-source adapters are supported; universal issuer/layout coverage is not claimed.
- Six deterministic financial facts remain the current numerical backbone.
- BYD latest, Xiaomi and Alibaba examples expose parser/layout boundaries and safely abstain in the existing extended regression.
- “下一份财报重点看什么” is a review checklist, not a scheduled notification service.
- 方法与实验 is historical technical evidence, not a normal research workflow.
- Real-time news, broker research, price targets, trading, portfolio management and unrestricted multi-agent debate remain out of scope.

## Resume here

Read first: [README.md](README.md), [DECISIONS.md](DECISIONS.md), the [V1.7.2 change note](docs/product/v1.7.1-to-v1.7.2-workspace-ux-change-note.md), the [V1.7.1 synthesis note](docs/product/v1.7-to-v1.7.1-synthesis-change-note.md), the [final delivery roadmap](docs/product/researchforge-final-delivery-roadmap.md), and [PORTFOLIO.md](PORTFOLIO.md).
