# ResearchForge

> A Financial Research Agent with Verifiable Procedures and a Controlled Learning Experiment.

ResearchForge V1.3 is a contract-first project for evidence-grounded company fundamental research and one controlled skill-evolution experiment. This repository currently contains the active product/research baseline and normative contracts that future implementation must satisfy. It does not yet contain the application runtime.

## Status

- Product/research scope: **V1.3 active baseline**
- Contract package: **V1.3.0**
- Completed/current gate: **C0 complete → G0 next**
- Runtime implementation: **not started**
- Supported deployment for V1.3: **local or controlled single-user demo**

Current critical path: complete the time-boxed data-source acceptance spike before application infrastructure.

## Start Here

1. [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — current gate, blockers, and one next action.
2. [`docs/product/researchforge-v1.3-scope.md`](docs/product/researchforge-v1.3-scope.md) — current product and research authority.
3. [`DECISIONS.md`](DECISIONS.md) — accepted and pending architecture/data choices.
4. [`docs/strategy/solo-success-plan.md`](docs/strategy/solo-success-plan.md) — L0–L4 delivery ladder and fallbacks.
5. [`docs/contracts/research-workflow.md`](docs/contracts/research-workflow.md) — bounded LangGraph orchestration.
6. [`PORTFOLIO.md`](PORTFOLIO.md) — claims that are safe at each evidence level.

## Authority Order

When documents conflict, use this order:

1. [`docs/product/researchforge-v1.3-scope.md`](docs/product/researchforge-v1.3-scope.md) defines active product and research scope.
2. [`docs/contracts/`](docs/contracts/) defines executable behavior, financial semantics, experiment isolation, and acceptance rules.
3. [`schemas/v1.3/`](schemas/v1.3/) defines current machine-readable artifact shapes.
4. Application code and UI must conform to the three layers above.

[`docs/product/v1.2-to-v1.3-change-note.md`](docs/product/v1.2-to-v1.3-change-note.md) records the upgrade. The V1.2 frozen scope and schemas remain immutable historical evidence; they are not current implementation authority.

A scope change is allowed only through an explicit decision, change note, contract update, and version impact assessment.

## V1.3 Outcomes

V1.3 has two separate outcomes:

1. A useful, evidence-grounded fundamental research workflow.
2. A controlled `failure → experience → skill patch → held-out validation` research experiment for earnings-quality omissions.

The product can be useful even if the research hypothesis is rejected. A self-improvement claim requires adopted-patch and sealed-test evidence. V1.3 does not provide investment advice, price predictions, trading, portfolio optimization, real-time market data, or autonomous open-ended model training.

## Delivery Ladder

| Level | Outcome | Current status |
|---|---|---|
| L0 Contract Ready | Scope, schemas, methods, validation | complete |
| L1 Resume Ready | One LangGraph research slice, deterministic tools, report, tests | not started |
| L2 Demo Ready | Verifier, trace, and replayable failure evidence | not started |
| L3 Differentiated | Controlled no-cluster/rejection/supported outcome | not started |
| L4 Full V1.3 | Five modes, two pages, supported storage, Docker, CI | not started |

Stopping earlier preserves honest portfolio value. “Self-improving” is not a completed claim until L3 adoption and sealed-test evidence exist.

## Repository Layout

```text
ResearchForge/
├── AGENTS.md
├── CHANGELOG.md
├── DECISIONS.md
├── PORTFOLIO.md
├── PROJECT_STATUS.md
├── README.md
├── project-status.json
├── docs/
│   ├── architecture/
│   │   └── implementation-blueprint.md
│   ├── product/
│   │   ├── researchforge-v1.3-scope.md
│   │   ├── v1.2-to-v1.3-change-note.md
│   │   └── researchforge-v1.2-scope-freeze.md  # historical
│   ├── contracts/
│   │   ├── README.md
│   │   ├── benchmark-protocol.md
│   │   ├── data-source-acceptance.md
│   │   ├── development-gates.md
│   │   ├── evolution-adoption-policy.md
│   │   ├── financial-methodology.md
│   │   ├── product-success-metrics.md
│   │   ├── research-workflow.md
│   │   ├── run-lifecycle.md
│   │   └── task-capability-matrix.md
│   ├── operations/
│   │   └── resume-playbook.md
│   └── strategy/
│       ├── project-scorecard.md
│       ├── risk-register.md
│       └── solo-success-plan.md
├── examples/
│   └── contracts/
│       ├── benchmark-case.example.json         # historical V1.2
│       └── v1.3/
│           ├── benchmark-case.example.json
│           ├── run-manifest.research.example.json
│           ├── run-manifest.patch-generation.example.json
│           └── workflow-trace.example.json
├── schemas/
│   ├── v1.2/                                  # historical contracts
│   └── v1.3/                                  # 11 current schemas,
│       └── workflow-trace.schema.json          # including LangGraph trace
└── scripts/
    └── validate_contracts.py
```

## Contract Rules

- Every persisted artifact carries `schema_version`.
- Every research result is traceable to immutable facts, evidence, skill version, formula version, model configuration, and evidence cutoff.
- Important numbers are calculated by deterministic tools, never by LLM mental arithmetic.
- LangGraph orchestrates the single Research Agent's typed workflow, conditional failure paths, checkpoint/resume, and Workflow Trace. Plain Python owns finance, retrieval, verification, storage semantics, and Evolution.
- External filings are untrusted data. They cannot modify prompts, tools, permissions, skills, or experiment policy.
- Counter-evidence search is mandatory; fabricating counter evidence is prohibited. A recorded `not_found` result is valid.
- Final-test data and labels are sealed from the Researcher and Optimizer until the candidate skill is frozen.
- Raw hidden chain-of-thought is not persisted. Store only explicit plans, tool records, evidence links, and concise decision summaries.

## Planned Implementation Order

```text
Contracts and data-source acceptance
→ golden earnings-quality cases
→ one LangGraph-orchestrated end-to-end research slice
→ deterministic and coverage verifier
→ one controlled evolution cycle
→ remaining product modes
→ two-page UI and packaging
```

## Validate the Contract Package

```bash
python3 scripts/validate_contracts.py
```

The dependency-free validator checks V1.3 JSON syntax, schema metadata, local `$ref` resolution, current examples and live project checkpoint, historical V1.2 integrity, Markdown links, and required project files.

## Safety and Disclaimer

ResearchForge is a research-assistance prototype, not investment advice. Any future data integration must document its license, provenance, retrieval time, publication time, and redistribution restrictions. Secrets and licensed raw datasets must not be committed.
