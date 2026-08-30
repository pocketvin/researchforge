# ResearchForge V1.2 — PRODUCT + RESEARCH SCOPE FREEZE

## A Financial Research Agent That Improves Its Research Procedures from Verified Failures

**中文定位：一个能够完成公司基本面研究，并从经过验证的重复研究错误中持续改进研究方法的金融 Research Agent。**

---

# 1. 一句话定义

ResearchForge 是一个：

> **能够自主完成证券基本面研究任务，并把过去研究过程中反复出现、经过 Verifier 验证的错误，沉淀成未来可以复用的 Research Skill 的 Financial Research Agent。**

它同时有两个层面：

```text
Product Layer
真正完成金融研究
        │
        ▼
Research Agent
        │
        ▼
Execution Traces
        │
        ▼
Evolution Layer
发现重复错误
        │
        ▼
Skill Improvement
```

核心不是“会自己改 Prompt”。

而是：

> **研究 Agent 在真实任务中积累经验，并逐渐形成更可靠的证券研究 Procedure。**

---

# 2. ResearchForge 最核心的产品价值

如果只是：

```text
读取财报
↓
计算几个指标
↓
生成摘要
```

那和直接把财报交给通用 AI 的区别太小。

所以 ResearchForge 的产品层必须能够完成：

> **一轮相对完整的公司基本面 Research。**

用户提出一个 Research Question，例如：

> 分析宁德时代最近几个季度基本面发生了什么变化，目前最大的基本面风险是什么？

ResearchForge 应该自己完成：

```text
理解研究问题
↓
拆解研究步骤
↓
获取结构化财务数据
↓
检索财报 / 公告 Evidence
↓
执行金融计算
↓
分析趋势
↓
进行公司 / 同行比较
↓
寻找 Supporting Evidence
↓
寻找 Counter Evidence
↓
识别风险与异常
↓
形成结构化 Research Thesis
↓
保留 Evidence 与 Sources
```

因此它首先是：

# Financial Research Agent

其次才是：

# Self-Improving Skill System

---

# 3. Product Scope 与 Research Scope 分离

这是 V1 最重要的架构原则。

## Product Scope

较宽。

用于证明：

> ResearchForge 本身是一个真正可以使用的 Financial Research Agent。

---

## Research / Evolution Scope

较窄。

用于证明：

> ResearchForge 是否真的能从错误中改善自己的 Research Skill。

两者不能继续绑定成完全一样的范围。

---

# 4. Product Layer 支持的五类 Research Task

V1 产品层至少支持以下五类任务。

---

## Task 1 — Company Fundamental Research

例如：

> 分析宁德时代最近几个季度基本面变化。

Agent 需要分析：

```text
Revenue Trend
Profit Trend
Margin Trend
Cash Flow
Working Capital
CapEx
Risk Signals
Major Changes
```

最终形成：

```text
Fundamental Summary
Key Changes
Financial Trends
Earnings Quality
Drivers
Risks
Outlook
Evidence
```

---

# 5. Task 2 — Earnings / Filing Analysis

例如：

> 宁德时代这次季度财报最值得关注的三个变化是什么？

Agent 自动：

```text
读取财务数字
↓
比较历史季度
↓
读取相关财报
↓
识别异常变化
↓
寻找管理层解释
↓
寻找反向 Evidence
↓
形成结论
```

这不是单纯：

> 财报摘要。

而是：

> 财报变化分析。

---

# 6. Task 3 — Peer Comparison

例如：

> 宁德时代和亿纬锂能，谁最近几个季度的基本面更健康？

Agent 使用统一 Research Framework 比较：

```text
Growth
Margins
Earnings Quality
Cash Conversion
Working Capital
CapEx
Risk
```

禁止：

> 随机挑几个指标进行比较。

最终输出：

```text
Comparison Table

Company A Strengths
Company A Weaknesses

Company B Strengths
Company B Weaknesses

Key Differences

Research Conclusion
```

---

# 7. Task 4 — Thesis / Research Question Investigation

这是非常重要的一类能力。

用户可以提出一个明确 Research Thesis：

> 宁德时代毛利率改善主要是不是因为原材料价格下降？

或者：

> 最近利润增长是否真正转化成了现金流？

Agent 不能直接回答。

而是：

```text
Research Thesis
↓
Relevant Variables
↓
Financial Data
↓
Filing Evidence
↓
Supporting Evidence
↓
Counter Evidence
↓
Alternative Explanation
↓
Conclusion + Confidence
```

