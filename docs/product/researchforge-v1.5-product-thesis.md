# ResearchForge V1.5 — Product Thesis

Status: **ACTIVE PRODUCT DIRECTION**
Product version: **V1.5 Productization**
Previous baseline: **V1.4 preserved as a reproducible engineering and research record**
Primary success target: **a real, independently auditable A-share fundamental-research run**

> ResearchForge is an evidence-grounded AI fundamental research workspace for A-share
> company research.

V1.5 changes the center of gravity of the project. Research is the product. Controlled Skill
Evolution is a frozen Quality / Research Lab asset behind the product, not the reason a normal
user opens ResearchForge.

## 1. Problem

People can ask a general-purpose LLM to analyze a listed company, but the answer is difficult to
trust because the user often cannot establish:

1. whether the model used the correct company, filing, period and publication cutoff;
2. whether financial values came from an authoritative disclosure or model memory;
3. whether a ratio or period comparison was calculated correctly;
4. which source supports each important conclusion;
5. whether conflicting evidence was searched for;
6. what is unknown or unavailable; and
7. what evidence would change the conclusion in the next reporting period.

The practical problem is not a shortage of fluent financial prose. It is the absence of a fast,
inspectable path from a research question to facts, calculations, evidence, uncertainty and a
monitoring plan.

## 2. Target User

Primary users are:

- individual researchers studying A-share company fundamentals;
- finance learners who want to understand how a conclusion is constructed;
- junior researchers who need a first-pass report they can audit rather than blindly accept.

Secondary users are interviewers and technical reviewers evaluating the system's data,
financial-engineering, agent-workflow and verification design.

V1.5 is not designed for professional trading desks, automated investment decisions, real-time
market surveillance or users seeking a buy/sell recommendation.

## 3. Job To Be Done

When I have a company, a reporting period and a fundamental-research question, I want
ResearchForge to use official public disclosures to produce a concise research result whose
conclusion, facts, calculations and evidence I can independently inspect, so that I can form my
own view without trusting a financial chatbot's black box.

The minimal user input is:

```text
Company + Period + Research Question
```

Example:

```text
宁德时代 + 2024H1 + 2024 年上半年利润是否真正转化成了经营现金流？
```

## 4. Product Promise

For an allowlisted real company and supported filing, ResearchForge will answer seven questions:

1. **Conclusion** — What is the bounded answer to the research question?
2. **Key facts** — Which normalized financial facts materially support it?
3. **Calculations** — Which deterministic formula produced every important number?
4. **Sources** — Which official document, page or section supports each fact and claim?
5. **Counter evidence** — What conflicting evidence was found, or what bounded search returned
   `not_found`?
6. **Limitations** — Which missing, incompatible or uncertain inputs constrain the conclusion?
7. **Monitoring** — What should be checked in the next comparable disclosure, and what trigger
   would change the conclusion?

The promise is auditability, not omniscience. When a source, value, comparison or interpretation
cannot be established, the product abstains or returns a clearly bounded partial result.

## 5. Core Design Principles

| Owner | Responsibility |
|---|---|
| LLM | question understanding and bounded research reasoning over supplied evidence |
| Deterministic Python | financial formulas, period semantics, numerical calculations and policy decisions |
| Evidence System | document identity, provenance, locators and claim-level traceability |
| Verifier | calculation consistency, citation resolution, evidence coverage, counter-evidence and required-check coverage |
| LangGraph | one bounded, checkpointed research workflow with routing, cancellation, recovery and sanitized trace |
| Quality / Research Lab | read-only experimental evidence about system quality; never required for a normal research run |

Additional rules:

- no material number is calculated in model prose;
- no claim is promoted to a verified fact without a resolvable artifact;
- retrieved disclosure text is untrusted data, never an instruction source;
- hidden chain-of-thought is neither required nor persisted;
- fixture reliability and human usefulness are reported as different kinds of evidence.

## 6. Core Workflow

