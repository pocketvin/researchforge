# ResearchForge Project Status

Last updated: 2026-09-02

Machine-readable mirror: [`project-status.json`](project-status.json)

## Current Position

- Scope: V1.4 active baseline; V1.2 and V1.3 are read-only history.
- Contract package: 1.4.0.
- Current gate: G4.
- Engineering: `V1.4 Full Engineering Product Ready` release candidate.
- Research: `RESEARCH_HYPOTHESIS_UNSUPPORTED_AFTER_TWO_EXPERIMENTS`.
- Release gate: full local evidence and GitHub Actions run `33613092646` pass; only the one deferred independent acceptance remains.
- Public repository: [pocketvin/researchforge](https://github.com/pocketvin/researchforge).
- OpenAI spend: USD `0.1523062` of USD `20.00`; no reservation remains.
- Human usefulness and market demand: unvalidated.

## Engineering Evidence

- Five research modes use one bounded ten-stage LangGraph with checkpoint/recovery,
  cancellation, timeout, conditional degradation, and one structure-only repair.
- Financial formulas, evidence loading, Verifier policy, persistence, and Evolution remain
  ordinary Python services independent of LangGraph.
- Research Result contains Claim—Fact—Evidence links, persisted synthetic Evidence Chunks,
  source hashes/locators, deterministic Calculation Records, counter-evidence boundaries,
  limitations, and explicit monitoring triggers.
- FastAPI exposes asynchronous run lifecycle resources, facts, evidence, calculations, trace,
  cancellation, catalog, and read-only Evolution artifacts.
- Content-addressed immutable JSON and eight PostgreSQL logical records pass migration
  `up/down/up`; Docker smoke resolves 6 facts, 1 evidence chunk, 4 calculations, 1 monitoring
  item, and 10 workflow stages through the frontend proxy.
- React Research and Skill Lab pages pass typecheck, lint, unit tests, production build,
  Playwright navigation, critical-impact accessibility checks, and browser inspection.
- The fixed reliability batch remains 20/20 successful with four runs per mode and zero
  provider calls.
- Current full backend suite: 160 tests passed before the final documentation refresh; the
  final release gate reruns the exact count after all edits.

## Formal Research Outcome

### Primary V1.4

- `experiment_primary_v1_4_001`
- 72/72 formal Evolution evaluations succeeded.
- Base: 36 evaluations, 9 failed evaluations, 10 failure events.
- Seed: 36 evaluations, no failure events.
- Outcome: `NO_ELIGIBLE_CLUSTER`.
- No Candidate, Validation, or Final Test.
- Spend: USD `0.0680124`.
- Result hash: `60d7620ca0f620e926c99f22a091d7305097dd787c28d89270977cb8a6c735ed`.

### Contingency V1.5

- `experiment_contingency_v1_5_001`
- Activated once after the frozen primary negative result.
- 72 formal Evolution evaluations succeeded.
- Base: 36 evaluations, 10 failed evaluations, 14 failure events.
- Seed: 36 evaluations, no failure events.
- Two zero-provider-token technical failures were retained as audit records and excluded from
  the formal denominator under the one-retry policy.
- Outcome: `NO_ELIGIBLE_CLUSTER`.
- No Candidate, Validation, or Final Test.
- Spend: USD `0.0646992`.
- Result hash: `dadd29917979b53a2b47ed66e7bfa9deae6ba8486802acc12bdba38ab3a3877f`.

The two-experiment stopping rule is applied. No further formal experiment is authorized. The
combined terminal outcome hash is
`bdc0c1aed55e930312f01ecaebee8969e96e7ff625b27b735b940fcff8a1d2af`.

## Simulated Usability Evidence

- Initial batch `simulated_usability_v1_4_001`: `FAIL`; monitoring actions and direct evidence
  linkage were not sufficiently explicit.
- Corrections: materialized Evidence Chunk IDs/excerpts/hashes, added monitoring triggers and
  next-review timing, exposed deterministic Calculation Records, and taught the Verifier to
  resolve evidence citations.
- Final batch `simulated_usability_v1_4_002`: `PASS`.
- All 3/3 isolated sessions located the key result, supporting evidence, a counter-evidence item
  or limitation, and a monitoring item; 2/3 met both high-score thresholds.
- Every record is `SIMULATED` and `human_user_value_validated: false`.

## Honest Non-Claims

- The research hypothesis is not supported.
- No Candidate was adopted and no sealed Final Test was consumed.
- ResearchForge is not a self-evolving agent.
- The public synthetic evidence is not verbatim filing text; official links and physical-page
  locators remain the source-verification path.
- The product is research assistance, not investment advice.
- AI simulations do not validate real-user usefulness or market demand.

## Remaining Required Work

1. Invoke the one final `$verify-completion` workflow and obtain `VERDICT: PASS` from the
   independent read-only reviewer. Implementation, public-safety scans, publication, and CI are
   already complete.

## Single Next Action

Run the independent read-only acceptance against the verified public commit. Do not run another
formal experiment or change the research outcome.

## Fast Resume

```bash
uv run python scripts/validate_contracts.py
git status --short
```

Then read, in order:

1. `PROJECT_STATUS.md`
2. `docs/evidence/g3-primary-formal-result.md`
3. `docs/evidence/g3-contingency-formal-result.md`
4. `docs/evidence/g4-simulated-usability.md`
5. `DECISIONS.md`
