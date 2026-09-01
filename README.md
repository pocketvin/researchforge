# ResearchForge

> A Financial Research Agent with Verifiable Procedures and a Controlled Learning Experiment.

ResearchForge V1.4 is an evidence-grounded company fundamental-research product and a controlled skill-evolution experiment. The current local product turns frozen A-share financial facts into schema-valid reports, deterministic evaluations, and sanitized ten-stage LangGraph traces without asking a model to perform arithmetic.

## 中文概览

ResearchForge V1.4 是一个面向 A 股基本面研究的本地单用户产品，也是一个封闭的 Skill 演化实验。Research 页面把五种研究任务转成可追溯的财务事实、`Decimal` 公式、Claim—Fact—Evidence、反证、限制与十阶段 LangGraph Trace；Skill Lab 只读展示失败聚类、Experience、Candidate Skill Diff、Validation 配对指标和一次性 Final Test。React、FastAPI 与 PostgreSQL 可由 Docker Compose 一键启动，大型不可变 JSON 使用内容寻址文件保存。

项目不会提供交易、实时行情或投资建议，也不会开放式自我修改。正式实验固定模型、数据、图、Verifier 和三次重复；主实验不支持假设时最多启用一次完全隔离的 V1.5 备用实验。真实用户价值尚未验证，三次 AI 可用性检查必须标记为 `SIMULATED`。当前离正式研究结论只差主数据包人工签字、轮换后的本地 API Key 及封闭实验执行；OpenAI 累计消费仍为 0 美元。

快速启动：`docker compose up -d --build --wait`，随后执行 `uv run python scripts/docker_smoke.py`。完整中英文演示见 [`docs/demo/walkthrough.md`](docs/demo/walkthrough.md)。

## Status

- Product/research scope: **V1.4 active baseline**
- Contract package: **1.4.0**
- Independently accepted gates: **V1.4 C0 + G0**
- Local implementation: **G1 five-mode breadth + G2 Verifier evidence implemented; one final independent acceptance is deferred until project completion**
- Active milestone: **G3 primary package signoff + rotated key + formal execution**
- Supported deployment for V1.4: **local or controlled single-user demo**

Current critical path: sign the prepared primary package, confirm a rotated local key, pass one synthetic provider calibration, then run the implemented controlled Evolution/Validation/Final Test executor. The disjoint V1.5 package, Docker runtime, screenshots, demo video, and three-session simulation executor are ready. After G3, run the three labeled simulations, publish the public package, and perform one final independent review. Synthetic tests and calibration are not a formal `SUPPORTED` result.

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

## Inspect the Formal Experiment Safely

First validate the one-request calibration boundary without contacting OpenAI:

```bash
uv run researchforge calibration-preflight
```

After the rotated key is confirmed, `calibrate` sends exactly one synthetic request and
freezes its model, prompt, Structured Output, coverage, usage, and cost evidence. This
request is explicitly marked `SYNTHETIC_CALIBRATION_ONLY_NOT_RESEARCH_EVIDENCE` and cannot
support the research hypothesis:

```bash
uv run researchforge calibrate
```

The formal offline preflight then validates the passed calibration, public hashes, 24
verifier-only ground-truth hashes, the Seed Skill, the 144-run plan, one-time Final Test
policy, and both budget ceilings. It never contacts OpenAI:

```bash
uv run researchforge evolution-preflight
```

Until owner signoff and a rotated local key are present, the expected result is
`status: BLOCKED` with `provider_contacted: false`. Never paste a key into a command or
Git-tracked file. After explicit signoff, keep the rotated key only in ignored local
environment configuration, set `RESEARCHFORGE_ROTATED_KEY_CONFIRMED=1`, load that local
environment, pass the calibration, and use `evolution-run` to execute or idempotently
resume the experiment.

The maximum plan is 144 formal runs: 72 Base/Seed Evolution runs, 36 paired
Seed/Candidate Validation runs, and—only after adoption—36 paired runs in the single
sealed Final Test stage. Every run uses the same ten-stage LangGraph; ordinary Python
owns clustering, patch policy, budget enforcement, and adoption decisions.

Start the frontend separately:

```bash
npm ci --prefix frontend
npm run dev --prefix frontend
```

Or start the complete packaged product:

```bash
docker compose up -d --build --wait
uv run python scripts/docker_smoke.py
```

The verified stack runs PostgreSQL, FastAPI, and Nginx/React with health checks and persistent volumes. Standard Docker Hub image names remain the defaults; optional `PYTHON_IMAGE`, `NODE_IMAGE`, `NGINX_IMAGE`, and `POSTGRES_IMAGE` build overrides are available for compatible mirrors.

The same aggregate budget ledger controls three fresh-context usability sessions. Offline preflight never contacts OpenAI:

```bash
uv run researchforge usability-preflight \
  --run-id <persisted-succeeded-run-id>
```

The expected result remains `BLOCKED` until the rotated local key is confirmed. A real run writes exactly three schema-valid records with `evidence_label: SIMULATED` and `human_user_value_validated: false`.

## Start Here

1. [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — current gate, blockers, and one next action.
2. [`docs/product/researchforge-v1.4-scope.md`](docs/product/researchforge-v1.4-scope.md) — current product and research authority.
3. [`DECISIONS.md`](DECISIONS.md) — accepted and pending architecture/data choices.
4. [`docs/strategy/solo-success-plan.md`](docs/strategy/solo-success-plan.md) — L0–L4 delivery ladder and fallbacks.
5. [`docs/contracts/research-workflow.md`](docs/contracts/research-workflow.md) — bounded LangGraph orchestration.
6. [`PORTFOLIO.md`](PORTFOLIO.md) — claims that are safe at each evidence level.
7. [`docs/demo/walkthrough.md`](docs/demo/walkthrough.md) — bilingual live demo and packaged evidence.

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
| L3 Research Supported | Adopted Candidate and supported sealed Final Test | executor and both frozen packages ready; live evidence blocked by signoff/key |
| L4 Full Engineering Product | Five modes, two pages, supported storage, Docker, CI, three labeled simulations | engineering/runtime/demo ready; simulations and publication pending G3 |

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
│   ├── demo/                                  # bilingual walkthrough and script
│   ├── assets/                                # verified screenshots and short MP4 preview
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
│   ├── docker_smoke.py
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
→ primary + contingency package freeze ✓
→ Docker smoke + simulation executor + demo packaging ✓
→ primary owner signoff + controlled live evolution cycle ← current
→ three live labeled simulations + public packaging
→ one final independent acceptance
```

## Validate the Contract Package

```bash
python3 scripts/validate_contracts.py
```

The dependency-free validator checks V1.4 JSON syntax, schema metadata, local `$ref` resolution, current examples and live project checkpoint, historical V1.2/V1.3 integrity, Markdown links, and required project files.

## Safety and Disclaimer

ResearchForge is a research-assistance prototype, not investment advice. Any future data integration must document its license, provenance, retrieval time, publication time, and redistribution restrictions. Secrets and licensed raw datasets must not be committed.