```text
Company resolution
→ Official disclosure discovery
→ Document acquisition and identity verification
→ Parsing and page/section mapping
→ Evidence Chunk creation
→ Structured Financial Fact normalization
→ Deterministic financial calculations
→ Bounded research reasoning
→ Counter-evidence search
→ Verifier checks
→ Structured Research Result
→ Monitoring plan
→ Expandable Research Trace
```

The existing ten-stage LangGraph remains the orchestration spine:

```text
understanding_question
→ planning
→ loading_financial_data
→ retrieving_evidence
→ calculating
→ cross_checking
→ searching_counter_evidence
→ forming_conclusion
→ validating_output
→ completed
```

V1.5 changes the data adapters and product presentation around that graph; it does not create
multiple agents or move formulas into LangGraph.

## 7. User Story

1. The user opens **Research**, selects an unambiguous company and supported reporting period,
   writes a question and selects **Start Research**.
2. ResearchForge shows plain-language progress while it resolves the official disclosure,
   loads normalized facts, performs calculations and verifies the result.
3. The completed page first shows **Executive Conclusion** and **Key Findings**.
4. The user can expand **Financial Facts**, **Calculations** and **Supporting Evidence** to audit
   the result without being forced through implementation detail.
5. **Counter Evidence**, **Risks & Limitations** and **Monitoring Plan** remain visible enough to
   prevent a one-sided conclusion.
6. An optional **Research Trace** explains which bounded stages ran and which artifacts they
   produced.
7. A separate **Quality Lab** link is available to technical reviewers, clearly labeled
   experimental, read-only and unnecessary for ordinary research.

## 8. V1.4 Starting Audit and V1.5 Closure Status

This section preserves the gap that motivated V1.5 and records its current disposition. It is not
a list of unresolved work. Remaining delivery work is governed by
[`researchforge-final-delivery-roadmap.md`](researchforge-final-delivery-roadmap.md).

### 8.1 Product narrative — closed in V1.5

- README, Portfolio, package metadata and demo now lead with the user's auditable company-research
  problem and Company + Period + Research Question.
- Candidate, cluster, Validation and Final Test mechanics are confined to the secondary Quality
  Lab story.

### 8.2 Real-world data — three-filing generalization checkpoint passed

- The default runtime uses a strict `product` namespace and a real-disclosure acquisition/parser
  adapter; fixture and Benchmark fallback are rejected.
- CATL 2024H1 preserves official source identity, hash, page locators, Evidence Chunks and six
  reviewed facts while raw PDFs remain ignored.
- Reusable deterministic extraction without registry-provided values is now implemented. Phase 3
  added CATL 2024FY and BYD 2024H1 through the same implementation: 18 facts and three verified
  Research Results, with backend, live Web E2E, Docker and public CI passing. This engineering
  evidence remains separate from human usefulness and final project acceptance.

### 8.3 Research reasoning and verification — closed for the first slice

- Product mode supports bounded OpenAI reasoning over supplied evidence and a zero-cost
  deterministic mode; neither path owns financial arithmetic or source truth.
- Deterministic formulas, point-in-time checks, Claim—Fact—Evidence linkage, Verifier rules and
  abstention behavior are active in the real CATL path.
- Breadth remains deliberately bounded to the useful earnings-quality path; new modes are not a
  remaining V1.5 objective.

### 8.4 Core user experience — closed for the first slice

- Research now starts with Company, Period, Question and Start Research.
- Facts, calculations, evidence, counter evidence and trace use progressive disclosure.
- The completed report follows the requested conclusion-to-monitoring narrative order and is
  covered by unit, E2E, accessibility and live-browser checks.
- Final hardening adds a direct n8n-form entry, raw Result/Trace links and an explicit Web terminal
  state that says when no research result was generated.

### 8.5 Quality Lab and validation — product surface closed, human evidence deferred

- Quality Lab is secondary, experimental, read-only and unnecessary for normal research.
- The frozen outcome `RESEARCH_HYPOTHESIS_UNSUPPORTED_AFTER_TWO_EXPERIMENTS` is honest and must
  remain immutable.
