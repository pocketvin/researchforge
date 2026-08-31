# ResearchForge

> A Financial Research Agent with Verifiable Procedures and a Controlled Learning Experiment.

ResearchForge V1.4 is an evidence-grounded company fundamental-research product and a controlled skill-evolution experiment. The current local product turns frozen A-share financial facts into schema-valid reports, deterministic evaluations, and sanitized ten-stage LangGraph traces without asking a model to perform arithmetic.

## Status

- Product/research scope: **V1.4 active baseline**
- Contract package: **1.4.0**
- Independently accepted gates: **V1.4 C0 + G0**
- Local implementation: **G1 five-mode breadth + G2 Verifier evidence implemented; one final independent acceptance is deferred until project completion**
- Active milestone: **G3 formal Benchmark data preparation**
- Supported deployment for V1.4: **local or controlled single-user demo**

Current critical path: finish the signed primary Benchmark package, run the controlled Evolution/Validation/Final Test experiment, then complete Docker smoke, three labeled simulations, demo/public packaging, and one final independent review. Synthetic policy tests are not a formal `SUPPORTED` result.

## Run the Zero-Cost Product Core

The default runtime is deterministic and does not read `OPENAI_API_KEY` or make provider calls.

```bash
uv run researchforge catalog

uv run researchforge run \
  --task-type filing_analysis \
  --company cn_300750 \
  --period 2024H1 \
  --question '2024年上半年利润是否转化为经营现金流?' \
  --research-time '2024-08-01T00:00:00+08:00' \
  --idempotency-key 'demo-catl-2024h1'
```

The output bundle contains the persisted Run Manifest, Research Result, and Workflow Trace. Immutable JSON is stored below `artifacts/objects/sha256/`; small run/idempotency pointers live alongside it and the whole directory is Git-ignored. The same workflow supports all five allowlisted research modes.

Start the API with the app factory:

```bash
uv run uvicorn researchforge.api.app:create_app --factory --reload
```

The API implements create/status/result/trace/facts/cancel resources, `GET /v1/catalog`, and read-only Evolution experiment/artifact endpoints. It returns `202` on creation, `425` while an artifact is not ready, and `409` for an idempotency conflict or a terminal run without a result.

Start the frontend separately:

```bash
npm ci --prefix frontend
npm run dev --prefix frontend
```

Or use `docker compose up --build` after registry connectivity is available. The Compose definition is validated, but the full image/runtime smoke test is not yet passing evidence because base-image metadata requests timed out locally.

## Start Here

