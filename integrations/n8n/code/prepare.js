// Transport validation only. Backend configuration is never taken from user input.
const incoming = $input.first().json;
const fromWebhook = Object.prototype.hasOwnProperty.call(incoming, 'body');
const surface = fromWebhook ? 'webhook' : 'form';
const body = fromWebhook ? incoming.body : incoming;
const fail = (message) => [{ json: {
  ok: false, http_status: 422, schema_version: '1.7.0', status: 'error',
  code: 'INVALID_INPUT', message, run_id: null, links: null, surface,
} }];
if (!body || typeof body !== 'object' || Array.isArray(body)) {
  return fail('请提交公司名称/股票代码和研究问题。');
}
const allowed = [
  'company_query', 'market_hint', 'requested_period_label', 'research_question',
  'research_time', 'idempotency_key', 'research_mode',
];
const formMetadata = ['submittedAt', 'formMode'];
const rawSupplied = Object.fromEntries(Object.entries(body)
  .filter(([key]) => !formMetadata.includes(key)));
const formFields = [
  'Company / 公司或股票代码', 'Market / 市场', 'Period / 报告期（可选）',
  'Research Question / 研究问题',
];
if (Object.keys(rawSupplied).some((key) => !(fromWebhook ? allowed : formFields).includes(key))) {
  return fail('包含不支持的字段；后端地址和数据命名空间不可由请求覆盖。');
}
const formMarket = rawSupplied['Market / 市场'];
const marketAliases = {
  'Auto / 自动识别': null,
  'A 股': 'CN',
  '美股': 'US',
  '港股': 'HK',
};
const supplied = fromWebhook ? rawSupplied : {
  company_query: rawSupplied['Company / 公司或股票代码'],
  market_hint: marketAliases[formMarket] ?? null,
  requested_period_label: rawSupplied['Period / 报告期（可选）'] || null,
  research_question: rawSupplied['Research Question / 研究问题'],
};
if (typeof supplied.company_query !== 'string' ||
    supplied.company_query.trim().length < 1 || supplied.company_query.length > 200 ||
    ![undefined, null, 'CN', 'US', 'HK'].includes(supplied.market_hint) ||
    typeof supplied.research_question !== 'string' ||
    supplied.research_question.trim().length < 1 || supplied.research_question.length > 4000) {
  return fail('请检查公司名称/股票代码、市场和研究问题。');
}
const normalizedPeriod = typeof supplied.requested_period_label === 'string'
  ? supplied.requested_period_label.trim() : supplied.requested_period_label;
if (normalizedPeriod && !/^20[0-9]{2}(Q[1-4]|H1|FY)$/.test(normalizedPeriod)) {
  return fail('报告期请使用 2025FY / 2025H1 / 2025Q1 等格式，留空表示 Latest。');
}
if (![undefined, 'general', 'financial_snapshot'].includes(supplied.research_mode)) {
  return fail('research_mode 仅支持 general 或 financial_snapshot。');
}
if (supplied.idempotency_key !== undefined &&
    (typeof supplied.idempotency_key !== 'string' || supplied.idempotency_key.length < 8 ||
     supplied.idempotency_key.length > 256 || !supplied.research_time)) {
  return fail('重试时必须同时提供原 idempotency_key 和 research_time。');
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
    company_query: supplied.company_query.trim(),
    market_hint: supplied.market_hint || null,
    requested_period_label: normalizedPeriod || null,
    research_question: supplied.research_question.trim(),
    research_mode: supplied.research_mode || 'general',
    research_time: supplied.research_time || new Date().toISOString(),
    idempotency_key: supplied.idempotency_key || `n8n-run-${$execution.id}`,
  },
} }];