- No human Pilot has been run and no human-usefulness claim is allowed. The final dual-surface
  tasks, A/B allocation, outcome fields, thresholds and denominator are frozen before recruitment.
  Phase 5 has passed local and public engineering gates; execution now requires real participant
  consent and coordination.

### 8.6 Demo and career value — final hardening engineering checkpoint passed

- The current product-first demo uses the official CATL 2024H1 disclosure, verified values,
  deterministic arithmetic, source citations, counter evidence, monitoring and a complete trace.
- Generalized extraction and same-backend n8n engineering have passed their checkpoints. The
  native n8n form, bounded failure page, dual-surface screenshots and reproducible launcher are
  implemented for Phase 5 and passed public CI. Real-human evaluation and the final project-wide
  acceptance are still required before release freeze.

## 9. V1.5 Scope

### P0 — Product narrative

- Make this document the highest active product-direction authority.
- Rewrite the first screen of `README.md` so a new reader understands the product, user, problem,
  input, output and differentiation within 30 seconds.
- Reframe `PROJECT_STATUS.md`, `PORTFOLIO.md`, `docs/product/` and `docs/demo/` around the research
  workspace.
- Preserve links to V1.4 research evidence under a clearly secondary Quality Lab section.

### P0 — Real-world disclosure ingestion

Implement a narrow, versioned pipeline:

```text
allowlisted Company
→ official Filing discovery record
→ acquired immutable document
→ parser output with page boundaries
→ Evidence Chunks
→ normalized Financial Facts
→ existing Research workflow
```

Initial coverage is deliberately small. The first vertical slice is CATL / 2024H1, followed by a
second compatible company or period only after the first slice is verified.

The product pipeline must preserve:

- source and announcement identity;
- official URL;
- publication and retrieval timestamps;
- raw-content SHA-256 and byte count;
- company, exchange, filing type and period;
- parser and mapping versions;
- page, section, table, row and column locators where applicable;
- parent-document and source-fact provenance;
- acquisition, parsing and fact-confidence/availability status.

Product data and benchmark data must use different configuration, directories, database
namespaces and identifiers. A product run cannot silently fall back to benchmark truth.

### P0 — Core Research experience

- Default input surface: Company, Period, Research Question, Start Research.
- Preserve task types as internal capability metadata or an advanced option; do not make users
  understand the mode taxonomy before their first run.
- Render the completed report in this order:
  1. Executive Conclusion;
  2. Key Findings;
  3. Financial Facts;
  4. Calculations;
  5. Supporting Evidence;
  6. Counter Evidence;
  7. Risks & Limitations;
  8. Monitoring Plan;
  9. Research Trace.
- Use progressive disclosure for facts, calculations, evidence and trace.
- All displayed values remain API artifacts; the browser performs presentation formatting only.

### P1 — Product surface

- Rename Skill Lab to **Quality Lab** or **Research Lab**.
- Label it `EXPERIMENTAL`, `READ-ONLY` and `NOT REQUIRED FOR NORMAL RESEARCH`.
- Move it behind a secondary navigation treatment.
- Keep every V1.4 experiment artifact and negative result unchanged.

### P1 — Human usability preparation

- Add a participant script, task sheet, consent/privacy note, observation rubric and feedback
  record schema or template.
- The legacy V1.5 kit prepares a Web-only session but is not the final evaluation protocol.
- No record is marked human unless a real participant actually completes it.
- Simulated evidence remains available only as historical engineering evidence.
- Formal recruitment and execution are deferred until the frozen final roadmap's Phase 6, after
  Web and n8n share one stable backend and verified pipeline.

### P1 — Job-search demo

- Provide a three-to-five-minute real-data walkthrough.
- Use a real company, official disclosure, verified values, deterministic calculation,
  evidence citation, counter-evidence boundary, monitoring plan and full Research Trace.
- Keep setup reproducible without committing full PDFs or secrets.
- State the exact supported-company boundary and abstention behavior.

