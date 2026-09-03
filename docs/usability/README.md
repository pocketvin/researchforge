# Legacy V1.5 Web-only Human Usability Preparation

This directory preserves the V1.5 Web-only preparation kit. It is not proof that a participant
study happened and it is not the final ResearchForge evaluation protocol.

Current status: **PREPARATION_ONLY · 0 completed real-human sessions · HUMAN_UNVALIDATED**.

Do not run a formal Pilot from this kit. The frozen delivery roadmap defers real-human evaluation
until reusable extraction, cross-period/company evidence, n8n integration, Web/n8n UX and the
demo are stable. The final protocol must evaluate both surfaces over the same backend with at
least six real target users and criteria frozen before testing.

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
