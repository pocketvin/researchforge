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
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { api } from './api'
import type {
  Catalog,
  Claim,
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
  ValidationDecision,
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

function EvidenceLink({ claim, facts }: { claim: Claim; facts: FinancialFact[] }) {
  const linked = claim.fact_ids
    .map((id) => facts.find((fact) => fact.fact_id === id))
    .filter((fact): fact is FinancialFact => Boolean(fact))
  return (
    <div className="claim-card">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`status-pill ${statusTone(claim.epistemic_status)}`}>
          {claim.epistemic_status}
        </span>
        <span className="micro-label">{claim.claim_type}</span>
        <span className="micro-label">置信度 {claim.confidence.level}</span>
      </div>
      <p className="mt-4 text-[15px] leading-7 text-slate-100">{claim.text}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {linked.map((fact) => (
          <span className="fact-chip" key={fact.fact_id} title={fact.fact_id}>
            {metricLabels[fact.metric_code] ?? fact.metric_code} · {formatFact(fact)}
          </span>
        ))}
      </div>
      <div className="counter-note">
        <Search size={14} />
        <span>
          反证搜索: {claim.counter_evidence_search.result} —{' '}
          {claim.counter_evidence_search.summary}
        </span>
      </div>
    </div>
  )
}

function ResearchPage() {
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [taskType, setTaskType] = useState<TaskType>('filing_analysis')
  const [companies, setCompanies] = useState<string[]>([])
  const [periods, setPeriods] = useState<string[]>([])
  const [question, setQuestion] = useState('所选期间的利润是否有效转化为经营现金流？')
  const [manifest, setManifest] = useState<RunManifest | null>(null)
  const [result, setResult] = useState<ResearchResult | null>(null)
  const [trace, setTrace] = useState<Trace | null>(null)
  const [facts, setFacts] = useState<FinancialFact[]>([])
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [cancelling, setCancelling] = useState(false)

  useEffect(() => {
    void api
      .catalog()
      .then((value) => {
        setCatalog(value)
        const first = value.companies[0]
        if (first) {
          setCompanies([first.company_id])
          setPeriods(first.period_labels.slice(-1))
        }
      })
      .catch((caught: unknown) => setError(String(caught)))
  }, [])

  const availablePeriods = useMemo(() => {
    if (!catalog || companies.length === 0) return []
    const selected = catalog.companies.filter((company) => companies.includes(company.company_id))
    return selected.reduce<string[]>(
      (shared, company, index) =>
        index === 0
          ? [...company.period_labels]
          : shared.filter((period) => company.period_labels.includes(period)),
      [],
    )
  }, [catalog, companies])

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

  function selectTask(next: TaskType) {
    setTaskType(next)
    setCompanies((current) => current.slice(0, next === 'peer_comparison' ? 2 : 1))
    setPeriods([])
  }

  function toggleCompany(companyId: string) {
    setCompanies((current) => {
      if (current.includes(companyId)) return current.filter((id) => id !== companyId)
      const limit = taskType === 'peer_comparison' ? 2 : 1
      return [...current, companyId].slice(-limit)
    })
    setPeriods([])
  }

  async function poll(runId: string) {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      const next = await api.manifest(runId)
      setManifest(next)
      if (!['queued', 'running'].includes(next.lifecycle_state)) {
        if (next.lifecycle_state === 'succeeded') {
          const [nextResult, nextTrace, nextFacts] = await Promise.all([
            api.result(runId),
            api.trace(runId),
            api.facts(runId),
          ])
          setResult(nextResult)
          setTrace(nextTrace)
          setFacts(nextFacts)
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
    setSubmitting(true)
    try {
      const created = await api.createRun({
        task_type: taskType,
        research_question: question,
        company_ids: companies,
        requested_period_labels: periods,
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

  const invalidCompanyCount =
    companies.length !== (taskType === 'peer_comparison' ? 2 : 1)
  const invalidPeriodCount =
    periods.length === 0 ||
    (['company_research', 'risk_detection'].includes(taskType) && periods.length < 2)

  return (
    <main className="page-shell">
      <section className="research-grid">
        <aside className="control-panel">
          <div>
            <p className="eyebrow">NEW RESEARCH RUN</p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-white">建立研究任务</h1>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              模型只接触冻结事实、确定性计算与允许证据。
            </p>
          </div>

          <form className="mt-7 space-y-6" onSubmit={(event) => void submit(event)}>
            <fieldset>
              <legend className="field-label">研究模式</legend>
              <div className="task-options">
                {catalog?.supported_task_types.map((task) => (
                  <button
                    className={task === taskType ? 'task-option selected' : 'task-option'}
                    key={task}
                    onClick={() => selectTask(task)}
                    type="button"
                  >
                    {taskLabels[task]}
                  </button>
                ))}
              </div>
            </fieldset>

            <fieldset>
              <legend className="field-label">
                公司 {taskType === 'peer_comparison' ? '· 请选择两家' : ''}
              </legend>
              <div className="space-y-2">
                {catalog?.companies.map((company) => (
                  <label className="company-option" key={company.company_id}>
                    <input
                      checked={companies.includes(company.company_id)}
                      onChange={() => toggleCompany(company.company_id)}
                      type="checkbox"
                    />
                    <span className="company-mark">{company.ticker.slice(-2)}</span>
                    <span className="min-w-0 flex-1">
                      <strong>{company.legal_name.replace('新能源科技股份有限公司', '')}</strong>
                      <small>{company.exchange} · {company.ticker}</small>
                    </span>
                    {companies.includes(company.company_id) && <Check size={16} />}
                  </label>
                ))}
              </div>
            </fieldset>

            <fieldset>
              <legend className="field-label">报告期</legend>
              <div className="flex flex-wrap gap-2">
                {availablePeriods.map((period) => (
                  <label className={periods.includes(period) ? 'period-chip selected' : 'period-chip'} key={period}>
                    <input
                      checked={periods.includes(period)}
                      onChange={() =>
                        setPeriods((current) =>
                          current.includes(period)
                            ? current.filter((value) => value !== period)
                            : [...current, period],
                        )
                      }
                      type="checkbox"
                    />
                    {period}
                  </label>
                ))}
              </div>
            </fieldset>

            <label className="block">
              <span className="field-label">研究问题</span>
              <textarea
                className="question-input"
                maxLength={4000}
                onChange={(event) => setQuestion(event.target.value)}
                rows={4}
                value={question}
              />
            </label>

            <button
              className="primary-button"
              disabled={submitting || invalidCompanyCount || invalidPeriodCount || !question.trim()}
              type="submit"
            >
              {submitting ? <LoaderCircle className="animate-spin" size={17} /> : <Sparkles size={17} />}
              {submitting ? '正在执行研究链路' : '开始可审计研究'}
            </button>
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
              <p>选择研究模式、公司和报告期。结果将展示事实、计算、反证与限制，而不是只有一段不可审计的回答。</p>
              <div className="empty-features">
                <span><ShieldCheck size={15} /> 截止时间控制</span>
                <span><GitBranch size={15} /> LangGraph Trace</span>
                <span><BookOpenCheck size={15} /> Claim—Fact 链路</span>
              </div>
            </div>
          )}

          {manifest && (
            <>
              <div className="stage-strip">
                {(trace?.stages ?? []).map((stage) => (
                  <div className="stage-item" key={`${stage.sequence}-${stage.stage}`} title={stage.sanitized_summary}>
                    <span className={`stage-dot ${statusTone(stage.status)}`}>
                      {stage.status === 'succeeded' ? <Check size={11} /> : <Square size={8} />}
                    </span>
                    <small>{stageLabels[stage.stage] ?? stage.stage}</small>
                  </div>
                ))}
                {!trace && <div className="stage-loading"><LoaderCircle className="animate-spin" size={16} /> 正在生成 Trace…</div>}
              </div>

              {manifest.failure && (
                <div className="error-banner" role="alert">
                  <CircleAlert size={17} />
                  <span><strong>{manifest.failure.code}</strong> — {manifest.failure.message}</span>
                </div>
              )}

              {result && (
                <div className="report-stack">
                  <section className="summary-card">
                    <div className="section-heading">
                      <span><Sparkles size={16} /> 执行摘要</span>
                      <span className="micro-label">{taskLabels[result.task_type]}</span>
                    </div>
                    <p>{result.executive_summary}</p>
                  </section>

                  <section>
                    <div className="section-heading"><span><BarChart3 size={16} /> 财务快照</span><span className="micro-label">API FACTS</span></div>
                    <div className="metric-grid">
                      {latestFacts.map((fact) => (
                        <article className="metric-card" key={fact.fact_id}>
                          <span>{fact.company.ticker} · {fact.period.fiscal_year}{fact.period.fiscal_period}</span>
                          <strong>{formatFact(fact)}</strong>
                          <small>{metricLabels[fact.metric_code] ?? fact.metric_code}</small>
                        </article>
                      ))}
                    </div>
                  </section>

                  <section>
                    <div className="section-heading"><span><GitBranch size={16} /> Claim—Fact—Evidence</span><span className="micro-label">{result.claims.length} CLAIMS</span></div>
                    <div className="space-y-3">
                      {result.claims.map((claim) => <EvidenceLink claim={claim} facts={facts} key={claim.claim_id} />)}
                    </div>
                  </section>

                  <section className="two-column-report">
                    <div className="report-panel">
                      <div className="section-heading"><span><ShieldCheck size={16} /> 核验项目</span></div>
                      <div className="check-list">
                        {result.mandatory_checks.map((check, index) => (
                          <div key={`${check.check_code}-${index}`}>
                            <span className={`status-dot ${statusTone(check.status)}`} />
                            <p><strong>{check.check_code}</strong><small>{check.finding}</small></p>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="report-panel">
                      <div className="section-heading"><span><CircleAlert size={16} /> 限制</span></div>
                      <ul className="limitation-list">
                        {result.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
                      </ul>
                    </div>
                  </section>

                  <section className="sources-panel">
                    <div className="section-heading"><span><BookOpenCheck size={16} /> 官方来源</span><span className="micro-label">{result.source_document_ids.length} DOCUMENTS</span></div>
                    {[...new Map(facts.map((fact) => [fact.source.document_id, fact])).values()].map((fact) => (
                      <a href={fact.source.uri} key={fact.source.document_id} rel="noreferrer" target="_blank">
                        <span><strong>{fact.company.legal_name}</strong><small>{fact.source.document_id} · 发布 {new Date(fact.source.published_at).toLocaleDateString('zh-CN')}</small></span>
                        <ArrowUpRight size={16} />
                      </a>
                    ))}
                  </section>
                </div>
              )}
            </>
          )}
        </section>
      </section>
    </main>
  )
}

function SkillLabPage() {
  const [experimentId, setExperimentId] = useState('')
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
        failureCluster,
        experience,
        patch,
        validationDecision,
        seedValidation,
        candidateValidation,
        seedFinal,
        candidateFinal,
      ] = await Promise.all([
        optional<FailureCluster>('failure-cluster'),
        optional<Experience>('experience'),
        optional<SkillPatch>('patch'),
        optional<ValidationDecision>('validation-decision'),
        optional<EvaluationBatch>('seed-validation-evaluations'),
        optional<EvaluationBatch>('candidate-validation-evaluations'),
        optional<EvaluationBatch>('seed-final_test-evaluations'),
        optional<EvaluationBatch>('candidate-final_test-evaluations'),
      ])
      setArtifacts({
        failureCluster,
        experience,
        patch,
        validationDecision,
        seedValidation,
        candidateValidation,
        seedFinal,
        candidateFinal,
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
          <p className="eyebrow">CONTROLLED EVOLUTION</p>
          <h1>Skill Lab</h1>
          <p>从已核验失败到有边界的 Skill Diff。这里是只读实验台，不允许 UI 触发自我修改。</p>
        </div>
        <div className="lab-principle"><ShieldCheck size={19} /><span><strong>封闭实验</strong><small>Evolution → Validation → Final Test</small></span></div>
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
              <h2>等待受控实验产物</h2>
              <p>没有硬编码的“成功故事”。当 CLI 冻结真实 Evolution Experiment 后，失败聚类、Candidate Diff、Validation 决策与 Final Test 才会在此渲染。</p>
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
          <button className={page === 'lab' ? 'active' : ''} onClick={() => setPage('lab')}><FlaskConical size={16} />Skill Lab</button>
        </nav>
        <div className="header-badge"><span /> LOCAL · V1.4</div>
      </header>
      {page === 'research' ? <ResearchPage /> : <SkillLabPage />}
      <footer>ResearchForge · 研究辅助工具，不构成投资建议 · 真实用户价值尚未验证</footer>
    </div>
  )
}
