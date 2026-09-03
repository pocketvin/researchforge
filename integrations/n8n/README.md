# ResearchForge × n8n

输入 **Company + Period + Research Question**，n8n 调用与 Web 相同的 ResearchForge 后端，等待
已验证研究完成，输出结论、事实、计算、证据、反证、限制、监控和 Trace。

n8n 只做外部工作流编排。不做财务运算、证据判断、研究结论生成或 Verifier 决策；不替代 LangGraph。
当前支持 CATL 2024H1、CATL 2024FY、BYD 2024H1。能力列表实时读取同一后端的 `/v1/catalog`。

## 本地启动（从仓库根目录）

前置：Docker Compose；主项目的启动前提见 [README](../../README.md)。n8n 固定为 `2.37.9`，
无需给 n8n 配置 OpenAI Key。默认推荐零消费 deterministic 模式；Web 与 n8n 一起使用同一模式。

```bash
RESEARCHFORGE_REASONING_MODE=deterministic docker compose up -d --build --wait
docker compose -f docker-compose.yml -f integrations/n8n/compose.yml --profile n8n run --rm --no-deps n8n import:workflow --input=/files/researchforge.workflow.json
docker compose -f docker-compose.yml -f integrations/n8n/compose.yml --profile n8n run --rm --no-deps n8n publish:workflow --id=researchforgeV15
docker compose -f docker-compose.yml -f integrations/n8n/compose.yml --profile n8n up -d --no-deps --wait n8n
```

导入前若本项目 n8n 已运行，先 `docker compose -f docker-compose.yml -f integrations/n8n/compose.yml
--profile n8n stop n8n`，再导入、发布和启动。重复导入会更新 **researchforgeV15**，不要覆盖已自行
修改的工作流；先用 n8n 导出备份或另存 ID。初始 JSON 的 `active: false`，发布是显式步骤。

也可在自己的 n8n 界面导入 [researchforge.workflow.json](researchforge.workflow.json)，在
**Prepare request** 节点设置可信 `backend_url` / `public_api_url`，然后发布。Compose 内部地址是
`http://api:8000`，宿主浏览器地址是 `http://127.0.0.1:8000`。不要从 webhook 参数设置地址。

编辑器：[本地 n8n](http://127.0.0.1:5678)。首次打开需自行创建本地 owner 账户；不要使用共享
密码或把账户信息提交 Git。CLI 导入/发布和 webhook smoke 不要求绕过账户管理。

## 发起研究

```bash
curl --fail-with-body --max-time 240 \
  http://127.0.0.1:5678/webhook/researchforge-v15 \
  -H 'Content-Type: application/json' \
  --data-binary @integrations/n8n/examples/request.json
```

最简输入仅需以下三项；会生成新的幂等键和研究截止时间：

```json
{
  "company_id": "cn_002594",
  "period": "2024H1",
  "research_question": "上半年利润是否真正转化成了经营现金流？"
}
```

初始 webhook HTTP 连接会等待结果；异步研究仍由后端执行，n8n 内部显示 Wait/Poll/IF。
这不是实时流式输出。网络断开不代表后端已取消。重复调用示例会返回同一个已有 run；要研究
新问题请使用新键。跨次重试必须同时保留原 `research_time` 和 `idempotency_key`。

## 输出中看什么

| 用户问题 | 输出字段（后端原值） |
|---|---|
| 结论 / 关键发现 | `conclusion` / `findings` |
| 数字与公式 | `financial_facts` / `calculations` |
| 来源与反证 | `supporting_evidence` / `counter_evidence` |
| 限制与下一步 | `limitations` / `monitoring` |
| 完整报告与执行过程 | `research_result` / `research_trace` |

Evidence 保留源 URL、页码、来源身份和 hash；Calculation 保留输入 Fact IDs、公式版本与数值。
`links.status/result/trace` 可直接在本机检查同一后端产物。`links.cancel` 需要显式 POST，打开链接
不会自动取消任务。`status: error` 时不返回伪造的报告。

## 安全与保留

- 仅单用户本地使用，n8n 端口绑定 `127.0.0.1`。无公网认证/限流/TLS 方案，不要公开 webhook。
- 不要把个人隐私或秘密放入研究问题。n8n 会在本地 volume 保存输入/输出，默认七天清理；
  成功和失败执行都可在编辑器复查。ResearchForge 自己的持久化与保留策略不受此设置替代。
- n8n 自己生成并保存本地加密配置；不进 Git。不读取 ResearchForge `.env` 或 OpenAI Key。
- n8n 是独立的第三方软件，适用其自身许可证；ResearchForge 的 MIT 不重新许可 n8n。
- Native JavaScript runner 使用本地模式；容器可能提示缺少 Python runner。此工作流仅使用
  JavaScript，不需要也不安装 Python runner。生产公网部署不在本项目范围内。

## 修改与验证

`code/*.js` 是可审查源文件；生成器写出可直接导入的单文件 JSON。改源文件后运行：

```bash
node integrations/n8n/build-workflow.mjs
node integrations/n8n/build-workflow.mjs --check
node --test integrations/n8n/workflow.test.mjs
uv run python -m scripts.n8n_smoke
```

实际 n8n smoke 对三个真实案例逐项比较五类后端产物，并验证相同输入重放、最小输入、无效参数、
不支持的公司/期间、幂等冲突和证据截止时间不足。另有隔离的纯 transport fixture 检查真实 Wait
循环、取消、超时和缺失产物；它不提供财务数据，也不算真人或真实研究证据。

参见 [失败行为](failure-behavior.md)、[几分钟演示](demo.md)、[工程证据](../../docs/evidence/v1.5-n8n/README.md)
和 [契约](../../docs/contracts/v1.5/n8n-integration.md)。正式 Web+n8n 真人评价仍在最终 Phase 6；
**当前 human usefulness = UNVALIDATED**。

Compose 健康检查使用 `/healthz/readiness`，只有数据库迁移、服务初始化和发布工作流启动完成后
才允许 smoke；通用 `/healthz` 只表示进程存活，不足以作为 webhook 就绪信号。

## 官方版本/节点依据

已用实际 `2.37.9` 镜像的 CLI help 和节点实现校对 import/publish、HTTP full response/neverError、
IF、Wait 和 Respond 配置。参考 [n8n 发布记录](https://github.com/n8n-io/n8n/releases/tag/n8n%402.37.9)、
[CLI](https://docs.n8n.io/hosting/cli-commands/)、[HTTP Request](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/)
和 [Wait](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.wait/)。
