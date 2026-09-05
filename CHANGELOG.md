# Changelog

## [Unreleased] — V1.7.1 Research Synthesis & Report UX

### Synthesis quality

- Corrected comprehensive-question routing so “完整分析” wins over narrower business/growth/risk keywords.
- Added explicit `model` vs `evidence_summary_fallback` synthesis modes; deterministic fallback now states that AI synthesis was not executed instead of promoting filing excerpts into a faux analyst report.
- Upgraded model Structured Output with per-Finding claim type/epistemic status and substantive Overall Judgment rationale, plus one repair retry that receives safe structural feedback.
- Added synthesis quality gates: comprehensive research requires multiple analytical Findings/sections, raw source-section headings and filing boilerplate are rejected, and Claim Fact IDs are filtered by actual metric relevance.

### Product UX and runtime

- Reworked the Web report around analytical headlines and evidence-on-demand, with explicit synthesis badges and a prominent fallback warning.
- Made `start_demo.py` actively default to `auto` so a prior CI deterministic environment cannot silently contaminate Owner Testing.
- Verified real model synthesis on 贵州茅台, NVIDIA and 腾讯 across CN/US/HK official-source packages.

## [Unreleased] — V1.7.1 Research Synthesis Correction

### Owner-feedback correction

- Recorded the first V1.7 Owner Acceptance as failed on synthesis quality rather than incorrectly freezing the release.
- Added explicit `synthesis_mode` so model Research Synthesis and deterministic Evidence Summary fallback cannot be confused.
- Fixed comprehensive-query routing precedence, synthesis-first prompts, analytical Claim semantics, unrelated Fact-chip filtering and evidence-on-demand report UX.
- Replaced blind structure retry with one bounded repair that receives only safe validation feedback.

### Verification

- Real model smoke passed for 贵州茅台 (`company_overview`, 8 Claims / 5 sections), NVIDIA (`growth_analysis`, 6 / 5) and 腾讯 (`business_analysis`, 6 / 5).
- Final V1.7.1 engineering gate passed: 210 pytest tests, strict mypy over 105 source files, 5 frontend unit tests, 3 mocked + 3 live E2E, fresh Docker smoke, 11 n8n Node tests, 3 actual n8n success cases and 5/5 transport-only failures.

## [Unreleased] — V1.7 General Company Research

### Research intelligence

- Added Question Router + six Research Skills, question-specific Research Plans, full-filing Evidence retrieval, counter-evidence and evidence-constrained Deep Analysis.
- Added V1.7 Research Result fields for Intent, Plan, Analysis Sections, Overall Judgment, Suggested Follow-ups and Evidence Coverage while preserving deterministic financial truth.
- Hardened SEC HTML retrieval so all chunks are not treated as one PDF page; real NVIDIA growth research now produces 6 Findings and 4 Deep Analysis sections instead of a two-item short answer.

### Surfaces and verification

- Added a separate V1.7 n8n workflow/schema and migrated the active launcher, form and Web entry without overwriting historical workflow artifacts.
- Verified quick and extended live regression: three-market quick success and 6 trusted successes + 3 safe abstentions across the nine-company suite.
- Completed the V1.7 engineering gate: 208 pytest tests, strict mypy over 105 source files, frontend unit/build plus 3 mocked and 3 live E2E, fresh Docker build, actual n8n 2.37.9 success runtime and 5/5 failure-fixture routes.

## [Unreleased] — V1.6 Autonomous Research

### Autonomous company research

- Replaced the fixed catalog-first entry with company name/ticker input plus optional CN/US/HK
  market and reporting-period hints.
- Added official company and filing discovery for CNINFO, SEC EDGAR and HKEXnews, with ambiguous
  entity resolution and provider/network failures converted into explicit abstentions.
- Added deterministic SEC XBRL and HK IFRS ingestion paths while preserving the existing verified
  Chinese native-PDF extractor; all successful runs still require the same six financial facts.
- Added run-scoped Fact/Evidence snapshots and reviewed-package cache reuse so historical research
  does not drift after a later acquisition.
- Added simplified/traditional Chinese HK issuer normalization with OpenCC without company-specific
  aliases.

### Product and release

- Rebuilt the Web Research entry around autonomous company discovery and added a separate V1.6 n8n
  form/webhook over the same autonomous backend. The immutable V1.5 n8n artifact remains preserved.
- Added quick and extended Golden Company Regression. Live CN/US/HK successes must contain six
  Facts, resolvable Claim/Evidence links and a completed Trace; unsupported layouts may only pass
  as explicit safe abstentions.
- Removed the six-person Human Pilot from the active release gate under RF-032. Historical Pilot
  contracts/templates remain audit history and do not become V1.6 validation evidence.
