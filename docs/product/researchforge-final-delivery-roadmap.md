# ResearchForge V1.6 Final Delivery Roadmap

**Updated:** 2026-09-05
**Status:** Active delivery authority

## Final product definition

ResearchForge V1.6 is an auditable Financial Research Agent:

> Input a public company name or ticker; ResearchForge resolves the issuer, finds an official filing, acquires and normalizes evidence, runs bounded research, and returns conclusions whose facts, calculations and trace can be inspected.

The product is not differentiated by “AI can summarize a filing”. Its differentiator is autonomous official-source acquisition plus a fail-closed, inspectable research process.

## V1.6 scope

Supported first-class markets:

- CN listed companies through CNINFO / official exchange disclosure sources.
- US listed companies through SEC EDGAR and official XBRL Company Facts.
- HK listed companies through HKEXnews and native-text IFRS reports.

The current deterministic research contract requires six core financial facts. Unsupported layouts must abstain.

## Phase A — Autonomous acquisition and company resolution

**Status: completed for the V1.6 release candidate.**

Deliverables:

1. Company/ticker input with optional market hint.
2. Entity resolution for CN, US and HK.
3. Official filing discovery with point-in-time cutoff.
4. Download/cache/identity verification.
5. CN PDF, SEC XBRL and HK IFRS extraction paths.
6. Immutable run-level Facts/Evidence snapshots.
7. Reviewed-package reuse for exact company+period cache hits.
8. Explicit abstention for ambiguous company, missing filing or unreliable extraction.

Acceptance evidence includes successful live runs for 贵州茅台, NVIDIA and Tencent plus the completed quick/extended Golden Regression.

## Phase B — Product surfaces

**Status: completed and runtime-verified.**

Web must expose company/ticker, Auto/CN/US/HK, optional period and research question. n8n must expose the same intent through a separate V1.6 workflow and use the same backend. Neither surface may calculate finance or invent a report on failure.

## Phase C — Golden Company Regression

**Status: PASS.**

Quick release set:

- CN: 贵州茅台
- US: NVIDIA
- HK: Tencent

Extended set adds 宁德时代, 比亚迪, Apple, Microsoft, Xiaomi and Alibaba.

For each case, a legal outcome is either:

- **Trusted success:** exactly six required facts, official-source provenance, valid Claim→Fact/Evidence references and completed Trace; or
- **Safe abstention:** explicit code/stage/reason and no research report.

Quick mode must contain at least one trusted success in each of CN, US and HK. Extended mode is used to expose parser/provider edge cases, not to force 100% success.

The release candidate passed this gate: the quick set succeeded in all three markets, and the extended nine-company set returned six trusted successes plus three explicit parser/normalization abstentions.

## Phase D — Full engineering gate

**Status: PASS locally for the V1.6 release candidate.**

Before Release Freeze, run the applicable repository gates:

```text
uv lock --check
ruff format --check
ruff check
mypy --strict
pytest
contract validation
frontend typecheck/lint/unit/build
mocked and live-backend Playwright E2E
n8n generation/unit/lint/runtime smoke
container build/start/smoke
git diff review
```

Historical V1.5 hashes and reviewed evidence must remain intact while V1.6 receives separate workflow/contracts where needed.

## Phase E — Owner acceptance and Release Freeze

**Status: pending owner acceptance.**

The owner manually tests representative arbitrary-company research, opens supporting evidence and Trace, records any final product/prompt/UI issues, and confirms the V1.6 promise is met. There is no six-person Human Pilot prerequisite.

Release Freeze is complete only after Golden Regression and the full engineering gate pass and remaining issues are either fixed or explicitly documented as non-blocking limitations.

## After V1.6 — V1.7 research intelligence

Only after V1.6 is frozen, continue with the differentiating research layer:

1. Evidence-first planning and collection before narrative generation.
2. Explicit Claim and Evidence objects across broader research questions.
3. Claim-level confidence from coverage, source quality, freshness and inference risk.
4. Stronger evaluator categories: retrieval, parsing, evidence, reasoning, citation, temporal and planning failures.
5. Bounded revision loop with maximum retry count.
6. Failure-attribution dashboard and regression metrics.
7. Reusable Research Skills such as FinancialHealth, RiskAnalysis and EarningsChange.

## Explicit non-goals for V1.6

- Trading or order execution.
- Price targets or buy/sell recommendations.
- Real-time market-data or high-frequency infrastructure.
- Bloomberg/AlphaSense-scale proprietary data coverage.
- Unrestricted support for every global exchange.
- Large multi-agent debate systems.
- Human Pilot as a release gate.

Historical V1.4/V1.5 experiment and usability materials remain immutable context, not active roadmap requirements.
