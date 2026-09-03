# ResearchForge Decision Log

This file records decisions that materially affect scope, architecture, data, evaluation, cost, or delivery. Chat history is not a durable decision record.

## Status Legend

- **ACCEPTED**: binding until replaced by a later decision.
- **ACCEPTED WITH RECORDED PROTOCOL DEVIATION**: binding, with the deviation and unchanged experiment controls preserved as evidence.
- **PROPOSED**: preferred option, awaiting implementation evidence or owner confirmation.
- **REJECTED**: considered and intentionally not used.
- **SUPERSEDED**: replaced by another decision.

## Decision Index

| ID | Decision | Status | Date | Blocks |
|---|---|---|---|---|
| RF-001 | Contract-first implementation | ACCEPTED | 2026-08-29 | — |
| RF-002 | Staged personal-success ladder | ACCEPTED | 2026-08-29 | — |
| RF-003 | Portfolio MVP before full V1.3 breadth | ACCEPTED | 2026-08-29 | — |
| RF-004 | Structured and filing data sources | ACCEPTED | 2026-08-31 | — |
| RF-005 | Evidence persistence and pgvector timing | ACCEPTED | 2026-08-30 | — |
| RF-006 | Initial company universe | SUPERSEDED | 2026-08-29 | — |
| RF-007 | Bounded LangGraph orchestration | ACCEPTED | 2026-08-30 | — |
| RF-008 | Upgrade the active scope to V1.3 | ACCEPTED | 2026-08-30 | — |
| RF-009 | Upgrade the active scope to V1.4 | ACCEPTED | 2026-08-30 | — |
| RF-010 | Replace the human pilot with labeled simulations | ACCEPTED | 2026-08-30 | — |
| RF-011 | OpenAI model and USD 20 budget boundary | ACCEPTED | 2026-08-30 | — |
| RF-012 | Primary and contingency experiment suites | ACCEPTED | 2026-08-30 | G0 evidence |
| RF-013 | One final independent acceptance | ACCEPTED | 2026-09-01 | Final release |
| RF-014 | One target report per formal Benchmark case | ACCEPTED | 2026-09-01 | — |
| RF-015 | Skill-conditioned coverage, deterministic verification | ACCEPTED | 2026-09-01 | G3 |
| RF-016 | Seal the V1.5 contingency before the primary experiment | ACCEPTED | 2026-09-01 | — |
| RF-017 | Portable container image sources | ACCEPTED | 2026-09-01 | — |
| RF-018 | One synthetic provider calibration before formal runs | ACCEPTED | 2026-09-01 | G3 |
| RF-019 | Activate contingency after any unsupported primary outcome | ACCEPTED WITH DEVIATION | 2026-09-02 | — |
| RF-020 | One zero-token technical retry with denominator audit | ACCEPTED | 2026-09-02 | — |
| RF-021 | Freeze unsupported terminal research outcome | ACCEPTED | 2026-09-02 | Final release |
| RF-022 | Make evidence, calculations, and monitoring directly auditable | ACCEPTED | 2026-09-02 | Final release |
| RF-023 | Make real, auditable company research the V1.5 product thesis | ACCEPTED | 2026-09-02 | — |
| RF-024 | Isolate a reviewed real-disclosure product namespace | ACCEPTED | 2026-09-02 | — |
| RF-025 | Use the model only for bounded research language | ACCEPTED | 2026-09-02 | — |
| RF-026 | Freeze final delivery order and defer human evaluation | ACCEPTED | 2026-09-03 | Final release |
| RF-027 | Make verified PDF recovery the only numerical truth source | ACCEPTED | 2026-09-03 | Phase 3 |

## RF-001 — Contract-First Implementation

Status: **ACCEPTED**

Decision:

Persisted artifacts and APIs must conform to the versioned schemas and semantic contracts before feature breadth is added.

Why:

Financial-period mistakes, benchmark leakage, unverifiable claims, and silent scope expansion are more expensive to repair after the UI and orchestration are built.

Consequence:

The first runtime work is deterministic data/financial tooling and a vertical slice, not the final interface.

## RF-002 — Staged Personal-Success Ladder

Status: **ACCEPTED**

