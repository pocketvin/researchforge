# Evolution and Patch Adoption Policy

Contract version: `1.3.0`

V1 implements one controlled, failure-driven skill-improvement cycle. It is not open-ended self-modification.

## 1. Eligible Failures

Only verifier-confirmed failures from valid Evolution runs may support a patch. Infrastructure errors, unavailable data, malformed benchmark packages, and LLM-judge-only opinions are ineligible.

A failure cluster is defined by both:

- a taxonomy label, such as `CRITICAL_OMISSION`; and
- a specific reusable signature, such as `cash_conversion_check_missing`.

Clustering by the broad label alone is prohibited.

## 2. Repetition Threshold

A cluster is eligible for Experience Distillation only when all are true:

```text
support_count >= max(3, ceil(0.20 × eligible_evolution_runs))
distinct_case_count >= 2
failure confirmed by deterministic or coverage verification
```

Multiple stochastic repeats of one case cannot by themselves establish reusable experience.

## 3. Experience Contract

An experience statement MUST include:

- failure signature;
- observed incorrect behavior;
- financial condition under which the rule applies;
- required check or procedure;
- exceptions/limitations;
- supporting failure IDs.

It MUST NOT include company-specific answers, Validation/Test labels, or a rule that simply names the benchmark cases.

## 4. Patch Boundary

The only allowed operations are `ADD`, `MODIFY`, and `REMOVE` in these fundamental-research sections:

- understand research question;
- financial snapshot;
- earnings quality;
- trend and driver analysis;
- evidence cross-check;
- research thesis.

A patch MUST NOT change:

- tools, data access, model, permissions, schemas, verifier, benchmark policy, or scoring;
- system-level safety instructions;
- Final Test packages;
- more than six operations or 6,000 changed characters.

Every patch is immutable, hash-addressed, linted for contradictory rules, and linked to at least three verified failures.

## 5. Paired Metrics

All metrics use paired Validation runs under identical runtime configurations.

### Repeat Error Rate

```text
Repeat Error Rate(skill)
= target-signature failures
  / eligible target opportunities
```

An eligible target opportunity is a Validation run whose verifier ground truth requires the behavior addressed by the patch.

### Repair Rate

```text
Repair Rate
= paired opportunities where Seed fails target and Candidate passes
  / paired opportunities where Seed fails target
```

If the denominator is zero, the patch is not evaluable and MUST NOT be adopted.

### Regression Rate

```text
Regression Rate
= non-target checks where Seed passes and Candidate fails
  / non-target checks where Seed passes
```

### Task Score

The V1 deterministic aggregate is:

```text
Task Score
= 0.30 × Calculation Accuracy
 + 0.25 × Citation Accuracy
 + 0.25 × Evidence Coverage
 + 0.20 × (1 - Critical Omission Rate)
```

Period correctness, schema validity, point-in-time validity, and tool execution are hard gates rather than compensable score components. LLM qualitative scores are diagnostic and are not included in the adoption score.

## 6. Adoption Rule

A Candidate is `ADOPTED` only when all conditions hold on the frozen Validation split:

1. target failure count is lower than Seed;
2. Repair Rate is at least `0.50`;
3. Candidate introduces no new calculation, period, point-in-time, schema, or citation-existence failure;
4. Candidate mean Task Score is no more than `0.02` below Seed;
5. Regression Rate is at most `0.05`;
6. static lint and rule-conflict checks pass;
7. the decision uses deterministic/coverage evidence, not an LLM judge alone.

Otherwise the Candidate is `REJECTED`. Thresholds are frozen before Validation is run and cannot be relaxed after seeing results.

## 7. Adoption and Rollback

- Adoption creates a new immutable skill version; it does not overwrite the Seed Skill.
- New runs atomically resolve one active skill version at queue time and keep it for the entire run.
- Rollback changes the active version pointer and records the reason; history remains intact.
- Candidate content is frozen before Validation. Final Test is run once only when Validation produces `ADOPTED`; a Validation-rejected Candidate never consumes Final Test.
- Final Test cannot be used to tune the same V1.3 candidate.
- A catastrophic new deterministic failure found on Final Test triggers operational rollback and an honest failed-generalization report, not test-set tuning.

If no Evolution cluster reaches the pre-registered minimum support, record `NO_ELIGIBLE_CLUSTER`, generate no Candidate, and leave Validation/Final Test sealed. This is a valid completed experimental outcome but not evidence of self-improvement.

## 8. Human Control

V1 MAY require an explicit project-owner confirmation before activating an adopted skill in Product mode. The experiment result remains determined by the frozen rule above. Human review cannot convert a failed Candidate into an adopted experimental result.
