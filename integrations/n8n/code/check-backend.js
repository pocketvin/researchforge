const response = $input.first().json;
const ready = response.statusCode === 200 && response.body?.status === 'ok' && response.body?.version === '1.7.2';
if (!ready) {
  return [{ json: {
    ok: false,
    http_status: 502,
    schema_version: '1.7.0',
    status: 'error',
    code: 'BACKEND_UNAVAILABLE_OR_UNSAFE',
    run_id: null,
    links: null,
    message: 'ResearchForge 后端未就绪；未创建研究任务。',
  } }];
}
return [{ json: { ok: true } }];