### P2 — Quality / Research Lab

- Freeze the two formal experiments, thresholds, packages, hashes and terminal result.
- Do not run a third formal experiment or reinterpret the frozen result.
- New quality research may be proposed only after real usage exposes a stable repeated failure
  pattern and a new versioned protocol is approved.

## 10. Real-data Isolation Contract

V1.5 uses three explicit data classes:

| Namespace | Purpose | May serve product runs? | Public repository rule |
|---|---|---:|---|
| `product` | acquired real disclosures and derived product artifacts | yes | metadata, facts and permitted excerpts only; raw documents ignored |
| `fixture` | deterministic developer tests and reproducible demos | only in explicit fixture mode | safe synthetic/reconciled package |
| `benchmark` | frozen evaluation and Quality Lab evidence | no | existing hashes and public-safe artifacts remain immutable |

Every run records its data namespace. Mixing namespaces in one run is a hard failure. Hidden
benchmark truth is never a product fallback.

## 11. Non-goals

V1.5 does not add:

- multi-agent systems, debate or role swarms;
- vector infrastructure without a measured retrieval need;
- full-market coverage;
- real-time prices, news monitoring or event trading;
- price targets, return forecasts or investment recommendations;
- portfolio optimization, execution or brokerage connections;
- autonomous prompt evolution, model routing or open-ended self-modification;
- a general OCR platform, data lake or enterprise document-management system;
- multi-tenancy, collaboration, mobile apps, Kubernetes or distributed orchestration.

## 12. Acceptance Criteria

### A. V1.4 asset protection

- V1.2, V1.3 and V1.4 schemas and historical scope documents remain unchanged.
- Primary and contingency package hashes, formal result hashes, thresholds, denominators and
  terminal negative result remain unchanged.
- Existing fixture/benchmark tests remain reproducible.
- The historical artifact named `experiment_contingency_v1_5_001` remains a frozen experiment
  identifier; it is not the product-scope authority for V1.5 Productization.

### B. Product narrative

- A first-time reader can identify What / Who / Problem / Input / Output / Difference from the
  first README screen.
- Normal product instructions lead to Research; Quality Lab is explicitly secondary.
- No page claims human validation, self-evolution or a supported research hypothesis.

### C. Real-data vertical slice

- At least one allowlisted real A-share filing is discovered or loaded from an official source,
  acquired, hashed, parsed and converted into evidence and facts without reading benchmark data.
- The end-to-end product run answers a real research question using those artifacts.
- Every material fact and claim resolves to an official source locator and immutable document
  hash.
- Every important numeric result resolves to a deterministic Calculation Record.
- Counter-evidence status, limitations and at least one monitoring item are present.
- Unverified, missing, incompatible or post-cutoff inputs cause abstention or explicit partial
  degradation, never model-memory completion.

### D. Core user experience

- The primary form exposes Company, Period, Question and Start Research without requiring
  experiment knowledge.
- The nine requested result sections appear in the defined narrative order.
- Evidence, Calculation and Trace details are expandable and keyboard accessible.
- Frontend unit, E2E and critical accessibility checks cover the primary real-research journey.

### E. Human evaluation preparation and evidence boundary

- A legacy Web-only Pilot kit exists as preparation evidence; it is not executed as the final
  evaluation.
- Human usefulness remains `UNVALIDATED` until real sessions exist.
- If sessions occur, raw feedback and dissent are retained; no simulated persona is counted as a
  person.
- Final human evaluation must cover Web and n8n with at least six real target users under criteria
  frozen before testing. Facilitator-assisted completion is not an independent pass.
- The frozen final record uses four outcomes—independent pass, assisted, failed and not attempted—
  so help, abandonment and failure cannot disappear from the denominator.

### F. Demo and career evidence

- A three-to-five-minute walkthrough shows one real end-to-end run and the seven product answers.
- Demo claims identify the exact company/period coverage and source boundary.
- Portfolio bullets emphasize ingestion, provenance, deterministic finance, verification,
  workflow and UX; the frozen experiment is an optional technical deep dive.

