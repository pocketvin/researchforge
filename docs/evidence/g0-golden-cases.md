# G0 Earnings-Quality Golden Cases

Evidence date: `2026-08-31`
Status: `OWNER_SIGNED`
Machine fixture: [`data/fixtures/g0/golden-cases.json`](../../data/fixtures/g0/golden-cases.json)

These three cases test deterministic financial semantics only. No language model produced or checked the arithmetic, and no result is investment advice.

## Case 1 — CATL 2024Q1 Earnings Quality

Research time: `2024-04-17T00:00:00+08:00`

| Calculation | Exact deterministic result |
|---|---:|
| Gross profit | CNY 21,071,872,300.00 |
| Gross margin | 26.4155279287% |
| Cash conversion (OCF / attributable net income) | 2.6982034084 |
| Frozen profit/cash divergence signal | 0 |

Expected interpretation: attributable profit and operating cash flow are both positive, with operating cash flow above attributable profit for this YTD period. This does not establish why conversion was strong.

## Case 2 — EVE Energy 2024Q1 Earnings Quality

Research time: `2024-04-26T00:00:00+08:00`

| Calculation | Exact deterministic result |
|---|---:|
| Gross profit | CNY 1,643,410,957.15 |
| Gross margin | 17.6382341512% |
| Cash conversion | -1.6433869271 |
| Frozen profit/cash divergence signal | 1 |

Expected interpretation: attributable net income is positive while operating cash flow is negative. The system must surface this as an investigation signal and must not invent a causal explanation.

## Case 3 — CATL versus EVE Energy 2024H1

Research time: `2024-09-04T00:00:00+08:00`

| Company | Gross profit | Gross margin | Cash conversion | Divergence |
|---|---:|---:|---:|---:|
| CATL | CNY 44,248,984,800.00 | 26.5334442376% | 1.9553456916 | 0 |
| EVE Energy, corrected filing | CNY 3,563,713,901.71 | 16.4534296149% | 0.1459270718 | 0 |

Expected interpretation: both sides use the same H1 YTD framework, CAS, CNY and consolidated scope. EVE uses the corrected filing available by the research time. A peer comparison may use each company's latest authoritative lineage; a same-company derivation or time comparison still rejects mixed restatement lineages.

## Acceptance Notes

- Production formulas recompute all stored values exactly with `Decimal`.
- Every input fact resolves to a schema-valid Financial Fact and an official Source Document.
- Point-in-time cutoffs pass for all three cases.
- Important figures come only from frozen facts and deterministic calculations; the future model may interpret these artifacts but may not replace the arithmetic.
- The cases do not include management explanations or counter-evidence; those enter at the G1 thin slice.