Decision:

Treat L1 Resume Ready, L2 Demo Ready, L3 Differentiated, and L4 Full V1.3 as independently valuable delivery levels.

Why:

A solo project can fail because all value is deferred until the hardest research claim. Earlier honest milestones preserve motivation and produce usable interview evidence.

Consequence:

Each level must be demonstrable and truthfully describable without claiming later capabilities.

## RF-003 — Portfolio MVP Before Full Product Breadth

Status: **ACCEPTED**

Decision:

Build one earnings-quality company-research thin slice first. It may use frozen local evidence packages and a CLI or single API endpoint. The five task modes and two-page UI remain required for full V1.3, not for L1.

Why:

This sequence validates data normalization, deterministic tools, citations, and the Research Procedure before investing in broad UI and infrastructure.

Consequence:

No task mode is deleted from V1.3; it is only sequenced later.

## RF-004 — Data Sources

Status: **ACCEPTED**

Preferred direction:

- authoritative facts from official SZSE/CNInfo filings;
- frozen local packages for Benchmark and repeatable public demos;
- no live structured provider dependency unless a later, separately versioned source passes the contract.

Evidence resolved in the preliminary G0 spike:

- full official PDFs are excluded from Git/public packages; only normalized facts, permitted short evidence, hashes, locators and links may be included;
- Tushare statement fields and publication/report metadata are technically suitable for comparison, but its personal/non-commercial/personal-viewing license fails the runtime, committed-demo and redistribution boundary;
- source-line mapping `1.0.0` freezes official labels, optional reconciliation fields, period bases and formula inputs.

Acceptance evidence:

- the owner signed the representative 20-fact sample on 2026-08-31;
- the implemented package has 8/8 hash-verified sources, 48/48 complete facts, 48/48 numeric and visual matches, stable page locators, point-in-time publication semantics, and 0 unresolved mismatches;
- the signed package hash is `56fd99ae6be655dc878d93a8c99f4bd3d6ba60feffaf2f21ffc81da2d180d58d`.

Final outcome:

Official SZSE/CNInfo-derived data is `FIXTURE-ONLY` for the stated CATL/EVE, four-period, six-metric package. It makes no live-ingestion, full-market, or full-PDF redistribution claim. Tushare is `REJECT` for runtime, committed-demo, redistribution and public-package use. See `docs/evidence/g0-source-spike.md`.

## RF-005 — Evidence Persistence and pgvector Timing

Status: **ACCEPTED**

Preferred direction:

1. L1/L2 use immutable file-backed source documents, evidence chunks, and run artifacts with deterministic retrieval.
2. Full V1.3 may map five core records plus `source_documents`, `evidence_chunks`, and `run_artifacts` to PostgreSQL/object storage.
3. pgvector is an optional index on `evidence_chunks` only after a frozen retrieval evaluation demonstrates value.

Reason:

This prevents database work from blocking the first useful report while making evidence persistence explicit. It resolves the V1.2 five-object ambiguity without turning retrieval infrastructure into a product goal.

Escalation:

Any further logical record requires an explicit decision and migration evidence. Do not hide a scope change behind an ORM migration.

## RF-006 — Initial Company Universe

Status: **SUPERSEDED** by RF-012

Preferred direction:

- Thin slice: two same-market, same-currency companies with comparable reporting periods and text-readable official filings.
- Formal Benchmark: expand to 4–6 companies only after G0 data and formula tests pass.

Candidate pair:

CATL and EVE Energy are suitable narrative candidates from the frozen demo, but they are not approved until source availability and metric reconciliation pass.

RF-012 replaces this open-ended proposal with fixed primary and contingency suites. G0 still decides whether each fixed company has sufficient source/provenance evidence; it does not choose a different universe silently.

## RF-007 — Bounded LangGraph Orchestration

Status: **ACCEPTED**

Decision:

Keep LangGraph in L1 and the full product as the one Research Agent's workflow engine. Use it for typed state, stable stages, conditional degradation, checkpoint/resume, one bounded structure-repair route, and audit events.

Do not use it for financial formulas, period semantics, retrieval algorithms, verifier policy, storage meaning, multiple agents, or the Evolution pipeline.

