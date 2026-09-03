# ResearchForge Final Delivery Roadmap

Status: **FROZEN**

Frozen on: 2026-09-03

Product direction: [`researchforge-v1.5-product-thesis.md`](researchforge-v1.5-product-thesis.md)

This roadmap fixes the remaining delivery order after the V1.5 productization slice. It does not
change the Product Thesis, reopen the frozen Evolution experiments or reinterpret historical
evidence.

## Governing outcome

ResearchForge is complete only when a real target user can use either the Web Research page or
the ResearchForge n8n workflow to submit Company + Period + Research Question to the same backend
and verified research pipeline, then independently inspect the conclusion, facts, calculations,
evidence, counter evidence or limitations, and monitoring plan.

Formal real-human evaluation happens only after the engineering, data, Web, n8n and demo surfaces
are stable and frozen. Until then, `human_user_value_validated` remains `false`.

## Phase 1 — Close V1.5

No new product feature is permitted in this phase.

- Correct stale local/CI status in `PROJECT_STATUS.md` and `project-status.json`.
- Reconcile the Product Thesis audit with capabilities already delivered in V1.5.
- Run the complete repository gate.
- Obtain `VERDICT: PASS` from the final independent read-only reviewer.

Exit: the V1.5 productization slice is independently accepted, while broad-data and human-value
claims remain explicitly unvalidated.

## Phase 2 — Reusable Financial Fact Extraction

Implement one bounded, reusable extraction path for exactly these metrics:

- `revenue`
- `operating_cost`
- `net_income`
- `operating_cash_flow`
- `accounts_receivable`
- `inventory`

Required path:

```text
Verified PDF
→ page-preserving parser
→ financial statement/table detection
→ metric row matching
→ reporting-period/column resolution
→ scale/unit detection
→ candidate numerical extraction
→ deterministic normalization
→ provenance verification
→ Financial Fact
```

The LLM is never the numerical truth source. Every promoted number must be deterministically
recoverable from the verified PDF. Ambiguous period, table, row, column or unit causes
abstention. Document hash, source locator, Evidence Chunk and provenance remain first-class.
Company-specific result code, a general OCR platform and additional metrics are out of scope.

## Phase 3 — Generalization Evidence

Use the same extraction implementation for:

1. CATL 2024H1;
2. one different CATL period, preferably 2024FY;
3. one different company with a similar period, preferably BYD 2024H1.

Each path must reach facts, deterministic calculations, evidence, counter evidence or an honest
limitation, monitoring and a verified Research Result. No company-specific result generator is
permitted.

## Phase 4 — n8n Integration

Add `integrations/n8n/` containing an importable workflow JSON, README, demo instructions,
necessary examples or screenshots, and failure-behavior documentation.

```text
Form/Webhook
→ POST ResearchForge run
→ run_id
→ wait and poll status
→ IF/Switch
→ retry while running
→ explicit failure branch
→ fetch Research Result
→ map conclusion/findings/evidence/limitations/monitoring
→ final workflow output
```

n8n owns external and business orchestration only. ResearchForge remains the owner of financial
arithmetic, evidence truth, verifier policy, research conclusions and the LangGraph workflow.
The integration must not require a core rewrite.

## Phase 5 — Final Product and Demo Hardening

Freeze a coherent Web and n8n product over the same backend capability:

- Web Research UX and n8n workflow UX;
- README, Portfolio, interview narrative and end-to-end demo;
- screenshots and failure/abstention experience;
- reproducible startup, CI, Docker and E2E evidence;
- final human-evaluation tasks, cases, fields, thresholds and denominator rules.

Exit: Phases 1–5 are stable and the evaluation protocol is frozen before recruiting or testing
participants.

## Phase 6 — Final Real-Human Evaluation

Evaluate both surfaces with at least six real target users:

- Surface A: ResearchForge Web;
- Surface B: ResearchForge n8n workflow.

Use counterbalanced order: Group A completes Web then n8n; Group B completes n8n then Web.
Equivalent but different company/period cases may be balanced across surfaces.

Shared observations cover task initiation, conclusion understanding, financial-fact discovery,
calculation understanding, evidence discovery, limitation/counter-evidence discovery, monitoring
discovery and trust-boundary understanding. Web adds navigation, hierarchy, progressive
disclosure and readability. n8n adds workflow-entry usability, status comprehension,
asynchronous waiting, failure-path comprehension and perceived automation value.

Simulated personas are not participants. Post-test threshold changes are prohibited. Failed
participants remain in the frozen denominator, and facilitator-assisted completion is not an
independent pass.

## Phase 7 — Release Freeze

Freeze ResearchForge only after all of the following exist:

- final independent acceptance PASS;
- reusable six-metric extraction;
- CATL 2024H1, an additional CATL period and an additional company;
- complete n8n integration;
- complete Web and n8n UX;
- final real-human evaluation;
- green CI, Docker and E2E gates.

After release freeze, do not add multi-agent systems, Evolution experiments, new benchmark
systems, trading, price prediction, portfolio optimization, real-time news, complex vector
infrastructure, broad new research modes or architecture for its own sake. Work shifts to Resume,
Portfolio, Demo, interview preparation and job applications.

## Authority and change control

The Product Thesis remains the highest statement of product purpose. This roadmap is the highest
authority for delivery sequence and phase exits. Existing V1.2–V1.4 schemas, packages, hashes,
formal experiment outcomes and audit artifacts remain immutable.

Changing this roadmap requires a new owner-approved decision record. Implementation convenience,
simulated feedback or a desired success claim is not sufficient reason to reorder phases or alter
frozen evaluation evidence.
