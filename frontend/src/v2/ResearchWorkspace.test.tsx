import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ResearchWorkspace from './ResearchWorkspace'

const run = { run_id: 'run_synthetic_ui', lifecycle_state: 'failed', created_at: '2026-09-10T00:00:00Z', request: { company_query: '测试公司（合成测试）', market_hint: 'CN', requested_period_label: '2025FY', research_question: '检查测试财报的现金流', research_time: '2026-09-10T00:00:00Z', idempotency_key: 'ui-fixture-only' }, failure: { code: 'MODEL_CREDIT_EXHAUSTED', message: '模型服务余额不足。' } }
const workspace = { documents: [{ document_id: 'doc_synthetic', title: '合成测试财报', company: { legal_name: '测试公司（合成测试）' }, published_at: '2026-04-01T00:00:00Z', period_label: '2025FY', page_count: 2, table_count: 1 }], catalog: [{ artifact_id: 'table_synthetic', kind: 'table', document_id: 'doc_synthetic', page_id: 'page_synthetic', page_number: 2, title: '现金流测试表', row_count: 2, column_count: 2 }], facts: [], calculations: [], working: { hypotheses: [], open_questions: [] }, stop_decision: null, observed_evidence: [], gaps: ['合成测试表，不作为真实研究验收。'] }
const table = { ...workspace.catalog[0], text: '项目 本期\n经营现金流 20', unit_candidates: ['人民币元'], extraction_status: 'candidate', rows: [[{ cell_id: 'header-a', text: '项目', header: true }, { cell_id: 'header-b', text: '本期', header: true }], [{ cell_id: 'value-a', text: '经营现金流' }, { cell_id: 'value-b', text: '20' }]], next_offset: null }
function response(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }) }

beforeEach(() => {
  localStorage.clear()
  localStorage.setItem('researchforge.v2.selected', run.run_id)
  vi.stubGlobal('fetch', vi.fn(async (input: string | URL | Request) => {
    const path = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url
    if (path === '/v2/capabilities') return response({ agent_ready: false, version: '2.0.0' })
    if (path.startsWith('/v2/research-runs?')) return response([run])
    if (path.endsWith('/workspace')) return response(workspace)
    if (path.includes('/trace?')) return response({ events: [{ sequence: 1, timestamp: run.created_at, event_type: 'run_failed', name: 'research', label: '模型请求未完成', status: 'failed', data: { failure: run.failure } }] })
    if (path.includes('/sources/table_synthetic')) return response(table)
    if (path.endsWith(`/${run.run_id}`)) return response(run)
    return response({ detail: { code: 'TEST_UNEXPECTED_ENDPOINT' } }, 404)
  }))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); localStorage.clear() })

