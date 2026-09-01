# G3 Controlled Experiment Engine Evidence

Evidence date: `2026-09-01`

Status: `ENGINE_READY_LIVE_RUN_BLOCKED`

## Implemented controls

- One controlled CLI can preflight, start, and idempotently resume the primary experiment.
- The plan is frozen at three repeats per case and condition: 72 Evolution runs,
  36 Validation runs, and 36 Final Test runs only after Validation adoption.
- Every research run uses the same ten-stage LangGraph and independent deterministic
  Verifier. Evolution policy, clustering, Experience distillation, patch lint, paired
  metrics, adoption, and Final Test decisions remain ordinary Python.
- Base uses no fundamental-research procedure; Seed uses immutable version `1.0.0`;
  Candidate is created only from an eligible exact-signature Seed failure cluster.
- Structured `reported_check_codes` makes missing required coverage observable without
  allowing the model to calculate financial values or see verifier ground truth.
- Final Test truth cannot be opened before Validation adoption. A durable unseal marker
  binds first access to one package hash and Candidate hash.
- The budget ledger persists reservations before provider contact. The conservative bound
  is USD `0.0064` per request and USD `1.8432` for 288 requests including one repair per
  run, below the USD 9 primary allocation and USD 20 aggregate cap.
- A previously exposed key cannot be used accidentally: live execution additionally
  requires local `RESEARCHFORGE_ROTATED_KEY_CONFIRMED=1`.
- Before any Benchmark request, exactly one synthetic calibration must pass with the
  frozen model/configuration, Structured Output schema, all seven required check codes,
  usage evidence, and the same aggregate ledger. It is never research evidence.

## Local verification

```text
uv run pytest -q tests/application/test_calibration.py tests/application/test_formal_experiment.py
6 passed

Synthetic full-path denominator:
144 runs = 72 Evolution + 36 Validation + 36 Final Test
144 schema-valid evaluations
OpenAI calls: 0
OpenAI spend: USD 0
```

The full-path test uses a deterministic `SYNTHETIC TEST DOUBLE` that intentionally gives
Seed one repeated cash-conversion omission and Candidate a repaired output. Its temporary
`SUPPORTED` result proves plumbing and Schema compatibility only. It is never written to
the committed evidence package and is not research-hypothesis evidence.

The real zero-network preflight reports:

```text
status: BLOCKED
provider_contacted: false
package_hash: 3638eb1ca7b8192cb6a901f4b0d51c8373ccaff1e776758605f1d4b975cb1c3f
case_count: 24
private_ground_truth_hash_count: 24
budget.experiment_worst_case: USD 1.8432
```

Calibration preflight separately reports `provider_contacted: false`, the immutable
synthetic context hash, USD `0.0064` worst case, and blocks without constructing an
OpenAI client until a rotated local credential is confirmed. A successful calibration
artifact is a mandatory input to the formal preflight.

The disjoint V1.5 contingency package is now sealed and verified before the first primary
call. Current blockers are the pending second owner signoff, missing rotated-key
confirmation, and the consequently unrun calibration. No provider request or Final Test
access has occurred.
