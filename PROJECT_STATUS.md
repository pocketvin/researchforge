# ResearchForge Project Status

<!-- V2-ACTIVE-STATUS -->
## V2 filing-research implementation — REAL FLOW / HELD-OUT FAILURES REPAIRED / FINAL OWNER ACCEPTANCE NOT ESTABLISHED

Updated: 2026-09-14

The V1.8.5 release history below remains frozen as audit history. V2 is now the only live filing-research runtime; independent held-out Owner Acceptance is still not established.

- Implementation: `src/researchforge/v2/`, `/v2` API and the sole Web research workspace at `/` (with `/research/v2` retained only as a V2 alias). V2 contracts are exported from live Pydantic models into `schemas/v2/`; generated-schema drift is tested.
- Real official CATL 2024H1 document environment: 174 pages, 414 native table candidates, page-image inspection and six canonical financial facts. Raw filing/page/table artifacts remain source-of-truth; parsed tables are candidates rather than automatically trusted facts.
- Primary hybrid route: DeepSeek V4 Flash for filing Tool Loop, public-state Reflection and structured Synthesis; Qwen Plus for claim-wise semantic review; Qwen3-VL Plus only for actual page-image interpretation. Kimi remains standby only. Eligible DeepSeek timeout/connection or HTTP 402/408/429/5xx failures visibly switch the rest of that Run to Qwen Plus Tool Calling + Qwen3-Max Reflection/Synthesis; HTTP 400 remains fail-closed.
- Complete-document bootstrap expands known financial-metric aliases plus statement context without closing the evidence universe. English and Chinese metric aliases and explicit Chinese units such as `万元` are supported. The real 3M FY2018 CAPEX fallback canary `run_131b617ec0394bcab000e35476ccf651` completed in **2 Agent turns / 7 provider calls / 33,023 tokens**, versus the older 7-turn / 166,626-token fallback baseline, while retaining the correct `$1,577 million` answer and annotated page recall 1.0. These are canary efficiency observations, not billing truth or a general quality claim.
- Research completion is objective-based rather than fixed-step. Required objectives are locked after initial decomposition; supporting discoveries cannot silently expand completion. Analytical conclusions require targeted counter-evidence. Evidence exhaustion cannot bypass deterministic work that is already possible: capital-intensity dimensions distinguish `complete`, `ready_to_calculate`, and genuinely `missing_inputs` states.
- Financial arithmetic remains deterministic. Verified Statement Series bridge table/page rows into calculations without model-copied operands. `calculate_series_metric` now safely migrates the unambiguous historical `metric + numerator_series_id + denominator_series_id` call shape to the current `formula + series_ids` contract, while ambiguous calls remain fail-closed. Failed Tool results are never cached as successful `no_new_information` responses.
- Final writing is isolated from research. Report IDs are Run-bound by schema; numeric provenance and citation validation remain deterministic. Focused extraction/calculation requests are limited to the material findings required by the user's required objectives, preventing unrelated method commentary from expanding the final report. Repeated writer-only failure can fall back to a conservative Safe Dossier report, which still must pass deterministic validation and claim-wise review.
- Current capital-intensity methodology measures direct capital demand (`CAPEX / Revenue`, `Average Net PP&E / Revenue`, `Average Total Assets / Revenue`); ROA is return context, not a definition. Without filing-linked thresholds/comparables or explicit characterization, categorical capital-intensity remains `limited / cannot_determine` rather than using invented cutoffs.
- FinanceBench is now formally a pinned **public development/canary** track, not validation or held-out quality evidence. The tracked suite `docs/contracts/v2/benchmarks/financebench-public-development-10-v1.json` contains 10 cases / 9 companies / 7 stratified reasoning strata plus 3 anchors, pins source commit/SHA/selector version, contains no answer/justification/evidence fields, and has suite hash `7ac57d910eb8792975137fbb27c1f4fac0722375ed5d2411a1e52c4ae461847a`. Suite executions record an implementation fingerprint and refuse resume after code changes, so pre-fix/post-fix results cannot be silently pooled.
- The post-run semantic assessor remains `uncalibrated_model`. Evidence/reference compression now selects claim/question-relevant windows instead of blindly truncating the head of long pages. On final Activision regression `run_0ceba675497f4b069350faf2fe66f95a`, deterministic `average_ratio_percent` produced 1.9%; the final focused report contains one material finding, and qwen3-max post-run assessment measured **10/10 atomic claims correct, 10/10 citation support, 1/1 reference finding covered**. It still records `product_claim_suitable=false` and `different_model_same_provider`, so this is diagnostic development evidence, not a product-quality claim.
- Latest canonical-runtime engineering gate: **297/297 project pytest PASS**, Ruff format/check PASS, strict MyPy PASS across **52 source files**, preserved V1 contract validator PASS (**625 schema refs / 126 Markdown links / 141 required contract files**), **48 V2 generated schemas** with zero drift, frontend typecheck/lint + **7/7 Vitest + 3/3 mocked E2E + 1/1 live-backend E2E** + production build PASS, n8n **8/8** Node contract tests PASS, `pip-audit` reports no known dependency vulnerabilities (editable local package skipped), `npm audit --audit-level=high` reports 0 vulnerabilities, and `git diff --check` PASS.
- Held-out acceptance machinery has now been exercised on real private suites **A through I**. Every result-exposed suite is retired to development exposure after inspection/tuning; no exposed suite is eligible for a formal rerun. Suite E completed all 8 product executions but the owner's blind review accepted only 1/8, exposing user-facing report-quality gaps. Later F/G/H/I suites exposed additional product failures rather than being retried or relabeled as passes. The final fresh suite I (`heldout-170fc492512500e2`, seal hash `6ae88c1b9dc32f13b563f29b21d87af4f8ca2740d9ba589b6b2cb0b8f9917122`) completed 1 product result and failed case 2 with `SAFE_REPORT_SEMANTIC_REJECTED`; attempt `heldout-170fc492512500e2-acceptance-1-2072c9324e` is retired with results opened and tuning recorded.
- I exposed four concrete development defects that have since been repaired without weakening the acceptance gates: (1) year-over-year analytical scope could expand beyond an explicit management bridge into adjacent cash-flow/OREO/equity/litigation disclosures; (2) percentage suffix-direction parsing could bind a later `decrease` phrase to an earlier positive percentage such as `4.28%`; (3) a pure `WorkingState` text-length overflow could terminate the entire Run after model repair; and (4) Safe Dossier absence-language normalization did not cover indirect forms such as `the filing notes ... but does not quantify`, and internal-ID stripping could leave punctuation shells. The current combined V2/startup focused gate is **204/204 pytest PASS** plus `compileall` PASS and targeted Ruff/`git diff --check` PASS. Zero-cost replay of the final retired California BanCorp state yields no submission blockers, and reconstruction of its Safe Dossier report passes deterministic validation with two core findings and no cash-flow/OREO/equity/litigation side items promoted into the main-driver answer.
- Runtime consolidation is complete: V2 is the sole live Web/API/CLI/MCP/n8n research path. The V1 Web, `/v1` live API, `ResearchRunService`, autonomous coordinator, V1 workflow/evaluation/evolution/database runtime and PostgreSQL/Alembic product dependency are retired. Useful V1-era primitives remain shared: official filing discovery/security, deterministic extraction/finance semantics, CAS/file locking and durable checkpoints. Persisted V1 Runs, reviewed packages, schemas, benchmarks, evolution evidence and historical n8n JSON remain immutable audit assets only and are never fallback product data.
- Final code/documentation audit tightened three live product edges without changing the research methodology: optional Kimi standby no longer blocks the active DeepSeek+Qwen hybrid route; provider readiness checks the actual non-empty secret value instead of the truthiness of `SecretStr`; and normal Chinese public prose localizes internal state tokens such as `limited` / `evidence_exhausted` while structured audit fields retain their original values. `README.md` is now a GitHub-oriented English entry point and `README.zh-CN.md` is a full Chinese counterpart with the same V2 facts, quick-start, runtime boundary and quality caveats.
- Final packaged Owner-stack verification is PASS on the consolidated runtime: only API, Frontend and optional n8n containers are running; API health reports `2.0.0-alpha.1 / runtime=v2`; the installed Python distribution is `2.0.0a1`; effective provider routing is `hybrid / deepseek-v4-flash` with DeepSeek Reflection/Synthesis, Qwen semantic review and Qwen3-VL vision; `/v1/runtime-capabilities` returns 404 through both API and Web; the API image contains neither `/app/data` nor migrations; and CLI plus MCP both reopened persisted V2 run `run_75724aebf164497394425716b9e7fcf6` with the same 6 facts and 134-event succeeded Trace without model calls.
- Product runtime parity is now enforced at startup. A real V2 Web run (`run_e2686722144246e5ae1d17a272be88f3`) proved that the previous Docker API environment silently dropped the `.env` hybrid settings and fell back to OpenAI-only `gpt-5.6-luna`, then failed before token consumption with `RateLimitError`. `docker-compose.yml` now forwards the behavior-bearing DeepSeek/Qwen settings and optional Kimi standby configuration by environment interpolation, `/v2/capabilities` exposes only non-secret effective role routing, and `start_demo.py` fails early if the running V2 provider/model roles differ from local settings. The current packaged API reports `hybrid / deepseek-v4-flash`, DeepSeek Reflection/Synthesis, Qwen semantic review/fallback and Qwen3-VL vision.
- Cash-flow health now has an explicit filing-only multidimensional method instead of treating `OCF / Net Income > 1` as a sufficient health threshold. The method separately covers operating cash generation/profit conversion, net cash and liquidity, investing/financing flows, and working-capital/one-off effects; material positive and negative evidence requires `mixed`. Real hybrid development runs moved the CATL 2024H1 question to the correct `mixed` state but still exposed unbenchmarked degree words in Safe Dossier prose. Those words are now deterministically neutralized without changing amounts or direction. No additional live model run was spent after that repair: zero-model replay of persisted run `run_a50501c611194c1896577427d831fb92` preserves `direct_answer=mixed`, renders four evidence-linked dimensions, removes the reviewer-flagged `较强/相当部分/较厚/主要来源/可观` language and stale internal-ID punctuation shells, and passes deterministic report validation. A post-fix live semantic-review success is therefore **not yet claimed**.
- Independent multi-issuer **held-out Owner Acceptance remains not established**. There is deliberately **no automatic J suite** after I: the alphabet loop is stopped. Another fresh formal suite requires a new explicit quality decision after reviewing whether the remaining uncertainty justifies additional acceptance spend. Until such a suite completes and the owner accepts its outputs, V2 must not claim held-out quality acceptance or superiority over V1.
- Scope/change note: `docs/product/v2-filing-research-implementation.md`.

