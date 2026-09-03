# Phase 4 — Same-backend n8n Engineering Evidence

Status: **ENGINEERING CHECKPOINT PASSED — LOCAL + PUBLIC CI**

Published implementation: `ba17df0b6f20e4d7b90b2d798bc169191d7bd91f` ·
[GitHub Actions 33781494639](https://github.com/pocketvin/researchforge/actions/runs/33781494639)

This is real n8n 2.37.9 executing the imported/published workflow, not a JSON-only simulation.
ResearchForge and its PostgreSQL-backed API are the same containers serving Web. Research wording
was deterministic, with zero provider calls. No human participated; usefulness is **UNVALIDATED**.

## Real disclosure paths

| Filing | Facts | Calculations | Evidence | Trace stages | All five backend artifacts identical |
|---|---:|---:|---:|---:|---|
| CATL 2024H1 | 6 | 4 | 8 | 10 | yes |
| CATL 2024FY | 6 | 4 | 6 | 10 | yes |
| BYD 2024H1 | 6 | 4 | 8 | 10 | yes |

Actual persisted webhook outputs:

- [CATL 2024H1](cn_300750-2024H1.json)
- [CATL 2024FY](cn_300750-2024FY.json)
- [BYD 2024H1](cn_002594-2024H1.json)
- [Machine-readable run IDs, time and workflow hash](summary.json)

Each output includes unchanged backend Research Result, Financial Facts, Calculation Records,
Evidence Chunks and Workflow Trace. Exact aliases for conclusion/findings/limitations/monitoring
were compared too. Official source identities and deterministic PDF recovery proofs remain in the
[Phase 3 evidence](../v1.5-generalization/README.md); n8n neither re-extracts nor substitutes them.

## Actual transport and failure checks

- Real production workflow: identical-request replay returns the original run ID; the minimal
  three-field request succeeds; invalid input, backend-address injection, unsupported company,
  idempotency conflict and too-early evidence cutoff return explicit failures (five checks).
- Eight Node test groups cover portable graph wiring, immutable retry inputs, namespace refusal,
  URL/run-ID constraints, every lifecycle state, count/time bounds, unknown states, unavailable
  artifacts and exact alias mapping.
- A separately named `[TEST ONLY]` workflow uses the identical route code with a three-poll test
  limit and an isolated HTTP transport fixture. Actual n8n execution passed five scenarios:
  running twice then failed, running twice then cancelled, three-poll exhaustion, unavailable
  status and completed-state/missing-artifact failure. No financial value or report exists in
  this fixture; it is not real-research evidence or a new benchmark.

Initial failures were retained in the work log: short n8n IDs first generated an undersized
idempotency key; fixed by a stable `n8n-run-` prefix. An unsupported-company test exposed the
backend's insufficient-data terminal behavior; n8n now mirrors Web by checking company/period
capability from the backend catalog before submitting. Strict typing caught a script import path,
corrected by invoking the smoke as a Python module.
The full backend regression initially expected seven V1.5 schemas; updated it for the new eighth
integration schema. The local Playwright default browser was missing; all five journeys passed
using the existing Chrome executable. n8n ESLint reuses the installed frontend toolchain without
adding dependencies and now understands the Code-node function body context.
首次公共 CI 的 n8n 容器检查失败：`/healthz` 在 n8n 发布工作流激活前已返回 200，smoke 收到
非 JSON 启动响应。已依据实际 2.37.9 服务实现改为 `/healthz/readiness`；该端点同时要求数据库
连接、迁移和 `fullyReady`，修复后必须重跑全部 CI，不能把首次运行记为通过。

## Reproduction

Start/import/publish using [integration README](../../../integrations/n8n/README.md), then:

```bash
node integrations/n8n/build-workflow.mjs --check
node --test integrations/n8n/workflow.test.mjs
uv run python -m scripts.n8n_smoke
```

For transport-fixture checks, CI documents the exact creation/import/publish sequence in
[ci.yml](../../../.github/workflows/ci.yml). The fixture workflow JSON lives only under ignored
`artifacts/n8n-runtime-fixture`; it cannot enter the product or Benchmark data namespace.

## Remaining boundaries

- Phase 5 still owns final Web/n8n UX, screenshots, interview narrative and release-ready demo.
- Phase 6 real-human Web+n8n evaluation has not begun; no simulated feedback substitutes for it.
- Final project-wide independent acceptance is deferred to Phase 7. No Phase 4 reviewer was run.
- Local webhook is not a public authenticated endpoint. A process crash or outer execution timeout
  may produce a disconnected request instead of custom JSON; retry with the original immutable
  request. See [failure behavior](../../../integrations/n8n/failure-behavior.md).
