# ResearchForge Project Status

**Updated:** 2026-09-05
**Contract package:** 1.5.0
**Product package:** 1.7.3
**Scope:** V1.7 General Company Research

Contract package: 1.5.0
Current gate: RELEASE_FREEZE
Scope: V1.7 general company research

**Gate meaning:** RELEASE_FREEZE remains in progress because owner re-acceptance is still pending.

## Current milestone

**V1.7.3 Reliability & Audit Hardening — ENGINEERING COMPLETE**

V1.7.3 keeps the V1.7/V1.7.1 research truth boundary and V1.7.2 workspace product, but closes lifecycle, restart, concurrency, source-trust and packaging gaps found in the project-wide audit. Engineering completion does not imply Owner Acceptance.

## V1.7.3 hardening delivered

- Autonomous submission persists a V1.7.3 `queued` Run before official-source discovery or acquisition.
- Preparation/discovery, dynamic package identity, retryable failure and cancellation are represented by the same durable Run; preparation-only failure never fabricates a LangGraph Trace.
- Persisted autonomous company/package context and the original total deadline survive process restart.
- Run-scoped file locks prevent background execution and restart recovery from running the same Run concurrently.
- File-backed idempotency and project budget reservation are atomic across repository/ledger instances.
- API startup recovery runs in a daemon thread and cannot block `/healthz` while a Run resumes.
- Terminal Runs delete their shared LangGraph checkpoint thread instead of accumulating stale checkpoint state.
- SEC/HKEX/discovery redirect final hosts are revalidated against official-source policy.
- Packaged API/Web/n8n ports bind to `127.0.0.1`; unauthenticated product services are not exposed to the LAN by default.
- Public Research rejects investment recommendations, buy/sell instructions and target-price requests at the input boundary.
- Recent Run history supports offset pagination and Web “load more”; queued autonomous history retains submitted company/market/period context.
- Historical Quality/Evolution method evidence is packaged as a read-only archive rather than depending on a mutable local artifact volume.
## Full engineering gate — PASS

Verified on the V1.7.3 working tree:

- `uv lock --check`, Ruff format/check and strict mypy: PASS; mypy checked **109 source files**.
- `pytest -q`: **225 passed**, with 2 known upstream deprecation warnings.
- Contract validation: PASS — **611 local schema refs**, **116 local Markdown links**, **128 required contract files**; V1.7.3 and preserved historical schemas/examples validate together.
- Frontend: typecheck/lint/build + **7 unit tests + 3 mocked E2E + 3 live-backend E2E**: PASS.
- n8n source: generated workflow check + **11 Node tests** + integration lint: PASS.
- Fresh API/frontend Docker images + PostgreSQL/API/Web health + **3 reviewed-cache Docker smoke cases**: PASS.
- Packaged Autonomous lifecycle observed `queued/queued → running/completed → succeeded/completed`; final manifest validates against the V1.7.3 runtime schema.
- Published ports verified localhost-only: API `127.0.0.1:8000`, Web `127.0.0.1:4173`, n8n `127.0.0.1:5678`.
- Actual n8n 2.37.9 runtime: **3 success cases**, idempotent replay, minimum cached input, native form, native form failure and 5 HTTP failure checks: PASS.
- Actual n8n transport-only fixture: **5/5 bounded failure scenarios PASS** with no research truth supplied.

## Research-quality evidence retained

- V1.7 extended Golden Regression: **6 trusted successes + 3 explicit safe abstentions; PASS**.
- V1.7.1 real-model smoke: 贵州茅台 `company_overview` **8 Claims / 5 sections**; NVIDIA `growth_analysis` **6 / 5**; 腾讯 `business_analysis` **6 / 5**.
- V1.7.3 changes runtime reliability and audit semantics; it does not replace or inflate that retained research-quality evidence.

## Release boundary

`RELEASE_FREEZE` remains **in progress only for owner re-acceptance**. No six-person Human Pilot is required. Owner acceptance must remain a human judgment; engineering tests cannot sign it on the owner's behalf.

The owner should verify one representative General Research run, one follow-up/history restore flow, the audit hierarchy, one explicit bounded failure, and that the visible product still feels useful after the reliability hardening.
## Known bounded limitations

- CN/US/HK official-source adapters are supported; universal issuer/layout coverage is not claimed.
- Six deterministic financial facts remain the current numerical backbone.
- BYD latest, Xiaomi and Alibaba examples expose parser/layout boundaries and safely abstain in the retained extended regression.
- “下一份财报重点看什么” is a review checklist, not a scheduled notification service.
- 方法与实验 is historical technical evidence, not a normal research workflow.
- Real-time news, broker research, price targets, trading, portfolio management and unrestricted multi-agent debate remain out of scope.

## Resume here

Read first: [README.md](README.md), [DECISIONS.md](DECISIONS.md), the [V1.7.3 change note](docs/product/v1.7.2-to-v1.7.3-reliability-audit-hardening-change-note.md), the [V1.7.2 UX note](docs/product/v1.7.1-to-v1.7.2-workspace-ux-change-note.md), the [final delivery roadmap](docs/product/researchforge-final-delivery-roadmap.md), and [PORTFOLIO.md](PORTFOLIO.md).
