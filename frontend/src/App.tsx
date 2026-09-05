import {
  Activity,
  ArrowUpRight,
  BarChart3,
  BookOpenCheck,
  Check,
  ChevronRight,
  CircleAlert,
  FlaskConical,
  GitBranch,
  LoaderCircle,
  Search,
  ShieldCheck,
  Sparkles,
  Square,
  Workflow,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { api } from './api'
import type {
  CalculationRecord,
  Claim,
  EvidenceChunk,
  EvaluationBatch,
  EvolutionArtifacts,
  EvolutionExperiment,
  FinancialFact,
  ResearchResult,
  RunManifest,
  TaskType,
  Trace,
  Experience,
  FailureCluster,
  SkillPatch,
  TechnicalRetries,
  ValidationDecision,
  ContingencyActivation,
  ProjectResearchOutcome,
} from './types'

const taskLabels: Record<TaskType, string> = {
  company_research: '公司研究',
  filing_analysis: '财报分析',
  peer_comparison: '同行比较',
  thesis_investigation: '命题检验',
  risk_detection: '风险扫描',
}

const stageLabels: Record<string, string> = {
  understanding_question: '理解问题',
  planning: '制定计划',
  loading_financial_data: '加载事实',
  retrieving_evidence: '定位证据',
  calculating: '确定性计算',
  cross_checking: '交叉核验',
  searching_counter_evidence: '搜索反证',
  forming_conclusion: '形成结论',
  validating_output: '验证结构',
  completed: '完成',
}

const metricLabels: Record<string, string> = {
  revenue: '营业收入',
  operating_cost: '营业成本',
  net_income: '净利润',
  operating_cash_flow: '经营现金流',
  accounts_receivable: '应收账款',
  inventory: '存货',
}

const researchTemplates = [
  ['完整分析', '帮我完整分析一下这家公司，覆盖业绩、增长、业务结构、财务质量、主要风险和管理层展望。'],
  ['业绩变化', '最近一个报告期的业绩发生了什么重要变化？主要原因是什么？'],
  ['增长来源', '这家公司最近的增长主要来自哪里？哪些业务或因素贡献最大？'],
  ['盈利能力', '这家公司的盈利能力怎么样？毛利率和利润变化主要受什么影响？'],
  ['现金流', '利润有没有真正转化成经营现金流？现金流质量有哪些值得注意的地方？'],
  ['财务风险', '当前最值得关注的三个财务或经营风险是什么？请按证据强弱排序。'],
  ['业务结构', '公司的主要业务和分部结构是什么？最近发生了哪些重要变化？'],
  ['管理层展望', '管理层如何描述未来增长、经营重点和主要不确定性？'],
  ['异常扫描', '这份官方报告里有哪些异常信号、矛盾或值得进一步验证的地方？'],
] as const

const terminalStateGuidance: Record<string, { title: string; action: string }> = {
  insufficient_data: {
    title: '资料不足，ResearchForge 已弃权',
    action: '检查公司、市场、报告期和研究截止时间；只有官方来源可定位且可可靠解析时才会生成报告。',
  },
  cancelled: { title: '研究已取消', action: '本次没有生成研究结果；如需继续，请重新发起一次新研究。' },
  failed: { title: '研究执行失败', action: '保留 Run ID 并检查 Research Trace；失败状态不会被包装成结论。' },
  timed_out: { title: '研究超时', action: '检查后端运行状态和 Trace 后再决定是否使用相同输入重试。' },
}

function formatFact(fact: FinancialFact): string {
  if (fact.value === null) return '不可用'
  if (fact.measurement_unit === 'CURRENCY') {
    const number = Number(fact.value) / 100_000_000
    return `${new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(number)} 亿元`
  }
  return fact.value
}

function statusTone(status: string): string {
  if (['succeeded', 'performed', 'PASS', 'completed'].includes(status)) return 'good'
  if (['failed', 'FAIL', 'timed_out'].includes(status)) return 'bad'
  if (['running', 'queued', 'uncertain'].includes(status)) return 'active'
  return 'muted'
}

function averageScore(batch: EvaluationBatch | null): string {
  if (!batch || batch.evaluations.length === 0) return '—'
  const total = batch.evaluations.reduce((sum, item) => sum + item.metrics.task_score, 0)
  return (total / batch.evaluations.length).toFixed(3)
}

function failedEvaluationCount(batch: EvaluationBatch | null): number {
  return batch?.evaluations.filter((item) => item.failure_events.length > 0).length ?? 0
}

function failureEventCount(batch: EvaluationBatch | null): number {
  return batch?.evaluations.reduce((sum, item) => sum + item.failure_events.length, 0) ?? 0
}

function EvidenceLink({
  claim,
  facts,
  evidence,
}: {
  claim: Claim
  facts: FinancialFact[]
  evidence: EvidenceChunk[]
}) {
  const linked = claim.fact_ids
    .map((id) => facts.find((fact) => fact.fact_id === id))
    .filter((fact): fact is FinancialFact => Boolean(fact))
  const citations = claim.support_evidence_ids
    .map((id) => evidence.find((chunk) => chunk.chunk_id === id))
    .filter((chunk): chunk is EvidenceChunk => Boolean(chunk))
  const separator = claim.text.indexOf(': ')
  const headline = separator > 0 ? claim.text.slice(0, separator) : claim.text
  const analysis = separator > 0 ? claim.text.slice(separator + 2) : ''
  return (
    <article className="claim-card">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`status-pill ${statusTone(claim.epistemic_status)}`}>
          {claim.epistemic_status}
        </span>
        <span className="micro-label">{claim.claim_type}</span>
        <span className="micro-label">置信度 {claim.confidence.level}</span>
      </div>
      <h3 className="finding-headline">{headline}</h3>
      {analysis && <p className="finding-analysis">{analysis}</p>}
      {linked.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {linked.map((fact) => (
            <span className="fact-chip" key={fact.fact_id} title={fact.fact_id}>
              {metricLabels[fact.metric_code] ?? fact.metric_code} · {formatFact(fact)}
            </span>
          ))}
        </div>
      )}
      <small className="finding-provenance">
        {linked.length} 项相关事实 · {claim.support_evidence_ids.length} 条支持证据
      </small>
      {citations.length > 0 && (
        <details className="claim-evidence">
          <summary>查看支持证据 ({citations.length})</summary>
          <div className="claim-evidence-list">
            {citations.map((chunk) => (
              <article key={chunk.chunk_id}>
                <strong>{chunk.section} · P{chunk.locator.page_start}</strong>
                <p>{chunk.text}</p>
                <a href={chunk.source_uri} rel="noreferrer" target="_blank">
                  打开官方披露 <ArrowUpRight size={12} />
                </a>
              </article>
            ))}
          </div>
        </details>
      )}
    </article>
  )
}

