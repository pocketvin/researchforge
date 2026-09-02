# G4 Simulated Usability Evidence

Evidence date: `2026-09-02`

Status: `PASS_SIMULATED_ONLY`

This evidence is produced by AI simulations. It is not a human user study, does not validate
market demand, and does not establish investment usefulness.

## Isolation and Budget

- Exactly three sessions per batch
- Each session used a fresh model context
- Prior session outputs were not supplied to later sessions
- Responses API used Structured Outputs, `store: false`, and no built-in tools
- Model: `gpt-5.6-luna`, medium reasoning
- Evidence label: `SIMULATED`
- `human_user_value_validated: false`
- Aggregate project OpenAI spend after completion: USD `0.1523062` of USD `20.00`

## Iteration Evidence

Batch `simulated_usability_v1_4_001` returned `FAIL`: all three sessions found the conclusion,
supporting facts, and limitations, but none found an explicit monitoring item. The sessions also
identified empty Claim-to-Evidence IDs and insufficiently visible formula provenance.

The product was corrected without changing experiment data or scoring thresholds:

- material claims now bind persisted Evidence Chunk IDs, hashes, source locators, and excerpts;
- Research Result now contains actionable monitoring items, triggers, and review timing;
- deterministic Calculation Records are available through the API and rendered in the UI;
- the Verifier resolves evidence citations instead of requiring them to be empty.

Batch `simulated_usability_v1_4_002` returned `PASS`:

- 3/3 sessions located the key result;
- 3/3 located supporting evidence;
- 3/3 located a counter-evidence item or limitation;
- 3/3 located a monitoring item;
- 2/3 met both high-score thresholds (`usefulness >= 4`, `auditability >= 4`).

The remaining dissent is retained: the public evidence is a synthetic normalized summary rather
than verbatim filing text, historical comparison is limited for a single-period run, and real
users have not validated the workflow.

## Visual Evidence

- [`../assets/research-page.png`](../assets/research-page.png)
- [`../assets/skill-lab-page.png`](../assets/skill-lab-page.png)
- [`../assets/researchforge-v1.4-final-demo.mp4`](../assets/researchforge-v1.4-final-demo.mp4)
