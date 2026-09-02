# G3 Contingency Formal Experiment Result

Evidence date: `2026-09-02`

Status: `COMPLETED_NEGATIVE_STOPPING_RULE_APPLIED`

After the unsupported primary result was frozen, the once-only V1.5 contingency experiment
ran on a company-disjoint package prepared before the primary experiment.

## Activation and Integrity

- Experiment: `experiment_contingency_v1_5_001`
- Activation count: 1
- Frozen protocol deviation recorded: `FROZEN_ACTIVATION_PREDICATE_TOO_NARROW`
- Data, labels, thresholds, graph, verifier, and model changed after observing primary: no
- Formal denominator: 72 succeeded Evolution evaluations
- Zero-provider-token technical failures retained outside the denominator: 2
- Retry policy: one retry only for a zero-token technical failure

## Result

- Base: 36 evaluations; 10 evaluations contained 14 failure events
- Seed: 36 evaluations; no failure events
- Outcome: `NO_ELIGIBLE_CLUSTER`
- Candidate created: no
- Validation opened: no
- Final Test consumed: no
- OpenAI spend: USD `0.0646992`
- Immutable result hash: `dadd29917979b53a2b47ed66e7bfa9deae6ba8486802acc12bdba38ab3a3877f`

## Terminal Research Outcome

`RESEARCH_HYPOTHESIS_UNSUPPORTED_AFTER_TWO_EXPERIMENTS`

The two-experiment stopping rule is applied and no further formal experiment is authorized.
Engineering delivery may complete, but ResearchForge must not claim an adopted Candidate,
sealed-test improvement, `SUPPORTED`, or a self-evolving agent. The immutable combined outcome
hash is `bdc0c1aed55e930312f01ecaebee8969e96e7ff625b27b735b940fcff8a1d2af`.
