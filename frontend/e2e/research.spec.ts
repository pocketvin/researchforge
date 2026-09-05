import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

const productCatalog = {
  schema_version: '1.5.0',
  data_namespace: 'product',
  implementation_level: 'V1_5_REAL_DATA',
  supported_task_types: ['filing_analysis'],
  limitations: ['少量人工核验的真实公开披露。'],
  companies: [
    {
      company_id: 'cn_300750',
      legal_name: '宁德时代新能源科技股份有限公司',
      ticker: '300750',
      exchange: 'SZSE',
      country_code: 'CN',
      period_labels: ['2024H1'],
    },
  ],
}

test('research and secondary Quality Lab are navigable', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: '开始公司研究' })).toBeVisible()
  await expect(page.getByLabel('Company search')).toHaveValue('贵州茅台')
  await expect(page.getByLabel('Market selector')).toHaveValue('AUTO')
  await expect(page.getByLabel('Period input')).toHaveValue('')
  await expect(page.getByText(/官方披露自动发现/)).toBeVisible()
  await expect(page.getByRole('link', { name: '使用 n8n 表单入口' })).toHaveAttribute(
    'href',
    'http://127.0.0.1:5678/form/researchforge-v17-form',
  )
  const researchAccessibility = await new AxeBuilder({ page }).analyze()
  expect(
    researchAccessibility.violations.filter((violation) => violation.impact === 'critical'),
  ).toEqual([])
  await page.getByRole('button', { name: /Quality Lab/ }).click()
  await expect(page.getByRole('heading', { name: 'Quality Lab' })).toBeVisible()
  await expect(page.getByText(/不是完成普通公司研究所必需/)).toBeVisible()
  const labAccessibility = await new AxeBuilder({ page }).analyze()
  expect(labAccessibility.violations.filter((violation) => violation.impact === 'critical')).toEqual(
    [],
  )
})