<!-- /V2-ACTIVE-STATUS -->


**Updated:** 2026-09-06
**Contract package:** historical product contracts preserved; V1.8 engineering artifacts use schema 1.8.0
**Product package:** 1.8.5
**Research scope:** V1.7 General Company Research

Contract package: 1.5.0
Current gate: RELEASE_FREEZE
Scope: V1.7 general company research

Current gate: **RELEASE_FREEZE**
Gate status: **completed — V1.8.5 engineering, remote CI, Owner re-acceptance and CAS reliability closeout all passed**

## Current milestone

**V1.8.5 Agent Engineering Hardening — ENGINEERING COMPLETE / REMOTE SYNC PASS**

V1.8.5 keeps the V1.7 research truth boundary and V1.7.3 lifecycle semantics while adding a current security/dependency baseline, Product Agent Eval, deterministic Failure Analysis, measured Retrieval Benchmark, MCP interoperability and interview/architecture evidence. It does not rewrite historical Research Results or claim new financial truth.

## V1.8.5 delivered

- LangGraph upgraded to the 1.x line; pypdf/test/security dependencies refreshed without replacing the bounded ten-stage StateGraph architecture.
- `pip-audit` and `npm audit` are explicit CI security gates; current local audits report no known/high vulnerabilities.
- API interactive docs are disabled by default; packaged Web exposes CSP, `nosniff`, frame denial, referrer and permissions policies.
- `researchforge eval` evaluates frozen Router/Retrieval cases and persisted Runs for routing, plan completion, grounding, citation validity, structured-output validity and ten-stage trajectory completion.
- Same-company Thread Eval verifies context identity and grounding but explicitly does not fabricate semantic-contradiction scores.
- Fourteen deterministic failure classes plus `researchforge failure-analyze` convert persisted failures into diagnosable regression candidates.
- The eight-case retrieval benchmark compares production lexical, TF-IDF sparse vector and simple RRF. Current evidence is insufficient to justify pgvector/dense retrieval, so production retrieval remains unchanged.
- MCP uses the official Python SDK and exposes seven bounded same-backend tools; stdio is default and optional Streamable HTTP binds to `127.0.0.1:8001`.
- V1.8 schemas/examples contract Agent Evaluation, Retrieval Benchmark, Failure Analysis and the MCP toolset while preserving V1.7.3/V1.7/V1.5/V1.4 history.
- GitHub CI is split into backend, contracts, eval, security, frontend and containers jobs.