这类任务能够明显区别于普通聊天式 AI。

---

# 8. Task 5 — Risk / Anomaly Detection

例如：

> 最近几个季度有没有值得警惕的基本面异常？

ResearchForge 自动检查：

```text
Profit ↑ / Cash Flow ↓

Receivables abnormal growth

Inventory abnormal growth

Margin deterioration

CapEx acceleration

Debt deterioration

One-off profit contribution

Revenue / Profit divergence
```

然后给出：

```text
Risk Signal

Evidence

Severity

Possible Explanation

What to Monitor Next
```

---

# 9. Research Agent 的统一 Workflow

所有产品任务尽量走同一个核心流程，而不是做五个完全独立 Agent。

```text
Research Question
        ↓
Task Understanding
        ↓
Research Plan
        ↓
Financial Data Tools
        ↓
Filing Evidence Retrieval
        ↓
Financial Analysis
        ↓
Cross-Check
        ↓
Counter Evidence
        ↓
Research Conclusion
        ↓
Structured Report
```

ResearchForge V1 仍然只做：

> **Single Research Agent。**

不做：

```text
Planner Agent
Researcher Agent
Critic Agent
Reviewer Agent
Multi-Agent Debate
```

Research Plan 是同一个 Agent 内部的步骤。

---

# 10. Fundamental Research Skill

V1 仍然只有一个核心 Skill：

```text
skills/
└── fundamental-research/
    ├── SKILL.md
    ├── references/
    │   └── research-guidelines.md
    └── scripts/
        └── financial_ratios.py
```

这个 Skill 不是一个针对单题的 Prompt。

它是一套基本面 Research Procedure。

---

# 11. Fundamental Research Skill 的基础结构

## Step 1 — Understand the Research Question

判断当前任务属于：

```text
Company Research

Filing Analysis

Peer Comparison

Thesis Investigation

Risk Detection
```

并确定：

> 需要哪些数据和 Evidence。

---

## Step 2 — Financial Snapshot

检查核心财务变量：

```text
Revenue

Net Income

Gross Margin

Operating Cash Flow

Accounts Receivable

Inventory

CapEx
```

计算：

```text
YoY

QoQ

Multi-quarter Trend
```

---

## Step 3 — Earnings Quality

检查：

```text
Accounting Profit

Operating Cash Flow

Receivables

Inventory

Cash Conversion
```

识别：

```text
Profit / Cash Divergence

Working Capital Deterioration

One-off Profit
```

---

## Step 4 — Trend / Driver Analysis

根据 Research Question 检查：

```text
Revenue Growth

Margin Change

Cost Change

Product / Business Mix

CapEx

Management Explanation
```

V1 不建设完整行业数据平台。

能够由已有财务数据与 Filing Evidence 支撑的 Driver 才分析。

---

## Step 5 — Evidence Cross-Check

任何重要结论都必须问：

```text
Financial Data 支持吗？

Filing Evidence 支持吗？

有没有 Counter Evidence？

有没有 Alternative Explanation？

有没有遗漏关键变量？

Citation 是否对应真实结论？
```

---

## Step 6 — Research Thesis

最终形成：

```text
Current Fundamentals

Key Changes

Earnings Quality

Key Drivers

Supporting Evidence

Counter Evidence

Key Risks

Outlook

Research Uncertainty
```

---

# 12. Product Layer 不等于 Benchmark Layer

ResearchForge 可以完成：

```text
Company Research
Filing Analysis
Peer Comparison
Thesis Investigation
Risk Detection
```

但 V1 不需要为五种任务分别构建严格 Benchmark。

这是控制 Scope 的关键。

---

# 13. V1 正式 Evolution Benchmark

正式 Self-Evolution Experiment 只选择：

# Earnings Quality Analysis

因为这类问题：

```text
容易获得结构化数据

容易构建 Ground Truth

容易确定遗漏变量

容易做 Deterministic Verification

容易识别重复 Failure

容易验证 Patch 是否真正修复问题
```

所以：

> **Product Capability 较宽，Evolution Benchmark 极窄。**

---

# 14. Evolution Benchmark 研究的问题

正式研究：

> Agent 是否经常因为只看利润表现，而遗漏现金流和营运资本恶化？

典型 Failure：

```text
Net Income ↑

Gross Margin ↑

Agent:
"Earnings quality improved."

但实际上：

OCF ↓
Receivables ↑
Inventory ↑
```

Verifier 标记：

```text
CRITICAL_OMISSION
```

---

# 15. Evolution Dataset

V1 Benchmark 只需要：

