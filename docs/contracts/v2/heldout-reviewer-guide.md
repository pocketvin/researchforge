# V2 Held-out Blind Reviewer Guide

This guide defines the only human action required by the V2 held-out acceptance protocol. It is not a
product prompt and must not be placed in the Research Agent context.

## What the reviewer does

The system generates one private offline `review.html`. Each case fits on one review card. Read the
question and the displayed answer(s), then make exactly one choice. The normal review page does not
show model/provider/version identity, Run IDs, token usage or Trace. Automated provenance/citation
checks run separately, so the human does not need to audit them.

For a blind A/B comparison choose one:

- **A better**
- **B better**
- **Tie**
- **Neither**

For a single-result acceptance choose one:

- **Meets standard**
- **Does not meet standard**
- **Cannot judge**

That is the complete required human task.

## What the reviewer does not do

Do not prepare a gold answer. Do not search the filing for every number. Do not label evidence IDs,
write a rubric, enumerate counter-evidence, correct the system answer, explain the decision, assign a
confidence score, or fill in reviewer-attestation metadata. Those jobs belong to deterministic checks,
automated evaluation and the acceptance runtime.

For pairwise review, implementation identity must stay hidden until after the choice is recorded. The
system owns A/B randomization and later resolves the selected candidate back to its actual Run.

## Review scale

Acceptance-v2 targets 8 cases across at least 4 issuer groups and 4 task strata. A complete owner
acceptance therefore requires at most eight choices. `Cannot judge` is a valid answer when the card
does not provide enough information; it is better than forcing a guess.

## After review

The last choice automatically downloads one judgment JSON file. No manual editing is required.
`scripts/summarize_v2_heldout_review.py` validates all choices against the frozen seal, restores any
hidden A/B candidate identity, aggregates the choices and completes the single-use acceptance ledger.
The current formal automatic runner uses the single-result `meets_standard` mode; pairwise remains
locked until both candidates can consume the identical frozen corpus. If a result is used to tune
product behavior, the suite is retired from held-out status and must not be rerun as if it were still
unseen.
