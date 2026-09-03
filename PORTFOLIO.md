# ResearchForge Portfolio and Interview Guide

This guide keeps every career claim tied to inspectable evidence. The product story comes first;
the frozen Evolution study is an optional quality-engineering deep dive.

## 30-Second Pitch

ResearchForge is an evidence-grounded AI workspace for A-share fundamental research. A user
selects a company and period, asks a question, and receives a structured conclusion whose facts,
formulas, official-source locators, counter evidence, limitations and monitoring actions can be
inspected independently. The model owns bounded reasoning; deterministic Python owns financial
math; LangGraph owns the auditable workflow.

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
  failure routing, one structured repair and a sanitized trace.
- **Auditability:** Claim—Fact—Evidence, Calculation Records, counter-evidence results and
  monitoring items are first-class artifacts.
- **Full-stack delivery:** FastAPI, Pydantic, content-addressed storage, PostgreSQL/Alembic,
  React/TypeScript, Docker and CI.
- **Research integrity:** negative experiments and failed simulated-usability evidence were
  retained instead of rewritten as success.

## Evidence Matrix

| Capability | Inspectable evidence | Current status |
|---|---|---|
| Deterministic finance | `src/researchforge/domain`, formula and period tests | implemented |
| Evidence provenance | Source/Fact/Evidence schemas, official CATL package, API resources | implemented for first real slice |
| Bounded AI workflow | ten-stage LangGraph and Workflow Trace | implemented |
| Verification | calculation, citation, cutoff and coverage Verifier | implemented |
| Product API | async lifecycle, facts, evidence, calculations, trace, cancel | implemented |
| Product UI | product-first Research page and secondary read-only Quality Lab | implemented; unit, E2E, accessibility and live-browser checks pass |
| Real disclosure ingestion | discovery/acquisition/parsing with strict product namespace | implemented for CATL 2024H1 |
| Human usability | real participant sessions | not run |
| Quality research | two frozen formal experiments and stopping rule | complete negative result |

## Claims Allowed Today

- “Built a versioned, evidence-grounded financial research system with deterministic finance,
  point-in-time provenance and a bounded LangGraph workflow.”
- “Implemented asynchronous research-run APIs and a React audit interface over immutable facts,
  calculations, evidence and traces.”
- “Used content-addressed JSON plus PostgreSQL/Alembic to separate immutable research artifacts
  from queryable lifecycle records.”
- “Implemented `Decimal` formulas and explicit behavior for YTD derivation, incompatible periods,
  restatements, zero, negative and missing inputs.”
- “Preserved two preregistered negative experiments and applied the stopping rule rather than
  changing thresholds to manufacture a result.”
- “Kept simulated usability evidence explicitly separate from real-user validation.”

## Claims Not Yet Allowed

- “ResearchForge supports broad or full-market A-share research.”
- “The product has been validated by real users.”
- “ResearchForge improves analyst accuracy or speed by X%.”
- “Built a production financial research platform.”
- “Built a self-evolving agent.”
- “The Evolution hypothesis is supported.”
- “The system provides investment recommendations or predicts returns.”

Human-usability claims unlock only after the final dual-surface evaluation uses real participants.
That evaluation is deliberately deferred until reusable extraction, generalization, n8n, Web UX
and demo hardening are frozen. The current real-ingestion claim is bounded to the one allowlisted
CATL 2024H1 filing.

## Resume Bullets: Current Evidence

- Built an auditable financial-research workspace using Python, FastAPI, Pydantic, LangGraph,
  React, PostgreSQL and content-addressed artifacts, with claim-level provenance and a
  reproducible three-container demo.
- Implemented deterministic `Decimal` finance, A-share reporting-period controls, YTD-to-quarter
  derivation, source cutoffs and verifier-backed abstention across 165 backend tests plus
  frontend E2E/accessibility gates.
- Designed a single-agent ten-stage workflow with checkpoint recovery, cancellation, timeouts,
  idempotent runs, structured-output repair and sanitized trace replay.
- Designed and executed a company-disjoint controlled quality study, retained two
  `NO_ELIGIBLE_CLUSTER` outcomes and enforced a two-experiment stop rule with total provider
  spend of USD 0.1523062.

- Built an allowlisted A-share disclosure-ingestion pipeline that acquires and hashes an official
  filing, preserves page-level provenance, normalizes reviewed financial facts, abstains on
  mapping/hash mismatches and produces an independently auditable research result.

## Three-to-Five-Minute Product Demo

1. **Problem — 30 seconds:** show why fluent financial chat is difficult to trust.
2. **Input — 20 seconds:** select a real company and period, then ask one bounded question.
3. **Conclusion — 40 seconds:** show the direct answer and key findings.
4. **Audit — 90 seconds:** expand one fact, one deterministic calculation and one official
   evidence locator.
5. **Challenge — 40 seconds:** show counter evidence or `not_found`, a limitation and an
   alternative explanation.
6. **Next action — 25 seconds:** show the monitoring trigger and next review period.
7. **Engineering — 35 seconds:** expand the ten-stage trace and explain the ownership boundary.

Quality Lab is optional after the main story. If time remains, use it to explain why honest
negative results are a feature of the engineering culture, not the product's core value.

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
- what evidence is required before claiming human usefulness.

## Public Repository Checklist

- no API keys, raw filing PDFs, private benchmark truth or local absolute paths;
- one clear README first screen with user, problem, input, output and differentiation;
- exact supported-company and period boundary;
- one-command fixture demo and a documented real-data acquisition path;
- source identity, license/redistribution boundary and provenance;
- deterministic calculation and abstention examples;
- full verification and CI evidence;
- human and simulated evidence labeled separately;
- Quality Lab explicitly secondary and read-only.
