# Final Dual-Surface Human Evaluation Contract

Status: **FROZEN BEFORE RECRUITMENT · ZERO COMPLETED SESSIONS**

This contract governs the final ResearchForge Phase 6 evaluation. It compares the interaction
surface, not two AI systems: Web and n8n call the same ResearchForge backend and verified research
pipeline. The machine record is
`schemas/v1.5/final-human-evaluation-session.schema.json`; the committed example is explicitly
`TEMPLATE_ONLY` and is not human evidence.

## Evidence boundary

- At least six real target users must consent and independently attempt both surfaces.
- A simulated persona, AI review, maintainer walkthrough or automated E2E run never counts.
- Only a consented real session may be labeled `REAL_HUMAN`; a scheduled blank record is
  `TEMPLATE_ONLY`.
- `independent_pass` means the participant completed the observable task without directional help.
  A prompted completion is `assisted`; assistance never counts as a pass.
- Failed and abandoned attempts remain in the denominator. A participant who withdraws may request
  deletion of their details; the aggregate withdrawal and failed-attempt count remains without
  identity or content.
- No name, email, employer, contact detail or recording is committed. Public summaries require
  separate consent.

## Frozen denominator and acceptance

An eligible participant is a consented target user who starts the first assigned surface. For each
eligible participant, both assigned surface attempts remain in the denominator even if the second
is abandoned. Only `independent_pass` contributes to any numerator; `assisted`, `failed` and
`not_attempted` contribute zero.

Phase 6 passes only when all rules hold:

1. At least six eligible participants, with Group A and Group B counts differing by no more than
   one.
2. At least 80% independent completion over all eight shared outcomes × both surfaces × all
   eligible participants.
3. Every shared outcome reaches at least 75% independent completion across both surfaces.
4. On each surface, at least two-thirds of eligible participants independently pass all eight
   shared outcomes in that attempt.
5. `successful_task_initiation` and `trust_boundary_understanding` each reach at least 5/6 on Web
   and at least 5/6 on n8n (scaled as 83.33% if more than six participants).
6. Every Web-specific and n8n-specific outcome reaches at least 75% independent completion on its
   own surface.
7. All eligible sessions, failures, assistance and withdrawals are accounted for; the public
   summary states sample limits and does not claim broad market validity.

These thresholds cannot change after the first real session. If they are not met, the result is an
honest failed or inconclusive evaluation, not `HUMAN_VALIDATED`.

## Surface identity

Web entry: `http://127.0.0.1:4173/`.

n8n entry: `http://127.0.0.1:5678/form/researchforge-v15-form`.

Both must expose Research Result and Trace links from the same backend. n8n owns form/business
orchestration only; finance, evidence, verification, conclusion generation and LangGraph remain in
ResearchForge.
