const response = $input.first().json;
const config = $('Prepare request').first().json;
const id = response.body?.run_id;
if (response.statusCode !== 202 || typeof id !== 'string' ||
    !/^run_[a-f0-9]{32}$/.test(id)) {
  const conflict = response.statusCode === 409;
  const invalid = response.statusCode === 422;
  return [{ json: { ok: false, http_status: conflict ? 409 : invalid ? 422 : 502,
    schema_version: '1.6.0', status: 'error', run_id: null, links: null,
    code: conflict ? 'IDEMPOTENCY_CONFLICT' : invalid ? 'UNSUPPORTED_OR_INVALID_INPUT' : 'SUBMISSION_UNCONFIRMED',
    message: conflict ? '该幂等键已用于不同输入；请还原原请求或使用新键。' :
      invalid ? (response.body?.detail?.message || '后端拒绝了公司、市场、期间或研究输入。') :
        '提交未获确认；请求可能已被接收。请使用下方原请求重试，不要生成新幂等键。',
    retry_request: config.request,
  } }];
}
const path = `/v1/research-runs/${id}`;
return [{ json: { ok: true, run_id: id, path,
  links: {
    status: config.public_api_url + path,
    result: config.public_api_url + path + '/result',
    trace: config.public_api_url + path + '/trace',
    cancel: config.public_api_url + path + '/cancel',
  },
} }];