- Moved active release validation to Golden Regression, full engineering gates and owner acceptance.

## [Unreleased] — Final Delivery Phases (V1.5 history)

### Phase 5: final product and demo hardening

- Added an ordinary-user n8n form and readable success/failure pages over the unchanged same-backend
  workflow; webhook JSON and HTTP behavior remain stable for automation.
- Added explicit Web no-result guidance, direct Result/Trace audit links and a visible handoff to
  the optional n8n entry.
- Added one reproducible deterministic launcher for Web, API, PostgreSQL and imported/published
  n8n, plus an automated native-form smoke and screenshot capture.
- Frozen the final six-plus-person Web+n8n evaluation tasks, A/B order, record schema, thresholds
  and denominator before recruitment; added a deterministic summary tool and tests.
- Captured actual Web and n8n form/result/abstention screenshots. These are engineering/demo
  evidence only; completed human sessions remain zero.

### Phase 4: n8n integration

- Added a portable, inactive-by-default n8n 2.37.9 workflow and optional local Compose service.
- The webhook reads backend capabilities, submits the existing research API, waits/polls with
  fixed bounds and maps original result, facts, calculations, evidence, limitations and monitoring.
- Added explicit input, namespace, idempotency, terminal-state, timeout and missing-artifact exits;
  trusted URLs cannot be overridden by user input. No ResearchForge core changes are needed.
- Added a V1.5 output envelope schema, real three-filing webhook comparison, separate transport-only
  failure fixture, Node routing tests, CI, setup/demo instructions and failure documentation.
- Human usefulness remains unvalidated and intermediate independent acceptance is not run.

### Phase 3: generalization evidence

- Added exactly CATL 2024FY and BYD 2024H1 as official identity-only records, preserving the
  original CATL H1 package hash and all frozen Quality Lab evidence.
- The same six-metric extractor handles report-wide units, wrapped period headers, note columns,
  reversed column order and parent-company/equity-table boundaries; ambiguity abstains.
- Added a bounded hash-checked three-package catalog, three real Research Result evidence bundles,
  live-backend Web E2E, and three-case Docker/migration smoke.
- Removed unsupported interim/audit assumptions from generic result and monitoring text.
- Phases 2–6 are engineering checkpoints only. Independent read-only acceptance occurs once at
  final Phase 7 after implementation, n8n, UX, real-human evaluation and release evidence.

### Phase 2: reusable Financial Fact extraction

- Replaced registry-provided fact values, pages and evidence text with deterministic native-PDF
  recovery for exactly six financial metrics.
- Added consolidated statement detection, wrapped-row handling, current-period column and unit
  resolution, `Decimal` normalization, page-level provenance verification and an all-or-nothing
  ambiguity policy.
- Added a V1.5 extraction-recovery schema and embedded six source-cell proofs in every ready
  ingestion manifest with `llm_used: false` and `numerical_truth_source: verified_pdf`.
- Rebuilt the CATL 2024H1 public-safe package from the unchanged official PDF identity while
  preserving all frozen V1.2–V1.4 artifacts.
- Added tests for exact row selection, parent/consolidated isolation, wrapped rows, missing rows,
  duplicate rows, wrong-period headers, conflicting units, missing native text and hash mismatch.

## [1.5.0] — Productization Accepted

### Direction

- Repositioned ResearchForge as an evidence-grounded AI fundamental-research workspace for
  A-share company research.
- Made real-public-disclosure research, auditability and human usability the product success
  criteria; Evolution hypothesis support is no longer a product completion condition.
- Added the V1.5 Product Thesis and V1.4→V1.5 productization change note.

### Product surface

- Reframed README, project status, portfolio and demo around Company + Period + Research
  Question and the seven auditable user answers.
- Rebuilt the primary Research surface around Company, Period, Question and Start Research, with
  conclusion-first output and progressive disclosure for facts, calculations, evidence and trace.
- Renamed Skill Lab to a secondary, experimental, read-only Quality Lab.

### Real-data product slice

- Added an allowlisted SZSE filing registry and an abstention-first acquisition/parser pipeline
  with HTTPS-host, redirect, byte-count, PDF-magic and SHA-256 checks.
- Added a real CATL 2024H1 product package containing one source identity, six reviewed facts and
  eight page-located evidence chunks, separate from fixture and Benchmark namespaces.
- Made the default API/CLI product runtime reject fixture or Benchmark fallback and expose only
  the currently verified `filing_analysis` capability.
