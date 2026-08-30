# Solo Success Plan

This plan improves the probability that one person can finish ResearchForge while keeping changes explicit against the active V1.4 scope baseline.

## North-Star User

The first user is a finance learner, junior analyst, or technical interviewer who needs an auditable company-research walkthrough. ResearchForge is not a professional trading terminal and does not make investment recommendations.

The first useful outcome is therefore:

> Given one earnings-quality question and a frozen evidence package, produce a reproducible report whose important numbers, periods, claims, and citations can be audited.

## Staged Success Ladder

Planning ranges are capacity estimates, not delivery promises.

| Level | Planning range | Required outcome | Honest portfolio value |
|---|---:|---|---|
| L0 Contract Ready | complete | Frozen scope, schemas, semantic contracts, validator | System and experiment design |
| L1 Resume Ready | 1–2 focused weeks | One LangGraph-orchestrated earnings-quality slice, deterministic tools, schema-valid report, tests | Python, agent workflow, finance correctness, citations |
| L2 Demo Ready | about 1 week | Verifier fixtures, trace inspection, replayable failure explanation | Evaluation and observability |
| L3 Research Supported | 1–2 focused weeks | Candidate adopted on Validation and supported once on sealed Final Test | Controlled self-improvement evidence |
| L4 Full Engineering Product | 2–3 focused weeks | Five modes, two pages, supported storage, Docker, CI, three labeled simulations | Full-stack product delivery without a human-value claim |

Each level must be independently demonstrable. Stopping at L1 or L2 is a valid portfolio outcome, but it is not a completed Evolution claim.

## Portfolio MVP

L1 intentionally narrows the implementation sequence, not V1.4 scope:

- one task: earnings-quality analysis;
- two approved companies and four comparable periods;
- frozen, redistribution-safe facts and evidence;
- one CLI command and one FastAPI run endpoint;
- one single-agent LangGraph workflow following `research-workflow.md`;
- deterministic financial calculations and schema validation;
- one inspectable result, Run Manifest, and graph trace.

Do not build the React pages, pgvector retrieval, or Evolution pipeline before this slice is correct.

## Complexity Budget

Until L1 passes, the implementation budget is:

- one Research Agent, one underlying model, one skill, and one graph;
- LangGraph only for workflow state, conditional routing, and auditable execution;
- plain Python for formulas, normalization, adapters, verifier rules, and Evolution;
- one structured data adapter and one filing adapter;
- file-backed immutable packages; no queue, distributed workers, Kubernetes, or extra service;
- one active milestone and one end-to-end slice at a time.

A new dependency or infrastructure component requires evidence that the current design cannot meet an acceptance criterion without it. Record the decision in `DECISIONS.md`.

## Kill and Fallback Rules

| Risk trigger | Stop rule | Fallback that preserves learning |
|---|---|---|
| No acceptable structured-data source | Stop after two person-days of the source spike | Use manually reconciled frozen fixtures; make no live-data claim |
| Filings cannot be parsed reliably | Do not build OCR infrastructure in V1 | Restrict initial companies to text-readable filings and record exclusions |
| Semantic/vector retrieval does not beat deterministic section filters | Do not add pgvector for novelty | Use section/keyword filters over frozen chunks |
| Primary experiment is unsupported | Freeze every artifact and threshold | Run at most one V1.5 experiment on the pre-frozen disjoint contingency suite |
| Second experiment is unsupported | Do not manufacture cases or lower thresholds | Mark engineering delivery complete but the owner-selected project completion target blocked |
| UI work blocks core correctness | Pause UI at the end of its time box | Demo through CLI/API and exported artifacts |

## Weekly Operating Rhythm

1. Pick one gate-level outcome and write its evidence before implementation.
2. Build the smallest vertical behavior that can disprove the current assumption.
3. Run tests and export a safe artifact rather than relying on a live narration.
4. Update the scorecard, decision log, and project checkpoint.
5. Leave one next action that can be started without reconstructing chat history.

## Definition of Engineering Usefulness

The product passes its V1.4 presentation check only when three isolated simulated personas can identify what changed, why it may matter, what evidence supports it, what contradicts it, and what remains unknown. Fluency, report length, and visual polish are not substitutes for these outcomes. This is not evidence that real target users find the product useful.
