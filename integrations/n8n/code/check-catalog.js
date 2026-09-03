const response = $input.first().json;
const config = $('Prepare request').first().json;
const catalog = response.body;
const valid = response.statusCode === 200 && catalog?.data_namespace === 'product' &&
  Array.isArray(catalog.companies) && Array.isArray(catalog.supported_task_types) &&
  catalog.supported_task_types.includes(config.request.task_type);
if (!valid) {
  return [{ json: { ok: false, http_status: 502, schema_version: '1.5.0', status: 'error',
    code: 'BACKEND_UNAVAILABLE_OR_UNSAFE', run_id: null, links: null,
    message: '后端不可达或不是 product 数据环境；未创建研究任务。请检查服务和配置。',
  } }];
}
// Read capabilities from the same backend catalog used by Web; never embed a company list.
const supported = catalog.companies.some((company) =>
  company.company_id === config.request.company_ids[0] &&
  Array.isArray(company.period_labels) &&
  company.period_labels.includes(config.request.requested_period_labels[0]));
if (!supported) {
  return [{ json: { ok: false, http_status: 422, schema_version: '1.5.0', status: 'error',
    code: 'UNSUPPORTED_OR_INVALID_INPUT', run_id: null, links: null,
    message: '该公司/期间不在后端公开的支持范围内；未创建研究任务。请检查 /v1/catalog。',
  } }];
}
return [{ json: { ok: true } }];