- Added bounded OpenAI Responses Structured Outputs with `store: false`, no built-in web search,
  fixed reasoning settings and a pre-dispatch USD 20 aggregate budget guard; deterministic mode
  remains available for zero-cost reproduction.
- Materialized claim-specific support citations and filing-based counter evidence for
  non-recurring-profit context and the unaudited interim-report boundary.

### Pilot and demo

- Added a privacy-minimized real-human pilot kit with consent notice, participant task sheet,
  neutral facilitator guide, observation rubric, stable threshold and schema-valid template.
- Added a real-data demo evidence record and a three-to-five-minute product-first walkthrough.

### Preserved

- V1.2/V1.3/V1.4 historical contracts, schemas and evidence.
- Both formal experiment results, thresholds, hashes, negative terminal outcome and stopping rule.
- The single-agent LangGraph, deterministic-finance, evidence, Verifier and non-goal boundaries.

### Still honest

- The real-data coverage is one company/period, not broad A-share support.
- The legacy Web-only Pilot kit was not executed. Formal Web+n8n human evaluation is deferred
  until extraction, generalization, integration and UX hardening are frozen; usefulness remains
  unvalidated.
- Local verification and published GitHub CI pass; the final independent reviewer returned
  `VERDICT: PASS` with no required findings.

## [1.4.0] — Release Candidate

### Added

- Active V1.4 scope and V1.3→V1.4 change note.
- Eight schemas/examples for Source Document, Calculation Record, Tool Record, Skill Version, Experience, Evolution Experiment, Retrieval Evaluation, and Simulated Usability Evaluation.
- Exact primary and contingency A-share experiment suites.
- Explicit OpenAI Responses API and aggregate budget contract.
- Immutable Seed Skill `1.0.0`, deterministic Decimal finance domain, and versioned source-line mapping.
- Public-safe G0 package with 8 Source Documents, 48 reconciled Financial Facts, artifact/package hashes, a representative 20-fact signoff sample, and 3 deterministic golden cases.
- Contract validation and regression tests for source lineage, unit normalization, point-in-time cutoffs, golden calculations and corrected-filing behavior.
- Zero-cost G1 filing-analysis thin slice with content-addressed JSON storage, a ten-stage LangGraph, deterministic earnings-quality analysis, CLI and asynchronous FastAPI resources.
- OpenAI Responses adapter boundary with strict Structured Outputs, `store: false`, no built-in tools, medium reasoning and a pre-dispatch aggregate budget guard.
- Lifecycle coverage for point-in-time insufficient data, honest counter-evidence `not_found`, one structure-only repair, second repair failure, queued cancellation and request idempotency.
- Durable JSON LangGraph checkpoints, restart recovery, active cancellation, timeouts, and sanitized unexpected-failure traces.
- Independent deterministic/coverage Verifier with stable failure signatures and persisted Evaluation Results.
- Five-mode runtime breadth plus a fixed 20-run reliability batch and per-mode safe missing-data cases.
- Hybrid SQLAlchemy/Alembic persistence for eight logical records while retaining immutable hash-addressed JSON artifacts.
- React/TypeScript Research and Skill Lab pages with API-only financial values, read-only experiment state, cancellation, unit/E2E/accessibility checks, and responsive styling.
- Docker Compose, backend/frontend images, and GitHub Actions CI definitions.
- Controlled Evolution policy engine and content-addressed experiment repository, plus a grouping-only 24-case preregistration that keeps Final Test sealed.
- Prepared and sealed the disjoint V1.5 contingency package: 24 official sources, 144 page-checked facts, 24 synthetic public evidence chunks, 24 cases, private truth hashes, and a frozen activation boundary.
- Controlled formal executor for 144 repeated Base/Seed/Candidate paths, durable progress, budget reservations, paired Validation adoption, and one-time Final Test consumption.
- One-request synthetic provider-calibration gate that freezes model/configuration, prompt hashes, Structured Output coverage, usage and cost evidence before formal Benchmark access.
- Owner-signed primary package authorization while preserving the preregistered one-time Final Test seal.
- Public GitHub package at `pocketvin/researchforge` after tracked-secret, PDF, remote-hash, and temporary-credential cleanup checks.
- GitHub Actions checkout/setup-node runtimes upgraded from Node 20-based v4 actions to Node 24-based v5 actions.
- `setup-uv` upgraded to the official immutable v9.0.0 commit, removing the remaining Node 20 action runtime.
- Three-session simulated-usability executor with fresh contexts, screenshot evidence, Structured Outputs, explicit `SIMULATED` labels, idempotent recovery, and aggregate/sub-budget guards.
- Full Docker runtime smoke, configurable compatible image sources, richer persisted Skill Lab artifacts, bilingual demo instructions, verified screenshots, and an H.264 preview video.
- Live synthetic calibration using the pinned Responses API configuration and budget ledger.
- Completed primary V1.4 and once-only company-disjoint V1.5 contingency experiments, both ending at `NO_ELIGIBLE_CLUSTER`; immutable negative results and the two-experiment stopping rule are preserved.
- Zero-provider-token technical retry audit with failed attempts excluded from the formal denominator under the frozen one-retry policy.
- Materialized Claim-to-Evidence Chunk citations, evidence excerpts/hashes, deterministic Calculation Record endpoints, and actionable monitoring items with explicit triggers and review timing.
- Two model-backed three-session usability batches: the initial `SIMULATED` failure drove the evidence/monitoring correction and the isolated repeat passed.
- Final public-safe evidence summaries for the two formal experiments, simulated usability, engineering runtime, and job-interview positioning.