```text
4–6 Companies

×

4–6 Company-Quarter Cases
```

总计：

```text
24–36 High-Quality Cases
```

每个 Case 必须有：

```text
Frozen Financial Data

Allowed Filing Evidence

Correct Reporting Period

Expected Checks

Known Failure Labels

Verifier Ground Truth
```

---

# 16. Benchmark Split

冻结：

```text
Evolution Set

Validation Set

Final Test Set
```

例如：

```text
Evolution      12–18

Validation      6–9

Final Test      6–9
```

---

# 17. Point-in-Time

保留原则：

```text
Evidence Publish Time
<=
Research Time
```

但不建设动态 Point-in-Time Platform。

Benchmark Case 自带：

```text
Frozen Evidence Package
```

Agent 只能访问当时已经存在的数据。

---

# 18. Structured Financial Data

产品层支持基本面 Research 所需的核心变量：

```text
Revenue

Net Income

Gross Margin

Operating Cash Flow

Accounts Receivable

Inventory

CapEx

Debt / Cash
```

不建设：

```text
完整 Commodity Database

完整行业数据库

卖方一致预期数据库

全市场实时行情数据库
```

---

# 19. Filing Evidence Retrieval

ResearchForge 必须具备真实 Evidence Retrieval。

流程：

```text
Annual / Interim / Quarterly Report
        ↓
Parse
        ↓
Chunk
        ↓
Metadata
        ↓
Embedding Retrieval
        ↓
Relevant Evidence
```

支持：

```text
Company
Period
Document Type
Section
```

过滤。

V1 不做复杂：

```text
Hybrid Retrieval

Multi-Retriever

Reranker

Query Expansion Pipeline

Retrieval Agent
```

如果简单 Retrieval 已经足够，不继续扩。

---

# 20. Financial Tools

提供确定性工具，例如：

```text
get_financial_metrics()

calculate_growth()

calculate_margin()

compare_periods()

compare_companies()

detect_financial_divergence()
```

LLM 不负责：

> 心算重要财务数据。

工具负责：

> 计算。

模型负责：

> Research Reasoning。

---

# 21. ResearchForge 与直接调用通用 AI 的区别

ResearchForge 必须能够明确证明以下差异。

## 通用 AI

```text
Question
↓
LLM
↓
Answer
```

---

## ResearchForge

```text
Research Question
↓
Research Procedure
↓
Financial Tools
↓
Historical Data
↓
Filing Retrieval
↓
Financial Calculation
↓
Evidence Cross-Check
↓
Counter Evidence
↓
Structured Thesis
↓
Trace
↓
Verifier
```

它不是：

> “一个金融 Prompt。”

而是：

> **有数据、有工具、有 Research Procedure、有 Evidence、有 Trace、有 Evaluation 的 Research System。**

---

# 22. Financial Verifier

Verifier 仍然是项目核心资产。

分为三部分。

---

## A. Deterministic Verification

程序判断：

```text
Financial Number Accuracy

Calculation Accuracy

YoY / QoQ Accuracy

Reporting Period Accuracy

Tool Execution

Schema

Citation Existence

Citation Time Validity
```

---

## B. Research Coverage Verification

正式 Benchmark 中检查：

```text
OCF 是否检查

Receivables 是否检查

Inventory 是否检查

Profit / Cash Divergence 是否识别

Counter Evidence 是否存在

Mandatory Variable 是否遗漏
```

---

## C. LLM Qualitative Judge

辅助诊断：

```text
Evidence 是否支持结论

是否 Overclaim

Alternative Explanation 是否合理

Counter Evidence 是否被真正考虑
```

LLM Judge：

> 不作为 Patch Adoption 的唯一依据。

---

# 23. Failure Taxonomy

保留：

```text
CALCULATION_ERROR

PERIOD_ERROR

CRITICAL_OMISSION

EVIDENCE_MISMATCH

ONE_SIDED_REASONING

OVERCLAIM

TOOL_MISUSE

CITATION_ERROR
```

其中最重点：

```text
CRITICAL_OMISSION

EVIDENCE_MISMATCH

ONE_SIDED_REASONING
```

---

# 24. Execution Trace

每次 Research 记录：

```text
Research Question

Research Plan

Tool Calls

Financial Data Used

Retrieved Evidence

Intermediate Analysis

Final Research Result

Verifier Feedback

Failure Labels
```

这些 Trace 不只是为了 Debug。

也是：

> Evolution 的原材料。

---

# 25. Evolution 只从重复错误开始

