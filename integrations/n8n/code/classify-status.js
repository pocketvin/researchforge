const response = $input.first().json;
const config = $('Prepare request').first().json;
const run = $('Accept submission').first().json;
const state = response.body?.lifecycle_state;
const polls = $runIndex + 1;
const base = { schema_version: '1.7.0', run_id: run.run_id, links: run.links, polls };
if (response.statusCode !== 200 || response.body?.run_id !== run.run_id) {
  return [{ json: { ...base, route: 'error', status: 'error', http_status: 502,
    code: 'STATUS_UNAVAILABLE',
    message: '无法确认后端任务状态；任务可能仍在运行。请检查状态链接，不要重复创建任务。',
  } }];
}
if (state === 'succeeded') return [{ json: { ...base, route: 'completed' } }];
if (state === 'queued' || state === 'running') {
  if (polls < config.max_polls && Date.now() - config.started_at_ms < config.max_wait_ms) {
    return [{ json: { ...base, route: 'waiting', lifecycle_state: state } }];
  }
  return [{ json: { ...base, route: 'error', status: 'error', http_status: 504,
    code: 'POLL_LIMIT_EXCEEDED',
    message: 'n8n 已达到等待上限；后端未被自动取消，可能仍在运行。请使用状态或取消链接。',
  } }];
}
const terminal = ['insufficient_data', 'failed', 'timed_out', 'cancelled'];
return [{ json: { ...base, route: 'error', status: 'error', http_status: 409,
  code: terminal.includes(state) ? `RUN_${state.toUpperCase()}` : 'UNKNOWN_BACKEND_STATE',
  message: state === 'insufficient_data' ? '可验证数据不足；没有生成研究报告。请检查来源和支持范围。' :
    state === 'cancelled' ? '后端任务已取消；没有可用研究报告。' :
      '后端任务没有可用研究结果。请检查状态和 Trace；n8n 不会编造报告或自动重跑研究。',
} }];
