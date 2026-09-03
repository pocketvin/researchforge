# Phase 5 Product-Hardening Evidence

Status: **LOCAL ENGINEERING CHECKPOINT PASSED · PUBLIC CI PENDING**

This directory binds new Phase 5 UX evidence without rewriting the preserved Phase 4 n8n output
artifacts in `docs/evidence/v1.5-n8n/`.

The actual imported and published n8n 2.37.9 workflow passed:

- the unchanged webhook contract and five exact backend artifact comparisons for CATL 2024H1,
  CATL 2024FY and BYD 2024H1;
- a native form GET with Company, Period and Research Question;
- a successful native-form research result with conclusion, facts, calculations, supporting
  evidence, counter evidence/limitations, monitoring and backend Result/Trace links;
- an unsupported BYD 2024FY form request showing a bounded “研究未生成” state without an Executive
  Conclusion;
- five existing real HTTP failure checks, idempotent replay and minimum input.

[`n8n-form-runtime-summary.json`](n8n-form-runtime-summary.json) binds this checkpoint to the exact
generated workflow hash. It is automated engineering evidence, not a human session or usability
claim.

Actual screenshots:

- [Web start](../../assets/research-page-v1.5-final-start.png)
- [Web completed result](../../assets/research-page-v1.5-final-result.png)
- [n8n form](../../assets/n8n-form-v1.5.png)
- [n8n completed result](../../assets/n8n-result-v1.5.png)
- [n8n bounded abstention](../../assets/n8n-abstention-v1.5.png)

Local full gate passed with 197 Python tests, strict typing of 92 source files, four frontend unit
tests, three mocked and three live E2E journeys, fresh Docker builds, Docker/n8n smoke, ten n8n
Node groups, nine active V1.5 schemas and 11 validated PNGs. Public candidate CI is not yet
available; this status must not be upgraded until all GitHub Actions jobs pass.