Why:

This preserves a relevant agent-engineering technology and makes a genuinely conditional workflow inspectable, while keeping domain logic portable and easy to test.

Consequence:

The graph is versioned and pinned. Graph nodes remain thin adapters around plain application/domain services. Base, Seed, and Candidate comparisons use the same graph version so orchestration cannot confound the experiment.

## RF-008 — Upgrade the Active Scope to V1.3

Status: **ACCEPTED**

Decision:

Supersede the V1.2 frozen scope with `docs/product/researchforge-v1.3-scope.md` and contract package 1.3.0. Preserve V1.2 scope and schemas as immutable historical evidence.

V1.3 formalizes staged product success, the G0 data-source decision, bounded LangGraph orchestration, a Workflow Trace artifact, explicit supporting evidence storage, conditional pgvector adoption, product-usefulness evidence, and schema-valid project resumption.

Why:

These changes directly improve feasibility, portfolio value, usefulness, completeness, and solo recoverability without adding a new research task or widening the Evolution target.

Consequence:

New artifacts use `schema_version: 1.3.0` and `schemas/v1.3/`. V1.2 artifacts are never silently interpreted as V1.3; any later migration creates a new artifact and preserves original provenance.

## RF-009 — Upgrade the Active Scope to V1.4

Status: **ACCEPTED**

Decision:

Supersede V1.3 with the active V1.4 scope and contract package `1.4.0`. Preserve the V1.3 scope, schemas, examples, and Git baseline as immutable history.

Reason:

The owner changed both the success-evidence meaning and the project completion rule. This is a minor contract change, not a clarification.

Consequence:

New artifacts use `schema_version: 1.4.0`. Any migration creates a new artifact and retains the V1.3 source hash.

## RF-010 — Labeled Simulations Instead of a Human Pilot

Status: **ACCEPTED**

Decision:

G4 requires exactly three isolated simulated-usability sessions. Every record uses `evidence_label: SIMULATED` and `human_user_value_validated: false`.

Reason:

The owner explicitly removed real-user recruitment from the project.

Consequence:

The final engineering label is `V1.4 Full Engineering Product Ready`. Documentation MUST state that human usefulness and market demand were not validated.

## RF-011 — OpenAI Model and Budget Boundary

Status: **ACCEPTED**

Decision:

Use the OpenAI Responses API with `store: false`, Structured Outputs, no built-in tools, `gpt-5.6-luna`, medium reasoning, and a USD 20 aggregate cap. `gpt-5.4-mini` is allowed only as a pre-formal-run fallback.

Budget:

- USD 1 calibration;
- USD 9 primary experiment;
- USD 6 contingency reserve;
- USD 2 simulations;
- USD 2 safety reserve.

Consequence:

A real request is rejected before dispatch if its worst-case estimate would breach the aggregate cap. Model/configuration changes after formal runs begin invalidate the experiment.

## RF-012 — Primary and Contingency Experiment Suites

Status: **ACCEPTED**

Decision:

- Primary V1.4: CATL and EVE Energy for Evolution, Gotion High-Tech for Validation, and Sunwoda for Final Test.
- Contingency V1.5: Great Power, Farasis Energy, BYD, and Zhuhai CosMX in a wholly disjoint pre-frozen suite.
- Six target reports per company: 2023Q3, 2023FY, 2024Q1, 2024H1, 2024Q3, and 2024FY.

Consequence:

Company inclusion still must pass G0 source/provenance evidence. Replacing a company or report period requires a new decision before any formal run. At most one contingency experiment may run after an unsupported primary result.

## RF-013 — One Final Independent Acceptance

Status: **ACCEPTED**

Decision:

Continue implementation in larger batches and defer new independent acceptance reviews until the full project is ready for final release. Existing C0 and G0 PASS verdicts remain historical evidence. G1/G2/G3/G4 local evidence must remain explicitly provisional until the final reviewer returns `VERDICT: PASS`.

Reason:

The owner prioritized development throughput and explicitly requested removal of repeated interim reviews.

Consequence:

Local test and evidence gates still run continuously, failures remain visible, and no interim milestone is described as independently accepted. The final release still requires the global completion workflow and independent read-only review.

