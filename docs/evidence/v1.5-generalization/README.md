# Phase 3 — Three-filing Generalization Evidence

Status: **ENGINEERING EVIDENCE — NOT INDEPENDENT ACCEPTANCE OR HUMAN VALIDATION**

Exactly three real filing paths use the same deterministic extractor, catalog, LangGraph workflow and Financial Verifier. No provider calls or benchmark truth are used.

This generator revalidated each local ignored PDF through the official identity/hash check, reran the page-preserving parser and extractor, and compared the resulting package and six recovery hashes with the published product package. No expected value or source page is supplied by the registry. The results below are persisted outputs, not mocks.

Publication metadata exposes a date, not a reliable intraday release time. Availability is conservatively set to 23:59:59 Asia/Shanghai on that date.

## 宁德时代新能源科技股份有限公司 / 2024H1

- Source: [宁德时代新能源科技股份有限公司2024年半年度报告](https://disc.static.szse.cn/disc/disk03/finalpage/2024-07-26/6d9c1c9e-239e-4946-a477-84ea91313086.PDF)
- Announcement: `szse-2024-07-26-6d9c1c9e`; published cutoff: `2024-07-26T23:59:59+08:00`.
- PDF SHA-256: `2a690cb2471c1f0d4539d909a9f068c03710a838ddd35313175790169e85eab1`; 174 physical pages.
- Package SHA-256: `2207187bd5d466d8c79a09863703bb373ec1890829f84505fc994c5e071669de`.
- Recovery: **6/6 metrics; missing 0; abstained 0**.
- Research Result: **succeeded**; Verifier failures: **0**; Trace: **10 stages**.
- [Actual result](catl-2024h1/research-result.json), [calculations](catl-2024h1/calculation-records.json), [trace](catl-2024h1/workflow-trace.json), [verification](catl-2024h1/evaluation-result.json).

| Metric | Recovered CNY | Physical page | Statement / row | Column | Unit |
|---|---:|---:|---|---|---|
| `revenue` | 166766833600.00 | 69 | 合并利润表 / 营业收入 | 2024年半年度 | 万元 |
| `operating_cost` | 122517848800.00 | 69 | 合并利润表 / 营业成本 | 2024年半年度 | 万元 |
| `net_income` | 22864987400.00 | 70 | 合并利润表 / 归属于母公司股东的净利润 | 2024年半年度 | 万元 |
| `operating_cash_flow` | 44708954600.00 | 73 | 合并现金流量表 / 经营活动产生的现金流量净额 | 2024年半年度 | 万元 |
| `accounts_receivable` | 58099476000.00 | 64 | 合并资产负债表 / 应收账款 | 期末余额 | 万元 |
| `inventory` | 48050676200.00 | 64 | 合并资产负债表 / 存货 | 期末余额 | 万元 |

### Deterministic calculations

- `gross_profit` = `44248984800.00` (`calculated`); Calculated as revenue minus operating cost.
- `gross_margin` = `0.2653344423755971583069020985` (`calculated`); Calculated as gross profit / revenue.
- `cash_conversion` = `1.955345691552841179348299138` (`calculated`); Calculated as operating cash flow / net income.
- `profit_cash_divergence` = `0` (`calculated`); No frozen profit/cash divergence rule was triggered.

### Result, counter evidence and monitoring

宁德时代新能源科技股份有限公司2024H1经营现金流/净利润为1.96倍, 毛利率为26.53%; 未触发预设的背离信号。结论仅覆盖已核验财务事实, 不构成投资建议。

该官方披露中已定位: 扣除非经常性损益后的净利润披露、财务报告未经审计; 不应仅凭单期现金转化外推长期收益质量。

- 当前结论仅覆盖所选期间已哈希核验的官方报告和六项财务事实。
- 一次性损益未纳入确定性公式; 反证与审计边界以实际来源证据为准。
- 该官方披露中已定位: 扣除非经常性损益后的净利润披露、财务报告未经审计; 不应仅凭单期现金转化外推长期收益质量。
- 单一报告期的现金转化不能证明长期收益质量, 需在下一同口径报告期复核。

- Monitor: 下一同口径报告期复核现金转化与营运资本; trigger: 经营现金流为负, 或现金转化比低于1.00倍。; 下一同口径财务报告发布后.

Research Result canonical SHA-256: `fb36e8bdb26dc5a5e0705acdc340bbdf8177612127640da6aea8744e25064f57`.

## 宁德时代新能源科技股份有限公司 / 2024FY

- Source: [宁德时代新能源科技股份有限公司2024年年度报告](https://static.cninfo.com.cn/finalpage/2025-03-15/1222806982.PDF)
- Announcement: `cninfo-1222806982`; published cutoff: `2025-03-15T23:59:59+08:00`.
- PDF SHA-256: `b4f1713d7b821eb076c102711d177fe942ccc2bc8dd171ae5d7a95799a65b0ad`; 229 physical pages.
- Package SHA-256: `254730983464b0a5206d025b1b1f4d19f918af7ca9e0e3f1549d9fc2a7ae676b`.
- Recovery: **6/6 metrics; missing 0; abstained 0**.
- Research Result: **succeeded**; Verifier failures: **0**; Trace: **10 stages**.
- [Actual result](catl-2024fy/research-result.json), [calculations](catl-2024fy/calculation-records.json), [trace](catl-2024fy/workflow-trace.json), [verification](catl-2024fy/evaluation-result.json).

| Metric | Recovered CNY | Physical page | Statement / row | Column | Unit |
|---|---:|---:|---|---|---|
| `revenue` | 362012554000 | 119 | 合并利润表 / 营业收入 | 2024年度 | 千元 |
| `operating_cost` | 273518959000 | 119 | 合并利润表 / 营业成本 | 2024年度 | 千元 |
| `net_income` | 50744682000 | 120 | 合并利润表 / 归属于母公司股东的净利润 | 2024年度 | 千元 |
| `operating_cash_flow` | 96990345000 | 123 | 合并现金流量表 / 经营活动产生的现金流量净额 | 2024年度 | 千元 |
| `accounts_receivable` | 64135510000 | 114 | 合并资产负债表 / 应收账款 | 期末余额 | 千元 |
| `inventory` | 59835533000 | 114 | 合并资产负债表 / 存货 | 期末余额 | 千元 |

### Deterministic calculations

- `gross_profit` = `88493595000` (`calculated`); Calculated as revenue minus operating cost.
- `gross_margin` = `0.2444489673692365928282144602` (`calculated`); Calculated as gross profit / revenue.
- `cash_conversion` = `1.911340088799847046041198958` (`calculated`); Calculated as operating cash flow / net income.
- `profit_cash_divergence` = `0` (`calculated`); No frozen profit/cash divergence rule was triggered.

### Result, counter evidence and monitoring

宁德时代新能源科技股份有限公司2024FY经营现金流/净利润为1.91倍, 毛利率为24.44%; 未触发预设的背离信号。结论仅覆盖已核验财务事实, 不构成投资建议。

在当前证据包的有界反证规则中未找到唯一可引用的额外反证; 不代表完整公告不存在反证或风险。

- 当前结论仅覆盖所选期间已哈希核验的官方报告和六项财务事实。
- 一次性损益未纳入确定性公式; 反证与审计边界以实际来源证据为准。
- 在当前证据包的有界反证规则中未找到唯一可引用的额外反证; 不代表完整公告不存在反证或风险。
- 单一报告期的现金转化不能证明长期收益质量, 需在下一同口径报告期复核。

- Monitor: 下一同口径报告期复核现金转化与营运资本; trigger: 经营现金流为负, 或现金转化比低于1.00倍。; 下一同口径财务报告发布后.

Research Result canonical SHA-256: `62a660a4c9eb5c524580491078c4bdfbf10a8c5f24d5dfc044a720cb5f094ae1`.

## 比亚迪股份有限公司 / 2024H1

- Source: [比亚迪股份有限公司2024年半年度报告](https://static.cninfo.com.cn/finalpage/2024-08-29/1221030552.PDF)
- Announcement: `cninfo-1221030552`; published cutoff: `2024-08-29T23:59:59+08:00`.
- PDF SHA-256: `769e9fc195141e7f525d65f0daa308d441c7e39408f0dd584a3722cfc8a306ba`; 222 physical pages.
- Package SHA-256: `bc6ef857e8170ecc52abd4bcbb730bef6bf0702d796c62f0f17a4d49fa4201aa`.
- Recovery: **6/6 metrics; missing 0; abstained 0**.
- Research Result: **succeeded**; Verifier failures: **0**; Trace: **10 stages**.
- [Actual result](byd-2024h1/research-result.json), [calculations](byd-2024h1/calculation-records.json), [trace](byd-2024h1/workflow-trace.json), [verification](byd-2024h1/evaluation-result.json).

| Metric | Recovered CNY | Physical page | Statement / row | Column | Unit |
|---|---:|---:|---|---|---|
| `revenue` | 301126713000 | 84 | 合并利润表 / 营业收入 | 截至2024年6月30日止6个月期间 | 千元 |
| `operating_cost` | 240859982000 | 84 | 合并利润表 / 营业成本 | 截至2024年6月30日止6个月期间 | 千元 |
| `net_income` | 13631257000 | 84 | 合并利润表 / 归属于母公司所有者的净利润 | 截至2024年6月30日止6个月期间 | 千元 |
| `operating_cash_flow` | 14178310000 | 88 | 合并现金流量表 / 经营活动产生的现金流量净额 | 截至2024年6月30日止6个月期间 | 千元 |
| `accounts_receivable` | 71814516000 | 81 | 合并资产负债表 / 应收账款 | 2024年6月30日 | 千元 |
| `inventory` | 112753013000 | 81 | 合并资产负债表 / 存货 | 2024年6月30日 | 千元 |

### Deterministic calculations

- `gross_profit` = `60266731000` (`calculated`); Calculated as revenue minus operating cost.
- `gross_margin` = `0.2001374451292868195323475005` (`calculated`); Calculated as gross profit / revenue.
- `cash_conversion` = `1.040132248992150907286099881` (`calculated`); Calculated as operating cash flow / net income.
- `profit_cash_divergence` = `0` (`calculated`); No frozen profit/cash divergence rule was triggered.

### Result, counter evidence and monitoring

比亚迪股份有限公司2024H1经营现金流/净利润为1.04倍, 毛利率为20.01%; 未触发预设的背离信号。结论仅覆盖已核验财务事实, 不构成投资建议。

该官方披露中已定位: 扣除非经常性损益后的净利润披露、财务报告未经审计; 不应仅凭单期现金转化外推长期收益质量。

- 当前结论仅覆盖所选期间已哈希核验的官方报告和六项财务事实。
- 一次性损益未纳入确定性公式; 反证与审计边界以实际来源证据为准。
- 该官方披露中已定位: 扣除非经常性损益后的净利润披露、财务报告未经审计; 不应仅凭单期现金转化外推长期收益质量。
- 单一报告期的现金转化不能证明长期收益质量, 需在下一同口径报告期复核。

- Monitor: 下一同口径报告期复核现金转化与营运资本; trigger: 经营现金流为负, 或现金转化比低于1.00倍。; 下一同口径财务报告发布后.

Research Result canonical SHA-256: `08d5c7a02399cd4c69883ef5d87a3bb27293acc2a07b549ffa6bde372f876214`.

## Bounded limitations

- This is evidence for three native-text filings, not full-market or OCR capability.
- Two value columns are supported; extra, missing or ambiguous columns abstain.
- Note columns are not financial values. Ambiguous note/value positions abstain.
- Parent-company and equity-change tables cannot supply consolidated target metrics.
- CATL 2024FY's counter-evidence rule found no unique qualifying excerpt. It is labeled `not_found`, not 'no risks' or 'unaudited'.
- No H1/FY growth comparison is inferred; each path uses one reporting period.
- The ratio denominator is attributable net income, not consolidated total profit.
- The Verifier evidence is deterministic consistency/coverage checking; it is not independent acceptance or real-human usefulness evidence.

## Reproduce

```bash
uv run python scripts/generalization_evidence.py --raw-root data/raw/product
uv run pytest tests/ingestion -q
uv run python scripts/validate_contracts.py
```
