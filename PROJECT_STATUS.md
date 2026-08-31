# ResearchForge Project Status

Last updated: 2026-09-01

Machine-readable mirror: [`project-status.json`](project-status.json)

## Current Position

- Scope: V1.4 active baseline
- Contract package: 1.4.0
- Current gate: G3
- Scope and contracts: V1.4 / `schema_version: 1.4.0`; V1.2 and V1.3 remain read-only history.
- Independently accepted gates: C0 and G0.
- Local engineering evidence: G1 thin/full breadth and G2 Verifier exit behavior are implemented; final independent acceptance is intentionally deferred until the whole project is ready.
- Active milestone: G3 formal data preparation and controlled experiment execution.
- Product runtime: five research modes share one ten-stage LangGraph, durable file checkpoints, deterministic finance/Verifier services, asynchronous API, CLI, hybrid PostgreSQL index, and two-page React UI.
- Packaging: CI and Docker Compose definitions exist. Local frontend build/E2E and migration up/down/up pass; Docker image build is currently unverified because both registry attempts timed out while fetching base-image metadata.
- OpenAI spend: USD 0.00. No live provider call has been made.

## What Is Proven Locally

- 132 backend tests are collected, including five successful mode cases, five missing-data cases, 20-run reliability, graph recovery/cancellation/timeout, API lifecycle, migration, security boundaries, Verifier fixtures, and synthetic Evolution policy tests.
- Fixed reliability batch: 20/20 succeeded; four runs per mode; no provider calls.
- The independent Verifier recomputes finance and catches calculation, omission, citation, cutoff, period, schema, and identity faults with stable signatures.
- Research and Skill Lab render persisted API artifacts. The frontend passes typecheck, lint, three unit tests, production build, Playwright navigation, and critical-impact axe checks.
- Primary 24-case split membership is pre-registered as grouping-only data: Evolution 12, Validation 6, Final Test 6. Final Test remains sealed.

## Honest Non-Claims

- G1/G2 are not recorded as independently accepted because the owner requested one final acceptance only.
- The synthetic Evolution tests prove decision-policy behavior only. They are not the formal benchmark and do not support a `SUPPORTED` claim.
- The 24-case suite does not yet contain fully prepared, owner-signed ground truth for every company/report.
- Human user value and market demand remain unvalidated; planned usability evidence is AI simulation labeled `SIMULATED`.
- Docker startup, public GitHub publication, demo video, three simulations, formal OpenAI experiment, and sealed Final Test are not complete.

## Single Next Action

Prepare and validate redistribution-safe primary Benchmark facts and ground truth for Gotion and Sunwoda, complete the second minimal owner signoff, then run the formal experiment under the frozen model/configuration and USD 20 budget guard.

## Active Blockers and Dependencies

1. A new rotated OpenAI key is required before live calibration. The key previously pasted into chat is treated as compromised and must never be used or stored.
2. Formal data preparation and the second owner signoff must complete before Validation or Final Test can run.
3. Docker registry connectivity must recover before the Compose smoke test can be evidenced.
4. `git push` remains a final publication action after secret/data scans; it has not been performed.

## Verification Snapshot

```text
Backend targeted checks
PASS: 68 locked packages, 98 formatted files, lint, strict mypy over 60 source files, and 132/132 tests.

Reliability batch
PASS: 20/20 succeeded; company_research=4, filing_analysis=4, peer_comparison=4, thesis_investigation=4, risk_detection=4; provider cost USD 0.

Frontend
PASS: TypeScript, ESLint, 3 unit tests, production build, 1 Playwright E2E, no critical axe violations.

Docker
PARTIAL: `docker compose config` passed; image build blocked by registry metadata timeout. No runtime smoke claim.

Independent acceptance
Deferred by owner until final project completion. C0 and G0 retain their prior PASS verdicts.
```

## Resume in Five Minutes

1. Read this file and [`docs/product/researchforge-v1.4-scope.md`](docs/product/researchforge-v1.4-scope.md).
2. Read [`docs/evidence/g1-full-reliability.md`](docs/evidence/g1-full-reliability.md), [`docs/evidence/g2-verifier.md`](docs/evidence/g2-verifier.md), and [`docs/evidence/g4-engineering-progress.md`](docs/evidence/g4-engineering-progress.md).
3. Run `uv run python scripts/validate_contracts.py` and `git status --short`.
4. Continue the Single Next Action; do not consume Final Test or claim `SUPPORTED` from synthetic fixtures.
