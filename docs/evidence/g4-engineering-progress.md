# G4 Engineering Progress Evidence

Evidence date: `2026-09-01`

Status: `ENGINEERING_RUNTIME_PASS_SIMULATIONS_PENDING`

## Passing Local Evidence

- React/TypeScript/Vite/Tailwind Research and Skill Lab pages.
- Research page renders API-derived facts, claims, evidence, counter-evidence, checks, sources, limitations, progress, cancellation and terminal failures.
- Skill Lab is read-only and renders persisted experiment status, split counts, budget, failure cluster, Experience, Candidate Skill Diff, paired Validation scores, sealed/consumed Final Test state, and raw immutable details.
- Frontend typecheck, ESLint, three unit tests, production build, Playwright navigation, and critical-impact axe checks pass.
- Eight SQLAlchemy logical records and Alembic initial migration exist; migration `up/down/up` and hybrid file/database mirroring pass in tests.
- Docker Compose builds and starts PostgreSQL, API, and frontend with health checks and persistent volumes. The runtime smoke created one real product run through the Nginx proxy, persisted it in PostgreSQL/content-addressed storage, and resolved six facts plus a ten-stage Trace.
- Alembic `up/down/up` passed inside the packaged API container.
- CI runs backend format/lint/type/tests/contracts, frontend type/lint/unit/build/E2E, then container build/start/runtime smoke and cleanup.
- Browser interaction verified both pages at a desktop viewport with no console warnings or errors. Public-fixture screenshots and a 12-second H.264 preview are stored in `docs/assets/`.
- The three-session simulation executor enforces fresh independent requests, Structured Outputs, `store: false`, no tools, exact `SIMULATED` labels, idempotent recovery, a USD 2 sub-cap, and the aggregate USD 20 cap. Offline preflight blocks before provider contact when the rotated key is absent.

## Unverified or Missing

- Three real model-backed isolated `SIMULATED` usability evaluations have not run; the executor and screenshots are ready.
- The public GitHub package has not been published.
- Formal G3 artifacts are absent; Skill Lab therefore correctly shows preregistered/PENDING or empty states, never an invented success story.
- Human usefulness remains explicitly unvalidated.

## Docker Runtime Evidence

```text
PASS: API, frontend, and PostgreSQL containers healthy
PASS: frontend proxy served the application and all five catalog modes
PASS: one filing-analysis run reached succeeded
PASS: 10 workflow stages, 6 persisted facts, result and source links resolved
PASS: migration up/down/up
```

Docker Hub token requests timed out in this environment. The verified local build used compatible official-library images from Amazon Public ECR through optional Compose build arguments; the committed defaults remain Docker Hub names.

## Simulation Preflight Evidence

```text
status: BLOCKED
provider_contacted: false
only blocker: rotated local OpenAI key is not confirmed ready
batch worst case: USD 0.6072
aggregate spend: USD 0.00
```

No simulated result is claimed yet. The screenshots prove presentation state only, not real-user value.
