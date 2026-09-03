// Transport validation only. Backend configuration is never taken from either user surface.
const incoming = $input.first().json;
const fromWebhook = Object.prototype.hasOwnProperty.call(incoming, 'body');
const surface = fromWebhook ? 'webhook' : 'form';
const body = fromWebhook ? incoming.body : incoming;
const fail = (message) => [{ json: {
  ok: false, http_status: 422, schema_version: '1.5.0', status: 'error',
  code: 'INVALID_INPUT', message, run_id: null, links: null, surface,
} }];
if (!body || typeof body !== 'object' || Array.isArray(body)) {
  return fail('请提交 JSON: company_id、period、research_question。');
}
const allowed = ['company_id', 'period', 'research_question', 'research_time', 'idempotency_key'];
const formMetadata = ['submittedAt', 'formMode'];
const rawSupplied = Object.fromEntries(Object.entries(body)
  .filter(([key]) => !formMetadata.includes(key)));
const formFields = ['Company / 公司', 'Period / 报告期', 'Research Question / 研究问题'];
if (Object.keys(rawSupplied).some((key) => !(fromWebhook ? allowed : formFields).includes(key))) {
  return fail('包含不支持的字段；后端地址、模式和数据命名空间不可由请求覆盖。');
}
// Display aliases are semantic UI metadata only; catalog validation remains authoritative.
const companyAliases = {
  '宁德时代 · 300750.SZSE': 'cn_300750',
  '比亚迪 · 002594.SZSE': 'cn_002594',
};
const supplied = fromWebhook ? rawSupplied : {
  company_id: companyAliases[rawSupplied['Company / 公司']],
  period: rawSupplied['Period / 报告期'],
  research_question: rawSupplied['Research Question / 研究问题'],
};
if (!/^cn_[0-9]{6}$/.test(supplied.company_id || '') ||
    !/^20[0-9]{2}(Q[1-4]|H1|FY)$/.test(supplied.period || '') ||
    typeof supplied.research_question !== 'string' ||
    supplied.research_question.trim().length < 8 || supplied.research_question.length > 2000) {
  return fail('请检查公司 ID、报告期和研究问题（8–2000 字）；可用范围见后端 /v1/catalog。');
}
if (supplied.idempotency_key !== undefined &&
    (typeof supplied.idempotency_key !== 'string' ||
     !/^[A-Za-z0-9._:-]{8,128}$/.test(supplied.idempotency_key) || !supplied.research_time)) {
  return fail('重试时必须同时提供原 idempotency_key 和 research_time，保持输入不变。');
}
if (supplied.research_time !== undefined &&
    (typeof supplied.research_time !== 'string' ||
     !/T.*(Z|[+-][0-9]{2}:[0-9]{2})$/.test(supplied.research_time) ||
     !Number.isFinite(Date.parse(supplied.research_time)))) {
  return fail('research_time 必须是含时区的 ISO 日期时间。');
}
return [{ json: {
  ok: true,
  surface,
  backend_url: 'http://api:8000',
  public_api_url: 'http://127.0.0.1:8000',
  started_at_ms: Date.now(),
  max_polls: 60,
  max_wait_ms: 150000,
  request: {
    task_type: 'filing_analysis',
    company_ids: [supplied.company_id],
    requested_period_labels: [supplied.period],
    research_question: supplied.research_question.trim(),
    research_time: supplied.research_time || new Date().toISOString(),
    idempotency_key: supplied.idempotency_key || `n8n-run-${$execution.id}`,
  },
} }];
