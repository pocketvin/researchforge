# Legacy V1.5 Web-only Human Usability Preparation

This directory contains the frozen final Web+n8n preparation kit and preserves the earlier V1.5
Web-only kit as history. Neither is proof that a participant study happened.

Current status: **PREPARATION_ONLY · 0 completed real-human sessions · HUMAN_UNVALIDATED**.

Phase 5 is green and frozen. The final protocol is ready for owner-coordinated recruitment and
evaluates both surfaces over the same backend with at least six real target users; criteria and
denominators were frozen before testing. No session exists yet, so this remains preparation rather
than human evidence.

Final kit:

1. [`final-dual-surface-protocol.md`](final-dual-surface-protocol.md) — allocation, tasks, metrics
   and frozen acceptance rules.
2. [`final-participant-task-sheet.md`](final-participant-task-sheet.md) — neutral task with no
   answers.
3. [`final-facilitator-guide.md`](final-facilitator-guide.md) — setup, help classification,
   failure exercise and privacy handling.
4. [`../contracts/v1.5/final-human-evaluation.md`](../contracts/v1.5/final-human-evaluation.md) —
   machine-record and denominator contract.
5. [`../../examples/contracts/v1.5/final-human-evaluation-session.template.json`](../../examples/contracts/v1.5/final-human-evaluation-session.template.json)
   — `TEMPLATE_ONLY`; copy only after a real person consents.

Legacy Web-only kit (superseded, retained for audit history):

Use the files in this order:

1. [`privacy-notice.md`](privacy-notice.md) — give this to the participant before consent.
2. [`participant-task-sheet.md`](participant-task-sheet.md) — the task, without hints about where
   interface elements are located.
3. [`facilitator-guide.md`](facilitator-guide.md) — setup, neutral facilitation and reset steps.
4. [`observation-rubric.md`](observation-rubric.md) — binary outcomes and acceptance rule.
5. [`pilot-status.md`](pilot-status.md) — evidence count and claim boundary.
6. [`../../examples/contracts/v1.5/human-usability-session.example.json`](../../examples/contracts/v1.5/human-usability-session.example.json)
   — copy this template only after a real person agrees to participate.

Completed records belong in ignored local storage under `artifacts/usability/real-human/` until
the participant approves a privacy-safe public summary. Never store names, email addresses,
employers, recordings or contact details in Git.