### G. Engineering gate

- Contracts, formatting, lint, strict typing, backend/frontend tests, E2E, migrations and Docker
  smoke pass.
- Public-safety checks find no secret, private benchmark truth, raw filing PDF or local absolute
  path in tracked files.
- GitHub CI passes on the published commit.
- One final project-wide independent acceptance returns `VERDICT: PASS` at Phase 7 before release
  completion is claimed; there are no Phase 2–6 independent reviews.

## 13. V1.5 Success Labels

- **V1.5 Direction Ready** — this Product Thesis, migration decision and scope authority are
  accepted.
- **V1.5 Real-data Slice Ready** — Acceptance C passes for one real filing.
- **V1.5 Pilot Preparation Ready** — Acceptance B–D and the legacy Web-only kit pass; no
  human-value claim and no authorization to run the final Pilot.
- **V1.5 Product Ready** — real-data, UX, demo, engineering and final independent acceptance pass.

Human validation is a final-delivery label, not a V1.5 closure label. It requires the dual-surface
Phase 6 protocol in the frozen final roadmap.

The Evolution hypothesis is not part of any V1.5 Productization success label.

## 14. Migration Plan from V1.4

### Phase 0 — Freeze and reframe

1. Tag V1.4 code, schemas, evidence and hashes as the preserved baseline.
2. Record a V1.4→V1.5 product-direction decision and change note.
3. Update `AGENTS.md` and repository authority order so this document governs product priority.
4. Reframe README, status, portfolio and demo without deleting historical evidence.

### Phase 1 — Separate product data from evaluation data

1. Introduce a V1.5 data-source/ingestion contract and new schema package for new persisted
   semantics rather than mutating V1.4 schemas.
2. Add explicit `product`, `fixture` and `benchmark` namespaces.
3. Implement allowlisted company resolution and official-document metadata ingestion.
4. Store raw acquired files only in ignored local storage; persist hashes and provenance.

### Phase 2 — Deliver one real research slice

1. Acquire and verify CATL 2024H1 from the recorded official source.
2. Parse page-delimited text and create real, locator-preserving Evidence Chunks.
3. Normalize the minimum earnings-quality facts through existing mapping and Decimal logic.
4. Run the existing bounded LangGraph, model reasoning boundary and Verifier over product data.
5. Persist an audit bundle that never reads benchmark truth.

### Phase 3 — Productize the Research page

1. Simplify the input surface.
2. Reorder the report around user questions.
3. Add progressive disclosure and accessibility coverage.
4. Move Skill Lab to the secondary, read-only Quality Lab surface.

### Phase 4 — Verify and demonstrate

1. Package the real-data demo and exact reproduction steps.
2. Add the legacy Web-only human-evaluation preparation kit without recruiting participants.
3. Run full verification, public CI and one final independent acceptance.

The post-V1.5 sequence, including reusable extraction, n8n and final real-human evaluation, is
defined by [`researchforge-final-delivery-roadmap.md`](researchforge-final-delivery-roadmap.md).

## 15. Complexity Removal Rule

Any proposed component must directly improve at least one of:

1. real research usability;
2. verifiability and abstention safety; or
3. job-search demonstration value.

If it does not, V1.5 freezes, hides, removes from the default path or declines it. Existing
Quality Lab code may remain for reproducibility, but it does not set the product roadmap.

## 16. Authority

For V1.5 Productization decisions, authority order is:

1. this Product Thesis;
2. the frozen final delivery roadmap for sequencing and phase exits;
3. V1.5 contracts and schemas created under its migration plan;
4. preserved V1.4 contracts for unchanged finance, evidence, workflow and safety semantics;
5. application code and UI.

When V1.5 work conflicts with frozen V1.4 experimental evidence, preserve the V1.4 evidence and
change only the V1.5 product path. No productization change may rewrite a historical experiment.
