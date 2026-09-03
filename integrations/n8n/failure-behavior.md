# Failure behavior / 失败出口

所有错误 JSON 都有 `status: error`、`code`、可操作 `message`、HTTP 状态、`run_id` 和 `links`
（任务尚未确认时为 null）。不转发网络异常原文、HTTP 响应头或任何秘密。

下表 HTTP 状态适用于 webhook 自动化契约。n8n 原生表单为了在浏览器中呈现完成页，领域失败
会返回 HTTP 200 的“研究未生成”页面，但保留相同 `code` / `message`，且绝不显示 Executive
Conclusion。自动化客户端必须使用 webhook，不应从表单 HTML 推断机器状态。

| 场景 | HTTP / code | 用户下一步 |
|---|---|---|
| 参数格式、额外字段或不完整重试信息 | 422 `INVALID_INPUT` | 修正输入；不创建 run |
| 后端不可达或 fixture/benchmark 环境 | 502 `BACKEND_UNAVAILABLE_OR_UNSAFE` | 恢复 product 后端 |
| 公司/期间不支持 | 422 `UNSUPPORTED_OR_INVALID_INPUT` | 选择 `/v1/catalog` 中的配对 |
| 同键不同输入 | 409 `IDEMPOTENCY_CONFLICT` | 还原原请求，或为新任务使用新键 |
| POST 未确认 | 502 `SUBMISSION_UNCONFIRMED` | 使用返回的 `retry_request` 原样重试；不要产生新键 |
| 状态查询失败/ID 不匹配 | 502 `STATUS_UNAVAILABLE` | 用状态链接查原 run，可能仍在运行 |
| 超过 60 轮或 150 秒等待预算 | 504 `POLL_LIMIT_EXCEEDED` | 查状态或显式 POST 取消；不自动取消后端 |
| 证据/事实不足 | 409 `RUN_INSUFFICIENT_DATA` | 查截止时间、支持范围和来源；没有报告 |
| 后端失败/超时/取消 | 409 `RUN_FAILED` / `RUN_TIMED_OUT` / `RUN_CANCELLED` | 查状态/Trace，不自动重跑研究 |
| 未知状态 | 409 `UNKNOWN_BACKEND_STATE` | 检查后端版本/契约；禁止当成功处理 |
| 完成后报告或审计产物不可读 | 502 `RESULT_ARTIFACTS_UNAVAILABLE` | 查持久化、报告和 Trace；不返回不完整成功 |

HTTP 请求最多三次网络尝试，每次五秒，重试间隔一秒。HTTP 4xx/5xx 使用显式分支，不作为
重新创建研究的理由。轮询预算在响应后检查，正在进行的 HTTP 调用可使总时长略超预算。

如果 n8n 本身崩溃、外层 300 秒执行超时、Webhook 连接中断或反向代理先超时，可能无法返回
上述自定义 JSON；客户端必须把空响应/非 JSON/断连接视为 **unknown transport outcome**。
带原键和原截止时间重试可恢复已提交任务。不能把 facilitator 的人工补救计为独立真人 PASS。

本地运行的 Wait 是短时内存等待；本集成不声称进程崩溃后自动恢复未完成的 webhook。后端任务
保留既有持久化/恢复语义；n8n 不更改它，也不保证 exactly-once 业务消费。外部下游如邮件、
交易或写入第三方系统不在授权范围内，本工作流没有这些节点。