## RF-014 — One Target Report per Formal Benchmark Case

Status: **ACCEPTED**

Decision:

Each of the 24 pre-registered primary cases binds exactly one target report and its six
same-period earnings-quality facts. The schema lower bound for `target_periods` is one;
product-mode trend analysis remains a separate acceptance concern.

Reason:

The frozen protocol defines six cases per company, one for each target report. Requiring
two target periods inside every case contradicted that case count and would either leak
another report into a case or silently redefine the experiment. Same-period revenue,
cost, net income, operating cash flow, receivables, and inventory are sufficient for the
omission experiment's deterministic checks.

Consequence:

The primary package contains 24 cases, not 12 multi-report cases. Every case is checked
for one source, one synthetic public evidence chunk, six facts, publication cutoff, and a
verifier-only ground-truth hash. Cross-period behavior continues to be tested by the
normal product workflow and is not inferred from this experiment.

## RF-015 — Skill-Conditioned Coverage, Deterministic Verification

Status: **ACCEPTED**

Decision:

Formal model output includes `reported_check_codes`, a bounded structured list of the
earnings-quality checks the answer explicitly records. The ten-stage LangGraph continues
to call deterministic finance services; the independent Verifier treats any required but
unreported code as a coverage omission. Base, Seed, and Candidate use the same wrapper,
model, graph, data, tools, schema, and verifier; only trusted skill content/hash differs.

Candidate rules are distilled by a deterministic, allowlisted mapping from one eligible
coverage signature. The artifact records `researchforge/deterministic-rule-distiller-v1`
as its generator rather than falsely claiming an extra model call.

Reason:

The hypothesis concerns whether a versioned procedure improves what the agent records,
not whether a model can replace formulas. Automatically inserting every check status
after generation would make Seed/Candidate omissions unobservable; allowing the model to
calculate values would violate the financial-correctness boundary.

Consequence:

A provider conclusion must attest only checks it explicitly covers; a null attestation is
a structure failure and receives the one allowed repair. Deterministic product output
retains native full coverage. Prompt-wrapper, resolved-instruction, skill, dataset, graph,
formula, and verifier hashes are persisted. Synthetic 144-run tests prove this control
path only and can never be cited as formal `SUPPORTED` evidence.

## RF-016 — Seal the V1.5 Contingency Before the Primary Experiment

Status: **ACCEPTED**

Decision:

Freeze package `package_v1_5_contingency_battery_earnings_quality` with package hash
`ba95986b94d416e7c5d3960749d253463d61161ca081b3454c4428b6344c93f4` before any
primary provider request. Keep both formal-run and activation authorization false.
Activation is allowed only after primary Validation rejects the Candidate and after the
complete primary negative result is frozen.

Reason:

Pre-freezing prevents company selection, labels, or deterministic truth from being
adapted after seeing the primary result. The four contingency companies have zero group
overlap with the primary package.

Consequence:

The primary preflight fails if the package, suite, public artifact catalog, hashes,
company isolation, sealed condition, or activation flags change. A passing primary
experiment leaves the contingency permanently unused.

## RF-017 — Portable Container Image Sources Without Changing Runtime Semantics

Status: **ACCEPTED**

Decision:

Keep standard Docker Hub official-library names as Compose defaults and expose four
optional build/image variables: `PYTHON_IMAGE`, `NODE_IMAGE`, `NGINX_IMAGE`, and
`POSTGRES_IMAGE`. A mirror may be used only for byte-compatible official-library images;
application dependencies remain pinned by `uv.lock` and `package-lock.json`.

Reason:

Docker Hub authentication timed out in the local network while Amazon Public ECR was
reachable. Making the image source configurable preserves reproducible packaging without
hard-coding one environment-specific registry.

Consequence:

The full three-service runtime smoke passed using Public ECR overrides. CI and normal
users retain the standard image defaults, and no registry credential enters the project.

## RF-018 — One Synthetic Provider Calibration Before Formal Runs

Status: **ACCEPTED**

Decision:

