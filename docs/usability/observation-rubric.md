# Real Human Pilot Observation Rubric

## Contract outcomes

Record each item as true only when completed without directional help:

| Field | Observable success |
|---|---|
| `selected_company` | Selects 宁德时代 and `2024H1` |
| `submitted_question` | Starts the supplied research question |
| `understood_conclusion` | Accurately paraphrases whether cash conversion was supported |
| `found_supporting_evidence` | Opens an official-source citation and identifies its page |
| `found_limitation_or_counter_evidence` | Identifies the unaudited-report or non-recurring-profit caveat |
| `identified_monitoring_item` | States one next-filing measure or trigger to revisit |

Opening the deterministic calculation is observed as a diagnostic task and recorded in feedback;
the six schema fields remain stable for cross-session comparison.

## Acceptance rule

`V1.5 Human Validated` requires at least three completed real-human sessions on the same stable
product slice. Every counted participant must independently complete the two trust-critical tasks:
finding supporting evidence and finding a limitation/counter-evidence item. Across counted
sessions, at least 90% of all six binary outcomes must be true, and every participant must identify
a monitoring item. Withdrawn, simulated or technically invalid sessions do not enter the
denominator.

This threshold is defined before any real session. Failure is reported as failure and may inform a
later version; it does not change the V1.4 research evidence.
