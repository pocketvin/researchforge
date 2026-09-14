# V2 n8n failure behavior / 失败出口

所有机器错误都保持 `status: error`、`code`、可操作 `message`、HTTP 状态、`run_id` 和 `links`。n8n 不转发秘密或网络异常原文，也不生成研究替代品。

| 场景 | HTTP / code | 用户下一步 |
|---|---|---|
| 参数格式、额外字段或非法报告期 | 422 `INVALID_INPUT` | 修正输入；不创建 V2 Run |
| V2 capability 未就绪 | 502 `BACKEND_UNAVAILABLE_OR_UNSAFE` | 恢复 canonical V2 backend |
| 后端拒绝研究边界（如投资建议） | 422 `UNSUPPORTED_OR_INVALID_INPUT` | 改成财报研究问题 |
| 同键不同输入 | 409 `IDEMPOTENCY_CONFLICT` | 还原原请求，或新任务使用新键 |
| POST 未确认 | 502 `SUBMISSION_UNCONFIRMED` | 原样检查/重试，不生成第二任务 |
| 状态查询失败/ID 不匹配 | 502 `STATUS_UNAVAILABLE` | 用状态链接查原 V2 Run |
| 超过轮询等待上限 | 504 `POLL_LIMIT_EXCEEDED` | 查状态或显式取消；n8n 不自动取消后端 |
| 财报证据不足 | 409 `RUN_INSUFFICIENT_DATA` | 查看来源与 Trace；没有报告 |
| 后端失败/超时/取消 | 409 `RUN_FAILED` / `RUN_TIMED_OUT` / `RUN_CANCELLED` | 查看 V2 状态/Trace，不自动重跑 |
| 完成后 V2 result/workspace/trace 不一致 | 502 `RESULT_ARTIFACTS_UNAVAILABLE` | 检查持久化；不返回不完整成功 |

原生表单为了显示错误页可以用 HTTP 200 呈现“研究未生成”，但不会出现结论。自动化客户端应使用 webhook JSON。

网络请求有有限重试，轮询也有上限。n8n 本身断线属于 unknown transport outcome；ResearchForge V2 Run 独立持久化，重新读取同一个 run_id 即可。n8n 不拥有 exactly-once 研究语义，也不包含邮件、交易或第三方写入动作。
