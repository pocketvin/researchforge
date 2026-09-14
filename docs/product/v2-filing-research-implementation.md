# V2 Filing Research — implementation and acceptance boundary

Updated: 2026-09-14

## Product scope

V2 is the sole live, filing-only Research Agent runtime. The V2 API uses `/v2`, the browser entry is `/` (`/research/v2` is an alias), and runtime artifacts/cache live under `artifacts/v2`. Frozen V1.8.5 contracts, evidence, reviewed packages and old Runs remain available only as immutable history; there is no live V1 research execution route. Do not reinterpret historical manifests, reports, or evolution experiments as V2 outputs.

The user-approved target is a single research agent with tool use, complete original-filing access, structured public research state, honest stopping, deterministic financial calculations, continuous trace persistence, and an evidence-first Web report. External news/search expansion, multi-agent debate, slides, trading, valuation breadth, and autonomous production deployment are not part of this milestone.

## Implemented structure

`src/researchforge/v2/contracts.py` defines typed requests, tools, hypotheses, open questions, submissions, reports, reviews, and events. `storage.py` handles run identity, content-addressed artifacts, raw blobs, event sequencing, and real timed spans. `documents.py` preserves native PDF pages or HTML sections, table-cell candidates, figures, footnote candidates, and navigable evidence. `preparation.py` reuses official-issuer/filing discovery and existing exact financial extraction rules, storing originals before model use.

`tools.py` exposes bounded native capabilities rather than a shell or arbitrary Python interpreter. `compute.py` and `series.py` keep arithmetic and statement-row promotion deterministic: the model names a page/row/metric, while code maps year headers, sign, explicit units and run-owned source lineage before any ratio is computed. English and Chinese aliases are supported for the bounded metric dictionary; explicit Chinese statement scales such as `万元` are parsed without magnitude inference. `runtime.py` uses one LangGraph research loop with durable public state, locked required Research Objectives, targeted counter-evidence, final synthesis, reference validation, and separately labeled semantic review.

The primary hybrid route uses DeepSeek V4 Flash for the high-frequency filing Tool Loop, public-state Reflection and structured Synthesis; Qwen Plus performs claim-wise semantic review and Qwen3-VL Plus is selected only for evidence that actually requires page-image understanding. Kimi remains optional standby metadata only and is not required for the active route. Provider-private histories do not cross provider boundaries. DeepSeek availability is not a single point of failure: timeout/connection or HTTP 402/408/429/5xx triggers a visible, run-sticky fallback to Qwen Plus for Tool Calling and Qwen3-Max for Reflection/Synthesis. If text-only Qwen semantic review itself fails, the explicitly labeled review fallback is DeepSeek V4 Flash and independence is downgraded; HTTP 400 is deliberately not hidden by research-provider fallback.

Writing is no longer allowed to destabilize completed research. Synthesis receives a Run-bound JSON Schema whose evidence/fact/calculation IDs are enums from the actual research context. Deterministic validation remains a second gate. If model prose repeatedly fails report-only constraints, a Safe Dossier Renderer can expose the already-submitted Objectives/Dossier without new inference or arithmetic; the conservative report still has to pass the same validation and claim-wise semantic review. Only a genuine material research-coverage gap returns to the Research Agent.

`api.py` exposes V2 submission/status/results, facts/calculations/search, source access, page images, workspace data, persisted event replay and SSE. `frontend/src/v2/` is the only browser research workspace: report, original tables/pages, hypothesis notebook, stop decision, live journal, technical disclosure, and evidence drawer. CLI, MCP and n8n call the same V2 Run resources.

Reliability boundaries are fail-closed at intake and recovery. Report periods are validated against supported market/report combinations before queueing. Document-cache fallback is eligible only when its parser version matches the current parser. Provider budget reservations are persisted as short 300-second leases so a process crash cannot reserve aggregate budget forever; confirmed spend remains durable, while stale reservations are reclaimed consistently with the existing “unconfirmed failed cost is not billing truth” policy. The durable event journal has no 2,000-event product truncation: `/trace` reads the complete requested suffix and SSE drains bounded internal batches before emitting terminal.

