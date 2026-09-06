# ResearchForge Portfolio and Interview Guide

This guide keeps every career claim tied to inspectable evidence. The product story comes first;
the frozen Evolution study is an optional quality-engineering deep dive.

## 30-Second Pitch

ResearchForge is an auditable autonomous financial-research agent for public companies. A user
enters a company name or ticker, optionally narrows the market or report period, and the system
resolves the issuer, finds an official disclosure, extracts financial facts deterministically,
then produces a conclusion whose facts, formulas, source evidence, counter evidence and execution
Trace can be inspected independently. CN, US and HK use different official-source adapters while sharing one research and verification pipeline. V1.8.5 adds an explicit Product Agent Eval/Failure loop, measured retrieval alternatives, security gates and a thin MCP interface over that same backend.

## The User Problem

General LLMs can produce fluent company analysis, but users cannot reliably tell whether they
used the correct filing, calculated the number correctly, found conflicting evidence or invented
a confident explanation. ResearchForge turns that trust problem into an artifact and interface
problem: every important result must be traceable and every missing input must remain missing.

## What Makes It Interview-Worthy

- **Product judgment:** a clear target user and Job To Be Done instead of “an agent that reads
  PDFs.”
- **Data engineering:** official-document identity, publication/retrieval time, hashes, page
  locators, normalized facts and provenance.
- **Financial correctness:** `Decimal` formulas, period comparability, YTD derivation,
  restatements, missing/negative/zero behavior and abstention.
- **AI boundary design:** model reasoning is separated from formulas, evidence policy and
  verification.
- **Agent orchestration:** one bounded LangGraph supports checkpoint/recovery, cancellation,
  failure routing, one structured repair and a sanitized trace; V1.7.3 makes autonomous preparation
  Run-first and hardens restart/concurrent execution around that graph.
- **Question-driven research:** six routed Research Skills produce inspectable plans, full-filing
  Evidence retrieval, Deep Analysis, overall judgment and follow-up questions.
- **Auditability:** Claim—Fact—Evidence, Calculation Records, counter-evidence results and
  monitoring items are first-class artifacts.
- **Full-stack delivery:** FastAPI, Pydantic, content-addressed storage, PostgreSQL/Alembic,
  React/TypeScript, Docker and CI.
- **Research integrity:** negative experiments and failed simulated-usability evidence were
  retained instead of rewritten as success.
- **Agent evaluation:** frozen component cases plus persisted Run checks for routing, planning, grounding, citations, structured output and ten-stage trajectory completion.
- **Failure engineering:** fourteen deterministic failure classes convert persisted failures into regression candidates without model calls.
- **Retrieval decisions by evidence:** lexical/TF-IDF/RRF are benchmarked before adding pgvector or dense retrieval; current results deliberately keep production unchanged.
- **Interoperability:** a seven-tool MCP server reuses the same ResearchForge backend instead of implementing a second finance/research stack.
- **Security operations:** dependency audits, browser/API security defaults and dedicated CI security gates can fail independently of ordinary tests.

## Evidence Matrix

| Capability | Inspectable evidence | Current status |
|---|---|---|
| Deterministic finance | `src/researchforge/domain`, formula and period tests | implemented |
| Autonomous entity/source discovery | CNINFO, SEC and HKEX discovery adapters + Golden Regression | live CN/US/HK success |
| Evidence provenance | Source/Fact/Evidence artifacts, official URLs, hashes and run snapshots | implemented |
| Bounded AI workflow | ten-stage LangGraph and Workflow Trace | implemented |
| Verification | calculation, citation, cutoff and coverage Verifier | implemented |
| Product API | autonomous submission plus lifecycle, facts, evidence, calculations, trace and cancel | implemented |
| Product UI | company-first Web Research + secondary read-only Quality Lab | unit, mocked E2E and live-backend E2E pass |
| Cross-market regression | quick + extended Golden Company suites | PASS; unsupported layouts abstain |
| n8n integration | V1.7.3 form/webhook over the same autonomous backend, with explicit synthesis/fallback mode | implemented and contract-tested |
| Quality research | two frozen formal experiments and stopping rule | complete negative historical result |
| Product Agent Eval | `researchforge eval`, V1.8 schemas and frozen evidence | Router 1.0; persisted Run checks pass |
| Retrieval benchmark | eight reviewed cases, lexical vs TF-IDF vs RRF | measured; production change deferred |
| Failure analysis | fourteen classes + real historical schema failure | implemented and regression-oriented |
| MCP | seven official-SDK tools over the same backend | contract-tested + live read-only smoke |
| Security gate | pip/npm audit + API/Web hardening | explicit CI job |

## Claims Allowed Today

- “Built an autonomous financial-research agent that resolves public companies and discovers
  official filings across CNINFO, SEC and HKEX.”
- “Separated numerical truth from model reasoning: PDF/XBRL extraction and `Decimal` calculations
  are deterministic, while material claims must resolve stored Facts and Evidence.”
- “Implemented run-scoped evidence snapshots so a historical research result cannot drift after
  a later disclosure fetch.”
- “Hardened the autonomous lifecycle so a durable queued Run exists before source discovery, with
  restart-safe dynamic context, cross-instance idempotency/budget locking and no fake preparation Trace.”
- “Built a bounded ten-stage LangGraph with lifecycle persistence, cancellation, failure routing
  and sanitized Trace rather than hidden chain-of-thought.”
- “Exposed the same authoritative ResearchForge pipeline through React and n8n without duplicating
  financial arithmetic or research logic in the automation layer.”
