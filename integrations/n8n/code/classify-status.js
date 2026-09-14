const response = $input.first().json;
const config = $('Prepare request').first().json;
const run = $('Accept submission').first().json;
const state = response.body?.lifecycle_state;
const polls = $runIndex + 1;
const base = { schema_version: '2.0.0', run_id: run.run_id, links: run.links, polls };
if (response.statusCode !== 200 || response.body?.run_id !== run.run_id) {
  return [{ json: { ...base, route: 'error', status: 'error', http_status: 502,
    code: 'STATUS_UNAVAILABLE', message: '无法确认 V2 后端任务状态；任务可能仍在运行。',
  } }];
}
if (state === 'succeeded') return [{ json: { ...base, route: 'completed' } }];
if (state === 'queued' || state === 'running') {
  if (polls < config.max_polls && Date.now() - config.started_at_ms < config.max_wait_ms) {
    return [{ json: { ...base, route: 'waiting', lifecycle_state: state } }];
  }
  return [{ json: { ...base, route: 'error', status: 'error', http_status: 504,
    code: 'POLL_LIMIT_EXCEEDED', message: 'n8n 达到等待上限；V2 后端任务未被自动取消。',
  } }];
}
const terminal = ['insufficient_data', 'failed', 'timed_out', 'cancelled'];
return [{ json: { ...base, route: 'error', status: 'error', http_status: 409,
  code: terminal.includes(state) ? `RUN_${state.toUpperCase()}` : 'UNKNOWN_BACKEND_STATE',
  message: state === 'insufficient_data' ? '可验证财报证据不足；没有生成报告。' :
    state === 'cancelled' ? '研究任务已取消。' : '研究任务没有可用结果；请检查状态与 Trace。',
} }];