### Changed

- Added `operating_cost` as the traceable source input and `gross_profit` as a deterministic formula, closing the initial gross-margin provenance gap without invalidating existing V1.4 artifacts.
- New artifacts use `schema_version: 1.4.0`; V1.2/V1.3 remain immutable history.
- G4 uses three explicitly labeled simulations instead of a human pilot.
- Overall completion requires Full Engineering Product Ready plus a `SUPPORTED` sealed result.
- pgvector adoption now has explicit Recall@5, citation, and latency thresholds.
- Intermediate independent acceptance is deferred to one final project review; local gate evidence remains provisional and is not recorded as independently passed.
- The terminal research label is `RESEARCH_HYPOTHESIS_UNSUPPORTED_AFTER_TWO_EXPERIMENTS`; engineering completion is separated from research support and no further formal experiment is authorized.

### Preserved

- Five bounded research modes and one LangGraph single-agent Research workflow.
- Plain-Python finance, retrieval, verifier, persistence semantics, and Evolution.
- No trading, real-time market data, multi-agent debate, or open-ended self-modification.

All notable contract and planning changes are recorded here. Product-scope changes require a separate decision and change note.

## [Contract Package 1.3.0] — 2026-08-30

### Added

- Active V1.3 product/research scope and explicit V1.2→V1.3 change note.
- Eleven current V1.3 schemas while preserving V1.2 schemas as history.
- Dedicated `workflow-trace` contract/example for sanitized LangGraph execution evidence.
- Explicit Run Manifest workflow configuration: engine, graph version, and checkpoint schema version.
- Honest `insufficient_data` terminal lifecycle state.
- Three supporting persistence records: source documents, evidence chunks, and run artifacts.

### Changed

- V1.2 is no longer the active frozen scope; V1.3 is a versioned baseline changed through explicit decisions and change notes.
- Product/portfolio completion is separated from the result of the Evolution research hypothesis.
- LangGraph remains required for the single Research Agent workflow but is prohibited from owning finance, retrieval, verifier, persistence, or Evolution semantics.
- pgvector is conditional on retrieval evidence instead of being an unconditional implementation blocker.
- Active contracts, status, guidance, examples, and validator target V1.3.
- `insufficient_data` persists a structured failure and Workflow Trace but never a Research Result artifact.

### Preserved

- Five product task modes, one Agent, one skill, and the earnings-quality Evolution target.
- Benchmark leakage protections and Base/Seed/Candidate comparability.
- V1.2 scope document, schemas, and example as immutable historical evidence.

## [Contract Package 1.2.1] — 2026-08-30

### Added

- Solo-success plan with Portfolio MVP and honest stopping levels.
- Portfolio/interview evidence guide.
- Data-source acceptance contract and spike protocol.
- Product-success metrics distinct from Evolution metrics.
- Implementation blueprint and complexity budget.
- Feasibility/career/usefulness/completeness/resumability scorecard.
- Risk register with triggers and fallbacks.
- Project status, decision log, and resume playbook.
- Machine-readable project-checkpoint schema and live `project-status.json`.
- Bounded LangGraph workflow contract and explicit framework/domain boundary.

### Changed

- README now exposes current gate, next action, success ladder, and strategy documents.
- AGENTS.md now requires one active milestone, status handoff, evidence-backed career claims, and complexity justification.
- Contract catalog and validator include the new contracts and project checkpoint.

### Scope

No V1.2 product capability was added or removed. These changes improve execution probability, proof quality, and project recoverability.

## [Contract Package 1.2.0] — 2026-08-29

### Added

- Initial V1.2 scope-preserving project scaffold.
- Nine core JSON Schemas.
- Financial methodology, task, Benchmark, Evolution, lifecycle, and development-gate contracts.
- Dependency-free contract validator and Benchmark Case example.
