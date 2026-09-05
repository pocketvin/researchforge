# ResearchForge V1.7.2 Final Delivery Roadmap

**Updated:** 2026-09-05
**Status:** V1.7.2 engineering complete; owner re-acceptance remains

## Final product definition

ResearchForge V1.7.2 is an auditable, question-driven Financial Research Agent with explicit Research Synthesis vs Evidence Summary modes:

> Input a public company name/ticker and a natural-language research question; ResearchForge resolves the issuer, finds an official filing, builds a verified numerical backbone plus full-filing Evidence, plans research around the question, and returns inspectable conclusions, Claims, Deep Analysis and Trace.

The product differentiates on **autonomous official-source acquisition + evidence-first reasoning + fail-closed auditability**, not on generic filing summarization.

## V1.7.2 implemented scope

- Markets: CN / US / HK through CNINFO, SEC EDGAR and HKEXnews.
- Skills: Company Overview, Earnings Change, Growth Analysis, Financial Health, Risk Analysis and Business Analysis.
- Numerical backbone: six deterministic facts and versioned calculations.
- Research evidence: native PDF/SEC HTML full-text chunks with source identity, locator and hash.
- Result: Intent, Plan, Claims, Deep Analysis, Overall Judgment, Evidence Coverage, Follow-ups and explicit `synthesis_mode`.
- Surfaces: Web and n8n V1.7.2 presentation over the same authoritative backend; stable V17 routes/IDs are retained for compatibility.
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


## Phase D.1 — V1.7.1 Research Synthesis correction

**Status: implemented and real-model verified.**

The first V1.7 Owner Acceptance failed because a deterministic General Research fallback displayed retrieved filing excerpts as if they were Findings/Deep Analysis. V1.7.1 separates `model` from `evidence_summary_fallback`, makes comprehensive routing win over narrower keywords, adds analytical claim semantics and substantive judgment rationale, filters unrelated Fact chips, and changes the Web to analysis-first/evidence-on-demand.

Real model smoke over official-source packages succeeded in all three markets: 贵州茅台 `company_overview` (8 Claims / 5 analytical sections), NVIDIA `growth_analysis` (6 / 5), and 腾讯 `business_analysis` (6 / 5).

## Phase D.2 — V1.7.2 Research Workspace UX Closeout

**Status: completed and runtime-verified.**

Owner feedback after V1.7.1 identified product-continuity rather than research-quality blockers. V1.7.2 adds a recent General Research history API and Web list, restores persisted reports without model reruns, makes Suggested Follow-ups create a new run immediately, preserves Research state across methodology navigation, and establishes an answer-first/audit-on-demand accordion hierarchy.

Monitoring is reframed as “下一份财报重点看什么” with an explicit non-alert explanation. Quality Lab is preserved as the read-only “方法与实验” archive but removed from primary navigation; inactive adoption steps no longer show fake arrows and loaded steps navigate to real sections.

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

Final verified counts: 211 pytest tests, 105 mypy source files, 7 frontend unit tests, 3 mocked E2E, 3 live-backend E2E, 11 n8n Node tests, 3 Docker smoke cases, 3 actual n8n success cases and 5 transport-only failure scenarios.

## Phase F — Owner re-acceptance / Release Freeze

**Status: pending owner re-acceptance; engineering is complete.**

The first V1.7 Owner Acceptance failed on synthesis quality and is preserved as such. The owner now manually rechecks representative model synthesis plus the V1.7.2 continuous-research/history workflow, audit hierarchy, the explicit fallback state and one bounded failure. Automation must not invent this human acceptance. There is no six-person Human Pilot prerequisite.

## Explicit non-goals

- Trading, order execution, price targets or buy/sell recommendations.
- Real-time market/news infrastructure or Bloomberg/AlphaSense-scale proprietary coverage.
- Unlimited global exchange/layout support.
- Multi-agent debate or unrestricted self-modification.
- Claims of validated human usefulness, analyst productivity improvement or investment performance.

Historical V1.4/V1.5 experiments, negative results and usability materials remain immutable audit context.