Send exactly one bounded synthetic request after rotated-key confirmation and before the
first formal Benchmark request. Freeze the pinned model/configuration, prompt hashes,
Structured Output coverage, context/output hashes, usage and aggregate spend in an
idempotent calibration artifact. Formal preflight requires that artifact to pass.

Reason:

An interface, model-availability, schema, or instruction failure should be detected before
it can contaminate a preregistered sample. One request is sufficient to exercise the live
boundary while staying far below the USD 1 calibration allocation.

Consequence:

Calibration uses only a declared synthetic payload, must explicitly report all seven
earnings-quality check codes, and is labeled
`SYNTHETIC_CALIBRATION_ONLY_NOT_RESEARCH_EVIDENCE`. It never counts toward Base, Seed,
Candidate, Validation, Final Test, usability, or a `SUPPORTED` conclusion. Failure blocks
formal execution until corrected without consuming a Benchmark case.

## RF-019 — Activate the Frozen Contingency After Any Unsupported Primary Outcome

Status: **ACCEPTED WITH RECORDED PROTOCOL DEVIATION**

Decision:

Activate the once-only V1.5 contingency after the primary experiment completed with
`NO_ELIGIBLE_CLUSTER`. Record `FROZEN_ACTIVATION_PREDICATE_TOO_NARROW` because the earlier
machine predicate named only a Validation rejection even though the owner-approved scope
authorized contingency after any unsupported primary result.

Reason:

The primary could not reach Validation because no cluster was eligible to create a Candidate.
Treating this as neither supported nor eligible for contingency would contradict the stated
two-experiment stop plan. The deviation changes no company, fact, truth value, model, threshold,
graph, verifier, or result.

Consequence:

The deviation, activation count, unchanged-data assertion, and primary result hash are immutable
audit fields. Contingency activation cannot occur a second time.

## RF-020 — One Retry for a Zero-Provider-Token Technical Failure

Status: **ACCEPTED**

Decision:

Allow exactly one retry when a formal attempt fails before consuming any provider tokens. Retain
the failed run and reason as a technical-retry artifact, bind it to the successful replacement,
and exclude the zero-token failed attempt from the preregistered scored denominator.

Reason:

A local deterministic bug or transport failure before provider consumption is not a model
observation. Counting both it and the replacement would change the planned number of scored
repeats; discarding it would erase useful operational evidence.

Consequence:

The contingency experiment records two such attempts. A second failure for the same retry key, or
any failure after provider tokens are consumed, is not silently retried. Indeterminate transport
outcomes are conservatively charged at the full reserved cost.

## RF-021 — Freeze the Unsupported Terminal Outcome and Separate Engineering Completion

Status: **ACCEPTED**

Decision:

After both formal experiments ended at `NO_ELIGIBLE_CLUSTER`, apply the two-experiment stopping
rule and freeze `RESEARCH_HYPOTHESIS_UNSUPPORTED_AFTER_TWO_EXPERIMENTS`. Continue only the bounded
engineering release work and simulated-usability correction.

Reason:

Changing cluster thresholds, companies, data, or the experiment count after observing two
negative results would invalidate the research design. The product can still demonstrate useful
engineering without claiming that the skill-evolution hypothesis succeeded.

Consequence:

No further formal experiment, Candidate, Validation, or Final Test is authorized. Public material
may claim full engineering readiness only after final acceptance; it must state that the research
hypothesis is unsupported and that real-user value remains unvalidated.

## RF-022 — Make Evidence, Calculations, and Monitoring Directly Auditable

Status: **ACCEPTED**

Decision:

Before the V1.4 public release, require completed Research Results to contain explicit monitoring
items and require every material claim to resolve its supporting evidence IDs. Expose immutable
run-scoped facts, evidence chunks, and deterministic calculation records through read-only API
resources and render those persisted artifacts directly in the Research page.

Reason:

The first isolated simulated-usability batch found the key result, support, and limitation, but
all three sessions missed a monitoring action and could not directly inspect the cited excerpt or
formula record. These were presentation and auditability defects, not grounds to alter the frozen
research experiment.

Consequence:

The additive API resources are `/facts`, `/evidence`, and `/calculations`; the V1.4 Research Result
contract requires `monitoring_items`. The correction changes no Benchmark package, model setting,
skill, threshold, evaluation denominator, or frozen experimental outcome. A second fresh three-
persona simulation passed with the original negative research result intact.