ResearchForge 不采用：

```text
一个任务失败
↓
马上修改 Skill
```

而采用：

```text
多条 Research Runs
↓
Verifier Failure Events
↓
Repeated Failure Detection
↓
Failure Cluster
↓
Reusable Experience
↓
Skill Patch
```

---

# 26. Experience Distillation

例如：

```text
Run 03
Missing OCF

Run 07
Missing OCF

Run 11
Missing Receivables

Run 14
Missing Cash Conversion
```

聚合为：

```text
Failure Cluster

CASH_CONVERSION_OMISSION

Support:
5 / 14 Runs
```

形成：

```text
Experience

Profitability improvement must be
cross-validated against operating
cash flow and working-capital changes.
```

---

# 27. V1 只研究 Failure-Driven Learning

V1 使用：

```text
Failed / Weak Runs

+

Verifier Feedback
```

进行 Experience Distillation。

成功 Runs 用于：

> Regression Validation。

V1 不实现完整：

```text
Positive Experience Mining
Success Strategy Extraction
```

进入 Future Work。

---

# 28. Skill Patch

Patch 只允许：

```text
ADD

MODIFY

REMOVE
```

每个 Patch 必须包含：

```text
Target Section

Operation

New Rule

Reason

Supporting Failures
```

例如：

```diff
## Earnings Quality

+ Mandatory Cash Conversion Check

+ Before concluding that earnings
+ quality has improved, inspect:

+ Operating Cash Flow
+ Accounts Receivable
+ Inventory

+ If accounting profit improves while
+ OCF deteriorates, explicitly flag
+ earnings-quality divergence.
```

---

# 29. Skill Version

Skill 版本例如：

```text
v1
↓
candidate v2
↓
validation
↓
v2
```

Patch 状态只保留：

```text
PROPOSED

ADOPTED

REJECTED
```

---

# 30. Held-Out Validation

任何 Candidate 都必须：

```text
Current Skill
vs
Candidate Skill
```

在未参与 Experience Distillation 的任务上运行。

Adoption Rule：

```text
Target Failure decreases

Overall performance not worse

Regression below threshold
```

满足：

```text
ADOPT
```

否则：

```text
REJECT
```

---

# 31. Evaluation Metrics

核心指标：

```text
Task Score

Calculation Accuracy

Evidence Coverage

Critical Omission Rate

Citation Accuracy
```

Evolution 核心指标：

```text
Repeat Error Rate

Repair Rate

Regression Rate
```

---

# 32. Repeat Error Rate

回答：

> Agent 已经从一种错误中学习以后，在新任务中还会不会重复犯？

例如：

```text
Before Evolution

41%

After Evolution

18%
```

这是 ResearchForge 最核心的指标之一。

---

# 33. Repair Rate

回答：

> Candidate Patch 到底修复了多少目标 Failure？

例如：

```text
Repair Rate

68%
```

---

# 34. Regression Rate

回答：

> 为了解决一个问题，Skill 有没有破坏原来正确的 Research Behavior？

例如：

```text
Regression Rate

4%
```

所以最终不是简单问：

> Score 有没有提高。

而是：

```text
修复了什么？

有没有再次犯？

有没有搞坏其他东西？
```

---

# 35. V1 Experiment Matrix

只需要：

```text
Base Agent

Seed Skill

Evolved Skill
```

可选：

```text
Naive Reflection
```

如果时间不足：

> Naive Reflection 不阻塞 V1。

---

# 36. Experiment 回答三个问题

## Q1

> 一个明确的 Financial Research Skill 是否比直接调用模型更可靠？

比较：

```text
Base Agent
vs
Seed Skill
```

---

## Q2

> 从真实失败中生成的 Skill Patch 是否能够继续改善？

比较：

```text
Seed Skill
vs
Evolved Skill
```

---

## Q3

> 新的 Research Procedure 是否能够迁移到未参与 Evolution 的 company-quarter？

使用：

```text
Final Test Set
```

---

# 37. V1 不要求无限 Evolution

V1 成功只要求：

# 一个真实完整 Evolution Cycle

例如：

```text
Skill v1

↓

14 Evolution Runs

↓

Repeated Cash Conversion Failure

↓

Experience

↓

Candidate v2

↓

Validation

↓

Adopt

↓

Skill v2

↓

Unseen Final Test
```

如果有时间：

> 做第二轮。

否则不影响 V1 完成。

---

# 38. 最终前端

只做：

# Page 1 — Research

# Page 2 — Skill Lab

---

# 39. Page 1 — Research

