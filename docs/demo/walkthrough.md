# ResearchForge V1.5 Reproducible Walkthrough / 可复现实演

## Evidence boundary / 证据边界

The default runtime uses only the strict `product` namespace. The current allowlist contains CATL
`2024H1`, CATL `2024FY` and BYD `2024H1`, all derived from hash-verified official SZSE filings by
the same six-metric extractor. Frozen fixture and Benchmark packages remain for tests and Quality
Lab but cannot serve a product run.

默认运行时只使用严格的 `product` 命名空间。白名单包含宁德时代 `2024H1`/`2024FY` 与比亚迪
`2024H1`。冻结 fixture 和 Benchmark 只用于测试与 Quality Lab，不能回退为产品数据。

## Zero-cost preflight / 零成本预检

```bash
RESEARCHFORGE_REASONING_MODE=deterministic uv run researchforge catalog
uv run python scripts/validate_contracts.py
```

Expected catalog boundary:

```text
data_namespace: product
companies: cn_300750 (2024H1, 2024FY); cn_002594 (2024H1)
supported_task_types: filing_analysis
```

## Start / 启动

For a reproducible zero-provider-cost UI run:

```bash
uv run python scripts/start_demo.py
```

Open Web at `http://127.0.0.1:4173/` or the n8n form at
`http://127.0.0.1:5678/form/researchforge-v15-form`. The launcher imports/publishes the exact
workflow and runs both smoke paths. `--dry-run` prints commands; `--no-build` reuses images.

If ignored `.env` contains a confirmed rotated key, omit the deterministic override to use the
bounded OpenAI wording adapter. API keys are never committed or pasted into demo evidence.

## Product walkthrough / 产品演示

1. Confirm the first screen shows Company, Period, Question and Start Research—no experiment
   terminology is needed.
2. Select 宁德时代, `2024H1` and ask whether profit converted into operating cash flow.
3. Start the run and read the Executive Conclusion before opening audit details.
4. Check the Key Finding: cash conversion is `1.96x`.
5. Expand Financial Facts and locate net income CNY `22,864,987,400.00` and operating cash flow
   CNY `44,708,954,600.00`.
6. Expand Calculations and inspect the deterministic formula record.
7. Expand Supporting Evidence and open one official source locator.
8. Read the unaudited-report and non-recurring-profit counter evidence.
9. Read Risks & Limitations and the next-filing Monitoring Plan.
10. Expand Research Trace and inspect all ten bounded LangGraph stages.

## n8n walkthrough / n8n 演示

1. From Web, follow **使用 n8n 表单入口**, or open the form URL above.
2. Submit CATL `2024H1` with the same question. The page waits on bounded polling and renders the
   same backend conclusion and artifacts without requiring an n8n editor account.
3. Expand Financial Facts, Calculations and Supporting Evidence; open Result/Trace links to prove
   backend identity.
4. Submit BYD `2024FY`. The page must say **研究未生成** with
   `UNSUPPORTED_OR_INVALID_INPUT` and no Executive Conclusion.
5. Use the webhook only when demonstrating machine integration and exact HTTP/error contracts.

## CLI reproduction / CLI 复现

```bash
RESEARCHFORGE_REASONING_MODE=deterministic \
RESEARCHFORGE_DATABASE_ENABLED=false \
uv run researchforge --artifact-root artifacts/v1.5-demo run \
  --task-type filing_analysis \
  --company cn_300750 \
  --period 2024H1 \
  --question '2024 年上半年利润是否真正转化成了经营现金流？' \
  --research-time '2026-09-03T00:00:00+08:00' \
  --idempotency-key 'v1.5-catl-2024h1-demo-deterministic-v1'
```

The verified reference run is `run_b69d4aaf34e045c19619d4b9f88ebaca`; ignored local artifacts
may be regenerated, so public evidence is summarized in [`v1.5-demo-evidence.md`](v1.5-demo-evidence.md).

## Quality Lab / 质量实验室

Quality Lab is optional, experimental and read-only. It is not required for normal research. If
shown, use it only to explain the immutable negative research outcome and the decision not to
manufacture a successful Candidate.

## Media / 媒体

V1.5 product screenshots:

- `docs/assets/research-page-v1.5-final-start.png`
- `docs/assets/research-page-v1.5-final-result.png`
- `docs/assets/n8n-form-v1.5.png`
- `docs/assets/n8n-result-v1.5.png`
- `docs/assets/n8n-abstention-v1.5.png`
- `docs/assets/quality-lab-page-v1.5.png`

The older `research-page.png`, `skill-lab-page.png` and V1.4 MP4 remain untouched historical
evidence. A V1.5 video can be recorded from this walkthrough without making it a product gate.

## Safety statement / 安全声明

The repository contains no API key, hidden ground truth or raw filing PDF. ResearchForge is not
investment advice. The final dual-surface protocol is frozen but remains `PREPARATION_ONLY` with
zero sessions; formal Web+n8n evaluation is deferred until Phase 6.
