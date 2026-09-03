# Three-minute n8n demo / 三分钟演示

这是一段可复现的工程演示，不是真人可用性评价。不声称 Human Validated。

1. **0:00–0:30 — 用户问题。** 打开 ResearchForge Web 和 n8n 原生表单。说明它们共用后端，
   输入都是公司、期间、研究问题，差别仅是交互入口。使用 CATL 2024H1 示例问现金转化。
2. **0:30–1:00 — 提交。** 在表单选择 CATL 2024H1，输入问题并开始研究。说明表单触发
   Create run → Wait → Poll → IF，但普通用户不必登录编辑器理解节点。
3. **1:00–2:00 — 检查。** 在完成页展开 Financial Facts、Calculations 与 Supporting
   Evidence。顺着页码打开官方来源；说明数值计算来自 Python，不是 n8n 或 LLM。打开完整
   Research Result 看同一个后端原始报告。
4. **2:00–2:30 — 反证与后续。** 展开 `counter_evidence`、`limitations`、`monitoring`。
   不把 `not_found` 解读为“完全没有反证”。打开 `links.trace` 展示十阶段 LangGraph。
5. **2:30–3:00 — 不知道时怎么办。** 再提交 BYD 2024FY。展示
   `UNSUPPORTED_OR_INVALID_INPUT` 的“研究未生成”页，没有 Executive Conclusion 或编造数字。
   webhook 的 cutoff、幂等冲突和 transport 失败保留在工程深潜演示。

可换为 CATL `2024FY` 或 BYD `2024H1` 复用相同流程，不更改节点或结果代码。正式求职材料
应配合 [三案例工程证据](../../docs/evidence/v1.5-n8n/README.md)，明确只覆盖三个财报，且
真人评价仍待 Phase 6，当前截图和自动化运行不能替代真实参与者。
