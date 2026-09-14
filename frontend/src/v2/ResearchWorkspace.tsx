import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowRight, BookOpen, ChevronRight, Clock, Code2, FileText, Layers, LoaderCircle, Search, ShieldCheck, Square, Table2, X } from 'lucide-react'
import { directAnswerLabels, metricLabels, stateLabels, terminal, v2 } from './api'
import type { Fact, Json, ResearchEvent, Result, Run, Source, Workspace } from './api'
import './workspace.css'

const emptyWorkspace: Workspace = { documents: [], catalog: [], facts: [], calculations: [], working: { objectives: [], hypotheses: [], open_questions: [] }, stop_decision: null, gaps: [], observed_evidence: [] }
const label = (value: string) => stateLabels[value] ?? value
const publicStatusText = (value: string) => value
  .replace(/\bevidence_exhausted\b/g, stateLabels.evidence_exhausted)
  .replace(/\bsufficient_evidence\b/g, stateLabels.sufficient_evidence)
  .replace(/\bnot_answerable_from_filings\b/g, stateLabels.not_answerable_from_filings)
  .replace(/\bneeds_attention\b/g, stateLabels.needs_attention)
  .replace(/\bnot_applicable\b/g, stateLabels.not_applicable ?? '不适用')
  .replace(/\banswerable\b/g, stateLabels.answerable)
  .replace(/\binvestigating\b/g, stateLabels.investigating)
  .replace(/\blimited\b/g, stateLabels.limited)
const publicTechnicalValue = (value: unknown): unknown => {
  if (Array.isArray(value)) return value.map(publicTechnicalValue)
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value as Json).map(([key, item]) => [key, publicTechnicalValue(item)]))
  if (typeof value === 'string') return publicStatusText(stateLabels[value] ?? value)
  return value
}
const timeLabel = (value: string) => new Date(value).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
const dateLabel = (value: string) => new Date(value).toLocaleDateString('zh-CN')
const asObject = (value: unknown): Json => value && typeof value === 'object' && !Array.isArray(value) ? value as Json : {}
const strings = (value: unknown): string[] => Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []


type MarketSelection = 'AUTO' | 'CN' | 'US' | 'HK'
type PeriodSuffix = 'FY' | 'H1' | 'Q1' | 'Q2' | 'Q3'
type PeriodYear = 'LATEST' | string
type PeriodType = 'AUTO' | PeriodSuffix

const periodSuffixes: Record<MarketSelection, PeriodSuffix[]> = {
  AUTO: ['FY', 'H1', 'Q1', 'Q2', 'Q3'],
  CN: ['FY', 'H1', 'Q1', 'Q3'],
  US: ['FY', 'Q1', 'Q2', 'Q3'],
  HK: ['FY', 'H1'],
}

const periodNames: Record<PeriodSuffix, string> = {
  FY: '年度报告',
  H1: '半年度报告',
  Q1: '第一季度报告',
  Q2: '第二季度报告',
  Q3: '第三季度报告',
}


const DEFAULT_RESEARCH_QUESTION = '请分析利润与经营现金流是否匹配，核对应收和存货，并结合财报解释主要风险。请先验证问题前提，不要假定现金流已经恶化。'
const researchQuestionPresets = [
  { label: '综合分析', question: DEFAULT_RESEARCH_QUESTION },
  { label: '盈利质量', question: '请分析盈利质量：净利润与经营现金流是否匹配，并解释主要差异、营运资金变化和一次性因素。' },
  { label: '增长驱动', question: '请分析本报告期收入和利润变化的主要驱动因素，并区分管理层明确披露与分析推断。' },
  { label: '现金流健康', question: '请分析现金流是否健康，综合经营现金流、净现金变化、投资与筹资活动以及营运资金因素。' },
  { label: '应收与存货', question: '请分析应收账款和存货的变化是否与收入增长匹配，并说明潜在回款、减值或库存风险。' },
  { label: '资本投入', question: '请分析公司的资本投入强度，重点看资本开支、固定资产或在建工程，以及它们与收入和现金流的关系。' },
  { label: '主要风险', question: '请基于本期财报识别最重要的经营和财务风险，并给出对应证据、反向证据与仍无法确认的边界。' },
  { label: '治理异常', question: '请检查财报中是否存在资金占用、违规担保、重大关联交易、内控缺陷或其他治理异常迹象；没有证据时不要推断存在。' },
] as const

function availableYears(now = new Date()) {
  const currentYear = now.getFullYear()
  return Array.from({ length: 6 }, (_, offset) => String(currentYear - offset))
}

function availablePeriodTypes(market: MarketSelection, year: PeriodYear, now = new Date()) {
  if (year === 'LATEST') return []
  const numericYear = Number(year)
  const currentYear = now.getFullYear()
  const currentMonth = now.getMonth() + 1
  const currentYearAvailable = new Set<PeriodSuffix>()
  if (currentMonth >= 4) currentYearAvailable.add('Q1')
  if (currentMonth >= 7) { currentYearAvailable.add('H1'); currentYearAvailable.add('Q2') }
  if (currentMonth >= 10) currentYearAvailable.add('Q3')
  if (numericYear < currentYear) return periodSuffixes[market]
  if (numericYear > currentYear) return []
  return periodSuffixes[market].filter((suffix) => currentYearAvailable.has(suffix))
}

function composePeriod(year: PeriodYear, periodType: PeriodType) {
  if (year === 'LATEST' || periodType === 'AUTO') return null
  return `${year}${periodType}`
}

function CitationButtons({ ids, onRead }: { ids: string[]; onRead: (id: string) => void }) {
  return <span className="rf2-citations">{ids.map((id, index) => <button type="button" key={id} onClick={() => onRead(id)} title={id}><BookOpen size={12} />证据 {index + 1}</button>)}</span>
}