用户可以选择 Research Mode：

```text
Company Research

Filing Analysis

Peer Comparison

Research Question

Risk Detection
```

输入例如：

```text
Company:
CATL

Period:
2025 Q3

Question:
What are the most important
fundamental changes?
```

或者：

```text
CATL
vs
EVE Energy
```

---

# 40. Research Report

输出：

```text
Executive Research Summary

Financial Snapshot

Key Changes

Earnings Quality

Drivers

Risk Signals

Supporting Evidence

Counter Evidence

Research Outlook

Sources
```

如果是 Peer Comparison：

```text
Comparison Table

Key Differences

Relative Strengths

Relative Risks
```

---

# 41. Page 2 — Skill Lab

展示：

```text
Current Skill

Research Runs

Failure Distribution

Repeated Failure

Experience

Patch Diff

Validation

Evolution Metrics
```

核心 Demo：

```text
Research Error
↓
Repeated Pattern
↓
Experience
↓
Skill Diff
↓
Validation
↓
Adopted Skill
```

---

# 42. Skill Lab 最关键展示

例如：

```text
Repeated Failure

CRITICAL_OMISSION

Cash Conversion Check Missing

5 / 14 Evolution Runs
```

然后：

```text
Extracted Experience

Profit growth must be cross-validated
against OCF, receivables and inventory.
```

然后：

```diff
+ Mandatory Cash Conversion Check
```

最后：

```text
Repeat Error

41% → 18%

Repair Rate

68%

Regression Rate

4%

PATCH ADOPTED
```

---

# 43. 产品 Demo 与研究 Demo 是同一个系统

Research 页面证明：

> **这个 Agent 本身能干活。**

Skill Lab 证明：

> **它不只是调用模型，还能从过去任务中改善自己的 Research Procedure。**

两个页面互相解释。

缺一不可。

---

# 44. Technology Stack

## Backend

```text
Python

FastAPI

Pydantic

LangGraph
```

LangGraph 只用于 Research Workflow。

Evolution Pipeline：

> 普通 Python。

---

## LLM

```text
OpenAI-Compatible API
```

一个底层模型。

不同角色：

```text
Researcher

Optimizer
```

通过 Prompt 区分。

---

## Data

```text
PostgreSQL

pgvector

JSON Benchmark Cases
```

---

## Frontend

```text
React

TypeScript

Vite

Tailwind
```

---

## Engineering

```text
Docker Compose

pytest

GitHub Actions

Structured Logging
```

Run 记录：

```text
Trace

Latency

Token Usage

Cost
```

不建设完整 Observability Platform。

---

# 45. Database Objects

只保留：

```text
cases

runs

skill_versions

evolution_runs

evaluations
```

---

# 46. Development Gates

## G0 — Research Skill

完成：

```text
Fundamental Research Skill
```

并能人工跑通几个真实 Research Case。

---

## G1 — Useful Research Agent

完成产品层核心能力：

```text
Company Research

Filing Analysis

Peer Comparison

Research Question

Risk Detection
```

不要求每个能力都非常深。

但至少需要：

> 用户明显感觉到它比直接问一个裸 LLM 多了一套真实 Research Workflow。

---

## G2 — Financial Verifier

完成：

```text
Deterministic Verification

Coverage Verification

Failure Taxonomy
```

如果 Verifier 无法稳定找到真实错误：

> 不进入 Evolution。

---

## G3 — Evolution

完成：

```text
Failure Events

Failure Clustering

Experience

Skill Patch

Held-out Validation

Skill Versioning
```

至少跑通：

> 一个真实 Evolution Cycle。

---

## G4 — Productization

最后完成：

```text
2-Page UI

Docker

CI

Charts

README

Demo Video
```

---

# 47. V1 明确不做

```text
全 A 股

股票价格预测

Buy / Sell

Target Price

自动交易

Portfolio Optimization

Quant Strategy Evolution

K线技术分析

High-Frequency Data

宏观全市场 Agent

新闻舆情平台

完整 Commodity Database

完整 Industry Data Platform

Sell-side Research Database

实时行情平台

Multi-Agent

Agent Debate

Knowledge Graph

Neo4j

RL

SFT

LoRA

Verifier Co-Evolution

Open-Ended Optimization

Skill Marketplace

Skill Routing

复杂 RAG

全网 Browser Research

完整多模态 Financial Parsing

复杂 Liquid Glass

Infinite Canvas

Research Report Drag-and-Drop
```

---

# 48. Future Work

可以包括：