## RF-023 — Make Real, Auditable Company Research the V1.5 Product Thesis

Status: **ACCEPTED**

Decision:

ResearchForge V1.5 is an evidence-grounded AI fundamental-research workspace for A-share
companies. The normal product journey is Company + Period + Research Question → official
disclosure → evidence → facts → deterministic calculations → reasoning → counter evidence →
verification → result → monitoring. Controlled Evolution is frozen as a secondary, read-only
Quality / Research Lab.

Reason:

The V1.4 engineering assets are useful independently of whether a bounded Skill patch emerged.
Two formal experiments produced no eligible cluster, and changing thresholds or adding
experiments would weaken research integrity. The larger user and portfolio value is an auditable
real-disclosure research result, while the current default runtime still depends on fixtures and
synthetic public evidence.

Consequence:

`docs/product/researchforge-v1.5-product-thesis.md` becomes the highest product-direction
authority. V1.4 schemas and frozen research evidence remain unchanged. New ingestion/data-
namespace semantics require V1.5 contracts and strict `product` / `fixture` / `benchmark`
isolation. Research UX, real-data ingestion, pilot readiness and the real-data demo take priority;
no new formal Evolution experiment is authorized.

## RF-024 — Isolate a Reviewed Real-Disclosure Product Namespace

Status: **ACCEPTED**

Decision:

Make `data/product/packages/catl-2024h1` the first and default product data root. Acquire only the
allowlisted official SZSE PDF, verify document magic, byte count and SHA-256 before parsing, retain
page boundaries and provenance, and materialize only reviewed row/column mappings. Keep fixture
and Benchmark roots explicit and reject namespace mismatch.

Reason:

Fixture reliability cannot establish a real user workflow, but broad-market discovery would add
large operational and data-quality risk before one vertical slice is useful. One reviewed filing
is enough to demonstrate the product contract and abstention behavior.

Consequence:

The initial product catalog exposes only CATL `2024H1` and `filing_analysis`. The raw PDF remains
ignored. Hash, mapping or source mismatch produces an abstained ingestion manifest instead of a
fact. V1.4 packages and hashes remain untouched.

## RF-025 — Use the Model Only for Bounded Research Language

Status: **ACCEPTED**

Decision:

In V1.5 product mode, OpenAI Responses Structured Outputs may turn supplied verified facts,
precomputed calculations and explicit counter evidence into bounded research language. The
request uses `store: false`, no built-in tools, no web search, a fixed model/configuration and the
existing aggregate budget ledger. Deterministic mode remains the zero-cost fallback.

Reason:

The product benefits from question-aware explanation, but arithmetic, period policy, provenance
and verification must remain deterministic and independently testable. Giving the model only the
bounded context preserves that ownership line.

Consequence:

The model may not invent missing facts, recalculate ratios or retrieve disclosures. Provider
unavailability degrades to the configured deterministic path only when that mode is explicitly
selected; a forced OpenAI mode without a confirmed rotated key fails before dispatch.

## RF-026 — Freeze Final Delivery Order and Defer Human Evaluation

Status: **ACCEPTED**

Decision:

Close V1.5 before new feature work, then deliver reusable deterministic six-metric extraction,
cross-period/company generalization, a bounded n8n integration, and final Web/n8n hardening in
that order. Only after those phases are stable and the protocol is frozen may at least six real
target users evaluate both surfaces over the same ResearchForge backend and verified pipeline.

Reason:

Early Web-only testing would measure a temporary data boundary and omit the external automation
surface. Deferring the Pilot avoids making a human-value claim about an interface or extraction
path that will materially change, while preserving all existing preparation and simulated
evidence honestly.

Consequence:

The old three-person Web-only rubric is retained as preparation history but cannot grant a final
human-validation label. Formal participants are not recruited before Phase 6. n8n owns only
external orchestration; finance, provenance, verification, reasoning and LangGraph remain one
shared backend pipeline. The exact phase order and release freeze are governed by
`docs/product/researchforge-final-delivery-roadmap.md`.

## RF-027 — Make Verified PDF Recovery the Only Numerical Truth Source

