import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const catalog = {
  schema_version: '1.4.0',
  implementation_level: 'G1_BREADTH',
  supported_task_types: [
    'company_research',
    'filing_analysis',
    'peer_comparison',
    'thesis_investigation',
    'risk_detection',
  ],
  limitations: ['fixture only'],
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
        if (path.includes('/v1/evolution-experiments/')) {
          return Promise.resolve(
            json({
              schema_version: '1.4.0',
              experiment_id: 'experiment_frontend_test',
              scope_version: '1.4',
              suite_id: 'suite_frontend_test',
              suite_hash: '7'.repeat(64),
              status: 'preregistered',
              outcome: 'PENDING',
              seed_skill_version_id: 'skill_fundamental_1_0_0',
              candidate_skill_version_id: null,
              split_case_ids: {
                evolution: ['case_evo_a', 'case_evo_b'],
                validation: ['case_val'],
                final_test: ['case_final'],
              },
              budget: { currency: 'USD', cap: 20, spent: 0 },
              final_test_consumed: false,
              preregistered_at: '2026-09-01T00:00:00+08:00',
              finished_at: null,
            }),
          )
        }
        if (path === '/v1/research-runs') return Promise.resolve(json({ run_id: manifest.run_id }))
        if (path.endsWith('/result')) {
          return Promise.resolve(
            json({
              result_id: 'result_frontend_test',
              task_type: 'filing_analysis',
              executive_summary: '经营现金流覆盖净利润，结论来自冻结事实。',
              claims: [
                {
                  claim_id: 'claim_frontend_test',
                  claim_type: 'earnings_quality',
                  epistemic_status: 'supported_inference',
                  materiality: 'material',
                  direction: 'positive',
                  text: '现金转化比为1.95倍。',
                  fact_ids: ['fact_ocf', 'fact_profit'],
                  counter_evidence_search: {
                    performed: true,
                    result: 'not_found',
                    summary: '当前证据包未发现额外反证。',
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
                  uri: 'https://example.test/filing.pdf',
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
                  uri: 'https://example.test/filing.pdf',
                },
                source_locator: { page: 69, section: '财务报表', table: '利润表' },
              },
            ]),
          )
        }
        if (path.includes('/v1/research-runs/')) return Promise.resolve(json(manifest))
        return Promise.resolve(new Response('{}', { status: 404 }))
      }),
    )
  })

  it('renders both primary product pages', async () => {
    render(<App />)
    expect(await screen.findByText('建立研究任务')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Skill Lab/ }))

    expect(screen.getByRole('heading', { name: 'Skill Lab' })).toBeInTheDocument()
    expect(screen.getByText('等待受控实验产物')).toBeInTheDocument()
  })

  it('renders a report only after loading API artifacts', async () => {
    render(<App />)
    const submit = await screen.findByRole('button', { name: '开始可审计研究' })
    await waitFor(() => expect(submit).toBeEnabled())

    fireEvent.click(submit)

    expect(await screen.findByText('经营现金流覆盖净利润，结论来自冻结事实。')).toBeInTheDocument()
    expect(screen.getByText('447.09 亿元')).toBeInTheDocument()
    expect(screen.getByText(/现金转化比为1.95倍/)).toBeInTheDocument()
    expect(screen.getAllByText(/真实用户价值尚未验证/)).toHaveLength(2)
  })

  it('renders persisted Evolution state without inventing a supported result', async () => {
    render(<App />)
    await screen.findByText('建立研究任务')
    fireEvent.click(screen.getByRole('button', { name: /Skill Lab/ }))
    fireEvent.change(screen.getByLabelText('实验 ID'), {
      target: { value: 'experiment_frontend_test' },
    })
    fireEvent.click(screen.getByRole('button', { name: '读取实验' }))

    expect(await screen.findByText('preregistered · PENDING')).toBeInTheDocument()
    expect(screen.getByText('保持封闭')).toBeInTheDocument()
    expect(screen.queryByText(/SUPPORTED/)).not.toBeInTheDocument()
  })
})