describe('V2 filing workspace — synthetic UI tests, not model-quality evidence', () => {
  it('is the only research web surface and has no legacy-web navigation', async () => {
    render(<ResearchWorkspace />)
    await screen.findByText('这次研究尚未生成报告')
    expect(screen.getByRole('heading', { name: '开始一项研究' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '旧版研究' })).not.toBeInTheDocument()
    expect(screen.queryByText('方法与实验')).not.toBeInTheDocument()
  })

  it('fills the research question from a preset without submitting it', async () => {
    render(<ResearchWorkspace />)
    await screen.findByText('这次研究尚未生成报告')
    const textarea = screen.getByRole('textbox', { name: 'V2 研究问题' }) as HTMLTextAreaElement
    const preset = screen.getByRole('button', { name: '现金流健康' })
    fireEvent.click(preset)
    expect(textarea.value).toBe('请分析现金流是否健康，综合经营现金流、净现金变化、投资与筹资活动以及营运资金因素。')
    expect(preset).toHaveAttribute('aria-pressed', 'true')
    fireEvent.change(textarea, { target: { value: '我想继续修改这个问题' } })
    expect(textarea.value).toBe('我想继续修改这个问题')
    expect(preset).toHaveAttribute('aria-pressed', 'false')
  })

  it('separates report year from report type and keeps market-aware options', async () => {
    render(<ResearchWorkspace />)
    await screen.findByText('这次研究尚未生成报告')
    const year = screen.getByRole('combobox', { name: 'V2 年份' }) as HTMLSelectElement
    const type = screen.getByRole('combobox', { name: 'V2 报告类型' }) as HTMLSelectElement
    const market = screen.getByRole('combobox', { name: 'V2 市场' }) as HTMLSelectElement
    expect(year.value).toBe('2024')
    expect(type.value).toBe('H1')
    expect(within(type).getByRole('option', { name: /半年度报告/ })).toHaveValue('H1')
    expect(within(type).queryByRole('option', { name: /第二季度报告/ })).not.toBeInTheDocument()
    fireEvent.change(market, { target: { value: 'US' } })
    expect(year.value).toBe('LATEST')
    expect(type.value).toBe('AUTO')
    expect(type).toBeDisabled()
    fireEvent.change(year, { target: { value: '2024' } })
    expect(type).not.toBeDisabled()
    expect(within(type).getByRole('option', { name: /第二季度报告/ })).toHaveValue('Q2')
    expect(within(type).queryByRole('option', { name: /半年度报告/ })).not.toBeInTheDocument()
  })

  it('keeps the real failure boundary visible and does not invent a completed report', async () => {
    render(<ResearchWorkspace />)
    expect(await screen.findByText('这次研究尚未生成报告')).toBeInTheDocument()
    expect(screen.getByText('模型服务余额不足。')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /开始财报研究/ })).toBeDisabled()
    expect(screen.queryByText('关键发现')).not.toBeInTheDocument()
    expect(screen.queryByText('质量满分')).not.toBeInTheDocument()
  })

  it('lets a failed-model run retain navigable tables and original filing links', async () => {
    render(<ResearchWorkspace />)
    await screen.findByText('这次研究尚未生成报告')
    fireEvent.click(screen.getByRole('button', { name: '财报与表格' }))
    fireEvent.click(await screen.findByRole('button', { name: /现金流测试表/ }))
    const dialog = await screen.findByRole('dialog', { name: '证据与原文' })
    expect(await within(dialog).findByRole('columnheader', { name: '项目' })).toBeInTheDocument()
    expect(within(dialog).getByRole('cell', { name: '20' })).toBeInTheDocument()
    expect(within(dialog).getByRole('link', { name: '原始财报文件' })).toHaveAttribute('href', '/v2/research-runs/run_synthetic_ui/documents/doc_synthetic/original')
    expect(within(dialog).getByText(/不自动等于规范财务事实/)).toBeInTheDocument()
    fireEvent.keyDown(document, { key: 'Escape' })
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('shows objectives, conditional support, report repairs, and degraded review independence', async () => {
    const successRun = { ...run, run_id: 'run_synthetic_success', lifecycle_state: 'succeeded', failure: null }
    const successWorkspace = {
      ...workspace,
      working: {
        objectives: [{ objective_id: 'obj_cash', question: '利润与经营现金流是否匹配？', priority: 'required', status: 'answered', evidence_ids: ['ev_cash'], conclusion: '合成测试结论：匹配。', remaining_uncertainty: '仍缺一项辅助指标。' }],
        hypotheses: [], open_questions: [],
      },
      stop_decision: { stop_reason: 'sufficient_evidence', direct_answer: 'no', summary: 'done', evidence_ids: ['ev_cash'], remaining_uncertainties: ['辅助指标未计算。'], why_stop: '必答问题已得到有条件回答，继续研究只增加细节。' },
    }
    const successResult = {
      report: {
        direct_answer: 'no', title: '合成测试研究报告', executive_summary: '合成测试结论。',
        findings: [{ claim_id: 'claim_cash', title: '现金流结论', text: '合成测试文本。', kind: 'inference', evidence_ids: ['ev_cash'], fact_ids: [], calculation_ids: [], confidence: 'medium', uncertainty: '合成测试边界。' }],
        sections: [{ title: '分析', text: '合成测试分析。', evidence_ids: ['ev_cash'] }], limitations: ['仅用于 UI 测试。'], follow_up_questions: [],
      },
      validation: { passed: true, warnings: ['语义复核认为部分结论仅有条件支持：claim_cash'] },
      semantic_review: { status: 'model_reviewed', is_ground_truth: false, provider: 'deepseek', model: 'deepseek-v4-flash', independence: 'reduced_same_provider', fallback_used: true, review: { claims: [{ claim_id: 'claim_cash', verdict: 'partial', reason: '证据支持方向，但措辞仍需保守。' }], question_answered: true, missing_material_topics: [] } },
      quality_note: '合成测试不代表真实模型质量。',
    }
    localStorage.setItem('researchforge.v2.selected', successRun.run_id)
    vi.stubGlobal('fetch', vi.fn(async (input: string | URL | Request) => {
      const path = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url
      if (path === '/v2/capabilities') return response({ agent_ready: true, version: '2.0.0' })
      if (path.startsWith('/v2/research-runs?')) return response([successRun])
      if (path.endsWith('/workspace')) return response(successWorkspace)
      if (path.includes('/trace?')) return response({ events: [
        { sequence: 1, timestamp: run.created_at, event_type: 'research_reflection', name: 'research_state', label: '已刷新研究状态', status: 'succeeded', data: { completeness: { required_objectives_answered: 1, required_objectives_limited: 0, required_objectives_total: 1, core_question_status: 'evidence_exhausted', expected_value_of_more_research: 'low' } } },
        { sequence: 2, timestamp: run.created_at, event_type: 'report_repair_requested', name: 'synthesis', label: '正在修正报告', status: 'needs_attention', data: { issues: ['synthetic'] } },
        { sequence: 3, timestamp: run.created_at, event_type: 'model_request_failed', name: 'semantic_review', label: 'Qwen 模型请求未返回可计量 usage', status: 'failed', data: { provider: 'qwen', model: 'qwen-plus', counted_as_estimated_cost: false } },
        { sequence: 4, timestamp: run.created_at, event_type: 'semantic_review_provider_fallback', name: 'semantic_review', label: 'Qwen 复核未返回，改用 DeepSeek 降级复核', status: 'needs_attention', data: { independence: 'reduced_same_provider' } },
        { sequence: 5, timestamp: run.created_at, event_type: 'research_provider_fallback', name: 'state_reflection', label: '主研究模型不可用，已切换备用模型', status: 'needs_attention', data: { from_model: 'deepseek-v4-flash', to_model: 'qwen3-max', status_code: 402 } },
        { sequence: 6, timestamp: run.created_at, event_type: 'report_repair_exhausted', name: 'synthesis', label: '模型报告连续修复未通过', status: 'needs_attention', data: { issues: ['synthetic'] } },
        { sequence: 7, timestamp: run.created_at, event_type: 'safe_report_fallback_used', name: 'synthesis', label: '已改用保守 Research Dossier 报告', status: 'succeeded', data: { reason: 'synthetic' } },
        { sequence: 8, timestamp: run.created_at, event_type: 'tool_result', name: 'submit_research', label: '提交研究成果', status: 'succeeded', data: { result: { dossier: { why_stop: '同一财报继续检索价值较低，故以 evidence_exhausted 提交并保留未知。' } } } },
      ] })
      if (path.endsWith('/result')) return response(successResult)
      if (path.endsWith(`/${successRun.run_id}`)) return response(successRun)
      return response({ detail: { code: 'TEST_UNEXPECTED_ENDPOINT' } }, 404)
    }))
    render(<ResearchWorkspace />)
    expect(await screen.findByText('这次研究必须回答什么')).toBeInTheDocument()
    expect(screen.getByText('利润与经营现金流是否匹配？')).toBeInTheDocument()
    expect(screen.getByText('直接答案')).toBeInTheDocument()
    expect(screen.getByText('否')).toBeInTheDocument()
    expect((await screen.findAllByText('语义复核：部分支持')).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/语义复核：0 项支持，1 项有条件支持/)).toBeInTheDocument()
    expect(screen.getByText(/DeepSeek 降级复核；独立性降低/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /研究过程/ }))
    expect(await screen.findByText(/核心问题：当前财报已无更多有效信息/)).toBeInTheDocument()
    expect(screen.getAllByText(/故以 当前财报已无更多有效信息 提交并保留未知/).length).toBeGreaterThanOrEqual(1)
    expect(screen.queryByText(/evidence_exhausted/)).not.toBeInTheDocument()
    expect(screen.queryByText(/needs_attention/)).not.toBeInTheDocument()
    expect(await screen.findByText('正在修正报告')).toBeInTheDocument()
    expect(screen.getByText(/只修正报告措辞、引用或数值声明/)).toBeInTheDocument()
    expect(screen.getByText('Qwen 复核未返回，改用 DeepSeek 降级复核')).toBeInTheDocument()
    expect(screen.getByText('主研究模型不可用，已切换备用模型')).toBeInTheDocument()
    expect(screen.getByText(/deepseek-v4-flash 当前不可用.*qwen3-max/)).toBeInTheDocument()
    expect(screen.getByText('模型报告连续修复未通过')).toBeInTheDocument()
    expect(screen.getByText(/不会重新启动研究.*研究 Dossier/)).toBeInTheDocument()
    expect(screen.getByText('已改用保守 Research Dossier 报告')).toBeInTheDocument()
    expect(screen.getByText(/不新增推断或心算.*确定性校验与独立语义复核/)).toBeInTheDocument()
    expect(screen.getByText(/未把最坏费用上限记成实际估算费用/)).toBeInTheDocument()
  })

  it('shows actual persisted events separately from hidden reasoning', async () => {
    render(<ResearchWorkspace />)
    await screen.findByText('这次研究尚未生成报告')
    fireEvent.click(screen.getByRole('button', { name: /研究过程/ }))
    expect(await screen.findByText('模型请求未完成')).toBeInTheDocument()
    expect(screen.getByText(/不展示或虚构模型的隐藏思维链/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '查看工程审计' }))
    expect(screen.getByRole('button', { name: '返回阅读视图' })).toBeInTheDocument()
  })
})
