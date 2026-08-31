import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

test('research and Skill Lab are navigable', async ({ page }) => {
  await page.route('**/v1/catalog', (route) =>
    route.fulfill({
      json: {
        schema_version: '1.4.0',
        implementation_level: 'G1_BREADTH',
        supported_task_types: ['filing_analysis'],
        limitations: ['fixture only'],
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
      },
    }),
  )
  await page.goto('/')

  await expect(page.getByRole('heading', { name: '建立研究任务' })).toBeVisible()
  const researchAccessibility = await new AxeBuilder({ page }).analyze()
  expect(
    researchAccessibility.violations.filter((violation) => violation.impact === 'critical'),
  ).toEqual([])
  await page.getByRole('button', { name: /Skill Lab/ }).click()
  await expect(page.getByRole('heading', { name: 'Skill Lab' })).toBeVisible()
  await expect(page.getByText('没有硬编码的“成功故事”')).toBeVisible()
  const labAccessibility = await new AxeBuilder({ page }).analyze()
  expect(labAccessibility.violations.filter((violation) => violation.impact === 'critical')).toEqual(
    [],
  )
})
