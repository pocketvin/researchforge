# Financial Methodology Contract

Contract version: `1.4.0`

This contract defines the financial meanings used by ingestion, deterministic tools, the Researcher, and the Verifier. A component MUST NOT invent its own formula or reporting-period interpretation.

## 1. Canonical Fact Rules

Every financial fact MUST preserve:

- company identity and exchange;
- reporting period start/end and fiscal label;
- `period_basis`: `instant`, `discrete`, `ytd`, or `ttm`;
- accounting standard and statement scope;
- as-reported/restated status;
- publication time and retrieval time;
- source document and stable page/section/table locator;
- base-unit value, measurement unit, currency, and sign convention;
- reported/derived status and source fact IDs for derived values.

Persisted currency values use base units (`canonical_scale = 1`). Millions/billions formatting belongs to the UI.

## 2. Core Metric Dictionary

| `metric_code` | Meaning | Normal basis | Sign rule |
|---|---|---|---|
| `revenue` | Consolidated operating revenue | discrete/YTD | natural statement value |
| `operating_cost` | Consolidated operating cost under the same scope as revenue | discrete/YTD | natural statement value |
| `net_income` | Net income attributable to the comparison scope selected for the case | discrete/YTD | natural statement value |
| `gross_profit` | Revenue minus cost of revenue under the same scope | discrete/YTD | natural statement value |
| `gross_margin` | `gross_profit / revenue` | discrete/YTD | positive ratio |
| `operating_cash_flow` | Net cash generated from operating activities | discrete/YTD | natural statement value |
| `accounts_receivable` | Trade/accounts receivable under the frozen mapping | instant | natural statement value |
| `inventory` | Reported inventory | instant | natural statement value |
| `capex` | Cash paid to acquire/construct long-lived assets under the frozen mapping | discrete/YTD | positive outflow magnitude |
| `total_debt` | Frozen sum of interest-bearing debt line items | instant | natural statement value |
| `cash_and_equivalents` | Cash and cash equivalents under the frozen mapping | instant | natural statement value |

The exact source-line mapping for each data provider MUST be versioned. Changing a mapping is a formula-version change.

Ratios such as `gross_margin` are stored as decimal `RATIO` values (`0.25` means 25%). Percentage formatting and percentage-point display conversions occur only at calculation/report boundaries.

## 3. Period Semantics

### 3.1 Instant Facts

Balance-sheet facts describe a point in time. Do not subtract them to create a “quarter value.” Changes are calculated as ending balance minus comparison ending balance.

### 3.2 Discrete and YTD Facts

Income-statement and cash-flow facts may be reported as a discrete period or year-to-date value. The adapter MUST label the basis before any comparison.

For a company with compatible statements and no restatement conflict:

```text
Q1_discrete = Q1_ytd
Q2_discrete = H1_ytd - Q1_ytd
Q3_discrete = Q3_ytd - H1_ytd
Q4_discrete = FY_ytd - Q3_ytd
```

A derived discrete fact MUST:

- use two facts with identical company, currency, accounting standard, statement scope, and restatement lineage;
- record `derived_from_ytd`;
- reference both source fact IDs;
- carry the active `formula_version`.

If these requirements are not met, the tool returns `unreliable` instead of guessing.

### 3.3 Comparison Eligibility

- YoY compares equivalent fiscal periods and bases.
- QoQ compares discrete quarters only; it MUST NOT compare Q3 YTD with Q2 discrete.
- TTM compares TTM with TTM.
- Peer comparison requires aligned period endings or a documented, verifier-approved alignment rule.
- Seasonal limitations MUST be stated when a QoQ conclusion is material.

## 4. Deterministic Formulas

All calculations use decimal arithmetic, not binary floating-point arithmetic.

### 4.1 Absolute Change

```text
absolute_change = current - comparison
```

### 4.2 Growth Rate

When `comparison > 0`:

```text
growth_rate = (current - comparison) / comparison
```

When `comparison <= 0`, standard percentage growth is `not_meaningful`; report absolute change and the sign transition instead. The LLM MUST NOT produce a conventional percentage from a zero or negative base.

### 4.3 Gross Margin

When `revenue > 0`:

```text
gross_profit = revenue - operating_cost
gross_margin = gross_profit / revenue
margin_change_pp = (current_margin - comparison_margin) × 100
```

Gross profit is `unavailable` when either source input is missing. Gross margin is `not_meaningful` when revenue is zero or negative.

### 4.4 Cash Conversion

When `net_income > 0`:

```text
cash_conversion = operating_cash_flow / net_income
```

When net income is zero or negative, the ratio is `not_meaningful`; the tool reports values, signs, and absolute divergence.

### 4.5 Working-Capital Changes

```text
receivables_change = receivables_end - receivables_comparison_end
inventory_change = inventory_end - inventory_comparison_end
```

Growth rates follow the positive-base rule. A working-capital deterioration conclusion MUST consider business growth and available management explanations; rising balances alone do not prove deterioration.

### 4.6 Profit/Cash Divergence

A deterministic divergence signal is eligible when any frozen rule is true:

1. net income is positive while operating cash flow is negative;
2. comparable net-income growth is positive while comparable operating-cash-flow growth is negative;
3. net income improves while operating cash flow declines in absolute value, with compatible periods.

The signal is evidence to investigate, not by itself a causal conclusion.

## 5. Restatements and Conflicts

- Use the latest statement published on or before `research_time`.
- Do not mix as-reported and restated values in one comparison.
- A correction creates a new fact with a new hash and lineage; it never overwrites the old fact.
- If authoritative sources conflict and the conflict cannot be resolved deterministically, mark the fact `unreliable` and surface the limitation.

## 6. Currency and Peer Comparison

V1 peer comparisons SHOULD use companies with the same reporting currency. Currency conversion is allowed only when a frozen, licensed FX source and formula version are available. Otherwise cross-currency values are not directly comparable and the run degrades or refuses.

Peer conclusions MUST compare the same framework: growth, margins, earnings quality, cash conversion, working capital, CapEx, debt/cash, and risk. Missing components are explicitly marked; the Agent cannot replace them with random available metrics.

## 7. Point-in-Time Rule

For every fact and evidence chunk used in a benchmark run:

```text
published_at <= research_time
```

Retrieval time does not make later-published information historically available. Product reports MUST display the effective evidence cutoff and MUST NOT imply point-in-time completeness when live data is incomplete.

## 8. Confidence

Confidence is categorical and evidence-based:

- `high`: all mandatory variables are available, calculations pass, claims have direct evidence, and no unresolved material contradiction exists;
- `medium`: conclusion is supported but has a material missing variable, plausible alternative, or evidence limitation;
- `low`: evidence is indirect, conflicting, or incomplete.

The model's self-reported probability is not a confidence measure.
