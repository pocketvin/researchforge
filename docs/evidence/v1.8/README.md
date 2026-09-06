# V1.8 Agent Engineering Evidence

This directory freezes engineering evidence for the V1.8.5 hardening layer. It does not replace the preserved V1.7 Research Result contract or the historical V1.4/V1.5 experiments.

## Frozen evidence

- `agent-eval-offline.json` — zero-provider-call Router/Retrieval component evaluation over the frozen V1.8 suite.
- `owner-thread-eval.json` — three persisted 贵州茅台 model runs evaluated for routing, plan completion, grounding, citation validity and ten-stage trajectory completion.
- `failure-model-schema.json` — a real historical `OUTPUT_SCHEMA_INVALID` failure classified as `MODEL_SCHEMA_FAILURE` and marked as a regression candidate.
- `mcp-live-smoke.json` — read-only MCP smoke over the Owner backend: company resolution, CNINFO discovery, six facts, evidence search, persisted model result and ten-stage Trace.

## Retrieval decision

The frozen eight-case suite measured:

| Strategy | Recall@10 | Precision@5 | MRR |
|---|---:|---:|---:|
| Production lexical | 0.8125 | 0.4583 | 0.75 |
| TF-IDF sparse vector | 0.8542 | 0.5417 | 1.00 |
| Lexical + TF-IDF RRF | 0.8750 | 0.3750 | 1.00 |

The result is intentionally not interpreted as permission to introduce pgvector or dense embeddings. TF-IDF is promising on this small reviewed suite; RRF improves recall while reducing precision. The production retriever remains unchanged until a broader frozen suite demonstrates a material, stable gain.

## Run-level evidence

The three-run persisted thread keeps one company context and three different research questions. Each successful run scored 1.0 for intent routing, plan completion, grounded claims, citation validity, structured output validity and ten-stage trajectory completion.

`semantic_consistency_scored` remains `false`: V1.8.5 does not pretend that deterministic structural checks prove prose-level contradiction freedom.

## Reproduce

```bash
uv run researchforge eval
uv run researchforge eval --api-base http://127.0.0.1:8000 --run-id <RUN_ID>
uv run researchforge failure-analyze <FAILED_RUN_ID> --api-base http://127.0.0.1:8000
uv run python scripts/mcp_smoke.py --api-base http://127.0.0.1:8000 --run-id <RUN_ID> --include-discovery
```