test('real-data research journey exposes a progressively auditable result', async ({ page }) => {
  const runId = 'run_e2e_real_data'
  await page.route('**/v1/**', (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    if (path === '/v1/catalog') return route.fulfill({ json: productCatalog })
    if (path === '/v1/autonomous-research-runs' && route.request().method() === 'POST') {
      return route.fulfill({ status: 202, json: { run_id: runId } })
    }
    if (path === `/v1/research-runs/${runId}`) {
      return route.fulfill({
        json: {
          run_id: runId,
          lifecycle_state: 'succeeded',
          input: {
            task_type: 'filing_analysis',
            research_question: '2024 年上半年利润是否真正转化成了经营现金流？',
            company_ids: ['cn_300750'],
            requested_period_labels: ['2024H1'],
            research_time: '2026-09-03T00:00:00+08:00',
          },
          artifacts: {
            result_id: `result_${runId}`,
            workflow_trace_id: `trace_${runId}`,
            evaluation_id: null,
          },
          failure: null,
        },
      })
    }
    if (path.endsWith('/result')) {
      return route.fulfill({
        json: {
          result_id: `result_${runId}`,
          task_type: 'filing_analysis',
          synthesis_mode: 'model',
          executive_summary: '经营现金流覆盖净利润；现金转化比为1.96倍。',
          claims: [
            {
              claim_id: 'claim_cash_conversion',
              claim_type: 'earnings_quality',
              epistemic_status: 'supported_inference',
              materiality: 'material',
              direction: 'positive',
              text: '经营现金流与净利润的现金转化比为1.96倍。',
              fact_ids: ['fact_profit', 'fact_ocf'],
              support_evidence_ids: ['chunk_profit', 'chunk_ocf'],
              counter_evidence_search: {
                performed: true,
                queries: ['未经审计'],
                result: 'found',
                evidence_ids: ['chunk_counter'],
                summary: '中期财务报告未经审计，限制单期结论外推。',
              },
              alternative_explanations: [],
              confidence: { level: 'high', basis: 'verified facts and formula' },
            },
          ],
          mandatory_checks: [
            {
              check_code: 'cash_conversion',
              status: 'performed',
              finding: '经营现金流除以净利润。',
              fact_ids: ['fact_ocf', 'fact_profit'],
              evidence_ids: ['chunk_ocf', 'chunk_profit'],
            },
          ],
          monitoring_items: [
            {
              monitor_code: 'next_cash_conversion',
              title: '下一同口径报告期复核现金转化与营运资本',
              rationale: '跟踪经营现金流、应收账款和存货。',
              trigger: '现金转化比低于1.00倍。',
              next_review: '下一同口径财务报告发布后',
              fact_ids: ['fact_ocf', 'fact_profit'],
              evidence_ids: ['chunk_ocf', 'chunk_profit'],
            },
          ],
          limitations: ['半年度财务报告未经审计。'],
          source_document_ids: ['doc_catl_2024h1'],
        },
      })
    }
    if (path.endsWith('/facts')) {
      return route.fulfill({
        json: [
          {
            fact_id: 'fact_profit',
            metric_code: 'net_income',
            value: '22864987400.00',
            currency: 'CNY',
            measurement_unit: 'CURRENCY',
            company: productCatalog.companies[0],
            period: { fiscal_year: 2024, fiscal_period: 'H1' },
            source: {
              document_id: 'doc_catl_2024h1',
              published_at: '2024-07-26T23:59:59+08:00',
              uri: 'https://disc.static.szse.cn/disc/example.PDF',
            },
            source_locator: { page: 70, section: '合并利润表', table: '利润表' },
          },
          {
            fact_id: 'fact_ocf',
            metric_code: 'operating_cash_flow',
            value: '44708954600.00',
            currency: 'CNY',
            measurement_unit: 'CURRENCY',
            company: productCatalog.companies[0],
            period: { fiscal_year: 2024, fiscal_period: 'H1' },
            source: {
              document_id: 'doc_catl_2024h1',
              published_at: '2024-07-26T23:59:59+08:00',
              uri: 'https://disc.static.szse.cn/disc/example.PDF',
            },
            source_locator: { page: 73, section: '合并现金流量表', table: '现金流量表' },
          },
        ],
      })
    }
    if (path.endsWith('/evidence')) {
      return route.fulfill({
        json: [
          {
            chunk_id: 'chunk_profit',
            document_id: 'doc_catl_2024h1',
            section: 'Financial statement fact: net_income',
            text: '归属于上市公司股东的净利润 22,864,987,400.00 元。',
            text_hash: 'a'.repeat(64),
            source_uri: 'https://disc.static.szse.cn/disc/example.PDF',
            locator: { page_start: 70, page_end: 70 },
          },
          {
            chunk_id: 'chunk_ocf',
            document_id: 'doc_catl_2024h1',
            section: 'Financial statement fact: operating_cash_flow',
            text: '经营活动产生的现金流量净额 44,708,954,600.00 元。',
            text_hash: 'b'.repeat(64),
            source_uri: 'https://disc.static.szse.cn/disc/example.PDF',
            locator: { page_start: 73, page_end: 73 },
          },
          {
            chunk_id: 'chunk_counter',
            document_id: 'doc_catl_2024h1',
            section: 'Counter evidence: assurance limitation',
            text: '本半年度财务报告未经审计。',
            text_hash: 'c'.repeat(64),
            source_uri: 'https://disc.static.szse.cn/disc/example.PDF',
            locator: { page_start: 64, page_end: 64 },
          },
        ],
      })
    }
    if (path.endsWith('/calculations')) {
      return route.fulfill({
        json: [
          {
            calculation_id: 'calc_cash_conversion',
            formula_code: 'cash_conversion',
            formula_version: '1.0.0',
            input_fact_ids: ['fact_ocf', 'fact_profit'],
            status: 'calculated',
            value: '1.955345691552841179348299138',
            measurement_unit: 'RATIO',
            explanation: 'Calculated as operating cash flow / net income.',
          },
        ],
      })
    }
    if (path.endsWith('/trace')) {
      return route.fulfill({
        json: {
          run_id: runId,
          terminal_state: 'succeeded',
          stages: Array.from({ length: 10 }, (_, index) => ({
            sequence: index + 1,
            stage: index === 9 ? 'completed' : `stage_${index + 1}`,
            status: 'succeeded',
            sanitized_summary: 'bounded workflow stage',
          })),
        },
      })
    }
    return route.fulfill({ status: 404, json: {} })
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'Research Company / 开始自主研究' }).click()
  await expect(page.getByText('经营现金流覆盖净利润；现金转化比为1.96倍。')).toBeVisible()
  await expect(page.getByText('MODEL SYNTHESIS')).toBeVisible()
  await expect(page.getByText('中期财务报告未经审计，限制单期结论外推。')).toBeVisible()
  await expect(page.getByText('下一同口径报告期复核现金转化与营运资本')).toBeVisible()

  const facts = page.locator('details').filter({ hasText: 'Financial Facts' })
  const calculations = page.locator('details').filter({ hasText: 'Calculations' })
  const evidence = page.locator('details').filter({ hasText: 'Supporting Evidence' })
  const trace = page.locator('details').filter({ hasText: 'Research Trace' })
  await expect(facts).not.toHaveAttribute('open', '')
  await expect(calculations).not.toHaveAttribute('open', '')
  await expect(evidence).not.toHaveAttribute('open', '')
  await expect(trace).not.toHaveAttribute('open', '')

  await facts.locator('summary').press('Enter')
  await calculations.locator('summary').press('Enter')
  await evidence.locator('summary').press('Enter')
  await trace.locator('summary').press('Enter')
  await page.getByText(/查看反证来源/).press('Enter')
  await expect(page.getByText('228.65 亿元', { exact: true })).toBeVisible()
  await expect(page.getByText(/Calculated as operating cash flow/)).toBeVisible()
  await expect(page.getByText(/经营活动产生的现金流量净额/).last()).toBeVisible()
  await expect(page.getByText('本半年度财务报告未经审计。')).toBeVisible()
  await expect(trace.locator('.stage-item')).toHaveCount(10)

  const accessibility = await new AxeBuilder({ page }).analyze()
  expect(accessibility.violations.filter((violation) => violation.impact === 'critical')).toEqual(
    [],
  )
})

