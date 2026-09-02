# ResearchForge Contract Catalog

V1.5 productization contracts are now active. The V1.4 catalog below remains the immutable
engineering and research baseline for existing artifacts.

- [V1.5 productization contracts](v1.5/README.md)
- [V1.5 product thesis](../product/researchforge-v1.5-product-thesis.md)

The remainder of this document records the preserved V1.4 contract package.

## Normative Language

- **MUST / MUST NOT**: required for V1.4 acceptance.
- **SHOULD / SHOULD NOT**: default behavior; deviations require a recorded reason.
- **MAY**: optional and non-blocking.

## Contract Documents

| Contract | Governs |
|---|---|
| [`financial-methodology.md`](financial-methodology.md) | Financial periods, normalization, formulas, missing data, restatements, peer alignment |
| [`task-capability-matrix.md`](task-capability-matrix.md) | Inputs, mandatory checks, outputs, degradation, and acceptance for five task modes |
| [`benchmark-protocol.md`](benchmark-protocol.md) | Dataset packaging, split isolation, repeated runs, leakage prevention, and reproducibility |
| [`evolution-adoption-policy.md`](evolution-adoption-policy.md) | Failure clustering, patch constraints, evaluation formulas, adoption, rejection, and rollback |
| [`run-lifecycle.md`](run-lifecycle.md) | Run states, timeouts, retries, idempotency, trace retention, and failure behavior |
| [`research-workflow.md`](research-workflow.md) | Bounded single-agent LangGraph stages, state, routing, and framework boundaries |
| [`data-source-acceptance.md`](data-source-acceptance.md) | Provider licensing, provenance, period semantics, reconciliation, and fallback |
| [`product-success-metrics.md`](product-success-metrics.md) | Correctness, reliability, user usefulness, and fair baseline evidence |
| [`development-gates.md`](development-gates.md) | Evidence required to exit each implementation gate |

## Machine-Readable Schemas

All current schemas use JSON Schema Draft 2020-12 and live under `schemas/v1.4/`.

| Schema | Persisted artifact |
|---|---|
| `common.schema.json` | Shared identifiers, company, period, source, hash, and version definitions |
| `financial-fact.schema.json` | Normalized reported or deterministically derived financial fact |
| `evidence-chunk.schema.json` | Point-in-time filing evidence with stable source locator |
| `claim.schema.json` | Auditable research claim and its support/counter-evidence search |
| `research-result.schema.json` | Structured result rendered into the Research report |
| `run-manifest.schema.json` | Reproducible run configuration, lifecycle, and usage record |
| `workflow-trace.schema.json` | Sanitized LangGraph stage events, versions, artifacts, terminal state, and usage |
| `source-document.schema.json` | Source identity, reporting period, publication time, hash, license, and public-package boundary |
| `calculation-record.schema.json` | Deterministic formula inputs, outcome, value, and explanation |
| `tool-record.schema.json` | Sanitized tool/adapter call audit record |
| `skill-version.schema.json` | Immutable Seed, Candidate, active, rejected, or rolled-back skill version |
| `experience.schema.json` | Reusable procedure distilled from eligible verified failures |
| `evolution-experiment.schema.json` | Pre-registration, split isolation, budget, run/evaluation links, and terminal outcome |
| `retrieval-evaluation.schema.json` | Deterministic-versus-semantic retrieval adoption evidence |
| `simulated-usability-evaluation.schema.json` | Explicitly simulated usability evidence that cannot represent a human pilot |
| `skill-patch.schema.json` | Constrained proposed/adopted/rejected research-procedure patch |
| `benchmark-case.schema.json` | Frozen case package manifest and split classification |
| `evaluation-result.schema.json` | Verifier checks, failures, metrics, and version provenance |
| `project-checkpoint.schema.json` | Current gate, verified commands, blockers, decisions, and resumption handoff |

## Global Invariants

1. **Immutable provenance:** facts and evidence are content-addressed or hash-verified; corrections create new records.
2. **Point-in-time safety:** evidence `published_at` MUST be at or before the case `research_time`.
3. **No unsupported conclusion:** a material claim MUST have supporting fact/evidence IDs unless it is explicitly a limitation.
4. **No fabricated opposition:** counter-evidence search is recorded even when no credible counter evidence is found.
5. **Reproducibility:** every run records model, parameters, skill hash, prompt hashes, tool versions, formula version, dataset package hash, and evidence cutoff.
6. **Experiment isolation:** the Optimizer cannot read Validation or Final Test ground truth; the Researcher cannot read any verifier ground truth.
7. **Version pinning:** an in-flight run uses one immutable skill version and one formula version.
8. **No hidden reasoning storage:** traces contain explicit, user-auditable artifacts rather than private chain-of-thought.
9. **Framework containment:** LangGraph owns orchestration and lifecycle routing only; financial and experimental meaning remains in deterministic services and contracts.
10. **Evidence-backed engineering usefulness:** product claims use recorded correctness, reliability, cost/latency, and labeled simulations rather than demo fluency; human value remains unvalidated.
11. **Recoverability:** every stopped work session leaves one schema-valid checkpoint and one next action.

## Versioning

- Active productization contract package version is `1.5.0`.
- The preserved V1.4 artifact contract package remains `1.4.0`.
- V1.2 and V1.3 schemas remain read-only historical contracts; new artifacts use `schemas/v1.4/`.
- Backward-compatible clarifications increment the patch component.
- A new required field, changed financial meaning, changed metric denominator, or changed split policy requires a new minor contract version.
- The V1.4 scope baseline is changed only through an explicit decision and change note.

## Validation

Run from the project root:

```bash
python3 scripts/validate_contracts.py
```

Validation success proves that the contract package is internally well-formed. It does not prove that future application behavior satisfies the contracts.