function SourceContent({ runId, sourceId, onRead }: { runId: string; sourceId: string; onRead: (id: string) => void }) {
  const [source, setSource] = useState<Source | null>(null)
  const [error, setError] = useState('')
  const [view, setView] = useState<'text' | 'image'>('text')
  const [loadingMore, setLoadingMore] = useState(false)
  const [rowLimit, setRowLimit] = useState(40)
  const alive = useRef(true)
  useEffect(() => {
    alive.current = true
    const controller = new AbortController()
    void v2.source(runId, sourceId, 0, controller.signal).then(setSource).catch((caught: unknown) => {
      if (!controller.signal.aborted) setError(caught instanceof Error ? caught.message : String(caught))
    })
    return () => { alive.current = false; controller.abort() }
  }, [runId, sourceId])

  async function loadMore() {
    if (!source || source.next_offset == null || loadingMore) return
    setLoadingMore(true)
    try {
      const next = await v2.source(runId, sourceId, source.next_offset)
      if (alive.current) setSource((previous) => ({ ...next, text: (previous?.text ?? '') + (next.text ?? '') }))
    } catch (caught: unknown) {
      if (alive.current) setError(caught instanceof Error ? caught.message : String(caught))
    } finally { if (alive.current) setLoadingMore(false) }
  }
  if (error) return <p className="rf2-error" role="alert">{error}</p>
  if (!source) return <p className="rf2-loading"><LoaderCircle size={18} className="rf2-spin" />读取本次研究保存的来源…</p>
  const pageId = source.kind === 'page' ? source.artifact_id : source.page_id ?? source.source_locator?.page_id
  const tableId = source.source_locator?.table_id
  const canImage = Boolean(pageId && (source.page_number != null || source.source_locator?.page != null || source.visual_inspection_available))
  return <>
    <div className="rf2-source-heading"><span className="rf2-kicker">{source.kind === 'table' ? '原生表格 · 待核查结构' : '本次研究的来源记录'}</span><h3>{source.title || source.label || (source.metric_code ? metricLabels[source.metric_code] ?? source.metric_code : `来源 ${sourceId.slice(-10)}`)}</h3><small>{source.page_number != null ? `PDF 第 ${source.page_number} 页` : '保留原始来源定位'}</small></div>
    <div className="rf2-source-actions">
      {pageId && pageId !== sourceId && <button type="button" onClick={() => onRead(pageId)}>查看完整页 <ArrowRight size={13} /></button>}
      {tableId && tableId !== sourceId && <button type="button" onClick={() => onRead(tableId)}>定位来源表格</button>}
      {source.source_artifact_id && source.source_artifact_id !== sourceId && <button type="button" onClick={() => onRead(source.source_artifact_id!)}>展开来源上下文</button>}
      {source.document_id && <a href={`/v2/research-runs/${encodeURIComponent(runId)}/documents/${encodeURIComponent(source.document_id)}/original`} target="_blank" rel="noreferrer">原始财报文件</a>}
    </div>
    {canImage && <div className="rf2-segment" aria-label="来源展示方式"><button type="button" aria-pressed={view === 'text'} onClick={() => setView('text')}>文字 / 表格</button><button type="button" aria-pressed={view === 'image'} onClick={() => setView('image')}>实际页面图像</button></div>}
    {view === 'image' && canImage ? <figure className="rf2-page-image"><img src={`/v2/research-runs/${encodeURIComponent(runId)}/page-images/${encodeURIComponent(pageId!)}`} alt={`财报原始页面 ${source.page_number ?? source.source_locator?.page ?? ''}`} /><figcaption>原始 PDF 的页面渲染，不是模型重绘。</figcaption></figure> : <>
      {source.rows ? <>
        <p className="rf2-note">下表保留原生单元格。识别到的表头、单位、合并关系与脚注仍需结合原页核验，不自动等于规范财务事实。</p>
        {source.unit_candidates && source.unit_candidates.length > 0 && <p className="rf2-note">页面中的单位候选：{source.unit_candidates.join('；')}</p>}
        <div className="rf2-table-scroll" tabIndex={0} role="region" aria-label="财报原生表格"><table><caption>{source.title || '财报原生表格'} · {source.row_count ?? source.rows.length} 行</caption><tbody>{source.rows.slice(0, rowLimit).map((row, index) => <tr key={index}>{row.map((cell) => cell.header ? <th key={cell.cell_id} rowSpan={cell.rowspan} colSpan={cell.colspan} scope="col">{cell.text ?? '—'}</th> : <td key={cell.cell_id} rowSpan={cell.rowspan} colSpan={cell.colspan} title={cell.cell_id}>{cell.text ?? '—'}</td>)}</tr>)}</tbody></table></div>
        {source.rows.length > rowLimit && <button className="rf2-secondary" type="button" onClick={() => setRowLimit((value) => value + 40)}>继续显示表格（还有 {source.rows.length - rowLimit} 行）</button>}
      </> : <div className="rf2-source-text">{source.text || source.explanation || '这个来源没有可用文本，请查看关联页面或原始财报。'}</div>}
      {source.next_offset != null && <button className="rf2-secondary" type="button" disabled={loadingMore} onClick={() => void loadMore()}>{loadingMore ? '读取中…' : '继续读取后文'}</button>}
    </>}
    {source.table_ids && source.table_ids.length > 0 && <div className="rf2-related"><h4>本页表格</h4>{source.table_ids.map((id, index) => <button type="button" key={id} onClick={() => onRead(id)}><Table2 size={14} />表格 {index + 1}<ChevronRight size={13} /></button>)}</div>}
    {source.footnote_ids && source.footnote_ids.length > 0 && <div className="rf2-related"><h4>同页脚注候选</h4><p className="rf2-note">同页关联不等于已确认适用于此表，需查看原文。</p>{source.footnote_ids.map((id, index) => <button type="button" key={id} onClick={() => onRead(id)}>脚注 {index + 1}<ChevronRight size={13} /></button>)}</div>}
    {source.input_fact_ids && <div className="rf2-related"><h4>计算输入</h4><CitationButtons ids={source.input_fact_ids} onRead={onRead} /></div>}
    <details className="rf2-technical"><summary><Code2 size={14} />来源审计信息</summary><pre>{JSON.stringify({ artifact_id: source.artifact_id, document_id: source.document_id, text_hash: source.text_hash, extraction_status: source.extraction_status, source_locator: source.source_locator }, null, 2)}</pre></details>
  </>
}