- “Ran live Golden Regression across CN/US/HK; unsupported current report layouts fail closed
  instead of being converted into plausible-looking reports.”
- “Preserved earlier negative experiments and historical usability material instead of rewriting
  old evidence after the product direction changed.”
- “Built a Product Agent Eval Harness that measures Router, Retrieval, planning, grounding, citation and trajectory behavior from frozen cases or persisted Runs.”
- “Compared lexical, TF-IDF and RRF retrieval on a frozen reviewed suite and deliberately deferred pgvector because the current gain/precision trade-off is not yet strong enough.”
- “Added a deterministic failure taxonomy so real failed Runs become diagnosable regression candidates rather than disappearing into logs.”
- “Exposed seven bounded MCP tools over the same ResearchForge backend and verified company discovery, Facts, Evidence, Result and Trace through an MCP client.”

## Claims Not Yet Allowed

- “ResearchForge supports every listed company or every filing layout.”
- “The product has been validated by a representative sample of real users.”
- “ResearchForge improves analyst accuracy or speed by X%.”
- “Built an enterprise production financial-research platform.”
- “Built a self-evolving or unrestricted multi-agent system.”
- “The historical Evolution hypothesis is supported.”
- “The system provides investment recommendations or predicts returns.”

The V1.8.5 release criterion was engineering reliability plus owner re-acceptance, not a six-person
Human Pilot. Owner re-acceptance and the final same-digest CAS reliability fix both passed, so Release Freeze is complete. This still does not justify a representative human-usability or market-demand claim. Coverage claims must be
phrased around the implemented CN/US/HK official-source adapters, the deterministic six-fact
numerical backbone plus full-filing Evidence retrieval, and explicit abstention on unsupported layouts.

## Resume Bullets: Current Evidence

- Built an auditable autonomous financial-research agent with Python, FastAPI, Pydantic, LangGraph,
  React, PostgreSQL and n8n, supporting company-first official-disclosure research across CNINFO,
  SEC and HKEX.
- Designed deterministic six-metric extraction and `Decimal` calculations with Claim–Fact–Evidence
  provenance, point-in-time source controls and fail-closed abstention for ambiguous entities or
  unsupported report layouts.
- Implemented run-scoped immutable evidence snapshots, asynchronous lifecycle APIs, idempotency,
  cancellation and a ten-stage sanitized Trace so each completed research run is reproducible and
  diagnosable.
- Built cross-market Golden Regression that verifies real official-source successes in CN, US and
  HK while treating unsupported layouts as explicit safe failures rather than fabricated results.
- Added a zero-provider-call Agent Eval/Failure pipeline and frozen retrieval benchmark; persisted model Runs score routing, plan completion, grounding, citation and ten-stage trajectory directly from stored artifacts.
- Added an official-SDK MCP interface with seven bounded tools over the authoritative backend, plus live read-only smoke and explicit security/eval GitHub CI gates.
- Preserved two preregistered negative quality experiments and their stop rule as historical
  evidence instead of changing thresholds after seeing the result.

## Three-to-Five-Minute Product Demo

1. **Problem — 25 seconds:** explain why a fluent financial answer is difficult to trust.
2. **Autonomous input — 25 seconds:** type a company name/ticker, choose Auto/CN/US/HK and ask one
   concrete research question; do not pre-upload a filing.
3. **Source discovery — 30 seconds:** show the resolved company/report period and official source.
4. **Conclusion — 35 seconds:** show the bounded answer and key findings.
5. **Audit — 80 seconds:** expand one Fact, deterministic Calculation, Evidence locator and Claim
   linkage.
6. **Failure integrity — 35 seconds:** use an unsupported period/layout and show explicit abstention
   rather than a generated report.
7. **Engineering — 35 seconds:** open the ten-stage Trace and explain the Python/LLM/n8n ownership
   boundary.

Then use the optional n8n form to submit the same company-first request and show that it returns
the same backend artifacts. Quality Lab is optional historical depth, not the product entry point.

## Technical Deep-Dive Topics

- why financial arithmetic is outside the model;
- how `published_at <= research_time` prevents hindsight leakage;
- why YTD cash-flow values cannot be treated as discrete quarters;
- how document identity and hashes protect against source drift;
- why evidence IDs and locators are stored instead of reconstructed in the browser;
- how the Verifier catches calculation, citation, period and omission failures;
- why LangGraph owns orchestration but not domain semantics;
- how product, fixture and benchmark namespaces prevent evaluation data becoming a product
  fallback;
- why the negative Evolution result remains frozen;
- why unsupported provider/layout states are explicit abstentions and how Golden Regression tests that boundary.
- how Agent Eval differs from unit tests and why V1.8 does not pretend deterministic checks prove semantic correctness;
- why the retrieval benchmark currently argues against immediately adding pgvector/dense embeddings;
- how a persisted `OUTPUT_SCHEMA_INVALID` becomes a typed failure and regression candidate;
- why MCP is a transport/interoperability layer rather than a second research implementation;
- why dependency audits need their own CI gate even when tests are green;

## Public Repository Checklist

- no API keys, raw filing PDFs, private benchmark truth or local absolute paths;
- one clear README first screen with user, problem, input, output and differentiation;
- explicit CN/US/HK provider and six-metric analysis boundary;
- one-command fixture demo and a documented real-data acquisition path;
- source identity, license/redistribution boundary and provenance;
- deterministic calculation and abstention examples;
- full verification and CI evidence;
- historical human/simulated evidence clearly separated from current V1.8.5 release evidence;
- Quality Lab explicitly secondary and read-only.
