// Transport validation only. Backend configuration is never taken from the webhook body.
const body = $input.first().json.body;
const fail = (message) => [{ json: {
  ok: false, http_status: 422, schema_version: '1.5.0', status: 'error',
  code: 'INVALID_INPUT', message, run_id: null, links: null,
} }];
if (!body || typeof body !== 'object' || Array.isArray(body)) {
  return fail('请提交 JSON: company_id、period、research_question。');
}
const allowed = ['company_id', 'period', 'research_question', 'research_time', 'idempotency_key'];
if (Object.keys(body).some((key) => !allowed.includes(key))) {
  return fail('包含不支持的字段；后端地址、模式和数据命名空间不可由请求覆盖。');
}
if (!/^cn_[0-9]{6}$/.test(body.company_id || '') ||
    !/^20[0-9]{2}(Q[1-4]|H1|FY)$/.test(body.period || '') ||
    typeof body.research_question !== 'string' ||
    body.research_question.trim().length < 8 || body.research_question.length > 2000) {
  return fail('请检查公司 ID、报告期和研究问题（8–2000 字）；可用范围见后端 /v1/catalog。');
}
if (body.idempotency_key !== undefined &&
    (typeof body.idempotency_key !== 'string' ||
     !/^[A-Za-z0-9._:-]{8,128}$/.test(body.idempotency_key) || !body.research_time)) {
  return fail('重试时必须同时提供原 idempotency_key 和 research_time，保持输入不变。');
}
if (body.research_time !== undefined &&
    (typeof body.research_time !== 'string' ||
     !/T.*(Z|[+-][0-9]{2}:[0-9]{2})$/.test(body.research_time) ||
     !Number.isFinite(Date.parse(body.research_time)))) {
  return fail('research_time 必须是含时区的 ISO 日期时间。');
}
return [{ json: {
  ok: true,
  backend_url: 'http://api:8000',
  public_api_url: 'http://127.0.0.1:8000',
  started_at_ms: Date.now(),
  max_polls: 60,
  max_wait_ms: 150000,
  request: {
    task_type: 'filing_analysis',
    company_ids: [body.company_id],
    requested_period_labels: [body.period],
    research_question: body.research_question.trim(),
    research_time: body.research_time || new Date().toISOString(),
    idempotency_key: body.idempotency_key || `n8n-run-${$execution.id}`,
  },
} }];
