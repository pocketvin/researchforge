# ResearchForge Project Status

**Updated:** 2026-09-05
**Contract package:** 1.5.0
**Product scope:** V1.7
**Scope: V1.7 general company research**

Contract package: 1.5.0
Current gate: RELEASE_FREEZE
Scope: V1.7 general company research

## Current milestone

**V1.7 Engineering Complete — READY FOR OWNER ACCEPTANCE**

ResearchForge now executes a question-driven, evidence-first company research flow:

`Company / Ticker → Official Filing → Full-text Evidence → Skill Routing → Research Plan → Claims / Deep Analysis → Verification → Trace`

The deterministic six-fact layer remains the numerical backbone. General Research adds full-filing Evidence retrieval, question-specific Skills, counter-evidence, deeper analysis sections, overall judgment and follow-up questions without allowing model memory to invent financial truth.

## V1.7 acceptance evidence

- Quick live regression: 贵州茅台 / NVIDIA / 腾讯 all succeeded from CNINFO / SEC / HKEX official sources.
- Extended nine-company regression: **6 trusted successes + 3 explicit safe abstentions; overall PASS**.
- NVIDIA retrieval hardening increased the real growth-analysis result from 2 Findings to **6 Findings / 4 Deep Analysis sections / 5 Follow-ups**.
- V1.7 n8n workflow is separate from preserved historical V1.6/V1.5 artifacts and returns Intent, Plan, Deep Analysis, Judgment, Follow-ups and Evidence Coverage from the same backend.
- Package versions, API health, Web and n8n active entry points are aligned to **1.7.0**.

## Full engineering gate — PASS

Verified on the final working tree:

- `uv lock --check`, Ruff format/check and strict mypy: PASS; mypy checked **101 source files**.
- `pytest -q`: **207 passed**.
- Contract validation: PASS; V1.7 schemas active while preserved V1.4/V1.5 historical contracts still validate.
- Frontend: typecheck/lint/build + **4 unit tests + 3 mocked E2E + 3 live-backend E2E**: PASS.
- n8n source: generated V1.7 workflow check + **10 Node tests**: PASS.
- Fresh Docker API/frontend build, PostgreSQL/API/Web health and 3 reviewed-cache Docker runs: PASS.
- Actual n8n 2.37.9 V1.7 runtime: 3 autonomous cases, five identical backend artifact families, native form, idempotent replay and 5 HTTP failure checks: PASS.
- Actual n8n transport-only fixture: **5/5 bounded failure scenarios PASS** and no research truth supplied.
- `git diff --check`: PASS before final documentation closeout.

## Release boundary

Engineering construction is complete. `RELEASE_FREEZE` remains **in progress only because owner manual acceptance is a human action** and is not fabricated by automation. There is no six-person Human Pilot requirement.

Owner acceptance should confirm:

1. A representative arbitrary-company Web request feels useful and sufficiently deep.
2. Supporting Evidence and Trace are understandable.
3. At least one unsupported case is clearly presented as a bounded failure, not a plausible report.
4. Any remaining UI/prompt limitations are either fixed or explicitly accepted as non-blocking.

## Known bounded limitations

- CN/US/HK are supported source adapters; universal listed-company/layout coverage is not claimed.
- Six deterministic financial facts remain required for the current numerical backbone.
- Latest BYD, Xiaomi and Alibaba examples currently expose parser/layout boundaries and safely abstain.
- V1.7 does not include real-time news, broker research, price targets, trading, portfolio management or unrestricted multi-agent debate.
- Human usefulness, analyst productivity improvement and investment performance are not validated claims.

## Resume here

Read first: [README.md](README.md), [DECISIONS.md](DECISIONS.md), the [final delivery roadmap](docs/product/researchforge-final-delivery-roadmap.md), [V1.7 change note](docs/product/v1.6-to-v1.7-general-research-change-note.md), and [PORTFOLIO.md](PORTFOLIO.md).

Primary checks:

```bash
RESEARCHFORGE_REASONING_MODE=deterministic uv run python scripts/autonomous_regression.py --all
RESEARCHFORGE_REASONING_MODE=deterministic uv run python scripts/start_demo.py --no-build
uv run python scripts/validate_contracts.py
git diff --check
git status --short
```
