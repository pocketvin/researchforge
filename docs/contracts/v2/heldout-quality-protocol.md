# V2 Held-out Financial Quality Acceptance Protocol

Status: **acceptance-v2 tooling implemented; no held-out acceptance suite has been sealed yet**.

A `held_out` label is not enough. ResearchForge treats held-out as an operational discipline: unseen
runtime inputs are frozen before product execution, the implementation is frozen before the first
run, and human input is limited to a final blind choice. Humans do not prepare reference answers,
mark evidence, reconcile financial facts, or write evaluator rubrics.

## 1. Private inputs and minimum coverage

The private bundle is outside Git and contains only:

- `runtime-cases.jsonl`: question, issuer, cutoff and frozen source-document metadata;
- `sources/`: frozen source files addressed by SHA-256;
- `bundle-manifest.json`: suite identity, case order and the frozen human review mode;
- `development-exposures.json`: private pre-run snapshot of already exposed issuer aliases, exact
  normalized-question hashes, development case IDs and the hashes of their source registries.

There is no required `reference-cases.jsonl` and no required review-attestation file. Git receives
only `HeldOutSuiteSeal`: hashes, counts, review mode, stratum counts and opaque case/company hashes.
No held-out question, answer, issuer name or source bytes are copied into the tracked seal.

Acceptance-v2 uses at least **8 cases, 4 issuer groups and 4 task strata**. This intentionally keeps
manual review small: a complete acceptance suite requires at most eight human choices. Issuers must
be disjoint from the versioned ResearchForge development-issuer exclusion manifest, which covers the
entire 32-issuer public FinanceBench universe rather than only cases actually executed. The seal also
rejects any exact normalized question already present in the frozen development-exposure snapshot. A
useful initial stratum set is direct extraction, deterministic multi-step numerical analysis,
filing-grounded analytical explanation, and evidence-limited/cannot-determine research.

## 2. Automatic preparation and checks

Questions and case metadata may be generated or selected automatically before freeze. Before the
seal is written, `seal_v2_heldout_suite.py` freezes the development-exposure snapshot from the tracked
issuer exclusions, public development suite, complete locally cached FinanceBench public source when
present, and persisted V2 run requests. The seal then verifies source bytes, runtime identity, issuer
and exact-question disjointness, and minimum coverage. Product and evaluator code may automatically
compute source identity, deterministic numeric checks, citation validity, evidence observation,
trajectory completion, tool/provenance integrity and other metrics that do not require subjective
human judgment.

Humans must not be asked to duplicate those checks. In particular, no person is required to author a
gold answer, locate every supporting page, verify every number, enumerate counter-evidence, or write a
reference rationale before the suite can be sealed.

## 3. Blind product execution

Product execution reads only the frozen runtime cases and source bytes. The formal V2 runner builds
the normal page/table/chunk/fact environment directly from those bytes and does not rediscover or
redownload the filing after seal creation. Source hashes and publication cutoffs are checked again at
execution. The implementation/model/tool/formula configuration is frozen before the first product
Run and bound to the acceptance attempt. Infrastructure failures may be retried only when retained as
explicit technical failures before any valid product result exists; a valid low-quality or partial
acceptance result remains part of the evidence and prevents an unseen retry.

The suite freezes exactly one human review mode before execution:

- `pairwise_preference`: run two candidates on the same frozen case, randomize which one is shown as
  A/B, and ask only which result is better;
- `meets_standard`: show one candidate result and ask only whether it meets the acceptance bar.

The reviewer-facing card may include the question, rendered answer and automatically linked source
material/citations. It must not expose implementation identity before the pairwise choice. The
current formal automatic runner supports `meets_standard`. Pairwise remains fail-closed until both
candidates have a same-frozen-corpus adapter; the synthetic A/B renderer alone is not evidence that a
V1/V2 comparison is fair.

## 4. Minimal human review

Human review is deliberately choice-only.

For `pairwise_preference`, the allowed answers are:

- `A better`
- `B better`
- `Tie`
- `Neither`

For `meets_standard`, the allowed answers are:

- `Meets standard`
- `Does not meet standard`
- `Cannot judge`

No written explanation, corrected answer, evidence annotation, source reconciliation, confidence
score or reviewer attestation is required. The machine-readable `HeldOutHumanJudgment` contract has
no comment/rationale field. One sealed case consumes one human choice.

The default delivery surface is a private offline page. For a formal current-V2 acceptance,
`scripts/run_v2_heldout_acceptance.py` verifies the seal, arms the single-use ledger, executes every
case from frozen source bytes and writes `review.html`. `scripts/build_v2_heldout_review.py` remains
available for already-finished candidate Runs. The page normalizes candidate output and omits
model/provider/version/Trace identity. The final click automatically downloads one
`HumanJudgmentFile`; `scripts/summarize_v2_heldout_review.py --attempt-ledger ...` validates it,
aggregates the choices and marks the acceptance attempt completed. Humans do not edit JSON or run a
scoring script.

## 5. Single-use acceptance semantics

A sealed suite is intended for one declared acceptance pass. Before execution, an ignored acceptance
ledger binds the seal to the exact implementation fingerprint. The only retry permitted on the same
seal is an explicitly recorded infrastructure `technical_failure` using the identical implementation
hash.

Once acceptance results are inspected and used to change prompts, tools, formulas, retrieval, stop
policy, report policy or model routing, that seal is retired from held-out status and becomes
regression/development evidence. A later held-out acceptance requires a new disjoint seal. The old
result is preserved and is never silently overwritten by a post-fix rerun.

## 6. Interpretation

Automatic metrics and model Judges may be reported, but uncalibrated model-Judge output is advisory.
The human choice is the final subjective acceptance signal because it directly measures the output
that a user sees instead of asking a human to manufacture hidden ground truth.

With the deliberately small eight-case owner suite, reporting must stay literal. Examples of allowed
claims are “V2 was preferred on 6/8 blind comparisons” or “7/8 outputs met the owner acceptance bar.”
The suite is not large enough by itself to support a broad statistical claim of universal financial
research superiority.

## 7. Current status

No V2 held-out seal currently exists. The tracked FinanceBench 10-case suite remains public
**development/canary** evidence and is ineligible for a V2-superiority claim.