## Important distinctions

- A parsed table is an **extraction candidate**, not a verified financial fact. Native borderless/cross-page tables, merged headers, uncertain units, vector figures and footnote scope remain observable limitations. Original pages are retained for inspection.
- Embedded figures and actual PDF rendering are supported as document objects. This is not a claim that every chart was recognized or that every chart value can be safely converted into a canonical fact.
- The initial bootstrap is only a starting context. Documents and pages remain accessible through tools; a retrieval miss does not remove the original from the agent's universe.
- The research notebook is an explicit model-authored work product. Its confidence labels and sufficiency judgment are **not** empirical quality scores.
- Hard reference validation is distinct from semantic model review. Model review is fallible and cannot prove global financial correctness.
- Current financial compute covers a bounded verified formula set. Broad KPI extraction and a complete financial-analysis formula library are not claimed.
- No model call is replaced by a deterministic imitation in the product path. Scripted model ports exist only in explicitly synthetic tests.
- True multi-turn research memory is deferred. A suggested follow-up currently creates a new same-company run; the UI says so.

## Actual live-source attempt

The recorded live run is `run_e281fb75e7e442e096e6846ac9f3e4a5`. Official discovery, acquisition, parsing and baseline facts succeeded for 宁德时代 2024H1: 174 PDF pages, 414 native table candidates, 1 embedded-image candidate, 7 footnote candidates, 182 evidence chunks and 6 canonical financial facts. Raw document SHA-256: `2a690cb2471c1f0d4539d909a9f068c03710a838ddd35313175790169e85eab1`.

The first OpenAI-backed provider request was rejected with HTTP 429 / `credit_balance_exhausted`; that historical failure remains preserved. With owner authorization, existing local SignalHarness provider credentials were copied into ResearchForge without printing secret values and the V2 provider layer was made role-routable rather than tied to OpenAI or Qwen. The current default hybrid path has completed real end-to-end filing research.

The original primary-provider reference smoke remains `run_a35c700d98a14877b1d47ee09d77452e` on CATL 2024H1: 3 Research Agent turns, four required objectives, targeted counter-evidence and a successful DeepSeek→Qwen report/review chain. Later live failures were deliberately kept because they drove stronger runtime contracts rather than being erased.

The current provider-failover canary is `run_131b617ec0394bcab000e35476ccf651` on the public FinanceBench 3M FY2018 CAPEX question. The DeepSeek request failed with HTTP 402, the Run visibly switched providers, and the fallback chain completed with Qwen3-Max Reflection, Qwen Plus filing Tool Calling, Qwen3-Max Synthesis and Qwen Plus claim-wise Review. Alias-aware bootstrap put the correct cash-flow page first, so the Run finished in **2 Agent turns / 7 provider calls / 33,023 tokens** with the correct `$1,577 million` answer and annotated evidence-page recall `1.0`. The older fallback baseline on the same question required 7 Agent turns / 15 provider calls / 166,626 tokens. These are canary efficiency measurements, not billing truth or a general quality claim.

Report-safety paths were also exercised independently. A real Safe Dossier report built from a filing-research dossier passed deterministic validation and Qwen Plus claim-wise review with all four local findings supported. Conversely, model-created source IDs, uncalculated percentages, unsupported industry thresholds and causal statements inferred only from gross/net PP&E differences were blocked rather than silently delivered.

Evidence:

- `artifacts/v2-implementation/outputs/live-run-id.txt`
- `artifacts/v2-implementation/outputs/live-run-summary.json`
- `artifacts/v2/runs/` and the matching immutable source/events/artifacts

## Independent quality evaluation

`src/researchforge/v2/quality.py` defines a reference-backed measurement instrument separate from product self-review. `scripts/evaluate_v2_quality.py` accepts a frozen case and optional report-bound independent semantic annotations. It makes no provider calls.

