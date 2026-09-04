# ResearchForge Project Status

**Updated:** 2026-09-05
**Contract package:** 1.5.0
**Product scope:** V1.6
**Scope: V1.6 autonomous productization**

Contract package: 1.5.0
Current gate: RELEASE_FREEZE
Scope: V1.6 autonomous productization

## Current milestone

**V1.6 Engineering Release Candidate — READY FOR OWNER ACCEPTANCE**

ResearchForge now supports a company-first autonomous research flow:

`Company / Ticker → Entity Resolution → Official Filing Discovery → Deterministic Extraction → Evidence / Claims / Trace → Research Result`

CN, US and HK are first-class live markets. Reviewed V1.5 filing packages remain immutable cache and regression evidence, not the product input boundary.

## Implemented in V1.6

- `POST /v1/autonomous-research-runs` accepts company/ticker, optional market/period and a research question.
- CNINFO, SEC EDGAR and HKEXnews own official company/filing discovery.
- CN native-PDF, SEC XBRL and HK IFRS paths recover the same six financial facts or fail closed.
- Simplified/traditional Chinese HK issuer resolution uses OpenCC and generic normalization, not company aliases.
- Dynamic Facts and Evidence are snapshotted per run so historical runs cannot drift after later acquisition.
- Exact reviewed company+period requests reuse immutable V1.5 packages before live acquisition.
- Web and the separate V1.6 n8n workflow call the same autonomous backend.
- Provider/network failures become explicit discovery/acquisition abstentions instead of uncaught exceptions.

## Golden Company Regression — PASS

Quick live set produced trusted success in every market:

- CN: 贵州茅台 → CNINFO → 2025FY → 6 Facts → completed Trace.
- US: NVIDIA → SEC → fiscal 2027Q2 → 6 Facts → completed Trace.
- HK: Tencent → HKEX → 2025FY → 6 Facts → completed Trace.

Extended nine-company regression also passed its fail-closed contract:

- Trusted success: 贵州茅台, NVIDIA, Tencent, 宁德时代, Apple and Microsoft.
- Explicit safe abstention: latest 比亚迪 (`STATEMENT_UNIT_UNRESOLVED`), Xiaomi and Alibaba (`HK_STATEMENT_UNRESOLVED`).
- No abstained case generated a Research Result.

## Full engineering gate — PASS locally
Verified on the current working tree:

- `uv lock --check`, Ruff and strict mypy: PASS; mypy checked 98 source files.
- `pytest -q`: **199 passed**.
- Contract validation: PASS; preserved V1.4/V1.5 hashes and historical evidence remain valid.
- Frontend: typecheck/lint/build + 4 unit tests + 3 mocked E2E + 3 live-backend E2E: PASS.
- n8n source: generated workflow check + 10 Node tests + ESLint: PASS.
- Fresh Docker API/frontend build and PostgreSQL/API/Web health checks: PASS.
- V1.6 Docker autonomous smoke: 3 reviewed-cache cases, each with 6 Facts and 10 Trace stages: PASS.
- Actual n8n 2.37.9 V1.6 runtime: 3 autonomous cases, identical five backend artifact families, native form, retry and 5 HTTP failure checks: PASS.
- Actual n8n transport-only fixture: 5/5 bounded failure scenarios: PASS.

The V1.6 public GitHub Actions run has **not** been claimed for this uncommitted release candidate.

## Release policy

RF-032 removed the six-person Web+n8n Human Pilot from the active release criteria. Existing Pilot protocols/templates remain historical evidence only.

Active release validation is:

`Golden Company Regression → Full Engineering Gate → Owner Acceptance → Release Freeze`

The first two stages are complete. There are no human-participant or engineering blockers currently known.

## Remaining acceptance
Only owner acceptance remains before marking `RELEASE_FREEZE` complete:

1. Manually submit representative arbitrary-company research through the Web surface.
2. Open at least one Fact/Evidence locator and the Research Trace.
3. Confirm an unsupported/failed case is understandable and does not look like a successful report.
4. Record any final product/prompt/UI issue; fix blockers or explicitly accept non-blocking limitations.

## Known bounded limitations

- V1.6 does not claim universal listed-company or filing-layout coverage.
- The current analysis contract requires exactly six comparable financial facts.
- Latest BYD, Xiaomi and Alibaba examples currently expose parser/normalization boundaries and safely abstain.
- Human usefulness, market demand, analyst productivity improvement and investment performance are not validated claims.
- No investment advice, price prediction or trade execution is provided.

## Resume here

Read first: [README.md](README.md), [DECISIONS.md](DECISIONS.md), the [final delivery roadmap](docs/product/researchforge-final-delivery-roadmap.md), and [PORTFOLIO.md](PORTFOLIO.md).

Primary checks:

```bash
RESEARCHFORGE_REASONING_MODE=deterministic uv run python scripts/autonomous_regression.py --all
RESEARCHFORGE_REASONING_MODE=deterministic uv run python scripts/start_demo.py --no-build
uv run python scripts/validate_contracts.py
git diff --check
git status --short
```
