# G0 Data-Source Spike Evidence

Evidence date: `2026-08-30`  
Decision scope: V1.4 A-share battery-company fixture construction and optional local reconciliation  
Status: `ACCEPTED_FIXTURE_ONLY` after the 20-fact owner signoff

This record documents product engineering boundaries, not legal advice. When a right is unclear, ResearchForge applies the stricter public-package rule.

## 1. Official Filing Source

| Item | Recorded evidence |
|---|---|
| Identity | Shenzhen Stock Exchange (SZSE) listed-company announcements and CNInfo disclosure service |
| Authoritative entry points | [SZSE company announcements](https://www.szse.cn/disclosure/notice/company/index.html), [CNInfo](https://www.cninfo.com.cn/) |
| Access | Public web search and direct filing PDF links; no product authentication planned |
| Publication time | Preserve the official disclosure timestamp and enforce `published_at <= research_time` |
| Stable identity | Record official URL, announcement identifier when exposed, full-file SHA-256, retrieval timestamp, page, section/table, row, and column |
| Redistribution boundary | The [SZSE legal statement](https://www.szse.cn/application/laws/) permits browsing/downloading for non-commercial use but reserves content rights and restricts profit-making reuse without permission |
| Public package | Do not commit full PDFs. Commit normalized factual values, source metadata, hashes and links; include only short evidence where its publication basis is documented, otherwise use synthetic evidence |
| Runtime decision | `FIXTURE-ONLY` accepted for this narrow package; no live-data reliability claim |

The controlled source set was downloaded only into ignored local storage, hash-verified, and reconciled at page level. The exact sources and results are recorded in [`g0-reconciliation.md`](g0-reconciliation.md); full filing payloads remain excluded from the public package.

## 2. Structured Reconciliation Candidate: Tushare

| Item | Recorded evidence |
|---|---|
| Identity | Tushare financial statement APIs |
| Access | Registered account and token; the income, balance-sheet and cash-flow endpoints each state a minimum 2,000-point permission level |
| API metadata | `ann_date`, actual announcement date where supplied, report period, report type, company type and update flag |
| Relevant docs | [Income statement](https://tushare.pro/document/2?doc_id=33), [Balance sheet](https://tushare.pro/document/2?doc_id=36), [Cash-flow statement](https://tushare.pro/document/2?doc_id=44), [permission table](https://tushare.pro/document/1?doc_id=108) |
| License boundary | The [data service agreement](https://tushare.pro/document/1?doc_id=405) describes a personal, non-transferable, non-commercial, revocable, time-limited license and limits use to personal viewing |
| Reliability boundary | The same agreement disclaims accuracy, completeness and timeliness guarantees; every value would still require official-filing reconciliation |
| Credentials | No account, token or provider payload is required or committed by ResearchForge |
| Decision | `REJECT` as a runtime, committed-demo, redistributed or public-package dependency; allowed only as an optional local manual comparison if the owner's own account and current terms permit it |

### Frozen Reconciliation Field Map

The executable mapping is versioned as `SOURCE_MAPPING_VERSION = 1.0.0` in `src/researchforge/domain/source_mapping.py`.

| Canonical metric | Official row target | Tushare endpoint/field | Transform |
|---|---|---|---|
| `revenue` | 营业收入 | `income.revenue` | direct |
| `operating_cost` | 营业成本 | `income.oper_cost` | direct |
| `net_income` | 归属于上市公司股东/母公司股东的净利润 | `income.n_income_attr_p` | direct |
| `gross_profit` | 营业收入、营业成本 | `income.revenue`, `income.oper_cost` | revenue minus operating cost |
| `gross_margin` | 营业收入、营业成本 | same as gross profit | gross profit divided by positive revenue |
| `operating_cash_flow` | 经营活动产生的现金流量净额 | `cashflow.n_cashflow_act` | direct |
| `accounts_receivable` | 应收账款 | `balancesheet.accounts_receiv` | direct |
| `inventory` | 存货 | `balancesheet.inventories` | direct |
| `capex` | 购建固定资产、无形资产和其他长期资产支付的现金 | `cashflow.c_pay_acq_const_fiolta` | direct positive outflow magnitude |
| `total_debt` | frozen six-line interest-bearing debt set | six frozen `balancesheet` fields | sum |
| `cash_and_equivalents` | 期末现金及现金等价物余额 | `cashflow.c_cash_equ_end_period` | direct |

`total_debt` is the sum of short-term borrowings, short-term bonds payable, current portion of non-current liabilities, long-term borrowings, bonds payable and lease liabilities. Trade notes, accounts payable and other payables are excluded. Changing this set requires a source-mapping/formula version change.

## 3. Spike Decision and Open Gate

The source architecture is feasible without a paid or live provider:

1. Official filings are the authority for the frozen package.
2. Local raw PDFs remain ignored and are never published or committed.
3. The package stores base-unit Decimal facts, complete period/publication/scope/restatement semantics, stable locators, official links and content hashes.
4. No missing field is converted to zero. Corrections create new immutable facts.
5. Tushare is not queried because its documented rights already fail the public/runtime acceptance boundary; this avoids a credential and cost dependency without weakening the official reconciliation standard.

The G0 source decision is final for this scope: eight filings for CATL and EVE Energy across 2023Q3, 2023FY, 2024Q1 and 2024H1 produced 48 reviewed facts, complete semantics, stable locators and 100% numeric agreement. The owner signed the representative 20-fact sample, so the official-source outcome is `FIXTURE-ONLY`; Tushare remains `REJECT` for product/public use.

The exact file list, bounded read scope, extraction denominator and correction handling are frozen in [`g0-filing-read-plan.md`](g0-filing-read-plan.md).
