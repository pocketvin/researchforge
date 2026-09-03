# Final Dual-Surface Facilitator Guide

Status: **FROZEN · PREPARATION ONLY**

## Before each session

1. Verify the candidate commit, green CI and local smoke evidence recorded for Phase 5.
2. Start the deterministic product stack and published n8n workflow; do not expose fixture or
   Benchmark namespaces.
3. Confirm Web, n8n form and `/v1/catalog` are reachable. Do not pre-open a completed report.
4. Preallocate Group A or B and copy the `TEMPLATE_ONLY` record into the ignored session directory.
5. Present the privacy notice and obtain consent. If consent is absent, stop and retain no session
   content.

## Neutral facilitation

Read the participant sheet verbatim. You may repeat the task or explain that a browser is local.
Do not name a button, section, page, formula, answer or expected caveat. If help is requested, first
record the current item as `assisted`, then provide the minimum help needed and quote the help in
`facilitator_assistance.notes`.

Record behavior, not inferred intent. A correct statement after a leading question is assisted.
An unattempted second surface after the study started remains `not_attempted` in the denominator.

## n8n failure exercise

After the successful n8n task, ask for BYD + `2024FY` with the same question. The expected product
behavior is a bounded refusal, but do not tell the participant that. Pass
`failure_path_comprehension` only if they explain that the pair is unsupported and no report or
financial answer was created.

## Record and privacy handling

- Validate each JSON record against
  `schemas/v1.5/final-human-evaluation-session.schema.json`.
- Use pseudonyms only. Never store names, emails, employers, contact information or raw recordings
  in the repository.
- Keep session records under ignored `artifacts/usability/real-human/` unless the participant
  separately permits a privacy-safe aggregate public summary.
- If the participant withdraws, follow their deletion request and retain only non-identifying
  aggregate withdrawal/attempt counts needed for honest denominator reporting.
- Never copy API keys, `.env`, n8n owner credentials or unrelated browser data into evidence.

## After all sessions

Calculate the frozen rates exactly as written in the final evaluation contract. Keep failed,
assisted, abandoned and eligible withdrawn attempts visible. Publish a result only after checking
every denominator; use `HUMAN_VALIDATED` only if all rules pass. Otherwise report the failed or
inconclusive outcome without changing thresholds.
