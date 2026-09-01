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
- Active milestone: G3 primary package is prepared and the controlled experiment executor is implemented; second owner signoff, contingency freeze, and live execution remain.
- Product runtime: five research modes share one ten-stage LangGraph, durable file checkpoints, deterministic finance/Verifier services, asynchronous API, CLI, hybrid PostgreSQL index, and two-page React UI.
- Packaging: CI and Docker Compose definitions exist. Local frontend build/E2E and migration up/down/up pass; Docker image build is currently unverified because both registry attempts timed out while fetching base-image metadata.
- OpenAI spend: USD 0.00. No live provider call has been made.

## What Is Proven Locally

- The current full gate passes 141 backend tests; primary-package and formal-engine regressions cover artifact relationships, split isolation, cutoffs, synthetic labeling, package hashes, budget persistence, repeated pairing, and Final Test controls.
- Fixed reliability batch: 20/20 succeeded; four runs per mode; no provider calls.
- The independent Verifier recomputes finance and catches calculation, omission, citation, cutoff, period, schema, and identity faults with stable signatures.
- Research and Skill Lab render persisted API artifacts. The frontend passes typecheck, lint, three unit tests, production build, Playwright navigation, and critical-impact axe checks.
- Primary 24-case package is prepared: 24 official Source Documents, 144 normalized Financial Facts, 24 explicitly synthetic public Evidence Chunks, and 24 cases split 12/6/6. All 96 newly acquired fact cells were page-matched; Final Test remains sealed and formal execution is disabled pending owner signoff.
- Offline formal-experiment plumbing ran all 144 pre-registered Base/Seed/Candidate paths with a synthetic test double. It validated three repeats, stable failure clustering, Experience and Candidate artifacts, paired adoption thresholds, durable budget state, and one-time Final Test unsealing. This is engineering evidence only.
- Zero-network preflight reports a USD 1.8432 maximum reservation for all 288 possible requests including one repair per run, below both the USD 9 primary allocation and USD 20 aggregate cap.

## Honest Non-Claims

- G1/G2 are not recorded as independently accepted because the owner requested one final acceptance only.
- The synthetic Evolution tests prove decision-policy behavior only. They are not the formal benchmark and do not support a `SUPPORTED` claim.
- The 24-case suite is not yet owner-signed. Its verifier-only ground truth is excluded from Git and represented publicly by 24 hashes; no formal run is authorized.
- Human user value and market demand remain unvalidated; planned usability evidence is AI simulation labeled `SIMULATED`.
- Docker startup, public GitHub publication, demo video, three simulations, formal OpenAI experiment, and sealed Final Test are not complete.

## Single Next Action

Freeze the disjoint V1.5 contingency package while the primary package awaits the second minimal owner signoff and a safe rotated local key; then run calibration and the formal primary experiment without changing model, graph, data, verifier, or thresholds.

## Active Blockers and Dependencies

1. A new rotated OpenAI key is required before live calibration. The key previously pasted into chat is treated as compromised and must never be used or stored.
2. The prepared package needs the second owner signoff before any formal Evolution, Validation, or Final Test run.
3. The disjoint V1.5 contingency suite must be frozen before the first formal primary run.
4. Docker registry connectivity must recover before the Compose smoke test can be evidenced.
5. `git push` remains a final publication action after secret/data scans; it has not been performed.

## Verification Snapshot

```text
Backend targeted checks
PASS: 69 locked packages, 105 formatted files, lint, strict mypy over 65 source files, 141/141 tests, contracts, diff whitespace, and Compose configuration.

Reliability batch
PASS: 20/20 succeeded; company_research=4, filing_analysis=4, peer_comparison=4, thesis_investigation=4, risk_detection=4; provider cost USD 0.

Frontend
PASS: TypeScript, ESLint, 3 unit tests, production build, 1 Playwright E2E, no critical axe violations.

Docker
PARTIAL: `docker compose config` passed; image build blocked by registry metadata timeout. No runtime smoke claim.

Independent acceptance
Deferred by owner until final project completion. C0 and G0 retain their prior PASS verdicts.

Primary Benchmark package
PASS locally: 24 sources, 144 facts, 24 synthetic chunks, 24 frozen cases; package hash 3638eb1ca7b8192cb6a901f4b0d51c8373ccaff1e776758605f1d4b975cb1c3f; owner signoff pending.

Formal experiment executor
PASS locally with a synthetic test double: 144/144 temporary runs and artifacts validated. Real preflight is BLOCKED before provider contact by pending owner signoff and rotated-key confirmation. OpenAI spend remains USD 0.
```

## Resume in Five Minutes

1. Read this file and [`docs/product/researchforge-v1.4-scope.md`](docs/product/researchforge-v1.4-scope.md).
2. Read [`docs/evidence/g1-full-reliability.md`](docs/evidence/g1-full-reliability.md), [`docs/evidence/g2-verifier.md`](docs/evidence/g2-verifier.md), and [`docs/evidence/g4-engineering-progress.md`](docs/evidence/g4-engineering-progress.md).
3. Run `uv run python scripts/validate_contracts.py` and `git status --short`.
4. Continue the Single Next Action; do not consume Final Test or claim `SUPPORTED` from synthetic fixtures.
