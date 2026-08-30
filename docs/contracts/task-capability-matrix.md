# Task Capability Matrix

Contract version: `1.4.0`

V1 supports an allowlisted universe of companies for which normalized financial facts and official filing evidence have been prepared. “Supported” does not mean full A-share coverage.

## Global Input Contract

Every request MUST resolve to:

- one of five `task_type` values;
- one company, or exactly two for peer comparison;
- at least one reporting period;
- a `research_time` and evidence cutoff;
- an answerable research question;
- an immutable skill and formula version.

Ambiguous ticker/company mappings require clarification or refusal. The system MUST NOT silently choose a similarly named security.

## Capability Matrix

| Task | Minimum data | Mandatory procedure | Required result emphasis | Degrade/refuse when |
|---|---|---|---|---|
| Company Research | One company; normally four comparable quarters; core facts and filings | Trend, earnings quality, working capital, CapEx, debt/cash, support and counter-evidence search | Current fundamentals, key changes, drivers, risks, outlook/monitoring | Fewer than two comparable periods or no authoritative filing evidence |
| Filing Analysis | One filing plus compatible comparison periods | Detect changes, calculate comparisons, retrieve management explanation, test alternative explanations | Three or more material changes when supported; otherwise fewer with explicit limitation | Filing cannot be parsed reliably or comparison period is incompatible |
| Peer Comparison | Exactly two companies; aligned periods and framework | Apply the same metric/check list to both companies; identify missing comparability | Comparison table, relative strengths, relative risks, conclusion with limitations | Period, currency, accounting scope, or metric mapping cannot be aligned |
| Thesis Investigation | One explicit falsifiable thesis; relevant facts and filings | State variables, collect support, search counter evidence, consider alternatives | Supported/rejected/mixed/insufficient conclusion and confidence | Thesis is price prediction, investment advice, unfalsifiable, or unsupported by available V1 data |
| Risk Detection | One company and at least two comparable periods | Run frozen anomaly checks and investigate every triggered signal | Risk, evidence, severity, possible explanation, next monitoring item | Required signals cannot be evaluated and no safe partial conclusion is possible |

## Mandatory Earnings-Quality Checks

Whenever a report makes a material statement about profit quality, it MUST record checks for:

1. operating cash flow;
2. accounts receivable;
3. inventory;
4. profit/cash divergence;
5. cash conversion when meaningful;
6. one-off contribution when data is available;
7. counter-evidence search.

`unavailable` is a valid check status only with a reason and resulting limitation. Omitting the check is not equivalent to unavailable data.

## Output Contract

The canonical response is `research-result.schema.json`. The UI renders that object; prose is not the source of truth.

Material claims MUST:

- reference financial fact IDs or evidence chunk IDs;
- distinguish verified fact, supported inference, causal hypothesis, uncertainty, and limitation;
- record counter-evidence search;
- include alternatives when a causal/driver explanation is asserted;
- carry confidence with an evidence-based rationale.

The Sources section MUST resolve each cited evidence ID to document, publication time, page/section, and URI.

## Degradation Behavior

The run terminates as `insufficient_data` rather than filling gaps from model memory when:

- authoritative facts are missing or incompatible;
- filing publication time exceeds the research cutoff;
- PDF parsing is too unreliable for the relevant claim;
- a peer comparison cannot be normalized;
- source licensing prevents the evidence from being used.

An `insufficient_data` run persists its structured failure and Workflow Trace but no Research Result. A partial report MAY instead complete only when its supported checks remain useful and unambiguous; it is a normal `completed` Research Result with explicit limitations, never an `insufficient_data` result artifact.

## Product Acceptance Cases

Before G1 can pass, each mode MUST have at least one frozen golden case that demonstrates:

- correct company and reporting-period resolution;
- deterministic calculations;
- evidence-linked material claims;
- counter-evidence search without fabrication;
- graceful handling of one missing-data condition;
- schema-valid output.

Peer Comparison additionally requires the same framework and period alignment for both companies. Thesis Investigation additionally requires a mixed or insufficient outcome fixture so the system is not rewarded only for confirming the prompt.