1. [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — current gate, blockers, and one next action.
2. [`docs/product/researchforge-v1.4-scope.md`](docs/product/researchforge-v1.4-scope.md) — current product and research authority.
3. [`DECISIONS.md`](DECISIONS.md) — accepted and pending architecture/data choices.
4. [`docs/strategy/solo-success-plan.md`](docs/strategy/solo-success-plan.md) — L0–L4 delivery ladder and fallbacks.
5. [`docs/contracts/research-workflow.md`](docs/contracts/research-workflow.md) — bounded LangGraph orchestration.
6. [`PORTFOLIO.md`](PORTFOLIO.md) — claims that are safe at each evidence level.

## Authority Order

When documents conflict, use this order:

1. [`docs/product/researchforge-v1.4-scope.md`](docs/product/researchforge-v1.4-scope.md) defines active product and research scope.
2. [`docs/contracts/`](docs/contracts/) defines executable behavior, financial semantics, experiment isolation, and acceptance rules.
3. [`schemas/v1.4/`](schemas/v1.4/) defines current machine-readable artifact shapes.
4. Application code and UI must conform to the three layers above.

[`docs/product/v1.3-to-v1.4-change-note.md`](docs/product/v1.3-to-v1.4-change-note.md) records the current upgrade. V1.2 and V1.3 scope/schema packages remain immutable historical evidence; they are not current implementation authority.

A scope change is allowed only through an explicit decision, change note, contract update, and version impact assessment.

## V1.4 Outcomes

V1.4 has two separate outcomes:

1. A useful, evidence-grounded fundamental research workflow.
2. A controlled `failure → experience → skill patch → held-out validation` research experiment for earnings-quality omissions.

Engineering delivery can remain useful after a negative experiment, but the owner-selected overall completion standard additionally requires a `SUPPORTED` sealed result. V1.4 does not provide investment advice, price predictions, trading, portfolio optimization, real-time market data, or autonomous open-ended model training.

## Delivery Ladder

| Level | Outcome | Current status |
|---|---|---|
| L0 Contract Ready | Scope, schemas, methods, validation | complete |
| L1 Resume Ready | One LangGraph research slice, deterministic tools, report, tests | local evidence implemented; final acceptance deferred |
| L2 Demo Ready | Verifier, trace, and replayable failure evidence | local evidence implemented; final acceptance deferred |
| L3 Research Supported | Adopted Candidate and supported sealed Final Test | not started |
| L4 Full Engineering Product | Five modes, two pages, supported storage, Docker, CI, three labeled simulations | in progress — core/UI/storage/CI implemented |

Stopping earlier preserves honest portfolio value. “Self-improving” is not a completed claim until L3 adoption and sealed-test evidence exist.

## Repository Layout

```text
ResearchForge/
├── .env.example
├── .python-version
├── AGENTS.md
├── CHANGELOG.md
├── DATA_NOTICE.md
├── DECISIONS.md
├── LICENSE
├── PORTFOLIO.md
├── PROJECT_STATUS.md
├── README.md
├── pyproject.toml
├── project-status.json
├── uv.lock
├── docs/
│   ├── architecture/
│   │   └── implementation-blueprint.md
│   ├── product/
│   │   ├── researchforge-v1.4-scope.md
│   │   ├── v1.3-to-v1.4-change-note.md
│   │   ├── researchforge-v1.3-scope.md          # historical
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
│       └── v1.4/
│           └── 12 current contract examples
├── schemas/
│   ├── v1.2/                                  # historical contracts
│   ├── v1.3/                                  # historical contracts
│   └── v1.4/                                  # 19 current schemas
├── scripts/
│   ├── build_g0_fixtures.py
│   ├── run_reliability_batch.py
│   └── validate_contracts.py
├── frontend/                                 # React Research + Skill Lab
├── migrations/                               # Alembic schema history
├── benchmark/suites/                         # pre-registered split membership
├── src/
│   └── researchforge/
│       ├── adapters/                         # fixtures, storage, OpenAI boundary
│       ├── api/                              # FastAPI resources
│       ├── application/                      # lifecycle, budget, analysis services
│       ├── domain/                           # Decimal formulas and period semantics
│       └── workflow/                         # bounded ten-stage LangGraph
└── tests/                                    # domain, adapters, workflow, API and CLI
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

## Implementation Order

```text
Contracts and data-source acceptance ✓
→ golden earnings-quality cases ✓
→ one LangGraph-orchestrated end-to-end research slice ✓
→ checkpoint recovery + deterministic and coverage verifier ✓
→ remaining product modes + 20-run reliability ✓
→ two-page UI + PostgreSQL + CI definitions ✓
→ signed formal Benchmark data + controlled evolution cycle ← current
→ Docker smoke + simulations + demo/public packaging
→ one final independent acceptance
```

## Validate the Contract Package

```bash
python3 scripts/validate_contracts.py
```

The dependency-free validator checks V1.4 JSON syntax, schema metadata, local `$ref` resolution, current examples and live project checkpoint, historical V1.2/V1.3 integrity, Markdown links, and required project files.

## Safety and Disclaimer

ResearchForge is a research-assistance prototype, not investment advice. Any future data integration must document its license, provenance, retrieval time, publication time, and redistribution restrictions. Secrets and licensed raw datasets must not be committed.