Each case fixes issuer, cutoff, corpus identity, numeric targets when available, acceptable evidence, semantic finding requirements, counter-evidence and acceptable unknowns. `FindingRequirement` IDs belong to the independent reference, while report `claim_id` values belong to system output; an assessor must map between them explicitly. Evaluation rejects a changed corpus, unknown report claim, or misbound annotation rather than giving a misleading low score. It reports fact recovery, evidence observation and trajectory diagnostics with explicit denominators; suite summaries use Wilson 95% intervals and never manufacture a composite score. Semantic correctness, completeness and stop quality remain **unmeasured** without report-bound annotations.

The external FinanceBench track is pinned to commit `cc39aeb4afdf33909ee1412188bf89035950c2eb` and uses its public 150-question open-source sample only as a development/canary source. Gold answers and evidence labels live under the isolated benchmark artifact root and are loaded only after the product Run; they never enter Agent context. Parsed PDFs are cached by content hash. The public sample is explicitly `development`, not validation, hidden, or held-out. Imported reference labels start as `provided`; source-consistency audits may mark a case `verified` or `suspect`. A suspect gold label is retained for audit but excluded from automatic gold-scalar measurement.

Synthetic tests validate the evaluator itself and FinanceBench canaries validate the external adapter; neither constitutes a reviewed multi-issuer product-quality benchmark. FinanceBench also exposed an important anti-overfitting lesson: its capital-intensity reference answer uses ROA as a supporting metric, but ResearchForge does not adopt that rubric merely to gain benchmark points. The product methodology now treats capital intensity as capital required per unit revenue (`CAPEX / Revenue`, `Average Net PP&E / Revenue`, `Average Total Assets / Revenue`) and keeps ROA as return context. Without filing-linked thresholds/comparables or an explicit source characterization, a categorical label remains limited/cannot-determine.

Post-run semantic assessor output is always labeled `uncalibrated_model`. Assessor independence is derived from the product Run's actual usage/model roles, including provider fallback. For example, if qwen3-max wrote a fallback report and qwen3-max is later used as benchmark Judge, metadata records `same_model_as_product_synthesis`; it is not described as independent. Reference-backed evaluation remains useful for development diagnostics, but held-out acceptance no longer requires humans to author reference labels. A quality claim requires a frozen unseen input set plus choice-only human acceptance of the finished outputs; broad statistical superiority still requires a larger study than the compact owner suite.

The canonical public-development suite is tracked at `docs/contracts/v2/benchmarks/financebench-public-development-10-v1.json`: 10 cases across 9 companies, with three historical anchors plus seven reasoning strata selected without reading answer/justification/evidence fields. It pins FinanceBench commit/source SHA, selector version/seed and canonical suite hash `7ac57d910eb8792975137fbb27c1f4fac0722375ed5d2411a1e52c4ae461847a`. Suite execution records also pin an implementation fingerprint and refuse resume after behavior-bearing code changes; public development results from different fingerprints must not be pooled as if they were one experiment.

The suite has already found defects in both product and evaluator code. A real Activision run showed that an older `calculate_series_metric` argument shape could be rejected and then incorrectly cached as `no_new_information`, causing the Agent to hand-calculate percentages. The capability boundary now migrates only that unambiguous historical series-pair shape, emits an auditable `tool_protocol_migrated` event, and never caches failed Tool results as successful research reuse. Final regression `run_0ceba675497f4b069350faf2fe66f95a` generated deterministic calculation `calc_219e29f1bd18d78eaffd0438 = 1.9%`, required one report-only scope repair, used no Safe Report, and ended with one material finding.

The same regression exposed an evaluator bug: head-only evidence truncation hid a `Capital expenditures (116) (131) (155)` line that the product had actually cited. Benchmark compression now selects claim/question-relevant windows in both cited product evidence and frozen reference pages. Reassessment of the final Activision report measured 10/10 atomic claims correct, 10/10 citation support and full reference-finding coverage. These values remain `uncalibrated_model` development diagnostics and are explicitly unsuitable for a product-quality claim.

## Acceptance gates

