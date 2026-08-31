# G4 Engineering Progress Evidence

Evidence date: `2026-09-01`

Status: `IN_PROGRESS_NOT_PRODUCT_READY`

## Passing Local Evidence

- React/TypeScript/Vite/Tailwind Research and Skill Lab pages.
- Research page renders API-derived facts, claims, evidence, counter-evidence, checks, sources, limitations, progress, cancellation and terminal failures.
- Skill Lab is read-only and renders persisted experiment status, split counts, budget, sealed Final Test state, and raw immutable details.
- Frontend typecheck, ESLint, three unit tests, production build, Playwright navigation, and critical-impact axe checks pass.
- Eight SQLAlchemy logical records and Alembic initial migration exist; migration `up/down/up` and hybrid file/database mirroring pass in tests.
- Docker Compose describes PostgreSQL, API, frontend, health checks and persistent volumes; `docker compose config` passes.
- CI runs backend format/lint/type/tests/contracts, frontend type/lint/unit/build/E2E, and container build.

## Unverified or Missing

- Docker image build and Compose runtime smoke are not passing evidence. Two attempts timed out while retrieving registry base-image metadata (first GHCR, then Docker Hub).
- Three isolated `SIMULATED` usability evaluations have not run.
- Demo video and public GitHub package have not been produced.
- Formal G3 artifacts are absent; Skill Lab therefore correctly shows preregistered/PENDING or empty states, never an invented success story.
- Human usefulness remains explicitly unvalidated.
