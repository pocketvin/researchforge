# ResearchForge V1.8.5 Final Delivery Roadmap

**Updated:** 2026-09-06
**Status:** V1.8.5 Release Freeze complete

## Final product definition

ResearchForge V1.8.5 is an auditable, question-driven Financial Research Agent with explicit Research Synthesis vs Evidence Summary modes plus a measured Agent-engineering layer for evaluation, failure analysis, retrieval benchmarking, security and MCP interoperability:

> Input a public company name/ticker and a natural-language research question; ResearchForge resolves the issuer, finds an official filing, builds a verified numerical backbone plus full-filing Evidence, plans research around the question, and returns inspectable conclusions, Claims, Deep Analysis and Trace.

The product differentiates on **autonomous official-source acquisition + evidence-first reasoning + fail-closed auditability**, not on generic filing summarization.

## V1.7.3 implemented scope

- Markets: CN / US / HK through CNINFO, SEC EDGAR and HKEXnews.
- Skills: Company Overview, Earnings Change, Growth Analysis, Financial Health, Risk Analysis and Business Analysis.
- Numerical backbone: six deterministic facts and versioned calculations.
- Research evidence: native PDF/SEC HTML full-text chunks with source identity, locator and hash.
- Result: Intent, Plan, Claims, Deep Analysis, Overall Judgment, Evidence Coverage, Follow-ups and explicit `synthesis_mode`.
- Surfaces: Web and n8n V1.7.3 presentation over the same authoritative backend; stable V17 routes/IDs are retained for compatibility.
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

## Phase D.3 — V1.7.3 Reliability & Audit Hardening

**Status: completed and runtime-verified.**

The project-wide audit found that autonomous source discovery could happen before a durable Run owned the work. V1.7.3 corrects the lifecycle to queued Run → preparation/discovery → graph execution → terminal state, persists dynamic recovery context and the original deadline, and records preparation-only failure/cancellation without fabricating a LangGraph Trace.

Run-scoped file locks, cross-instance idempotency/budget locking, non-blocking startup recovery and terminal checkpoint cleanup harden concurrent/restart behavior. Official-source redirect final hosts are revalidated, public product ports bind to localhost, public Research rejects investment-advice/target-price requests, history is paginated, queued history preserves submitted company context, and the methodology archive ships its read-only historical evidence.

A V1.7.3 runtime Run Manifest contract was added without replacing the V1.7 Research Result schema or rewriting historical contracts. n8n retains the stable V17 workflow/routes while requiring the V1.7.3 backend health contract.

## Phase D.4 — V1.7.3 Owner Runtime Isolation Correction

**Status: completed and real-owner-path verified.**

Owner re-testing exposed that a previously created deterministic container can remain deterministic even when `.env` and a fresh Compose rendering both say `auto`. Owner startup now force-recreates the stack and verifies `/v1/runtime-capabilities`; deterministic packaging smoke uses the isolated `researchforge-gate` project on separate ports and volumes. The Web surfaces `AI READY` vs `EVIDENCE ONLY` before research starts, and fallback no longer uses successful-research semantics.

After runtime recovery, two representative General Research questions still exposed out-of-context Evidence IDs in model Structured Output. Evidence/Fact ID fields are now dynamically enum-constrained to the exact current-run context before provider generation, while graph validation remains in place. The exact owner-path categories were rerun successfully: 贵州茅台 profitability (6 Claims / 5 sections / Supported) and 大华股份 growth (6 / 5 / Supported), both with `synthesis_mode=model`.

## Phase D.5 — V1.8.5 Agent Engineering Hardening

**Status: implemented; final release gate pending.**

V1.8.5 preserves the V1.7 research truth boundary and V1.7.3 lifecycle contracts while adding current dependency/security baselines, Product Agent Eval, deterministic failure classification, a frozen retrieval benchmark and a seven-tool MCP interface over the same backend.

The first frozen retrieval suite measures production lexical against TF-IDF sparse-vector and simple RRF alternatives. TF-IDF improves the current small suite; naïve RRF raises recall while reducing precision. Per RF-041, this is not enough evidence to introduce pgvector/dense retrieval.

Persisted Owner model Runs can be evaluated without rerunning the model. Three same-company 贵州茅台 Runs pass routing, plan, grounding, citation, structured-output and ten-stage trajectory checks; prose-level contradiction scoring is intentionally not claimed. A real historical Evidence-ID `OUTPUT_SCHEMA_INVALID` failure is classified as `MODEL_SCHEMA_FAILURE` and retained as a regression candidate.

MCP uses the official Python SDK, stdio by default and optional localhost Streamable HTTP. It exposes company resolution, filing discovery, research submission, persisted result/trace/facts and evidence search while leaving finance/evidence/research ownership in the existing backend.

See [V1.8.5 engineering note](v1.8.5-agent-engineering-hardening.md), [architecture](../architecture/v1.8.5-agent-engineering.md) and [measured evidence](../evidence/v1.8/README.md).

## Phase E — V1.8.5 Full engineering gate

**Status: PASS — local gate + public GitHub CI.**

The preserved V1.7.3 gate passed previously. V1.8.5 reran the complete local gate after the dependency, Eval, MCP and CI changes, then passed public GitHub CI on `main` across backend, contracts, eval, security, frontend and containers.

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

Fresh V1.8.5 local gate: **233 pytest tests**, strict mypy over **120 source files**, **625 local schema refs**, 7 frontend unit tests, 3 mocked + 3 live-backend E2E, no known Python dependency vulnerabilities, 0 frontend audit vulnerabilities, 11 n8n Node tests, 3 isolated Docker smoke cases, 3 actual n8n success cases, 5/5 transport-only failures and a seven-tool MCP live smoke. Owner runtime is V1.8.5 `auto + model_synthesis`, localhost-only, with API docs disabled and Web security headers verified.

## Phase F — Owner re-acceptance / Release Freeze

**Status: COMPLETE — Owner re-acceptance passed.**

The first V1.7 Owner Acceptance failed on synthesis quality and remains preserved as historical evidence. After the V1.8.5 engineering and remote gates passed, the owner manually re-tested a representative 贵州茅台 risk-analysis run in the V1.8.5 Web workspace, observed `AI READY` + `MODEL SYNTHESIS` with supported conclusions/findings, and reported no release blocker. This manual acceptance completes Release Freeze. There is no six-person Human Pilot prerequisite.

## Explicit non-goals

- Trading, order execution, price targets or buy/sell recommendations.
- Real-time market/news infrastructure or Bloomberg/AlphaSense-scale proprietary coverage.
- Unlimited global exchange/layout support.
- Multi-agent debate or unrestricted self-modification.
- Claims of validated human usefulness, analyst productivity improvement or investment performance.

Historical V1.4/V1.5 experiments, negative results and usability materials remain immutable audit context.