Status: **ACCEPTED**

Decision:

The product filing registry stores only reviewed document identity, company and period metadata.
One reusable Python extractor must recover exactly revenue, operating cost, attributable net
income, operating cash flow, accounts receivable and inventory from native PDF statement text.
It resolves consolidated table, exact row, current-period column and declared unit separately,
then promotes the value only after deterministic normalization and page-level recovery checks.

Reason:

The first V1.5 slice proved the research experience but its registry repeated manually reviewed
values and locators. That made the derived package auditable yet did not prove reusable Financial
Fact extraction across future company/period documents. Numerical truth must be source-recovered,
not supplied by either configuration or a language model.

Consequence:

Any missing, duplicate or conflicting table, row, period column, unit or provenance check abstains
the whole package. Parent-company statements cannot satisfy consolidated metrics. Scanned-only
documents abstain because Phase 2 does not introduce OCR. Each ready ingestion manifest records
six recovery proofs and `llm_used: false`. This decision replaces RF-024's reviewed-cell mapping
implementation detail without changing RF-024's source allowlist, document verification,
namespace isolation or raw-PDF exclusion.

## RF-028 — Perform One Final Project-wide Independent Acceptance

Status: **ACCEPTED**

Decision:

Treat Phases 2–6 as engineering checkpoints with tests, formatting, lint, strict typing, contract
validation, applicable Docker/E2E coverage, public CI and honest status evidence. Do not request an
independent acceptance verdict for any intermediate phase. Run one independent read-only review at
Phase 7 after extraction, three-filing generalization, n8n integration, both final UX surfaces,
real-human evaluation and release evidence are frozen.

Reason:

Intermediate reviewer cycles slow delivery and judge partial surfaces rather than the complete
product. Normal engineering gates still expose regressions, while the final reviewer can assess
the shared backend, evidence boundary and both user surfaces as one coherent ResearchForge product.

Consequence:

The completed Phase 1 verdict remains historical evidence. The quota-limited Phase 2 reviewer
attempt produced no verdict and is neither a pass nor a blocker. Phase 2 closes on its engineering
checkpoint and Phase 3 begins immediately. This decision is the project-specific implementation of
RF-013's final-review policy and governs the remaining frozen roadmap.

## RF-029 — Generalize by Financial Semantics, Not Company-specific Answers

Status: **ACCEPTED**

Decision:

Add exactly CATL 2024FY and BYD 2024H1 as identity-only registry records. Extend the same native-text
extractor for explicit report-wide units, wrapped duration headers, period-column order, optional
note-reference columns and parent-company/equity-table boundaries. Keep the six-metric and
all-or-nothing abstention contract. Bind the three product packages in one hash-checked index.

Consequence:

The original CATL 2024H1 package hash remains unchanged. All three paths reach the same LangGraph,
deterministic formulas, evidence linkage, Verifier and persisted Research Result. Limitation text
must describe actual retrieved evidence and must not assume every filing is an unaudited interim
report. Missing unique counter evidence is `not_found`, not manufactured opposition. No new
Benchmark, model call or formal experiment is introduced.

## RF-030 — Keep n8n as a Bounded Same-backend Transport Surface

Status: **ACCEPTED**

Decision:

Use one portable local webhook workflow on pinned n8n 2.37.9. Read the product capability catalog,
POST the unchanged ResearchForge API input, wait/poll within fixed bounds, explicitly route failure,
then return unchanged persisted artifacts and presentation aliases. Keep all finance, evidence,
Verifier, conclusions and LangGraph logic in ResearchForge. Do not rewrite the core for n8n.

Consequence:

The workflow has no model, financial calculation or third-party side-effect nodes. URLs are trusted
operator configuration, redirects are off, namespace fallback is refused, and idempotent retries
preserve both cutoff time and key. Poll exhaustion does not cancel backend research. Real filing
smokes compare all output artifacts to the backend; a separately labeled transport-only fixture
tests actual n8n waiting and failures without supplying financial truth. No new research experiment
or human validation claim is introduced. The custom transport envelope has a new V1.5 schema;
unchanged financial artifacts retain V1.4 schemas.