## Fresh local engineering gate — PASS

- `uv lock --check`, Ruff format/check: PASS.
- strict mypy: **120 source files**, PASS.
- pytest: **233 passed**.
- Contract validation: PASS — **625 local schema refs**, four active V1.8 engineering schemas/examples plus preserved history; V1.8 offline/thread Eval, Failure and MCP evidence validate.
- Agent Eval: Router accuracy **1.0**; lexical Recall@10 **0.8125**, TF-IDF **0.8542**, RRF **0.8750**. Precision@5 is lexical **0.4583**, TF-IDF **0.5417**, RRF **0.3750**.
- Persisted three-turn 贵州茅台 Thread: all three model Runs score **1.0** for routing, plan completion, grounding, citations, structured output and trajectory.
- Security: `pip-audit` reports **no known vulnerabilities**; `npm audit --audit-level=high` reports **0 vulnerabilities**.
- Frontend: typecheck/lint/build + **7 unit tests + 3 mocked E2E + 3 live-backend E2E**: PASS.
- Isolated deterministic Docker gate: **3/3 PASS** with separate ports/volumes.
- Owner stack force-recreated as **V1.8.5**, `reasoning_mode=auto`, `research_output_mode=model_synthesis`.
- Owner packaging: API/Web/n8n publish only on localhost; `/docs` and `/openapi.json` return 404 by default; Web security headers verified.
- n8n 2.37.9: **11/11 Node tests**, 3 actual success cases, idempotent/minimum-input/form checks and **5/5 transport-only bounded failures**: PASS.
- MCP: 7-tool contract test + live read-only smoke passed; 贵州茅台 resolves to CNINFO 2025FY, existing Run exposes 6 facts, 5 retrieved evidence items, 6 model Claims and a 10-stage succeeded Trace.
- Post-acceptance CI exposed a same-digest CAS race under concurrent Runs; local atomic-install fix plus deterministic concurrency regression passed **30/30 repeated runs**.

