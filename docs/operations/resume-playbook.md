# Resume Playbook

The goal is to restart useful work within 15 minutes after any interruption without relying on chat history.

## Fifteen-Minute Resume

1. Read the top half of `PROJECT_STATUS.md` and the matching `project-status.json`.
2. Read only the pending decisions named there.
3. Run `python3 scripts/validate_contracts.py`.
4. Inspect the listed blockers and last changed files.
5. Start the single `next_action.first_step`; do not create a competing workstream.

If the human and machine checkpoints disagree, treat the older one as stale, reconstruct status from verified artifacts, and update both before implementation.

## End-of-Session Checklist

- record completed evidence, not estimated progress;
- update current gate/milestone and blockers in both status files;
- leave exactly one next action with a first step and acceptance evidence;
- record commands, exit codes, and concise outcomes;
- update `DECISIONS.md` when a choice changes architecture, data, cost, or scope;
- create the Workspace Codex review file;
- do not leave secrets, licensed payloads, or local absolute paths in public-facing artifacts.

## One-Work-in-Progress Rule

There may be one `in_progress` milestone. A second idea goes into a pending decision or future list; it does not become active work. A blocked milestone remains active until its documented fallback is taken or the blocker is resolved.

## Handoff Template

```text
Outcome reached:
Current gate/milestone:
Last passing command:
Artifacts proving the outcome:
Open blockers/decisions:
Single next action:
First command or file to open:
Do not start yet:
```

## Resumability Metric

At each gate, perform one cold resume using only repository files. Pass when the next correct action begins within 15 minutes and no chat transcript or unrecorded local knowledge is required. Record the date and elapsed time in the gate evidence.

