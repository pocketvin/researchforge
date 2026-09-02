# ResearchForge Portfolio and Interview Guide

This document turns engineering work into honest, inspectable career evidence. Replace placeholders only with measured results.

## 30-Second Pitch

ResearchForge is a contract-first financial research agent that combines deterministic financial calculations, point-in-time filing evidence, structured claims, and a verifier. Its research experiment tests whether repeated, verified earnings-quality omissions can be converted into a bounded research-procedure patch that improves held-out cases without regression.

## What Makes It Interview-Worthy

The differentiator is not “an LLM that reads PDFs.” The useful engineering evidence is:

- correct financial-period normalization, including YTD-to-quarter derivation;
- a single auditable Agent workflow with deterministic tools;
- claim-to-fact/evidence provenance and point-in-time controls;
- reproducible evaluation with Base/Seed/Evolved comparisons;
- benchmark leakage prevention and bounded skill versioning;
- a product report and a Skill Lab driven by real stored artifacts;
- explicit trade-offs that keep a solo project shippable.

## Evidence Matrix

| Capability to demonstrate | Required artifact | Earliest level |
|---|---|---|
| Python domain engineering | Decimal financial tools and tests | L1 |
| FastAPI/Pydantic design | Schema-backed run endpoint and response | L1 |
| LangGraph orchestration | One versioned end-to-end Research workflow trace with tested failure routes | L1 |
| Retrieval grounding | Filing chunks with stable citations | L1 |
| Evaluation engineering | Deterministic and coverage verifier fixtures | L2 |
| Experiment design | Frozen splits, immutable metrics, and an honest terminal outcome | L3 |
| Self-improvement claim | Adopted patch plus sealed Final Test evidence | L3 |
| Full-stack delivery | Research and Skill Lab pages, Docker, CI | L4 |

## Claims Allowed Today

You may say:

- “Designed a versioned contract architecture for an auditable financial research agent.”
- “Defined deterministic finance, point-in-time evidence, experiment-isolation, and patch-adoption rules.”
- “Implemented bounded single-agent LangGraph orchestration with durable checkpoints and a versioned, machine-readable Workflow Trace.”
- “Built five frozen-fixture research modes, a deterministic Verifier, and a 20/20 local reliability batch with exact denominators.”
- “Built a two-page React interface and hybrid immutable-file/PostgreSQL persistence; verified a three-service Docker run through Nginx, FastAPI, PostgreSQL, and a ten-stage trace.”
- “Prepared two redistribution-safe, company-disjoint 24-case benchmark packages with official links, page locators, artifact hashes, sealed labels, and one-time Final Test controls.”
- “Executed two controlled formal experiments with 144 total scored Evolution evaluations, preserved two negative `NO_ELIGIBLE_CLUSTER` outcomes, and enforced a two-experiment stopping rule instead of manufacturing an improvement claim.”
- “Closed an AI-simulated usability failure by adding persisted Evidence Chunk links, deterministic Calculation Records, and monitoring triggers; the isolated repeat passed 3/3 locateability checks while remaining explicitly non-human evidence.”
- “Kept all OpenAI work under a pre-dispatch USD 20 guard; calibration, both formal experiments, and two usability batches consumed USD 0.1523062 in total.”

You must not yet say:

- “Built a production financial research agent.”
- “Improved research accuracy by X%.”
- “Created a self-evolving agent.”
- “The research hypothesis is supported.”
- “Validated product value with real users.”

Those claims require the matching level in `PROJECT_STATUS.md`.

## Evidence-Backed Resume Bullets

These statements are supported by the frozen project evidence:

- Built an evidence-grounded financial research system with Python, FastAPI, Pydantic,
  LangGraph, React, PostgreSQL, and content-addressed artifacts; shipped five modes and a
  reproducible three-container demo.
- Implemented deterministic `Decimal` formulas, point-in-time source controls, Claim—Fact—Evidence
  provenance, and an independent Verifier across 24-case primary and contingency suites.
- Designed and executed a preregistered skill-evolution study with company-disjoint splits and
  three repeats; preserved negative results and stopped after two experiments when no eligible
  Candidate cluster emerged.
- Built a 160-test backend suite plus frontend unit/E2E/accessibility and Docker migration smoke
  gates, enforced in GitHub Actions.

If a metric is not measured, remove the metric instead of estimating it.

## Five-Minute Demo Story

1. **Problem, 30 seconds:** bare LLM research can calculate incorrectly, omit cash conversion, or cite unsupported text.
2. **Research run, 90 seconds:** ask one company earnings-quality question and show plan, facts, tools, evidence, claims, and sources.
3. **Audit, 45 seconds:** click one material claim and resolve it to fact/evidence IDs and reporting cutoff.
4. **Formal result, 45 seconds:** show Base/Seed denominators and the retained failure events from the primary and contingency experiments.
5. **Stop rule, 45 seconds:** show why `NO_ELIGIBLE_CLUSTER` produced no Candidate, kept Validation sealed, and left Final Test unconsumed.
6. **Usability iteration, 45 seconds:** show the initial simulated failure, evidence/monitoring correction, and final `SIMULATED` PASS while stating that no real user was tested.

## Interview Deep-Dive Topics

Be prepared to explain:

- why financial arithmetic is outside the LLM;
- why A-share cash-flow values may be YTD and how discrete quarters are derived;
- why company-level split isolation matters;
- why an LLM judge cannot be the sole adoption criterion;
- why file-backed frozen packages come before pgvector in the thin slice;
- why LangGraph owns orchestration and recovery but not finance, retrieval, or Evolution semantics;
- why V1.4 separates product usefulness from whether the research hypothesis succeeds;
- how idempotency, version hashes, and immutable artifacts support reproducibility;
- what evidence would cause the project to reject a patch or report insufficient data.

## Public Repository Checklist

Before publishing:

- remove all secrets, proprietary/licensed data, and local absolute paths;
- include synthetic or redistribution-safe fixtures;
- provide one-command validation and one-command demo startup;
- include architecture, limitations, costs, and non-investment-advice notice;
- publish actual test output and experiment denominators;
- label screenshots and demo metrics as real or illustrative;
- make the first README screen explain the problem, demo, evidence, and current limits.