## Research-quality evidence retained

- V1.7 extended Golden Regression: **6 trusted successes + 3 explicit safe abstentions; PASS**.
- V1.7.1 real-model smoke: 贵州茅台 8 Claims / 5 sections; NVIDIA 6 / 5; 腾讯 6 / 5.
- V1.7.3 Owner regression: 贵州茅台 profitability and 大华股份 growth both returned `synthesis_mode=model`, 6 Claims / 5 sections and Supported.
- V1.8.5 does not inflate those research-quality claims; it evaluates and exposes the engineering around them.

## Release boundary

`RELEASE_FREEZE` is complete. Owner re-acceptance is PASS: the owner manually exercised the V1.8.5 model-synthesis path on a representative 贵州茅台 risk-analysis question and reported no release blocker. The later same-digest content-addressed-store concurrency defect was fixed with atomic idempotent installation; local deterministic concurrency regression and public CI run `34012311498` both passed.

No six-person Human Pilot was required. Owner Acceptance was supplied manually by the owner and was not generated by tests.

## Known bounded limitations

- CN/US/HK official-source adapters are supported; universal issuer/layout coverage is not claimed.
- Six deterministic financial facts remain the numerical backbone.
- The initial V1.8 retrieval suite contains eight reviewed cases; it is a decision baseline, not proof that TF-IDF is universally superior.
- Thread Eval does not score prose-level semantic contradiction.
- MCP is local-first and unauthenticated; remote/public deployment is not claimed.
- Real-time news, broker research, price targets, trading, portfolio management, unrestricted multi-agent debate and open-ended self-modification remain out of scope.

## Resume here

Read first: [README.md](README.md), [V1.8.5 engineering note](docs/product/v1.8.5-agent-engineering-hardening.md), [V1.8.5 architecture](docs/architecture/v1.8.5-agent-engineering.md), [V1.8 evidence](docs/evidence/v1.8/README.md), [DECISIONS.md](DECISIONS.md), [final delivery roadmap](docs/product/researchforge-final-delivery-roadmap.md), and [PORTFOLIO.md](PORTFOLIO.md).
