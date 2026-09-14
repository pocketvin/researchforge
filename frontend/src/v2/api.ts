export type Json = Record<string, unknown>
export type RunState = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled' | 'timed_out' | 'insufficient_data'
export type DirectAnswer = 'yes' | 'no' | 'mixed' | 'cannot_determine' | 'not_applicable'
export interface ResearchRequest { company_query: string; market_hint: 'CN' | 'US' | 'HK' | null; requested_period_label: string | null; research_question: string; research_time: string; idempotency_key: string }
export interface Run { run_id: string; lifecycle_state: RunState; request: ResearchRequest; created_at: string; finished_at?: string | null; cancel_requested?: boolean; failure?: { code: string; message: string } | null; usage?: Json }
export interface ResearchEvent { sequence: number; timestamp: string; event_type: string; name: string; label: string; status: string; duration_ms?: number | null; span_id?: string | null; parent_span_id?: string | null; data: Json }
export interface Cell { cell_id: string; text: string | null; row?: number; column?: number; rowspan?: number; colspan?: number; header?: boolean }
export interface Source { artifact_id: string; kind: string; document_id: string; title?: string; label?: string; text?: string; text_hash?: string; page_number?: number | null; page_id?: string; table_ids?: string[]; footnote_ids?: string[]; source_artifact_id?: string; metric_code?: string; source_locator?: { page?: number | null; page_id?: string; table_id?: string }; next_offset?: number | null; rows?: Cell[][]; row_count?: number; column_count?: number; unit_candidates?: string[]; extraction_status?: string; visual_inspection_available?: boolean; explanation?: string; input_fact_ids?: string[] }
export interface Fact extends Source { fact_id: string; metric_code: string; value: string; currency: string | null; period: { fiscal_year: number; fiscal_period: string; period_basis: string } }
export interface Calculation extends Source { calculation_id: string; formula_code: string; value: string | null; status: string; input_fact_ids: string[] }
export interface Filing { document_id: string; title: string; published_at: string; period_label: string; page_count: number | null; table_count: number; company: { legal_name: string } }
export interface ResearchObjective { objective_id: string; question: string; priority: 'required' | 'supporting'; status: 'open' | 'answered' | 'limited'; evidence_ids: string[]; conclusion: string; remaining_uncertainty: string }
export interface Hypothesis { hypothesis_id: string; statement: string; status: string; materiality: string; evidence_for: string[]; evidence_against: string[]; unknowns: string[]; would_change_conclusion: string; confidence: string }
export interface Notebook { objectives: ResearchObjective[]; hypotheses: Hypothesis[]; open_questions: Json[]; decision_summary?: string }
export interface Dossier { stop_reason: string; direct_answer?: DirectAnswer; summary: string; evidence_ids: string[]; remaining_uncertainties: string[]; why_stop: string }
export interface Workspace { documents: Filing[]; catalog: Source[]; facts: Fact[]; calculations: Calculation[]; working: Notebook; stop_decision: Dossier | null; gaps: string[]; observed_evidence: Source[] }
export interface Finding { claim_id: string; title: string; text: string; kind: string; evidence_ids: string[]; fact_ids: string[]; calculation_ids: string[]; confidence: string; uncertainty: string }
export interface Result { report: { direct_answer?: DirectAnswer; title: string; executive_summary: string; findings: Finding[]; sections: Array<{ title: string; text: string; evidence_ids: string[] }>; limitations: string[]; follow_up_questions: string[] }; validation: Json; semantic_review: { status?: string; is_ground_truth?: boolean; provider?: string | null; model?: string | null; independence?: 'independent_provider' | 'reduced_same_provider' | 'same_provider' | 'unspecified'; fallback_used?: boolean; protocol_repair_attempts?: number; review?: { claims: Array<{ claim_id: string; verdict: string; reason: string }>; question_answered?: boolean; missing_material_topics?: string[] } }; quality_note: string }
export const terminal = (state: string) => ['succeeded', 'failed', 'cancelled', 'timed_out', 'insufficient_data'].includes(state)
export const directAnswerLabels: Record<DirectAnswer, string> = { yes: '是', no: '否', mixed: '证据混合', cannot_determine: '无法判断', not_applicable: '不适用' }
export const stateLabels: Record<string, string> = { queued: '等待运行', running: '正在研究', succeeded: '已完成', failed: '执行失败', cancelled: '已取消', timed_out: '达到时间边界', insufficient_data: '证据不足', started: '进行中', needs_attention: '需要处理', supported: '获得支持', partial: '部分支持', unsupported: '缺少支持', contradicted: '与证据冲突', unverifiable: '无法核实', investigating: '仍在研究', not_answerable_from_filings: '仅凭财报无法回答', answerable: '已有足够信息形成结论', evidence_exhausted: '当前财报已无更多有效信息', sufficient_evidence: '现有证据已足够', mixed: '支持与反证并存', rejected: '不再支持', unresolved: '尚未解决', required: '必答', supporting: '辅助', answered: '已回答', limited: '有边界结论', open: '待回答', high: '较高', medium: '中等', low: '较低', verified_fact: '披露事实', observation: '观察', supported_inference: '有证据的推断', inference: '分析推断', risk: '风险', hypothesis: '研究假设' }
export const metricLabels: Record<string, string> = { revenue: '营业收入', operating_cost: '营业成本', net_income: '净利润', operating_cash_flow: '经营活动现金流净额', accounts_receivable: '应收账款', inventory: '存货', gross_profit: '毛利润', gross_margin: '毛利率', cash_conversion: '利润现金转换比', absolute_change: '绝对变化', growth_rate: '增长率' }
const obj = (value: unknown): Json => value && typeof value === 'object' && !Array.isArray(value) ? value as Json : {}
const arr = (value: unknown): unknown[] => Array.isArray(value) ? value : []
const texts = (value: unknown): string[] => arr(value).filter((item): item is string => typeof item === 'string')
const text = (value: unknown, fallback = '') => typeof value === 'string' ? value : fallback
function source(value: unknown): Source {
  const valueObject = obj(value)
  const rawRows = arr(valueObject.rows)
  const rows: Cell[][] | undefined = Array.isArray(valueObject.rows) ? rawRows.map((row, rowIndex) => arr(Array.isArray(row) ? row : obj(row).cells).map((cell, columnIndex) => {
    const item = obj(cell)
    return { cell_id: text(item.cell_id, `r${rowIndex}c${columnIndex}`), text: typeof cell === 'string' ? cell : item.text == null ? null : String(item.text), rowspan: typeof item.rowspan === 'number' ? item.rowspan : undefined, colspan: typeof item.colspan === 'number' ? item.colspan : undefined, header: item.header === true }
  })) : undefined
  return { ...valueObject, artifact_id: text(valueObject.artifact_id || valueObject.fact_id || valueObject.calculation_id || valueObject.evidence_id || valueObject.chunk_id || valueObject.document_id), kind: text(valueObject.kind), document_id: text(valueObject.document_id || obj(valueObject.source).document_id), title: text(valueObject.title), label: text(valueObject.label), text: text(valueObject.text), rows, unit_candidates: texts(valueObject.unit_candidates), table_ids: texts(valueObject.table_ids), footnote_ids: texts(valueObject.footnote_ids) } as Source
}
function normalizeWorkspace(value: unknown): Workspace {
  const data = obj(value), working = obj(data.working ?? data.working_state), notebook = obj(working.notebook ?? working)
  const rawCatalog = arr(data.catalog)
  return { documents: arr(data.documents).map((item) => {
    const document = obj(item), company = obj(document.company), period = obj(document.reporting_period)
    const id = text(document.document_id)
    const pages = rawCatalog.filter((item) => obj(item).document_id === id && obj(item).kind === 'page')
    return { document_id: id, title: text(document.title, id), published_at: text(document.published_at), company: { legal_name: text(company.legal_name) }, period_label: text(document.period_label, `${period.fiscal_year ?? ''}${period.fiscal_period ?? ''}`), page_count: typeof document.page_count === 'number' ? document.page_count : pages.length && pages.some((item) => typeof obj(item).page_number === 'number') ? pages.length : null, table_count: typeof document.table_count === 'number' ? document.table_count : rawCatalog.filter((item) => obj(item).document_id === id && obj(item).kind === 'table').length }
  }), catalog: rawCatalog.map(source), facts: arr(data.facts).map((item) => ({ ...source(item), ...obj(item) } as Fact)), calculations: arr(data.calculations).map((item) => ({ ...source(item), ...obj(item) } as Calculation)), working: { objectives: arr(notebook.objectives).map((item) => { const objective = obj(item); return { ...objective, evidence_ids: texts(objective.evidence_ids), conclusion: text(objective.conclusion), remaining_uncertainty: text(objective.remaining_uncertainty) } as ResearchObjective }), hypotheses: arr(notebook.hypotheses).map((item) => { const hypothesis = obj(item); return { ...hypothesis, evidence_for: texts(hypothesis.evidence_for), evidence_against: texts(hypothesis.evidence_against), unknowns: texts(hypothesis.unknowns), would_change_conclusion: Array.isArray(hypothesis.would_change_conclusion) ? texts(hypothesis.would_change_conclusion).join('；') : text(hypothesis.would_change_conclusion) } as Hypothesis }), open_questions: arr(notebook.open_questions).map(obj), decision_summary: text(notebook.decision_summary) }, stop_decision: (data.stop_decision ?? data.dossier ?? null) as Dossier | null, gaps: arr(data.gaps ?? data.extraction_gaps).map((gap) => typeof gap === 'string' ? gap : text(obj(gap).message || obj(gap).reason, JSON.stringify(gap))), observed_evidence: arr(data.observed_evidence).map(source) }
}
async function read<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/v2${path}`, init)
  const body: unknown = await response.json().catch(() => ({}))
  if (!response.ok) {
    const value = obj(body), detail = obj(value.detail)
    throw new Error(text(detail.message || detail.code || value.message || value.code || value.detail, `HTTP ${response.status}`))
  }
  return body as T
}
const base = (runId: string) => `/research-runs/${encodeURIComponent(runId)}`
export const v2 = {
  capabilities: async () => {
    const value = await read<Json>('/capabilities')
    return { agent_ready: value.agent_ready === true || value.model_configured === true || value.agent_available === true || value.model_ready === true, version: text(value.version, '2.0.0') }
  },
  history: async () => {
    const value = await read<unknown>('/research-runs?limit=100')
    return (Array.isArray(value) ? value : arr(obj(value).runs)) as Run[]
  },
  run: (runId: string, signal?: AbortSignal) => read<Run>(base(runId), { signal }),
  workspace: async (runId: string, signal?: AbortSignal) => normalizeWorkspace(await read<unknown>(`${base(runId)}/workspace`, { signal })),
  result: (runId: string, signal?: AbortSignal) => read<Result>(`${base(runId)}/result`, { signal }),
  trace: (runId: string, after = 0, signal?: AbortSignal) => read<{ events: ResearchEvent[] }>(`${base(runId)}/trace?after=${after}`, { signal }),
  source: async (runId: string, sourceId: string, offset = 0, signal?: AbortSignal) => source(await read<unknown>(`${base(runId)}/sources/${encodeURIComponent(sourceId)}?offset=${offset}&max_chars=18000`, { signal })),
  submit: (payload: ResearchRequest) => read<{ run_id: string; created: boolean }>('/research-runs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }),
  cancel: (runId: string) => read<Run>(`${base(runId)}/cancel`, { method: 'POST' }),
}
