# ResearchForge V1.7 Final Delivery Roadmap

**Updated:** 2026-09-05
**Status:** Engineering delivery complete; owner acceptance remains

## Final product definition

ResearchForge V1.7 is an auditable, question-driven Financial Research Agent:

> Input a public company name/ticker and a natural-language research question; ResearchForge resolves the issuer, finds an official filing, builds a verified numerical backbone plus full-filing Evidence, plans research around the question, and returns inspectable conclusions, Claims, Deep Analysis and Trace.

The product differentiates on **autonomous official-source acquisition + evidence-first reasoning + fail-closed auditability**, not on generic filing summarization.

## V1.7 implemented scope

- Markets: CN / US / HK through CNINFO, SEC EDGAR and HKEXnews.
- Skills: Company Overview, Earnings Change, Growth Analysis, Financial Health, Risk Analysis and Business Analysis.
- Numerical backbone: six deterministic facts and versioned calculations.
- Research evidence: native PDF/SEC HTML full-text chunks with source identity, locator and hash.
- Result: Intent, Plan, Claims, Deep Analysis, Overall Judgment, Evidence Coverage and Follow-ups.
- Surfaces: Web and separate n8n V1.7 workflow over the same authoritative backend.
- Compatibility: `financial_snapshot` preserves the narrow V1.6-style filing-analysis path; General Research uses versioned evidence packages.

## Phase A — Question-driven research layer

**Status: completed.**

Question Router, Research Planner, evidence retrieval, counter-evidence, evidence-constrained drafting and validation are implemented in the existing bounded ten-stage LangGraph. No second research engine or multi-agent debate was introduced.

## Phase B — Retrieval quality hardening

**Status: completed.**

SEC HTML no longer collapses all chunks into a two-item same-page cap. Retrieval now preserves HTML diversity and ranks direct answer signals above accidental section labels. Real NVIDIA growth research produces 6 Claims, 4 Deep Analysis sections and 5 follow-ups with Blackwell / hyperscale / segment evidence represented.

## Phase C — Web + n8n V1.7 surfaces

**Status: completed and runtime-verified.**

Web exposes General Research fields and progressive audit details. n8n V1.7 returns the same backend artifacts plus Intent, Plan, Deep Analysis, Judgment, Follow-ups and Evidence Coverage. Historical V1.5/V1.6 workflow artifacts are preserved rather than overwritten.

## Phase D — Golden Company Regression

**Status: PASS.**

Quick set: 贵州茅台 / NVIDIA / 腾讯 — trusted success in all three supported markets.

Extended set: 贵州茅台, NVIDIA, 腾讯, 宁德时代, 比亚迪, Apple, Microsoft, Xiaomi, Alibaba. Outcome: **6 trusted successes + 3 safe abstentions**. A legal outcome is either a fully auditable success or an explicit code/stage/reason with no Research Result.

## Phase E — Full engineering gate

**Status: PASS.**

```text
uv lock --check
ruff format --check
ruff check
mypy --strict
pytest
contract validation
frontend typecheck/lint/unit/build
mocked and live-backend Playwright E2E
n8n generation/unit/runtime + failure fixture
fresh Docker build/start/smoke
git diff review
```

Final verified counts: 207 pytest tests, 101 mypy source files, 4 frontend unit tests, 3 mocked E2E, 3 live-backend E2E, 10 n8n Node tests, 3 actual n8n success cases and 5 transport-only failure scenarios.

## Phase F — Owner acceptance / Release Freeze

**Status: pending owner action; not an engineering blocker.**

The owner manually checks representative arbitrary-company research, Evidence/Trace readability and one bounded failure. Automation must not invent this human acceptance. There is no six-person Human Pilot prerequisite.

## Explicit non-goals

- Trading, order execution, price targets or buy/sell recommendations.
- Real-time market/news infrastructure or Bloomberg/AlphaSense-scale proprietary coverage.
- Unlimited global exchange/layout support.
- Multi-agent debate or unrestricted self-modification.
- Claims of validated human usefulness, analyst productivity improvement or investment performance.

Historical V1.4/V1.5 experiments, negative results and usability materials remain immutable audit context.