```text
Margin Driver Benchmark

Positive Experience Mining

Industry Research

Commodity Data

News Research

Macro Research

More Financial Skills

Open-Ended Skill Optimization

Multiple Research Domains

MCP Financial Tools

Multiple Models
```

但：

> 不阻塞 V1。

---

# 49. V1 最终成功标准

ResearchForge V1 完成需要证明两件完全不同的事。

---

## Product Success

ResearchForge 本身必须能够：

> **完成一轮有实际意义的公司基本面 Research。**

不能只是：

```text
读财报
+
算几个指标
```

而应具备：

```text
Research Planning

Financial Tools

Historical Comparison

Filing Evidence

Company Comparison

Supporting Evidence

Counter Evidence

Risk Detection

Structured Thesis
```

---

## Research Success

系统必须证明：

> **至少一种重复金融研究错误，可以通过 Trace → Verifier → Experience → Skill Patch → Held-out Validation 被真实改善。**

---

# 50. 最终 Demo Story

第一幕：

用户问：

> 宁德时代最近几个季度基本面有什么重要变化？

ResearchForge：

```text
获取财务数据
↓
读取财报 Evidence
↓
分析历史趋势
↓
检查盈利质量
↓
寻找风险
↓
输出结构化 Research Report
```

此时已经是一个真正能用的 Financial Research Agent。

---

第二幕：

切换到 Skill Lab。

系统发现：

> Research Agent 在过去多个 Earnings Quality Cases 中，反复出现 Cash Conversion Omission。

---

第三幕：

Verifier 展示：

```text
Net Income ↑

but

OCF ↓

Receivables ↑

Inventory ↑
```

Agent 多次仍然：

> Earnings quality improving.

---

第四幕：

系统发现：

```text
5 / 14 Runs

same failure
```

形成：

```text
CASH_CONVERSION_OMISSION
```

---

第五幕：

提炼 Experience：

> Profitability improvement must be cross-validated against operating cash flow and working-capital changes.

---

第六幕：

生成 Skill Diff：

```diff
+ Mandatory Cash Conversion Check

+ Operating Cash Flow
+ Accounts Receivable
+ Inventory
+ Profit / Cash Divergence
```

---

第七幕：

Held-out Validation：

```text
Repeat Error
41% → 18%

Repair Rate
68%

Regression Rate
4%
```

Patch：

```text
ADOPTED
```

---

第八幕：

回到 Research 页面。

ResearchForge 在一个完全新的公司季度任务中：

> 自动使用新的 Research Procedure。

不再遗漏：

```text
OCF
Receivables
Inventory
```

故事结束。

---

# 51. ResearchForge 最终不是在证明什么

它不是证明：

> “我比 ChatGPT 更聪明。”

也不是：

> “我训练了一个更强的金融模型。”

也不是：

> “我发明了一个新的 Self-Evolution 算法。”

而是在证明：

> **一个通用 LLM 加上明确的金融 Research Procedure、可靠的数据工具、Evidence Grounding、Verifier 和经验反馈闭环，可以形成一个比裸模型调用更稳定、更可审计、并能够持续改善研究方法的 Financial Research Agent。**

---

# 52. 最终项目定位

英文：

# ResearchForge

### A Financial Research Agent That Learns from Verified Research Failures

中文：

# ResearchForge

### 一个能够完成公司基本面研究，并从经过验证的研究错误中持续改进研究方法的金融 Agent

核心产品闭环：

```text
Research Question
↓
Real Financial Research
↓
Evidence-Grounded Result
↓
Execution Trace
↓
Verified Failure
↓
Reusable Experience
↓
Research Skill Patch
↓
Regression Validation
↓
Better Future Research
```

---

# ResearchForge V1.2 — FROZEN

以后判断一个功能能不能进入 V1，要分别问两个问题。

## Product Gate

> **它是否明显提升 ResearchForge 完成真实公司基本面研究的能力？**

## Evolution Gate

> **它是否直接帮助证明 Agent 可以从经过验证的重复错误中改善自己的 Research Procedure？**

两个问题都不是：

> 不做。

不能因为：

```text
技术很酷

招聘 JD 出现过

最新论文用了

以后也许会用

显得项目更复杂
```

重新扩大 Scope。

允许修改 V1 Scope 的理由只有两个：

1. 当前 Product Layer 被真实使用证明不足以形成有意义的金融 Research；
2. 当前 Evolution Layer 被真实实验发现无法完成可靠的 Failure → Patch → Validation 闭环。

除此之外：

# Freeze.
