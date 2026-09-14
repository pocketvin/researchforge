import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

async function mockV2(page: import('@playwright/test').Page) {
  await page.route('**/v2/capabilities', (route) =>
    route.fulfill({
      json: {
        version: '2.0.0-alpha.1',
        agent_ready: true,
        provider: 'hybrid',
        model: 'deepseek-v4-flash',
      },
    }),
  )
  await page.route('**/v2/research-runs?**', (route) => route.fulfill({ json: [] }))
}

test('root is the V2 research workspace and the legacy web is gone', async ({ page }) => {
  await mockV2(page)
  await page.goto('/')

  await expect(page.getByRole('heading', { name: '开始一项研究' })).toBeVisible()
  await expect(page.getByLabel('V2 公司')).toHaveValue('宁德时代')
  await expect(page.getByLabel('V2 年份')).toHaveValue('2024')
  await expect(page.getByLabel('V2 报告类型')).toHaveValue('H1')
  await expect(page.getByRole('link', { name: '旧版研究' })).toHaveCount(0)
  await expect(page.getByText('方法与实验')).toHaveCount(0)

  const accessibility = await new AxeBuilder({ page }).analyze()
  expect(accessibility.violations.filter((item) => item.impact === 'critical')).toEqual([])
})

test('/research/v2 remains a V2 alias rather than a legacy router', async ({ page }) => {
  await mockV2(page)
  await page.goto('/research/v2')

  await expect(page.getByRole('heading', { name: '开始一项研究' })).toBeVisible()
  await expect(page.getByText('从财报到可核查的判断')).toBeVisible()
  await expect(page.getByRole('link', { name: '旧版研究' })).toHaveCount(0)
})

test('market-specific report types remain available on the V2 root', async ({ page }) => {
  await mockV2(page)
  await page.goto('/')

  await page.getByLabel('V2 市场').selectOption('US')
  await expect(page.getByLabel('V2 年份')).toHaveValue('LATEST')
  await page.getByLabel('V2 年份').selectOption('2024')

  const reportType = page.getByLabel('V2 报告类型')
  await expect(reportType.locator('option', { hasText: '第二季度报告' })).toHaveCount(1)
  await expect(reportType.locator('option', { hasText: '半年度报告' })).toHaveCount(0)
})
