# ResearchForge V1.5 Product Demo Script

Status: **IMPLEMENTED REAL-DATA SLICE · HUMAN USEFULNESS UNVALIDATED**
Length: 3–5 minutes

## 1. The trust problem — 30 seconds

“A normal financial chatbot can give a fluent answer, but I cannot easily verify which filing it
used, how it calculated the number, whether it found conflicting evidence, or what should change
my mind. ResearchForge turns that black box into an inspectable research workspace.”

## 2. Start a real research run — 20 seconds

Select:

```text
宁德时代 / 2024H1
2024 年上半年利润是否真正转化成了经营现金流？
```

Choose **Start Research**. State the exact boundary: this release supports one reviewed real
filing and does not claim full-market coverage.

## 3. Executive Conclusion and Key Findings — 40 seconds

Show the direct answer first: operating cash flow was CNY 44.709 billion, net income was CNY
22.865 billion and deterministic cash conversion was 1.96x. Explain that the model may word the
answer, but it never owns those values or the ratio.

## 4. Audit one number and one claim — 90 seconds

Expand, in order:

1. Financial Facts: net income on physical PDF page 70 and operating cash flow on page 73.
2. Calculations: `cash_conversion = operating_cash_flow / net_income`, full precision
   `1.955345691552841179348299138`, displayed as `1.96x`.
3. Supporting Evidence: open the page-located official-source excerpts.
4. Source identity: show the official URL and PDF SHA-256
   `2a690cb2471c1f0d4539d909a9f068c03710a838ddd35313175790169e85eab1`.
5. Key Finding: show its two fact IDs and two evidence IDs.

Explain that the LLM interprets supplied artifacts; deterministic Python owns the formula and the
Evidence System owns provenance.

## 5. Challenge the conclusion — 40 seconds

Show both filing-based counter signals: the report includes adjusted profit excluding
non-recurring items, and the interim financial report is unaudited. Then show the limitation that
one half-year cannot establish long-run earnings quality.

## 6. Monitoring Plan — 25 seconds

Show the next comparable filing review: recheck operating cash flow, net income, receivables and
inventory. The current weakening trigger is negative operating cash flow or cash conversion below
1.00x.

## 7. Research Trace — 35 seconds

Expand the ten-stage LangGraph trace. Explain that LangGraph owns bounded orchestration,
checkpoint/recovery and sanitized events. Finance, evidence, verification and persistence remain
ordinary testable Python.

## Optional: Quality Lab — 30 seconds

Only if the interviewer asks about experimentation, open **Quality Lab** and state:

- it is experimental, read-only and not required for normal research;
- two formal experiments ended at `NO_ELIGIBLE_CLUSTER`;
- `RESEARCH_HYPOTHESIS_UNSUPPORTED_AFTER_TWO_EXPERIMENTS` is frozen;
- no third experiment is authorized.

## Required closing boundary

- Coverage is CATL `2024H1`, not the full A-share market.
- ResearchForge is research assistance, not investment advice.
- The pilot kit is ready, but zero real-human sessions exist and usefulness is unvalidated.
- Historical AI usability sessions remain `SIMULATED` quality evidence only.