function ResearchPage() {
  const [companyQuery, setCompanyQuery] = useState('贵州茅台')
  const [marketHint, setMarketHint] = useState<'AUTO' | 'CN' | 'US' | 'HK'>('AUTO')
  const [periodLabel, setPeriodLabel] = useState('')
  const [question, setQuestion] = useState('帮我完整分析一下这家公司，覆盖业绩、增长、业务结构、财务质量、主要风险和管理层展望。')
  const [manifest, setManifest] = useState<RunManifest | null>(null)
  const [result, setResult] = useState<ResearchResult | null>(null)
  const [trace, setTrace] = useState<Trace | null>(null)
  const [facts, setFacts] = useState<FinancialFact[]>([])
  const [evidence, setEvidence] = useState<EvidenceChunk[]>([])
  const [calculations, setCalculations] = useState<CalculationRecord[]>([])
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [cancelling, setCancelling] = useState(false)

  const latestFacts = useMemo(() => {
    const byMetric = new Map<string, FinancialFact>()
    for (const fact of facts) {
      const key = `${fact.company.company_id}:${fact.metric_code}`
      const current = byMetric.get(key)
      const factPeriod = `${fact.period.fiscal_year}${fact.period.fiscal_period}`
      const currentPeriod = current
        ? `${current.period.fiscal_year}${current.period.fiscal_period}`
        : ''
      if (!current || factPeriod > currentPeriod) byMetric.set(key, fact)
    }
    return [...byMetric.values()]
  }, [facts])

  const supportingEvidence = useMemo(
    () => evidence.filter((chunk) => !chunk.section.startsWith('Counter evidence:')),
    [evidence],
  )

  async function poll(runId: string) {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      const next = await api.manifest(runId)
      setManifest(next)
      if (!['queued', 'running'].includes(next.lifecycle_state)) {
        if (next.lifecycle_state === 'succeeded') {
          const [nextResult, nextTrace, nextFacts, nextEvidence, nextCalculations] = await Promise.all([
            api.result(runId),
            api.trace(runId),
            api.facts(runId),
            api.evidence(runId),
            api.calculations(runId),
          ])
          setResult(nextResult)
          setTrace(nextTrace)
          setFacts(nextFacts)
          setEvidence(nextEvidence)
          setCalculations(nextCalculations)
        } else if (next.artifacts.workflow_trace_id) {
          setTrace(await api.trace(runId))
        }
        return
      }
      await new Promise((resolve) => window.setTimeout(resolve, 500))
    }
    throw new Error('运行状态轮询超时')
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setResult(null)
    setTrace(null)
    setFacts([])
    setEvidence([])
    setCalculations([])
    setSubmitting(true)
    try {
      const created = await api.createAutonomousRun({
        company_query: companyQuery.trim(),
        market_hint: marketHint === 'AUTO' ? null : marketHint,
        requested_period_label: ['latest', '最新'].includes(periodLabel.trim().toLowerCase())
          ? null
          : periodLabel.trim() || null,
        research_mode: 'general',
        research_question: question,
        research_time: new Date().toISOString(),
        idempotency_key: crypto.randomUUID(),
      })
      await poll(created.run_id)
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setSubmitting(false)
    }
  }

  async function cancelRun() {
    if (!manifest || !['queued', 'running'].includes(manifest.lifecycle_state)) return
    setCancelling(true)
    setError(null)
    try {
      setManifest(await api.cancel(manifest.run_id))
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setCancelling(false)
    }
  }

  const invalidCompany = !companyQuery.trim()

  return (
    <main className="page-shell">
      <section className="research-grid">
        <aside className="control-panel">
          <div>
            <p className="eyebrow">COMPANY · PERIOD · QUESTION</p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-white">开始公司研究</h1>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              基于真实官方披露回答一个可核验的基本面问题。
            </p>
          </div>

          <form className="mt-7 space-y-6" onSubmit={(event) => void submit(event)}>
            <label className="block">
              <span className="field-label">Company / 公司或股票代码</span>
              <input
                aria-label="Company search"
                className="product-select"
                onChange={(event) => setCompanyQuery(event.target.value)}
                placeholder="贵州茅台 / 600519 / NVDA / 00700"
                value={companyQuery}
              />
            </label>

            <div className="two-field-grid">
              <label className="block">
                <span className="field-label">Market / 市场</span>
                <select
                  aria-label="Market selector"
                  className="product-select"
                  onChange={(event) => setMarketHint(event.target.value as typeof marketHint)}
                  value={marketHint}
                >
                  <option value="AUTO">Auto / 自动识别</option>
                  <option value="CN">A 股</option>
                  <option value="US">美股</option>
                  <option value="HK">港股</option>
                </select>
              </label>
              <label className="block">
                <span className="field-label">Period / 报告期</span>
                <input
                  aria-label="Period input"
                  className="product-select"
                  onChange={(event) => setPeriodLabel(event.target.value)}
                  placeholder="Latest（默认）/ 2025FY"
                  value={periodLabel}
                />
              </label>
            </div>

            <label className="block">
              <span className="field-label">研究问题</span>
              <textarea
                className="question-input"
                maxLength={4000}
                onChange={(event) => setQuestion(event.target.value)}
                rows={5}
                value={question}
              />
              <div className="research-template-grid" aria-label="研究问题模板">
                {researchTemplates.map(([label, prompt]) => (
                  <button
                    className={question === prompt ? 'active' : ''}
                    key={label}
                    onClick={() => setQuestion(prompt)}
                    type="button"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </label>

            <button
              className="primary-button"
              disabled={submitting || invalidCompany || !question.trim()}
              type="submit"
            >
              {submitting ? <LoaderCircle className="animate-spin" size={17} /> : <Sparkles size={17} />}
              {submitting ? '正在发现并核验官方披露' : 'Research Company / 开始自主研究'}
            </button>

            <div className="data-boundary-note">
              <ShieldCheck size={15} />
              <span>
                官方披露自动发现 · 不确定即弃权 · 确定性公式 · Claim-level evidence
              </span>
            </div>

            <a
              aria-label="使用 n8n 表单入口"
              className="automation-entry"
              href="http://127.0.0.1:5678/form/researchforge-v17-form"
              rel="noreferrer"
              target="_blank"
            >
              <Workflow size={17} />
              <span><strong>使用 n8n 表单入口</strong><small>同一后端 · 同一证据与验证链路</small></span>
              <ArrowUpRight size={14} />
            </a>
          </form>
        </aside>

        <section className="result-workspace" aria-live="polite">
          <div className="workspace-topline">
            <div>
              <p className="eyebrow">RESEARCH WORKSPACE</p>
              <h2 className="mt-2 text-xl font-semibold text-white">
                {manifest ? `Run ${manifest.run_id.slice(-10)}` : '等待研究任务'}
              </h2>
            </div>
            {manifest && (
              <div className="flex items-center gap-2">
                {['queued', 'running'].includes(manifest.lifecycle_state) && (
                  <button
                    className="cancel-button"
                    disabled={cancelling}
                    onClick={() => void cancelRun()}
                    type="button"
                  >
                    <Square size={11} /> {cancelling ? '取消中' : '取消'}
                  </button>
                )}
                <span className={`status-pill ${statusTone(manifest.lifecycle_state)}`}>
                  <Activity size={13} /> {manifest.lifecycle_state}
                </span>
              </div>
            )}
          </div>

          {error && (
            <div className="error-banner"><CircleAlert size={17} /><span>{error}</span></div>
          )}

          {!manifest && !error && (
            <div className="empty-state">
              <div className="empty-orbit"><BarChart3 size={32} /></div>
              <h3>把问题变成证据链</h3>
              <p>输入任意支持市场的上市公司名称或股票代码。ResearchForge 会自主定位官方披露，再逐层给出数字、公式、证据、反证和结论。</p>
              <div className="empty-features">
                <span><ShieldCheck size={15} /> 截止时间控制</span>
                <span><GitBranch size={15} /> LangGraph Trace</span>
                <span><BookOpenCheck size={15} /> Claim—Fact 链路</span>
              </div>
            </div>
          )}

          {manifest && (
            <>
              {!result && <div className="stage-strip">
                {(trace?.stages ?? []).map((stage) => (
                  <div className="stage-item" key={`${stage.sequence}-${stage.stage}`} title={stage.sanitized_summary}>
                    <span className={`stage-dot ${statusTone(stage.status)}`}>
                      {stage.status === 'succeeded' ? <Check size={11} /> : <Square size={8} />}
                    </span>
                    <small>{stageLabels[stage.stage] ?? stage.stage}</small>
                  </div>
                ))}
                {!trace && <div className="stage-loading"><LoaderCircle className="animate-spin" size={16} /> 正在生成 Trace…</div>}
              </div>}

              {manifest.failure && !result && (
                <section className="terminal-state-card" role="alert">
                  <CircleAlert size={21} />
                  <div>
                    <span className="micro-label">NO RESEARCH RESULT GENERATED</span>
                    <h3>{terminalStateGuidance[manifest.lifecycle_state]?.title ?? '研究未生成结果'}</h3>
                    <p><strong>{manifest.failure.code}</strong> — {manifest.failure.message}</p>
                    <small>{terminalStateGuidance[manifest.lifecycle_state]?.action ?? '请检查运行状态和研究轨迹。'}</small>
                    <nav>
                      <a href={`/v1/research-runs/${manifest.run_id}`} target="_blank">查看运行状态 <ArrowUpRight size={12} /></a>
                      {manifest.artifacts.workflow_trace_id && (
                        <a href={`/v1/research-runs/${manifest.run_id}/trace`} target="_blank">查看 Research Trace <ArrowUpRight size={12} /></a>
                      )}
                    </nav>
                  </div>
                </section>
              )}

              {result && (
                <div className="report-stack">
                  {result.synthesis_mode === 'evidence_summary_fallback' && (
                    <section className="synthesis-warning" role="status">
                      <CircleAlert size={18} />
                      <div>
                        <strong>EVIDENCE SUMMARY FALLBACK · 未执行 AI 综合分析</strong>
                        <p>当前只展示已核验的证据与确定性财务事实，不把财报摘录包装成完整研究结论。请在模型综合可用后重新运行。</p>
                      </div>
                    </section>
                  )}
                  <section className="summary-card">
                    <div className="section-heading">
                      <span><Sparkles size={16} /> Executive Conclusion / 核心结论</span>
                      <span className="summary-meta">
                        <span className={`synthesis-badge ${result.synthesis_mode === 'model' ? 'model' : 'fallback'}`}>
                          {result.synthesis_mode === 'model' ? 'MODEL SYNTHESIS' : 'EVIDENCE SUMMARY'}
                        </span>
                        <span className="micro-label">{result.research_intent?.label ?? taskLabels[result.task_type]}</span>
                      </span>
                    </div>
                    <p>{result.executive_summary}</p>
                    {result.overall_judgment && (
                      <div className="judgment-row">
                        <strong>{result.overall_judgment.label}</strong>
                        <span>{result.overall_judgment.rationale}</span>
                      </div>
                    )}
                  </section>

                  <section>
                    <div className="section-heading"><span><BarChart3 size={16} /> {result.synthesis_mode === 'model' ? 'Key Findings / 关键发现' : 'Verified Evidence Summary / 已核验证据摘要'}</span><span className="micro-label">{result.claims.length} ITEMS</span></div>
                    <div className="space-y-3">
                      {result.claims.map((claim) => (
                        <EvidenceLink
                          claim={claim}
                          facts={facts}
                          evidence={evidence}
                          key={claim.claim_id}
                        />
                      ))}
                    </div>
                  </section>

                  {result.analysis_sections && result.analysis_sections.length > 0 && (
                    <section className="report-panel deep-analysis-panel">
                      <div className="section-heading">
                        <span><BookOpenCheck size={16} /> Deep Analysis / 深入分析</span>
                        <span className="micro-label">{result.analysis_sections.length} SECTIONS</span>
                      </div>
                      <div className="deep-analysis-list">
                        {result.analysis_sections.map((section) => (
                          <article key={section.title}>
                            <h3>{section.title}</h3>
                            <p>{section.text}</p>
                            <small>{section.evidence_ids.length} 条官方证据</small>
                          </article>
                        ))}
                      </div>
                    </section>
                  )}

                  <details className="audit-section">
                    <summary><span><BarChart3 size={16} /> Financial Facts / 财务事实</span><small>{latestFacts.length} VERIFIED FACTS</small></summary>
                    <div className="metric-grid audit-content">
                      {latestFacts.map((fact) => (
                        <article className="metric-card" key={fact.fact_id}>
                          <span>{fact.company.ticker} · {fact.period.fiscal_year}{fact.period.fiscal_period} · P{fact.source_locator.page ?? '—'}</span>
                          <strong>{formatFact(fact)}</strong>
                          <small>{metricLabels[fact.metric_code] ?? fact.metric_code}</small>
                        </article>
                      ))}
                    </div>
                  </details>

                  <details className="audit-section">
                    <summary><span><Activity size={16} /> Calculations / 确定性计算</span><small>FORMULA V1.0.0</small></summary>
                    <div className="calculation-list audit-content">
                      {calculations.map((calculation) => (
                        <article key={calculation.calculation_id}>
                            <span className={`status-dot ${statusTone(calculation.status)}`} />
                            <p>
                              <strong>{calculation.formula_code} · {calculation.value ?? '不适用'}</strong>
                              <small>{calculation.explanation}</small>
                            </p>
                        </article>
                      ))}
                    </div>
                  </details>

                  <details className="audit-section">
                    <summary><span><BookOpenCheck size={16} /> Supporting Evidence / 支持证据</span><small>{supportingEvidence.length} CITATIONS</small></summary>
                    <div className="audit-content evidence-list">
                      {supportingEvidence.map((chunk) => (
                        <article className="evidence-snippet" key={chunk.chunk_id}>
                          <div><BookOpenCheck size={14} /><strong>{chunk.section} · P{chunk.locator.page_start}</strong><span title={chunk.text_hash}>HASH {chunk.text_hash.slice(0, 10)}</span></div>
                          <p>{chunk.text}</p>
                          <a href={chunk.source_uri} rel="noreferrer" target="_blank">打开官方披露 <ArrowUpRight size={13} /></a>
                        </article>
                      ))}
                    </div>
                  </details>

                  <section className="report-panel counter-panel">
                    <div className="section-heading"><span><Search size={16} /> Counter Evidence / 反证与相反信号</span><span className="micro-label">SEARCHED</span></div>
                    {[...new Map(result.claims.filter((claim) => claim.counter_evidence_search.performed).map((claim) => [claim.counter_evidence_search.summary, claim.counter_evidence_search])).values()].map((counter) => (
                      <article className="counter-result" key={counter.summary}>
                        <div className="counter-result-heading">
                          <span className={`status-pill ${counter.result === 'found' ? 'active' : 'muted'}`}>{counter.result}</span>
                          <p>{counter.summary}</p>
                        </div>
                        {counter.evidence_ids.length > 0 && (
                          <details className="counter-sources">
                            <summary>查看反证来源 ({counter.evidence_ids.length})</summary>
                            <div className="evidence-list">
                              {evidence.filter((chunk) => counter.evidence_ids.includes(chunk.chunk_id)).map((chunk) => (
                                <article className="evidence-snippet" key={chunk.chunk_id}>
                                  <div><BookOpenCheck size={14} /><strong>{chunk.section} · P{chunk.locator.page_start}</strong><span title={chunk.text_hash}>HASH {chunk.text_hash.slice(0, 10)}</span></div>
                                  <p>{chunk.text}</p>
                                  <a href={chunk.source_uri} rel="noreferrer" target="_blank">打开官方披露 <ArrowUpRight size={13} /></a>
                                </article>
                              ))}
                            </div>
                          </details>
                        )}
                      </article>
                    ))}
                  </section>

                  <section className="report-panel">
                    <div className="section-heading"><span><CircleAlert size={16} /> Risks & Limitations / 风险与限制</span></div>
                    <ul className="limitation-list">
                      {result.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
                    </ul>
                  </section>

                  <section className="report-panel">
                    <div className="section-heading"><span><Activity size={16} /> Monitoring Plan / 后续监控</span><span className="micro-label">NEXT FILING</span></div>
                    <div className="monitor-list">
                      {result.monitoring_items.map((item) => (
                        <article key={item.monitor_code}>
                          <strong>{item.title}</strong><p>{item.rationale}</p><small>触发条件：{item.trigger}</small><small>复核时间：{item.next_review}</small>
                        </article>
                      ))}
                    </div>
                  </section>

                  {result.suggested_follow_ups && result.suggested_follow_ups.length > 0 && (
                    <section className="report-panel follow-up-panel">
                      <div className="section-heading"><span><Sparkles size={16} /> Suggested Follow-ups / 继续研究</span></div>
                      <div className="follow-up-grid">
                        {result.suggested_follow_ups.map((followUp) => (
                          <button key={followUp} onClick={() => setQuestion(followUp)} type="button">
                            <span>{followUp}</span><ChevronRight size={14} />
                          </button>
                        ))}
                      </div>
                    </section>
                  )}

                  <details className="audit-section">
                    <summary><span><GitBranch size={16} /> Research Trace / 研究轨迹</span><small>{trace?.stages.length ?? 0} LANGGRAPH STAGES</small></summary>
                    <div className="audit-content">
                      <div className="stage-strip embedded">
                        {(trace?.stages ?? []).map((stage) => (
                          <div className="stage-item" key={`${stage.sequence}-${stage.stage}`} title={stage.sanitized_summary}><span className={`stage-dot ${statusTone(stage.status)}`}><Check size={11} /></span><small>{stageLabels[stage.stage] ?? stage.stage}</small></div>
                        ))}
                      </div>
                      <div className="check-list trace-checks">
                        {result.mandatory_checks.map((check, index) => (
                          <div key={`${check.check_code}-${index}`}><span className={`status-dot ${statusTone(check.status)}`} /><p><strong>{check.check_code}</strong><small>{check.finding}</small></p></div>
                        ))}
                      </div>
                    </div>
                  </details>

                  <nav className="artifact-links" aria-label="后端原始产物">
                    <span>验证同一后端原始产物</span>
                    <a href={`/v1/research-runs/${manifest.run_id}/result`} target="_blank">Research Result <ArrowUpRight size={12} /></a>
                    <a href={`/v1/research-runs/${manifest.run_id}/trace`} target="_blank">Research Trace <ArrowUpRight size={12} /></a>
                  </nav>
                </div>
              )}
            </>
          )}
        </section>
      </section>
    </main>
  )
}

function QualityLabPage() {
  const [experimentId, setExperimentId] = useState('experiment_contingency_v1_5_001')
  const [experiment, setExperiment] = useState<EvolutionExperiment | null>(null)
  const [artifacts, setArtifacts] = useState<EvolutionArtifacts | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function loadExperiment(event: React.FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setArtifacts(null)
    try {
      const loadedExperiment = await api.experiment(experimentId)
      setExperiment(loadedExperiment)
      async function optional<T>(kind: string): Promise<T | null> {
        try {
          return await api.experimentArtifact<T>(experimentId, kind)
        } catch {
          return null
        }
      }
      const [
        baseEvolution,
        seedEvolution,
        failureCluster,
        experience,
        patch,
        validationDecision,
        seedValidation,
        candidateValidation,
        seedFinal,
        candidateFinal,
        technicalRetries,
        activation,
        projectResearchOutcome,
      ] = await Promise.all([
        optional<EvaluationBatch>('base-evolution-evaluations'),
        optional<EvaluationBatch>('seed-evolution-evaluations'),
        optional<FailureCluster>('failure-cluster'),
        optional<Experience>('experience'),
        optional<SkillPatch>('patch'),
        optional<ValidationDecision>('validation-decision'),
        optional<EvaluationBatch>('seed-validation-evaluations'),
        optional<EvaluationBatch>('candidate-validation-evaluations'),
        optional<EvaluationBatch>('seed-final_test-evaluations'),
        optional<EvaluationBatch>('candidate-final_test-evaluations'),
        optional<TechnicalRetries>('technical-retries'),
        optional<ContingencyActivation>('activation'),
        optional<ProjectResearchOutcome>('project-research-outcome'),
      ])
      setArtifacts({
        baseEvolution,
        seedEvolution,
        failureCluster,
        experience,
        patch,
        validationDecision,
        seedValidation,
        candidateValidation,
        seedFinal,
        candidateFinal,
        technicalRetries,
        activation,
        projectResearchOutcome,
      })
    } catch (caught: unknown) {
      setExperiment(null)
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page-shell lab-page">
      <section className="lab-hero">
        <div>
          <p className="eyebrow">EXPERIMENTAL · READ-ONLY</p>
          <h1>Quality Lab</h1>
          <p>ResearchForge 背后的质量研究档案。它保存 V1.4 的冻结实验与负结果，但不是完成普通公司研究所必需的功能。</p>
        </div>
        <div className="lab-principle"><ShieldCheck size={19} /><span><strong>只读技术资产</strong><small>NOT REQUIRED FOR NORMAL RESEARCH</small></span></div>
      </section>

      <section className="lab-grid">
        <div className="lab-main">
          <form className="experiment-search" onSubmit={(event) => void loadExperiment(event)}>
            <Search size={17} />
            <input aria-label="实验 ID" onChange={(event) => setExperimentId(event.target.value)} placeholder="输入 experiment_id" value={experimentId} />
            <button disabled={!experimentId || loading}>{loading ? '读取中' : '读取实验'}</button>
          </form>
          {error && <div className="error-banner"><CircleAlert size={17} />{error}</div>}
          {!experiment && !error && (
            <div className="lab-empty">
              <FlaskConical size={36} />
              <h2>读取冻结质量研究</h2>
              <p>这里不会运行或追加正式 Evolution 实验。读取已有记录，可检查失败聚类、Candidate Diff、Validation 决策、Final Test 与已冻结负结果。</p>
            </div>
          )}
          {experiment && (
            <div className="experiment-dashboard">
              <div className="experiment-title-row">
                <div>
                  <span className="micro-label">{experiment.suite_id}</span>
                  <h2>{experiment.experiment_id}</h2>
                  <small>冻结于 {new Date(experiment.preregistered_at).toLocaleString('zh-CN')}</small>
                </div>
                <span className={`status-pill ${statusTone(experiment.status)}`}>
                  {experiment.status} · {experiment.outcome}
                </span>
              </div>
              {(artifacts?.projectResearchOutcome || experiment.outcome === 'NO_ELIGIBLE_CLUSTER') && (
                <article className="research-outcome-card">
                  <div>
                    <span className="micro-label">RESEARCH OUTCOME</span>
                    <strong>
                      {artifacts?.projectResearchOutcome?.research_hypothesis_supported
                        ? '研究假设获得支持'
                        : '研究假设未获支持'}
                    </strong>
                  </div>
                  <p>
                    {artifacts?.projectResearchOutcome?.claim_boundary
                      ?? 'Seed 未形成达到预注册阈值的失败簇，因此未生成 Candidate。'}
                  </p>
                  <small>
                    {artifacts?.projectResearchOutcome
                      ? `${artifacts.projectResearchOutcome.formal_experiment_count} 次正式实验 · stopping rule 已执行`
                      : `${experiment.outcome} · Validation 与 Final Test 保持封闭`}
                  </small>
                </article>
              )}
              <div className="experiment-metrics">
                <article><small>Seed Skill</small><strong>{experiment.seed_skill_version_id}</strong></article>
                <article><small>预算使用</small><strong>{experiment.budget.spent.toFixed(2)} / {experiment.budget.cap.toFixed(2)} {experiment.budget.currency}</strong></article>
                <article><small>Final Test</small><strong>{experiment.final_test_consumed ? '已消费' : '保持封闭'}</strong></article>
              </div>
              <div className="split-grid">
                {(
                  [
                    ['evolution', 'Evolution'],
                    ['validation', 'Validation'],
                    ['final_test', 'Final Test'],
                  ] as const
                ).map(([split, label]) => (
                  <article className="split-card" key={split}>
                    <span>{label}</span>
                    <strong>{experiment.split_case_ids[split].length} cases</strong>
                    <small>{split === 'final_test' && !experiment.final_test_consumed ? 'SEALED' : 'FROZEN'}</small>
                  </article>
                ))}
              </div>
              <div className="evolution-evidence-grid">
                {(
                  [
                    ['Base', artifacts?.baseEvolution ?? null],
                    ['Seed', artifacts?.seedEvolution ?? null],
                  ] as const
                ).map(([label, batch]) => (
                  <article key={label}>
                    <div className="section-heading">
                      <span>{label} · Evolution</span>
                      <span className="micro-label">{batch?.evaluations.length ?? 0} EVALS</span>
                    </div>
                    <strong>{averageScore(batch)}</strong>
                    <p>
                      {failedEvaluationCount(batch)} 个失败评估 · {failureEventCount(batch)} 个失败事件
                    </p>
                  </article>
                ))}
              </div>
              {(artifacts?.activation || artifacts?.technicalRetries) && (
                <article className="experiment-audit-card">
                  <div className="section-heading">
                    <span><ShieldCheck size={15} /> 协议与技术审计</span>
                    <span className="micro-label">IMMUTABLE</span>
                  </div>
                  {artifacts.activation && (
                    <p>
                      V1.5 {artifacts.activation.status} · 主实验 {artifacts.activation.primary_outcome} ·
                      激活次数 {artifacts.activation.activation_count}。协议偏差
                      {' '}{artifacts.activation.protocol_deviation.code}；数据或阈值变更:
                      {' '}{String(artifacts.activation.protocol_deviation.data_or_threshold_changed)}。
                    </p>
                  )}
                  <p>
                    零-token 技术重试 {artifacts.technicalRetries?.records.length ?? 0} 次；失败 Run
                    均保留并排除在正式研究分母之外。
                  </p>
                </article>
              )}
              <div className="lab-artifact-grid">
                <article className="lab-artifact-card">
                  <div className="section-heading">
                    <span><CircleAlert size={15} /> 失败聚类</span>
                    <span className="micro-label">
                      {artifacts?.failureCluster ? `${artifacts.failureCluster.support_count} hits` : 'PENDING'}
                    </span>
                  </div>
                  {artifacts?.failureCluster ? (
                    <>
                      <strong>{artifacts.failureCluster.failure_label}</strong>
                      <code>{artifacts.failureCluster.signature}</code>
                      <p>{artifacts.failureCluster.distinct_case_ids.length} 个独立案例，共 {artifacts.failureCluster.eligible_run_count} 个可评估运行。</p>
                    </>
                  ) : <p>尚无达到冻结支持阈值的核验失败聚类。</p>}
                </article>
                <article className="lab-artifact-card">
                  <div className="section-heading">
                    <span><BookOpenCheck size={15} /> Experience</span>
                    <span className="micro-label">VERIFIER-GROUNDED</span>
                  </div>
                  {artifacts?.experience ? (
                    <>
                      <strong>{artifacts.experience.failure_label}</strong>
                      <p>{artifacts.experience.observed_behavior}</p>
                      <blockquote>{artifacts.experience.required_procedure}</blockquote>
                    </>
                  ) : <p>只有失败聚类通过门槛后才会蒸馏 Experience。</p>}
                </article>
              </div>
              <article className="skill-diff-card">
                <div className="section-heading">
                  <span><GitBranch size={15} /> Candidate Skill Diff</span>
                  <span className={`status-pill ${statusTone(artifacts?.patch?.status ?? 'pending')}`}>
                    {artifacts?.patch?.status ?? 'PENDING'}
                  </span>
                </div>
                {artifacts?.patch ? artifacts.patch.operations.map((operation) => (
                  <div className="diff-operation" key={`${operation.operation}-${operation.target_section}`}>
                    <span>+ {operation.operation} · {operation.target_section}</span>
                    <p>{operation.new_rule}</p>
                    <small>{operation.reason}</small>
                  </div>
                )) : <p>Candidate 仅由受控 CLI 在合格失败聚类上生成；UI 保持只读。</p>}
              </article>
              <div className="paired-results">
                <article>
                  <div className="section-heading"><span>Validation 配对</span><span className="micro-label">3 REPEATS</span></div>
                  <div className="score-pair">
                    <span><small>Seed</small><strong>{averageScore(artifacts?.seedValidation ?? null)}</strong></span>
                    <ChevronRight size={16} />
                    <span><small>Candidate</small><strong>{averageScore(artifacts?.candidateValidation ?? null)}</strong></span>
                  </div>
                  <p>{artifacts?.patch?.decision?.decision_reason ?? 'Validation 尚未产生采用或回滚证据。'}</p>
                  <span className={`status-pill ${statusTone(artifacts?.validationDecision?.status ?? 'pending')}`}>
                    {artifacts?.validationDecision?.status ?? 'SEALED'}
                  </span>
                </article>
                <article>
                  <div className="section-heading"><span>Final Test</span><span className="micro-label">ONE-TIME</span></div>
                  <div className="score-pair">
                    <span><small>Seed</small><strong>{averageScore(artifacts?.seedFinal ?? null)}</strong></span>
                    <ChevronRight size={16} />
                    <span><small>Candidate</small><strong>{averageScore(artifacts?.candidateFinal ?? null)}</strong></span>
                  </div>
                  <p>{experiment.final_test_consumed ? `封闭测试已消费，结果：${experiment.outcome}` : 'Validation 采用 Candidate 前保持封闭，不展示结果。'}</p>
                  <span className={`status-pill ${statusTone(experiment.outcome)}`}>{experiment.final_test_consumed ? experiment.outcome : 'SEALED'}</span>
                </article>
              </div>
              <details className="experiment-details">
                <summary>查看不可变实验记录</summary>
                <pre className="experiment-json">{JSON.stringify(experiment, null, 2)}</pre>
              </details>
            </div>
          )}
        </div>
        <aside className="lab-side">
          <h2>采用路径</h2>
          {['失败聚类', 'Experience 蒸馏', 'Candidate Skill Diff', 'Validation 配对', '封闭 Final Test'].map((step, index) => (
            <div className="adoption-step" key={step}>
              <span>{index + 1}</span><p><strong>{step}</strong><small>{index < 3 ? 'Evolution only' : 'sealed split'}</small></p><ChevronRight size={15} />
            </div>
          ))}
          <div className="honesty-note"><CircleAlert size={16} /><p>若实验不支持假设，系统保留负结果，不会把工程完成改写成研究成功。</p></div>
        </aside>
      </section>
    </main>
  )
}

export default function App() {
  const [page, setPage] = useState<'research' | 'lab'>('research')
  return (
    <div className="app-root">
      <header className="app-header">
        <button className="brand" onClick={() => setPage('research')}>
          <span className="brand-mark">RF</span>
          <span><strong>ResearchForge</strong><small>Evidence before narrative</small></span>
        </button>
        <nav aria-label="主导航">
          <button className={page === 'research' ? 'active' : ''} onClick={() => setPage('research')}><BarChart3 size={16} />Research</button>
          <button className={`secondary ${page === 'lab' ? 'active' : ''}`} onClick={() => setPage('lab')}><FlaskConical size={16} />Quality Lab</button>
        </nav>
        <div className="header-badge"><span /> REAL DATA · V1.7.1</div>
      </header>
      {page === 'research' ? <ResearchPage /> : <QualityLabPage />}
      <footer>ResearchForge · 研究辅助工具，不构成投资建议 · 真实用户价值尚未验证</footer>
    </div>
  )
}