test('terminal abstention is explicit and never renders a research report', async ({ page }) => {
  const runId = 'run_e2e_insufficient_data'
  await page.route('**/v1/**', (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/v1/catalog') return route.fulfill({ json: productCatalog })
    if (path === '/v1/autonomous-research-runs' && route.request().method() === 'POST') {
      return route.fulfill({ status: 202, json: { run_id: runId } })
    }
    if (path === `/v1/research-runs/${runId}`) {
      return route.fulfill({ json: {
        run_id: runId,
        lifecycle_state: 'insufficient_data',
        input: { task_type: 'filing_analysis', research_question: '资料不足时是否会弃权？', company_ids: ['cn_300750'], requested_period_labels: ['2024H1'], research_time: '2020-01-01T00:00:00Z' },
        artifacts: { result_id: null, workflow_trace_id: `trace_${runId}`, evaluation_id: null },
        failure: { code: 'EVIDENCE_CUTOFF', message: '研究截止时间早于可用官方披露。' },
      } })
    }
    if (path.endsWith('/trace')) return route.fulfill({ json: { run_id: runId, terminal_state: 'insufficient_data', stages: [] } })
    return route.fulfill({ status: 404, json: {} })
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'Research Company / 开始自主研究' }).click()
  await expect(page.getByRole('heading', { name: '资料不足，ResearchForge 已弃权' })).toBeVisible()
  await expect(page.getByText(/不会被包装成结论|官方来源可定位/)).toBeVisible()
  await expect(page.getByText('Executive Conclusion / 核心结论')).toHaveCount(0)
  await expect(page.getByRole('link', { name: /查看 Research Trace/ })).toBeVisible()
})