function SourceDrawer({ runId, sourceId, onRead, onClose }: { runId: string; sourceId: string; onRead: (id: string) => void; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLElement>(null)
  const closeAction = useRef(onClose)
  useEffect(() => { closeAction.current = onClose }, [onClose])
  useEffect(() => {
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null
    closeRef.current?.focus()
    function key(event: KeyboardEvent) {
      if (event.key === 'Escape') { event.preventDefault(); closeAction.current() }
      if (event.key !== 'Tab') return
      const elements = panelRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], summary, [tabindex="0"]')
      if (!elements?.length) return
      const first = elements[0], last = elements[elements.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', key)
    return () => { document.removeEventListener('keydown', key); previous?.focus() }
  }, [])
  return <div className="rf2-drawer-overlay"><button className="rf2-drawer-backdrop" type="button" aria-label="关闭来源" onClick={onClose} tabIndex={-1} /><aside ref={panelRef} className="rf2-source-drawer" role="dialog" aria-modal="true" aria-labelledby="rf2-drawer-title"><header><h2 id="rf2-drawer-title"><BookOpen size={18} />证据与原文</h2><button type="button" ref={closeRef} onClick={onClose} aria-label="关闭证据面板"><X size={20} /></button></header><SourceContent key={`${runId}:${sourceId}`} runId={runId} sourceId={sourceId} onRead={onRead} /></aside></div>
}

function eventSummary(event: ResearchEvent): string {
  const result = asObject(event.data.result ?? event.data.output)
  if (event.event_type === 'research_reflection') {
    const completeness = asObject(event.data.completeness)
    const answered = Number(completeness.required_objectives_answered ?? 0)
    const limited = Number(completeness.required_objectives_limited ?? 0)
    const total = Number(completeness.required_objectives_total ?? 0)
    return `必答目标 ${answered + limited}/${total} 已形成结论；核心问题：${label(String(completeness.core_question_status ?? 'investigating'))}；继续研究价值：${label(String(completeness.expected_value_of_more_research ?? 'high'))}。`
  }
  if (event.event_type === 'research_provider_fallback') {
    const fromModel = String(event.data.from_model ?? '主模型')
    const toModel = String(event.data.to_model ?? '备用模型')
    return `${fromModel} 当前不可用；本 Run 已显式切换到 ${toModel}，沿用同一份已保存证据、研究目标与运行边界，不静默伪装成原模型。`
  }
  if (event.event_type === 'report_repair_requested') return '研究证据不变；本次只修正报告措辞、引用或数值声明，不重新搜索财报。'
  if (event.event_type === 'report_model_stalled') return '报告模型重复生成相同的无效草稿；系统停止重复调用，转入保守 Research Dossier 报告，不重新研究。'
  if (event.event_type === 'report_generation_fallback_requested') return '报告结构或上下文未满足交付契约；研究结果保持不变，正在改用保守 Research Dossier 报告。'
  if (event.event_type === 'report_repair_exhausted') return '模型报告连续修复仍未通过；不会重新启动研究，下一步只使用已经提交的研究 Dossier 生成保守报告。'
  if (event.event_type === 'safe_report_fallback_used') return '已使用 Research Objectives / Dossier 生成不新增推断或心算的保守报告；该报告仍经过确定性校验与独立语义复核。'
  if (event.event_type === 'safe_report_fallback_rejected') return '保守报告仍未通过确定性或语义校验；系统停止交付，但已完成的研究证据与轨迹仍然保留。'
  if (event.event_type === 'semantic_review_repair_requested') return '独立复核漏审或重复了结论；只重发复核结果，不改写研究报告，也不重新搜索财报。'
  if (event.event_type === 'semantic_review_provider_fallback') return 'Qwen 复核请求未返回；本次改用 DeepSeek 做降级复核，复核独立性降低。'
  if (event.event_type === 'model_request_failed') return '模型请求未返回可计量 usage；未把最坏费用上限记成实际估算费用，风险上限单独保留。'
  if (event.event_type === 'research_state_reference_correction') return '模型状态中出现无法映射到本次 Run 的引用；系统已移除并保守降级相关结论。'
  if (event.event_type === 'research_state_refresh_requested') return '新增证据可能改变研究状态，正在重新评估必答目标、假设与停止条件。'
  if (event.name === 'update_research_state') return publicStatusText(String(asObject(result.working_state).decision_summary ?? ''))
  if (event.name === 'submit_research') return publicStatusText(String(asObject(result.dossier).why_stop ?? ''))
  if (result.error) return String(result.message ?? result.error)
  if (Array.isArray(result.results)) return `本次返回 ${result.results.length} 项候选；新增 ${Number(event.data.new_observed_count ?? 0)} 条已见证据。检索命中不等于证明结论。`
  if (Array.isArray(result.facts)) return `返回 ${result.facts.length} 项规范财务事实。`
  if (result.formula_code) return `${metricLabels[String(result.formula_code)] ?? result.formula_code}：${result.value ?? '当前不适用'}。${result.explanation ?? ''}`
  if (Array.isArray(event.data.issues)) return strings(event.data.issues).join('；')
  return ''
}

function ResearchTimeline({ events, onRead }: { events: ResearchEvent[]; onRead: (id: string) => void }) {
  const [audit, setAudit] = useState(false)
  const finished = useMemo(() => new Set(events.filter((event) => event.event_type === 'span_finished').map((event) => event.span_id)), [events])
  const visible = events.filter((event) => audit || (
    ['run_queued', 'source_loaded', 'parse_progress', 'agent_turn', 'tool_result', 'research_state_refresh_requested', 'research_reflection', 'research_state_reference_correction', 'research_provider_fallback', 'report_repair_requested', 'report_model_stalled', 'report_generation_fallback_requested', 'report_repair_exhausted', 'safe_report_fallback_used', 'safe_report_fallback_rejected', 'semantic_review_repair_requested', 'semantic_review_provider_fallback', 'model_request_failed', 'validation_feedback', 'run_resumed', 'run_completed', 'run_failed', 'cancel_requested', 'context_compacted'].includes(event.event_type)
    || (event.event_type === 'span_started' && !finished.has(event.span_id))
    || (event.event_type === 'span_finished' && ['discovery', 'acquisition', 'document_parse', 'fact_extraction', 'bootstrap', 'synthesis', 'semantic_review', 'reference_validation'].includes(event.name))
  ))
  return <section className="rf2-panel"><div className="rf2-section-heading"><div><span className="rf2-kicker">RESEARCH JOURNAL</span><h2>研究过程</h2></div><button type="button" className="rf2-quiet" aria-pressed={audit} onClick={() => setAudit((value) => !value)}><Code2 size={15} />{audit ? '返回阅读视图' : '查看工程审计'}</button></div><p className="rf2-note">这里记录真实调用、来源和公开研究状态，不展示或虚构模型的隐藏思维链。</p>
    <div className="rf2-timeline">{visible.length === 0 && <p className="rf2-muted">任务事件将在后端保存后出现在这里。</p>}{visible.map((event) => {
      const summary = eventSummary(event)
      const result = asObject(event.data.result ?? event.data.output)
      const refs = strings(event.data.new_observed_evidence_ids)
      return <article className={`rf2-timeline-event ${event.status === 'failed' ? 'rf2-event-error' : ''}`} key={event.sequence}><div className="rf2-timeline-dot" /><div><div className="rf2-event-top"><time>{timeLabel(event.timestamp)}</time>{event.duration_ms != null && <span>{event.duration_ms < 1000 ? `${event.duration_ms} ms` : `${(event.duration_ms / 1000).toFixed(1)} s`}</span>}<span>{label(event.status)}</span></div><h3>{event.label}</h3>{summary && <p>{summary}</p>}{refs.length > 0 && <CitationButtons ids={refs} onRead={onRead} />}{typeof result.page_id === 'string' && <button type="button" className="rf2-text-link" onClick={() => onRead(result.page_id as string)}>查看该页</button>}<details className="rf2-technical"><summary>调用与返回详情</summary><pre>{JSON.stringify(audit ? event : publicTechnicalValue(event.data), null, 2)}</pre></details></div></article>
    })}</div>
  </section>
}

function FinancialFacts({ facts, onRead }: { facts: Fact[]; onRead: (id: string) => void }) {
  return <div className="rf2-facts-grid">{facts.map((fact) => <button type="button" key={fact.fact_id} className="rf2-fact" onClick={() => onRead(fact.fact_id)}><span>{metricLabels[fact.metric_code] ?? fact.metric_code}</span><strong>{Number.isFinite(Number(fact.value)) ? new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(Number(fact.value)) : fact.value}</strong><small>{fact.currency} · {fact.period.fiscal_year}{fact.period.fiscal_period} · {fact.period.period_basis === 'instant' ? '期末余额' : '报告期累计值'}</small><span className="rf2-fact-source"><BookOpen size={12} />查看来源</span></button>)}</div>
}

function RunPane({ runId, onRefreshHistory, onFollowUp }: { runId: string; onRefreshHistory: () => void; onFollowUp: (question: string, run: Run) => void }) {
  const [run, setRun] = useState<Run | null>(null)
  const [workspace, setWorkspace] = useState<Workspace>(emptyWorkspace)
  const [result, setResult] = useState<Result | null>(null)
  const [events, setEvents] = useState<ResearchEvent[]>([])
  const [error, setError] = useState('')
  const [streamState, setStreamState] = useState('正在连接研究事件')
  const [tab, setTab] = useState<'report' | 'sources' | 'journal'>('report')
  const [sourceId, setSourceId] = useState<string | null>(null)
  const [sourceQuery, setSourceQuery] = useState('')
  const [sourceKind, setSourceKind] = useState('table')
  const [sourceLimit, setSourceLimit] = useState(30)
  const [cancelling, setCancelling] = useState(false)
  const historyCallback = useRef(onRefreshHistory)
  useEffect(() => { historyCallback.current = onRefreshHistory }, [onRefreshHistory])
  useEffect(() => {
    const controller = new AbortController()
    let active = true, busy = false, cursor = 0, isTerminal = false
    let stream: EventSource | null = null
    function merge(batch: ResearchEvent[]) {
      if (!active || batch.length === 0) return
      cursor = Math.max(cursor, ...batch.map((event) => event.sequence))
      setEvents((previous) => [...new Map([...previous, ...batch].map((event) => [event.sequence, event])).values()].sort((a, b) => a.sequence - b.sequence))
    }
    async function refresh() {
      if (!active || busy) return
      busy = true
      try {
        const current = await v2.run(runId, controller.signal)
        if (!active) return
        setRun(current)
        const [data, trace] = await Promise.all([v2.workspace(runId, controller.signal), v2.trace(runId, cursor, controller.signal)])
        if (!active) return
        setWorkspace(data); merge(trace.events); setError('')
        if (current.lifecycle_state === 'succeeded') {
          const report = await v2.result(runId, controller.signal)
          if (active) setResult(report)
        }
        if (terminal(current.lifecycle_state)) {
          isTerminal = true; stream?.close()
          if (active) { setStreamState('已读取持久化研究记录'); historyCallback.current() }
        }
      } catch (caught: unknown) {
        if (active && !controller.signal.aborted) setError(caught instanceof Error ? caught.message : String(caught))
      } finally { busy = false }
    }
    void refresh()
    if (typeof EventSource !== 'undefined') {
      stream = new EventSource(`/v2/research-runs/${encodeURIComponent(runId)}/events`)
      stream.onopen = () => { if (active) setStreamState('实时事件已连接') }
      stream.addEventListener('research', (message) => {
        if (!active) return
        try { merge([JSON.parse((message as MessageEvent<string>).data) as ResearchEvent]) } catch { /* Status polling remains authoritative. */ }
      })
      stream.addEventListener('terminal', () => { stream?.close(); void refresh() })
      stream.onerror = () => { if (active && !isTerminal) setStreamState('事件连接重试中，状态查询仍在继续') }
    }
    const timer = window.setInterval(() => { if (!isTerminal) void refresh() }, 2500)
    return () => { active = false; controller.abort(); stream?.close(); window.clearInterval(timer) }
  }, [runId])

  async function cancel() {
    setCancelling(true)
    try { setRun(await v2.cancel(runId)); onRefreshHistory() }
    catch (caught: unknown) { setError(caught instanceof Error ? caught.message : String(caught)) }
    finally { setCancelling(false) }
  }
  const catalog = workspace.catalog.filter((item) => item.kind === sourceKind && `${item.title ?? ''} ${item.label ?? ''} ${item.page_number ?? ''} ${item.artifact_id}`.toLowerCase().includes(sourceQuery.toLowerCase()))
  const review = result?.semantic_review.review
  const reviewCounts = (review?.claims ?? []).reduce<Record<string, number>>((counts, item) => { counts[item.verdict] = (counts[item.verdict] ?? 0) + 1; return counts }, {})
  const semanticSummary = review ? `语义复核：${reviewCounts.supported ?? 0} 项支持，${reviewCounts.partial ?? 0} 项有条件支持${(reviewCounts.unsupported ?? 0) + (reviewCounts.contradicted ?? 0) > 0 ? `，${(reviewCounts.unsupported ?? 0) + (reviewCounts.contradicted ?? 0)} 项需修正` : ''}` : '语义复核尚未完成'
  const reviewBoundary = result?.semantic_review.independence === 'independent_provider'
    ? '本次由独立 Provider 复核，但仍不是准确性保证。'
    : result?.semantic_review.independence === 'reduced_same_provider'
      ? 'Qwen 复核未返回，本次由研究 Provider DeepSeek 降级复核；独立性降低，不能视为独立交叉验证。'
      : result?.semantic_review.independence === 'same_provider'
        ? '本次复核与研究使用同一 Provider，不属于独立交叉验证。'
        : '语义复核是模型判断，不是准确性保证。'
  return <div className="rf2-run-workspace">
    <div className="rf2-run-heading"><div><span className="rf2-kicker">FILING RESEARCH</span><h1>{workspace.documents[0]?.company.legal_name ?? run?.request.company_query ?? '正在读取研究任务'}</h1><p>{run?.request.research_question}</p><div className="rf2-metadata"><span><FileText size={13} />{workspace.documents.map((doc) => doc.period_label).join(' · ') || run?.request.requested_period_label || '最新可用报告'}</span>{run && <span><Clock size={13} />资料截止 {dateLabel(run.request.research_time)}</span>}</div></div><div className="rf2-run-status"><span className={`rf2-status ${run?.lifecycle_state ?? ''}`}>{run && !terminal(run.lifecycle_state) && <LoaderCircle size={14} className="rf2-spin" />}{run ? label(run.lifecycle_state) : '读取中'}</span>{run && !terminal(run.lifecycle_state) && <button type="button" className="rf2-quiet" disabled={cancelling || run.cancel_requested} onClick={() => void cancel()}><Square size={12} />{run.cancel_requested ? '取消已请求' : cancelling ? '请求取消…' : '取消研究'}</button>}<small>{streamState}</small></div></div>
    <nav className="rf2-tabs" aria-label="研究工作台视图">{[['report', '研究报告', FileText], ['sources', '财报与表格', Table2], ['journal', '研究过程', Layers]].map(([key, text, Icon]) => { const TabIcon = Icon as typeof FileText; return <button key={key as string} type="button" aria-current={tab === key ? 'page' : undefined} onClick={() => setTab(key as typeof tab)}><TabIcon size={16} />{text as string}{key === 'journal' && <span>{events.filter((event) => event.event_type === 'tool_result').length} 次工具调用</span>}</button> })}</nav>
    {error && <div className="rf2-error" role="alert">{error}<p>已保存的记录不会因为浏览器断线丢失。可在左侧重新选择该任务。</p></div>}
    {run?.failure && <div className="rf2-failure" role="alert"><h2>这次研究尚未生成报告</h2><p>{run.failure.message}</p><code>{run.failure.code}</code><p>已获取的财报、表格候选和执行记录仍可查看。任务失败不代表已经完成研究。</p><button type="button" onClick={() => setTab('journal')}>查看失败位置 <ArrowRight size={14} /></button></div>}
    {tab === 'report' && <>
      {!result && !run?.failure && <section className="rf2-panel rf2-progress"><LoaderCircle size={28} className="rf2-spin" /><h2>{events.at(-1)?.label ?? '准备研究环境'}</h2><p>资料会先被核验和保存，再交给代理按问题查阅、计算与验证。报告尚未通过检查前，不会展示成品结论。</p><button className="rf2-text-link" type="button" onClick={() => setTab('journal')}>查看正在进行的研究 <ArrowRight size={14} /></button></section>}
      {workspace.working.objectives.length > 0 && <section className="rf2-panel"><div className="rf2-section-heading"><div><span className="rf2-kicker">RESEARCH OBJECTIVES</span><h2>这次研究必须回答什么</h2></div><span>{workspace.working.objectives.filter((item) => item.priority === 'required' && item.status !== 'open').length}/{workspace.working.objectives.filter((item) => item.priority === 'required').length} 个必答目标已形成结论</span></div><div className="rf2-objectives">{workspace.working.objectives.map((objective) => <article className={`rf2-objective rf2-objective-${objective.status}`} key={objective.objective_id}><div><span className="rf2-status">{label(objective.priority)}</span><span className="rf2-status">{label(objective.status)}</span></div><h3>{objective.question}</h3>{objective.conclusion && <p>{objective.conclusion}</p>}<CitationButtons ids={objective.evidence_ids} onRead={setSourceId} />{objective.remaining_uncertainty && <p className="rf2-note">仍有边界：{objective.remaining_uncertainty}</p>}</article>)}</div></section>}
      {result && <>
        <section className="rf2-conclusion"><span className="rf2-kicker">研究结论</span>{result.report.direct_answer && result.report.direct_answer !== 'not_applicable' && <div className={`rf2-direct-answer rf2-direct-${result.report.direct_answer}`}><span>直接答案</span><strong>{directAnswerLabels[result.report.direct_answer]}</strong></div>}<h2>{result.report.title}</h2><p>{result.report.executive_summary}</p><div className="rf2-trust-note"><ShieldCheck size={16} /><span>引用与声明数值已检查；{semanticSummary}。{reviewBoundary}</span></div></section>
        <section className="rf2-panel"><div className="rf2-section-heading"><h2>关键发现</h2><span>{result.report.findings.length} 项分析</span></div><div className="rf2-findings">{result.report.findings.map((finding, index) => {
          const verdict = review?.claims.find((item) => item.claim_id === finding.claim_id)
          return <article className="rf2-finding" key={finding.claim_id}><span className="rf2-finding-number">{String(index + 1).padStart(2, '0')}</span><div><div className="rf2-finding-meta"><span>{label(finding.kind)}</span><span>研究判断置信度：{label(finding.confidence)}</span>{verdict && <span className={`rf2-review-verdict rf2-review-${verdict.verdict}`}>语义复核：{label(verdict.verdict)}</span>}</div><h3>{finding.title}</h3><p>{finding.text}</p><CitationButtons ids={finding.evidence_ids} onRead={setSourceId} />{finding.uncertainty && <p className="rf2-note">证据边界：{finding.uncertainty}</p>}{(finding.fact_ids.length > 0 || finding.calculation_ids.length > 0) && <details className="rf2-technical"><summary>相关数字与计算</summary><CitationButtons ids={[...finding.fact_ids, ...finding.calculation_ids]} onRead={setSourceId} /></details>}{verdict && <details className="rf2-technical"><summary>语义复核：{label(verdict.verdict)}</summary><p>{verdict.reason}</p></details>}</div></article>
        })}</div></section>
        <section className="rf2-panel"><div className="rf2-section-heading"><h2>深入分析</h2></div>{result.report.sections.map((section, index) => <article className="rf2-analysis" key={`${section.title}:${index}`}><h3>{section.title}</h3><p>{section.text}</p><CitationButtons ids={section.evidence_ids} onRead={setSourceId} /></article>)}</section>
      </>}
      {workspace.facts.length > 0 && <section className="rf2-panel"><div className="rf2-section-heading"><h2>财务事实</h2><span>点击追溯来源</span></div><p className="rf2-note">金额以原币基础单位显示。期末余额与报告期累计值分开标注；没有可比期间时不生成趋势。</p><FinancialFacts facts={workspace.facts} onRead={setSourceId} /></section>}
      {workspace.working.hypotheses.length > 0 && <section className="rf2-panel"><div className="rf2-section-heading"><h2>假设与反向检验</h2><span>公开研究笔记</span></div>{workspace.working.hypotheses.map((hypothesis) => <article className="rf2-hypothesis" key={hypothesis.hypothesis_id}><span className="rf2-status">{label(hypothesis.status)}</span><h3>{hypothesis.statement}</h3><div><strong>支持材料</strong><CitationButtons ids={hypothesis.evidence_for} onRead={setSourceId} /></div><div><strong>相反材料</strong>{hypothesis.evidence_against.length ? <CitationButtons ids={hypothesis.evidence_against} onRead={setSourceId} /> : <span className="rf2-note">尚无已记录的相反材料，不代表不存在反证。</span>}</div>{hypothesis.unknowns.length > 0 && <p>仍需确认：{hypothesis.unknowns.join('；')}</p>}{hypothesis.would_change_conclusion && <p className="rf2-note">什么会改变判断：{hypothesis.would_change_conclusion}</p>}</article>)}</section>}
      {workspace.stop_decision && <section className="rf2-panel"><span className="rf2-kicker">STOP DECISION</span><h2>为什么在这里结束研究</h2><p>{workspace.stop_decision.why_stop}</p><p className="rf2-note">{workspace.stop_decision.stop_reason === 'sufficient_evidence' ? '代理判断：现有证据已足以回答。' : '代理判断：当前财报已无更多有效信息，保留无法确认的部分。'}</p>{workspace.stop_decision.remaining_uncertainties.map((item, index) => <p className="rf2-limitation" key={index}>{item}</p>)}</section>}
      {result && <section className="rf2-panel"><h2>限制与验证边界</h2>{result.report.limitations.map((item, index) => <p className="rf2-limitation" key={index}>{item}</p>)}<p className="rf2-note">{result.quality_note}</p><p className="rf2-note">独立质量基准尚未对本次报告评分，不展示虚构的总分。</p>{result.report.follow_up_questions.length > 0 && run && <div className="rf2-followups"><h3>进一步研究</h3><p className="rf2-note">以下会发起新的同公司研究，暂不是继承历史论点的连续会话。</p>{result.report.follow_up_questions.map((question) => <button type="button" key={question} onClick={() => onFollowUp(question, run)}>{question}<ArrowRight size={15} /></button>)}</div>}</section>}
    </>}
    {tab === 'sources' && <>
      <section className="rf2-panel"><div className="rf2-section-heading"><h2>本次研究的完整财报</h2><span>{workspace.documents.length} 份来源</span></div>{workspace.documents.map((document) => <article className="rf2-document" key={document.document_id}><FileText size={23} /><div><h3>{document.title}</h3><p>{document.period_label} · {document.page_count == null ? 'HTML 原始文件' : `${document.page_count} 页`} · {document.table_count} 个表格候选</p><small>披露于 {dateLabel(document.published_at)}</small></div><button type="button" className="rf2-secondary" onClick={() => setSourceId(document.document_id)}>阅读原文</button></article>)}{workspace.documents.length === 0 && <p className="rf2-note">尚未获得可查阅的财报包。下载或解析失败的详细位置见研究过程。</p>}<details className="rf2-technical"><summary>解析覆盖与已知限制</summary>{workspace.gaps.map((gap, index) => <p key={index}>{gap}</p>)}</details></section>
      <section className="rf2-panel"><div className="rf2-section-heading"><h2>在原文中导航</h2><span>不是只有 Top-K 片段</span></div><div className="rf2-source-filters"><select aria-label="来源类型" value={sourceKind} onChange={(event) => { setSourceKind(event.target.value); setSourceLimit(30) }}><option value="table">表格</option><option value="page">页面 / HTML 区段</option><option value="section">章节</option><option value="figure">图像候选</option><option value="footnote">脚注候选</option></select><label><Search size={15} /><input aria-label="筛选来源目录" placeholder="按标题或页码筛选目录" value={sourceQuery} onChange={(event) => { setSourceQuery(event.target.value); setSourceLimit(30) }} /></label></div><div className="rf2-catalog">{catalog.slice(0, sourceLimit).map((item) => <button type="button" key={item.artifact_id} onClick={() => setSourceId(item.artifact_id)}><span>{item.kind === 'table' ? <Table2 size={17} /> : <FileText size={17} />}<strong>{item.title || item.label || `${item.kind} · ${item.page_number != null ? `P${item.page_number}` : item.artifact_id.slice(-8)}`}</strong><small>{item.row_count != null ? `${item.row_count} 行 × ${item.column_count} 列` : item.extraction_status}</small></span><ChevronRight size={15} /></button>)}</div>{catalog.length === 0 && <p className="rf2-note">这个分类没有匹配目录项；没有提取到结构不等于财报里没有，可以回到完整页查看。</p>}{catalog.length > sourceLimit && <button className="rf2-secondary" type="button" onClick={() => setSourceLimit((count) => count + 30)}>显示更多（还有 {catalog.length - sourceLimit} 项）</button>}</section>
    </>}
    {tab === 'journal' && <ResearchTimeline events={events} onRead={setSourceId} />}
    <div className="rf2-run-footer"><span>Run {runId.slice(-12)} · 来源固定，历史不随重新下载改写</span><a href={`/v2/research-runs/${encodeURIComponent(runId)}/trace`} target="_blank" rel="noreferrer">原始事件记录</a></div>
    {sourceId && <SourceDrawer runId={runId} sourceId={sourceId} onRead={setSourceId} onClose={() => setSourceId(null)} />}
  </div>
}

export default function ResearchWorkspace() {
  const [company, setCompany] = useState('宁德时代')
  const [market, setMarket] = useState<MarketSelection>('CN')
  const [periodYear, setPeriodYear] = useState<PeriodYear>('2024')
  const [periodType, setPeriodType] = useState<PeriodType>('H1')
  const [question, setQuestion] = useState(DEFAULT_RESEARCH_QUESTION)
  const [selected, setSelected] = useState<string | null>(() => { try { return localStorage.getItem('researchforge.v2.selected') } catch { return null } })
  const [history, setHistory] = useState<Run[]>([])
  const [capabilities, setCapabilities] = useState<{ agent_ready: boolean; version: string } | null>(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const yearOptions = useMemo(() => availableYears(), [])
  const periodTypeOptions = useMemo(() => availablePeriodTypes(market, periodYear), [market, periodYear])
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    void v2.capabilities().then((data) => { if (mounted.current) setCapabilities(data) }).catch(() => { if (mounted.current) setError('V2 后端尚未连接。旧版入口仍可使用。') })
    void v2.history().then((data) => { if (mounted.current) setHistory(data) }).catch(() => undefined)
    return () => { mounted.current = false }
  }, [])
  function selectRun(id: string) {
    setSelected(id)
    try { localStorage.setItem('researchforge.v2.selected', id) } catch { /* History remains on the server. */ }
  }
  function refreshHistory() { void v2.history().then((data) => { if (mounted.current) setHistory(data) }).catch(() => undefined) }
  const primaryHistory = history.filter((item) => ['queued', 'running', 'succeeded'].includes(item.lifecycle_state)).slice(0, 8)
  const diagnosticHistory = history.filter((item) => !['queued', 'running', 'succeeded'].includes(item.lifecycle_state)).slice(0, 24)
  function historyButton(item: Run) {
    return <button type="button" key={item.run_id} aria-current={selected === item.run_id ? 'page' : undefined} onClick={() => selectRun(item.run_id)}><strong>{item.request.company_query}</strong><span>{item.request.requested_period_label ?? '最新报告'} · {dateLabel(item.created_at)}</span><p>{item.request.research_question}</p><small>{label(item.lifecycle_state)}</small></button>
  }
  async function submit(nextQuestion = question, previous?: Run) {
    if (submitting) return
    setSubmitting(true); setError('')
    try {
      const created = await v2.submit({ company_query: previous?.request.company_query ?? company.trim(), market_hint: previous?.request.market_hint ?? (market === 'AUTO' ? null : market), requested_period_label: previous?.request.requested_period_label ?? composePeriod(periodYear, periodType), research_question: nextQuestion, research_time: new Date().toISOString(), idempotency_key: crypto.randomUUID() })
      if (mounted.current) { selectRun(created.run_id); refreshHistory() }
    } catch (caught: unknown) { if (mounted.current) setError(caught instanceof Error ? caught.message : String(caught)) }
    finally { if (mounted.current) setSubmitting(false) }
  }
  return <div className="rf2-app"><header className="rf2-header"><a href="/" className="rf2-brand"><span>RF</span><div><strong>ResearchForge</strong><small>财报研究工作台</small></div></a><div className="rf2-header-right"><span className="rf2-alpha">V2 · 开发预览</span></div></header><div className="rf2-layout"><aside className="rf2-sidebar"><div className="rf2-sidebar-intro"><span className="rf2-kicker">从财报到可核查的判断</span><h2>开始一项研究</h2><p>让代理围绕问题阅读原文、检验假设，并留下可回看的证据链。</p></div><form onSubmit={(event) => { event.preventDefault(); void submit() }}><label>公司或股票代码<input aria-label="V2 公司" value={company} onChange={(event) => setCompany(event.target.value)} placeholder="公司名称 / ticker" required /></label><div className="rf2-form-row"><label>市场<select aria-label="V2 市场" value={market} onChange={(event) => { const nextMarket = event.target.value as MarketSelection; setMarket(nextMarket); if (periodType !== 'AUTO' && !periodSuffixes[nextMarket].includes(periodType)) { setPeriodYear('LATEST'); setPeriodType('AUTO') } }}><option value="AUTO">自动识别</option><option value="CN">A 股</option><option value="US">美股</option><option value="HK">港股</option></select></label><label>年份<select aria-label="V2 年份" value={periodYear} onChange={(event) => { const nextYear = event.target.value as PeriodYear; setPeriodYear(nextYear); if (nextYear === 'LATEST') setPeriodType('AUTO'); else if (periodType === 'AUTO' || !availablePeriodTypes(market, nextYear).includes(periodType)) setPeriodType(availablePeriodTypes(market, nextYear)[0] ?? 'AUTO') }}><option value="LATEST">最新</option>{yearOptions.map((year) => <option key={year} value={year}>{year}</option>)}</select></label></div><label>报告类型<select aria-label="V2 报告类型" value={periodType} disabled={periodYear === 'LATEST'} onChange={(event) => setPeriodType(event.target.value as PeriodType)}><option value="AUTO">自动选择</option>{periodTypeOptions.map((suffix) => <option key={suffix} value={suffix}>{periodNames[suffix]}（{suffix}）</option>)}</select></label><label>研究问题<textarea aria-label="V2 研究问题" rows={6} value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={4000} required /></label><div className="rf2-question-presets" aria-label="常用研究问题"><div><span>常用问题</span><small>点击填入，可继续修改</small></div><div>{researchQuestionPresets.map((preset) => <button type="button" key={preset.label} aria-pressed={question === preset.question} onClick={() => setQuestion(preset.question)}>{preset.label}</button>)}</div></div><button type="submit" className="rf2-primary" disabled={submitting || capabilities?.agent_ready !== true || !company.trim() || !question.trim()}>{submitting ? <LoaderCircle className="rf2-spin" size={16} /> : <ArrowRight size={16} />}{submitting ? '创建研究任务…' : '开始财报研究'}</button><p className="rf2-note">{capabilities ? capabilities.agent_ready ? '模型配置已就绪，余额与可调用性以实际服务响应为准。' : '研究模型尚未配置，不能以确定性模拟替代代理。' : '正在读取运行能力…'}</p></form>{error && <p className="rf2-error" role="alert">{error}</p>}<section className="rf2-history"><div><h3>最近研究</h3><button type="button" className="rf2-quiet" onClick={refreshHistory}>刷新</button></div>{history.length === 0 && <p className="rf2-note">研究记录保存在后端，完成与失败都会保留。</p>}{primaryHistory.map(historyButton)}{diagnosticHistory.length > 0 && <details className="rf2-history-diagnostics"><summary>失败、取消与证据不足记录（{diagnosticHistory.length}）</summary><div>{diagnosticHistory.map(historyButton)}</div></details>}</section><div className="rf2-scope"><ShieldCheck size={16} /><p>当前只研究官方财务披露。原生表格提取、模型分析和独立质量评测分开标识。</p></div></aside><main className="rf2-main">{selected ? <RunPane key={selected} runId={selected} onRefreshHistory={refreshHistory} onFollowUp={(nextQuestion, run) => { setQuestion(nextQuestion); void submit(nextQuestion, run) }} /> : <section className="rf2-welcome"><div className="rf2-welcome-icon"><BookOpen size={38} /></div><span className="rf2-kicker">EVIDENCE BEFORE NARRATIVE</span><h1>不只读出数字，<br />还要看清判断的依据。</h1><p>完整财报始终可查。代理能够搜索段落、展开表格、核对原页和计算事实；研究结束后，你可以沿每一条重要结论回到来源。</p><div className="rf2-welcome-features"><span><Table2 size={18} />原文、表格与页面</span><span><Layers size={18} />真实研究轨迹</span><span><ShieldCheck size={18} />明确的证据边界</span></div><small>V2 仍在验证中。工程测试通过不代表真实模型研究质量已验收。</small></section>}</main></div><footer className="rf2-footer">财报研究辅助工具，不构成投资建议。模型判断与解析候选均可能出错，请核查重要结论的原始依据。</footer></div>
}
