import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const catalog = {
  schema_version: '1.5.0',
  data_namespace: 'product',
  implementation_level: 'V1_5_REAL_DATA',
  supported_task_types: ['filing_analysis'],
  limitations: ['目前仅支持少量人工核验的真实公开披露。'],
  companies: [
    {
      company_id: 'cn_300750',
      legal_name: '宁德时代新能源科技股份有限公司',
      ticker: '300750',
      exchange: 'SZSE',
      country_code: 'CN',
      period_labels: ['2024Q1', '2024H1'],
    },
  ],
}

const manifest = {
  run_id: 'run_frontend_test',
  lifecycle_state: 'succeeded',
  input: {
    task_type: 'filing_analysis',
    research_question: '利润是否转化为现金流？',
    company_ids: ['cn_300750'],
    requested_period_labels: ['2024H1'],
    research_time: '2024-08-01T00:00:00+08:00',
  },
  artifacts: {
    result_id: 'result_frontend_test',
    workflow_trace_id: 'trace_frontend_test',
    evaluation_id: null,
  },
  failure: null,
}

function json(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('ResearchForge UI', () => {
  beforeEach(() => {
    vi.stubGlobal('crypto', { randomUUID: () => 'frontend-idempotency-key' })
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const path = String(input)
        if (path === '/v1/catalog') return Promise.resolve(json(catalog))
        if (path.endsWith('/artifacts/failure-cluster')) {
          return Promise.resolve(json({
            cluster_id: 'cluster_cash_conversion',
            failure_label: 'PROCEDURE_OMISSION',
            signature: 'coverage_cash_conversion:missing',
            eligible_run_count: 36,
            support_count: 12,
            distinct_case_ids: ['case_a', 'case_b'],
          }))
        }
        if (path.endsWith('/artifacts/experience')) {
          return Promise.resolve(json({
            experience_id: 'experience_cash_conversion',
            failure_label: 'PROCEDURE_OMISSION',
            observed_behavior: '报告遗漏现金转化核验。',
            applicable_condition: '净利润为正且经营现金流可用。',
            required_procedure: '形成重大结论前记录确定性的现金转化结果。',
            exceptions: [],
          }))
        }
        if (path.endsWith('/artifacts/patch')) {
          return Promise.resolve(json({
            patch_id: 'patch_cash_conversion',
            candidate_version: '1.0.0-candidate.1',
            status: 'ADOPTED',
            operations: [{
              operation: 'ADD',
              target_section: 'earnings_quality',
              new_rule: '形成重大结论前记录确定性的现金转化结果。',
              reason: '修复已核验失败聚类。',
            }],
            decision: {
              target_failure_reduced: true,
              deterministic_quality_preserved: true,
              overall_non_inferior: true,
              regression_within_threshold: true,
              decision_reason: 'repair_rate=1.000; regression_rate=0.000',
            },
          }))
        }
        if (path.endsWith('/artifacts/validation-decision')) {
          return Promise.resolve(json({
            status: 'ADOPTED',
            decision: null,
            seed_evaluation_ids: ['eval_seed'],
            candidate_evaluation_ids: ['eval_candidate'],
          }))
        }
        if (path.endsWith('/artifacts/base-evolution-evaluations')) {
          return Promise.resolve(json({
            condition: 'base',
            split: 'evolution',
            repeat_count: 3,
            evaluations: [
              { evaluation_id: 'eval_base_1', case_id: 'case_a', metrics: { task_score: 0.8 }, failure_events: [{ failure_label: 'CRITICAL_OMISSION', signature: 'coverage_a' }] },
              { evaluation_id: 'eval_base_2', case_id: 'case_b', metrics: { task_score: 1 }, failure_events: [] },
            ],
          }))
        }
        if (path.endsWith('/artifacts/seed-evolution-evaluations')) {
          return Promise.resolve(json({
            condition: 'seed',
            split: 'evolution',
            repeat_count: 3,
            evaluations: [
              { evaluation_id: 'eval_seed_1', case_id: 'case_a', metrics: { task_score: 1 }, failure_events: [] },
              { evaluation_id: 'eval_seed_2', case_id: 'case_b', metrics: { task_score: 1 }, failure_events: [] },
            ],
          }))
        }
        if (path.includes('experiment_negative') && path.endsWith('/artifacts/activation')) {
          return Promise.resolve(json({
            status: 'ACTIVATED_ONCE',
            authorization_basis: 'V1.4_SCOPE_ANY_UNSUPPORTED_PRIMARY',
            primary_outcome: 'NO_ELIGIBLE_CLUSTER',
            activation_count: 1,
            protocol_deviation: {
              code: 'FROZEN_ACTIVATION_PREDICATE_TOO_NARROW',
              data_or_threshold_changed: false,
              explanation: '冻结输入未改变。',
            },
          }))
        }
        if (path.includes('experiment_negative') && path.endsWith('/artifacts/technical-retries')) {
          return Promise.resolve(json({
            policy: 'one_retry_only_for_zero_provider_token_technical_failure',
            records: [{
              retry_key: 'evolution:base:case_a:repeat-1',
              failed_run_id: 'run_failed',
              retry_run_id: 'run_retry',
              retry_state: 'succeeded',
              provider_tokens_before_failure: 0,
              excluded_failed_run_from_formal_denominator: true,
            }],
          }))
        }
        if (path.includes('experiment_negative') && path.endsWith('/artifacts/project-research-outcome')) {
          return Promise.resolve(json({
            status: 'RESEARCH_HYPOTHESIS_UNSUPPORTED_AFTER_TWO_EXPERIMENTS',
            formal_experiment_count: 2,
            research_hypothesis_supported: false,
            primary: { experiment_id: 'primary', outcome: 'NO_ELIGIBLE_CLUSTER', result_hash: '1'.repeat(64) },
            contingency: { experiment_id: 'experiment_negative', outcome: 'NO_ELIGIBLE_CLUSTER', result_hash: '2'.repeat(64) },
            final_test_consumed: false,
            stopping_rule_applied: true,
            claim_boundary: '工程交付可以完成，但两轮正式实验均未支持研究假设。',
          }))
        }
        if (path.includes('/artifacts/')) {
          return Promise.resolve(new Response('{}', { status: 404 }))
        }
        if (path.includes('/v1/evolution-experiments/')) {
          const negative = path.includes('experiment_negative')
          return Promise.resolve(
            json({
              schema_version: '1.4.0',
              experiment_id: negative ? 'experiment_negative' : 'experiment_frontend_test',
              scope_version: negative ? '1.5' : '1.4',
              suite_id: 'suite_frontend_test',
              suite_hash: '7'.repeat(64),
              status: negative ? 'completed' : 'preregistered',
              outcome: negative ? 'NO_ELIGIBLE_CLUSTER' : 'PENDING',
              seed_skill_version_id: 'skill_fundamental_1_0_0',
              candidate_skill_version_id: null,
              split_case_ids: {
                evolution: ['case_evo_a', 'case_evo_b'],
                validation: ['case_val'],
                final_test: ['case_final'],
              },
              budget: { currency: 'USD', cap: negative ? 6 : 20, spent: negative ? 0.06 : 0 },
              final_test_consumed: false,
              preregistered_at: '2026-09-01T00:00:00+08:00',
              finished_at: null,
            }),
          )
        }
        if (path === '/v1/autonomous-research-runs') return Promise.resolve(json({ run_id: manifest.run_id }))
        if (path.endsWith('/result')) {
          return Promise.resolve(
            json({
              result_id: 'result_frontend_test',
              schema_version: '1.7.0',
              task_type: 'company_research',
              executive_summary: '经营现金流覆盖净利润，结论来自真实官方披露与确定性计算。',
              research_intent: {
                skill: 'growth_analysis', label: '增长来源', search_terms: ['growth'],
                preferred_sections: ['Management discussion'],
              },
              analysis_sections: [
                { title: '增长驱动', text: 'Blackwell 产品爬坡和客户需求共同推动增长。', evidence_ids: ['chunk_catl_ocf'] },
                { title: '持续性', text: '仍需跟踪客户需求和现金流转化。', evidence_ids: ['chunk_catl_profit'] },
              ],
              overall_judgment: { label: 'Supported', rationale: '关键判断由官方披露和已核验事实支持。' },
              suggested_follow_ups: ['增长来自哪个业务？', '毛利率为何变化？', '客户集中度如何？', '主要风险是什么？'],
              evidence_coverage: {
                available_chunk_count: 12, selected_chunk_count: 4,
                selected_evidence_ids: ['chunk_catl_ocf', 'chunk_catl_profit'],
                cited_evidence_ids: ['chunk_catl_ocf', 'chunk_catl_profit'],
                sections: ['Management discussion'],
              },
              claims: [
                {
                  claim_id: 'claim_frontend_test',
                  claim_type: 'earnings_quality',
                  epistemic_status: 'supported_inference',
                  materiality: 'material',
                  direction: 'positive',
                  text: '现金转化比为1.95倍。',
                  fact_ids: ['fact_ocf', 'fact_profit'],
                  support_evidence_ids: ['chunk_catl_ocf', 'chunk_catl_profit'],
                  counter_evidence_search: {
                    performed: true,
                    queries: ['未经审计 非经常性损益'],
                    result: 'found',
                    evidence_ids: ['chunk_catl_counter'],
                    summary: '报告未经审计，且扣除非经常性损益后的净利润低于归母净利润。',
                  },
                  alternative_explanations: [],
                  confidence: { level: 'high', basis: 'deterministic' },
                },
              ],
              mandatory_checks: [
                {
                  check_code: 'operating_cash_flow',
                  status: 'performed',
                  finding: '已核对经营现金流。',
                  fact_ids: ['fact_ocf'],
                  evidence_ids: ['chunk_catl_ocf'],
                },
              ],
              monitoring_items: [
                {
                  monitor_code: 'working_capital_cash_conversion_cn_300750',
                  title: '下一同口径报告期复核现金转化与营运资本',
                  rationale: '持续跟踪经营现金流、应收账款和存货。',
                  trigger: '现金转化比低于1.00倍。',
                  next_review: '下一同口径财务报告发布后',
                  fact_ids: ['fact_ocf', 'fact_profit'],
                  evidence_ids: ['chunk_catl_ocf', 'chunk_catl_profit'],
                },
              ],
              limitations: ['真实用户价值尚未验证。'],
              source_document_ids: ['doc_catl'],
            }),
          )
        }
        if (path.endsWith('/trace')) {
          return Promise.resolve(
            json({
              terminal_state: 'succeeded',
              stages: [
                {
                  sequence: 1,
                  stage: 'completed',
                  status: 'succeeded',
                  sanitized_summary: 'done',
                },
              ],
            }),
          )
        }
        if (path.endsWith('/facts')) {
          return Promise.resolve(
            json([
              {
                fact_id: 'fact_ocf',
                metric_code: 'operating_cash_flow',
                value: '44708689000',
                currency: 'CNY',
                measurement_unit: 'CURRENCY',
                company: catalog.companies[0],
                period: { fiscal_year: 2024, fiscal_period: 'H1' },
                source: {
                  document_id: 'doc_catl',
                  published_at: '2024-07-26T23:59:59+08:00',
                  uri: 'https://disc.static.szse.cn/disc/example.PDF',
                },
                source_locator: { page: 71, section: '财务报表', table: '现金流量表' },
              },
              {
                fact_id: 'fact_profit',
                metric_code: 'net_income',
                value: '22865307000',
                currency: 'CNY',
                measurement_unit: 'CURRENCY',
                company: catalog.companies[0],
                period: { fiscal_year: 2024, fiscal_period: 'H1' },
                source: {
                  document_id: 'doc_catl',
                  published_at: '2024-07-26T23:59:59+08:00',
                  uri: 'https://disc.static.szse.cn/disc/example.PDF',
                },
                source_locator: { page: 69, section: '财务报表', table: '利润表' },
              },
            ]),
          )
        }
        if (path.endsWith('/evidence')) {
          return Promise.resolve(
            json([
              {
                chunk_id: 'chunk_catl_ocf',
                document_id: 'doc_catl',
                section: 'Financial statement fact: operating_cash_flow',
                text: '经营活动产生的现金流量净额 44,708,954,600.00 元。',
                text_hash: 'a'.repeat(64),
                source_uri: 'https://disc.static.szse.cn/disc/example.PDF',
                locator: { page_start: 73, page_end: 73 },
              },
              {
                chunk_id: 'chunk_catl_profit',
                document_id: 'doc_catl',
                section: 'Financial statement fact: net_income',
                text: '归属于上市公司股东的净利润 22,864,987,400.00 元。',
                text_hash: 'b'.repeat(64),
                source_uri: 'https://disc.static.szse.cn/disc/example.PDF',
                locator: { page_start: 70, page_end: 70 },
              },
              {
                chunk_id: 'chunk_catl_counter',
                document_id: 'doc_catl',
                section: 'Counter evidence: assurance limitation',
                text: '本半年度报告未经审计。',
                text_hash: 'c'.repeat(64),
                source_uri: 'https://disc.static.szse.cn/disc/example.PDF',
                locator: { page_start: 64, page_end: 64 },
              },
            ]),
          )
        }
        if (path.endsWith('/calculations')) {
          return Promise.resolve(
            json([
              {
                calculation_id: 'calc_cash_conversion',
                formula_code: 'cash_conversion',
                formula_version: '1.0.0',
                input_fact_ids: ['fact_ocf', 'fact_profit'],
                status: 'calculated',
                value: '1.95',
                measurement_unit: 'RATIO',
                explanation: '经营现金流除以净利润。',
              },
            ]),
          )
        }
        if (path.includes('/v1/research-runs/')) return Promise.resolve(json(manifest))
        return Promise.resolve(new Response('{}', { status: 404 }))
      }),
    )
  })

  it('keeps Quality Lab secondary to the primary research product', async () => {
    render(<App />)
    expect(await screen.findByText('开始公司研究')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '使用 n8n 表单入口' })).toHaveAttribute(
      'href',
      'http://127.0.0.1:5678/form/researchforge-v17-form',
    )

    fireEvent.click(screen.getByRole('button', { name: /Quality Lab/ }))

    expect(screen.getByRole('heading', { name: 'Quality Lab' })).toBeInTheDocument()
    expect(screen.getByText('读取冻结质量研究')).toBeInTheDocument()
    expect(screen.getByText(/不是完成普通公司研究所必需/)).toBeInTheDocument()
  })

  it('renders a report only after loading API artifacts', async () => {
    render(<App />)
    const submit = await screen.findByRole('button', { name: 'Research Company / 开始自主研究' })
    await waitFor(() => expect(submit).toBeEnabled())

    fireEvent.click(submit)

    expect(await screen.findByText('经营现金流覆盖净利润，结论来自真实官方披露与确定性计算。')).toBeInTheDocument()
    expect(screen.getByText('447.09 亿元')).toBeInTheDocument()
    expect(screen.getByText(/现金转化比为1.95倍/)).toBeInTheDocument()
    expect(screen.getAllByText('增长来源').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('Supported')).toBeInTheDocument()
    expect(screen.getByText('Blackwell 产品爬坡和客户需求共同推动增长。')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '增长来自哪个业务？' })).toBeInTheDocument()
    fireEvent.click(screen.getByText(/Supporting Evidence/))
    expect(screen.getByText(/经营活动产生的现金流量净额/)).toBeInTheDocument()
    expect(screen.queryByText(/SYNTHETIC/)).not.toBeInTheDocument()
    expect(screen.getByText('下一同口径报告期复核现金转化与营运资本')).toBeInTheDocument()
    fireEvent.click(screen.getByText(/Calculations/))
    expect(screen.getByText(/经营现金流除以净利润/)).toBeInTheDocument()
    expect(
      screen.getByText('报告未经审计，且扣除非经常性损益后的净利润低于归母净利润。'),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByText(/查看反证来源/))
    expect(screen.getByText('本半年度报告未经审计。')).toBeInTheDocument()
    expect(screen.getAllByText(/真实用户价值尚未验证/)).toHaveLength(2)
    expect(screen.getByRole('navigation', { name: '后端原始产物' })).toBeInTheDocument()
  })

  it('renders persisted Evolution state without inventing a supported result', async () => {
    render(<App />)
    await screen.findByText('开始公司研究')
    fireEvent.click(screen.getByRole('button', { name: /Quality Lab/ }))
    fireEvent.change(screen.getByLabelText('实验 ID'), {
      target: { value: 'experiment_frontend_test' },
    })
    fireEvent.click(screen.getByRole('button', { name: '读取实验' }))

    expect(await screen.findByText('preregistered · PENDING')).toBeInTheDocument()
    expect(screen.getByText('保持封闭')).toBeInTheDocument()
    expect(await screen.findAllByText('PROCEDURE_OMISSION')).toHaveLength(2)
    expect(screen.getAllByText('形成重大结论前记录确定性的现金转化结果。')).toHaveLength(2)
    expect(screen.getByText(/repair_rate=1.000/)).toBeInTheDocument()
    expect(screen.queryByText(/SUPPORTED/)).not.toBeInTheDocument()
  })

  it('renders the honest two-experiment negative outcome and audit trail', async () => {
    render(<App />)
    await screen.findByText('开始公司研究')
    fireEvent.click(screen.getByRole('button', { name: /Quality Lab/ }))
    fireEvent.change(screen.getByLabelText('实验 ID'), {
      target: { value: 'experiment_negative' },
    })
    fireEvent.click(screen.getByRole('button', { name: '读取实验' }))

    expect(await screen.findByText('completed · NO_ELIGIBLE_CLUSTER')).toBeInTheDocument()
    expect(screen.getByText('研究假设未获支持')).toBeInTheDocument()
    expect(screen.getByText(/两轮正式实验均未支持研究假设/)).toBeInTheDocument()
    expect(screen.getByText(/零-token 技术重试 1 次/)).toBeInTheDocument()
    expect(screen.getByText(/1 个失败评估 · 1 个失败事件/)).toBeInTheDocument()
    expect(screen.getByText(/0 个失败评估 · 0 个失败事件/)).toBeInTheDocument()
    expect(screen.queryByText(/研究假设获得支持/)).not.toBeInTheDocument()
  })
})