1. Versioned contracts and no historical schema reinterpretation.
2. Backend lint, strict types, unit tests, real-tool integration with synthetic model transport, failure/recovery/cancellation tests.
3. Frontend types, lint, unit tests, build and actual endpoint/DOM checks on isolated preview ports.
4. No raw hidden reasoning or encrypted reasoning payload in persisted artifacts; no secret output.
5. Original source/table/page navigation works for the real stored filing, including failed model runs.
6. Real provider multi-turn tool use, objective-based stopping, counter-evidence, final synthesis and semantic-review loop complete successfully. **PASS on the recorded CATL hybrid smoke.**
7. Frozen unseen quality acceptance with choice-only human judgment, not just regression tests. **Not yet established.**

Current verification records belong in `artifacts/v2-implementation/outputs/engineering-verification.json`. The 2026-09-14 canonical-runtime gate records 302/302 pytest, Ruff format/check, strict MyPy across 52 source files, preserved V1 contract validation (625 schema refs / 126 Markdown links / 141 required files), 48 generated V2 schemas with zero drift, Python/frontend dependency audits, frontend typecheck/lint/7 Vitest + 3 mocked E2E + 1 live-backend E2E, production build and 8/8 n8n Node contract tests as PASS. Only actual command exit codes and measured outputs may be recorded as passing. The existence of code, schemas, screenshots or a test double is not final product acceptance.

## Owner runtime boundary

Ports 8000/4173 are the canonical V2 Owner runtime. Do not recreate them as a deterministic test stack.
Deterministic packaging checks use isolated ports/projects through `scripts/container_gate.py`; owner
startup goes through `scripts/start_demo.py` and verifies effective V2 provider routing. Historical V1
releases remain preserved as evidence, not as a parallel running service. No push, public exposure or
production release is inferred from local implementation work.

## Held-out acceptance boundary

The public FinanceBench suite is intentionally development-only. A separate V2 held-out acceptance
protocol now exists at `docs/contracts/v2/heldout-quality-protocol.md`, with reviewer procedure at
`docs/contracts/v2/heldout-reviewer-guide.md`. Acceptance-v2 freezes only private runtime cases and
source bytes before execution; it does not require human-authored reference cases or pre-run review
attestations. Git receives only a non-revealing seal (hashes/counts/review mode/opaque case and issuer
hashes); private questions and sources are rejected if they become Git-visible.

The tracked development-issuer exclusion manifest covers companies materially used by ResearchForge
V1/V2 development, owner acceptance, product smokes and the entire 32-issuer FinanceBench public
universe. Seal creation also freezes a private development-exposure snapshot containing exposed
issuer aliases, exact-question hashes, public case IDs and source-registry hashes, including persisted
V2 requests. Acceptance-v2 rejects both issuer and exact-question overlap and uses at least 8 cases, 4
issuer groups and 4 task strata.

Formal current-V2 execution is implemented by `scripts/run_v2_heldout_acceptance.py`: it re-verifies
the seal, arms the single-use ledger, builds the normal V2 document environment from the exact sealed
PDF/HTML bytes, checks SHA-256 and publication cutoff, and never performs live filing discovery. The
formal automatic runner currently supports single-result `Meets standard / Does not meet standard /
Cannot judge`. Blind pairwise presentation remains implemented and browser-tested, but automatic
pairwise execution is intentionally fail-closed until V1 and V2 can consume the same frozen corpus;
no unfair comparison is treated as acceptance evidence.

No explanation, corrected answer, evidence labeling or manual number audit is required. A frozen seal
is single-use for quality acceptance. Only a recorded infrastructure `technical_failure` before the
first valid product result may retry on the identical implementation hash. A later failure after any
valid product result retires the attempt instead of reopening the hidden suite. If revealed results
are used to change product behavior, that seal is retired and a later acceptance requires a new
disjoint seal.

No real held-out acceptance bundle or seal has been created. The choice-only delivery mechanism has
been browser-verified only with an explicitly synthetic 8-case private demo: the offline page showed
four blind A/B choices, advanced from 1/8 to 2/8 on one click, downloaded eight judgments on the final
click, and restored the hidden candidate mapping in the generated summary. The strengthened synthetic
script chain additionally passes seal → exposure-bound verification → review generation, and focused
tests cover frozen-source execution, tamper/cutoff rejection, single-pass orchestration and attempt
retirement after partial results. This is tooling evidence, not quality evidence.
