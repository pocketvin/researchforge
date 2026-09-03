# Three-minute n8n demo / 三分钟演示

这是一段可复现的工程演示，不是真人可用性评价。不声称 Human Validated。

1. **0:00–0:30 — 用户问题。** 打开 ResearchForge Web 和本地 n8n。说明它们共用后端，
   输入都是公司、期间、研究问题，差别仅是交互入口。使用 CATL 2024H1 示例问现金转化。
2. **0:30–1:00 — 提交。** 按 [README](README.md) 的 curl 示例调用生产 webhook，
   在 n8n Executions 中打开刚产生的执行，展示 Create run → Wait → Poll → IF。
   该示例已固定时间和幂等键，重复调用不会生成新 run。
3. **1:00–2:00 — 检查。** 在 Respond / Map verified output 展开 `conclusion`、
   `financial_facts`、`calculations`。顺着 Fact ID 找到 Evidence 的官方 URL 和页码；
   说明数值计算来自 Python，不是 n8n 或 LLM。打开 `links.result` 看同一个原始报告。
4. **2:00–2:30 — 反证与后续。** 展开 `counter_evidence`、`limitations`、`monitoring`。
   不把 `not_found` 解读为“完全没有反证”。打开 `links.trace` 展示十阶段 LangGraph。
5. **2:30–3:00 — 不知道时怎么办。** 将请求的 `research_time` 改为
   `2020-01-01T00:00:00Z`，并换一个新 `idempotency_key`。展示
   `RUN_INSUFFICIENT_DATA`，没有编造报告。若只修改问题但保留旧键，展示 409 幂等冲突。

可换为 CATL `2024FY` 或 BYD `2024H1` 复用相同流程，不更改节点或结果代码。正式求职材料
应配合 [三案例工程证据](../../docs/evidence/v1.5-n8n/README.md)，明确只覆盖三个财报，且
最终 Web/n8n UX 和真人评价仍待后续阶段完成。
