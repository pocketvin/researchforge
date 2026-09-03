import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

for (const [company, period] of [
  ['cn_300750', '2024H1'],
  ['cn_300750', '2024FY'],
  ['cn_002594', '2024H1'],
]) {
  test(`real backend research: ${company}/${period}`, async ({ page }) => {
    await page.goto('/')
    await expect(page.getByLabel('Company selector')).not.toBeEmpty()
    await page.getByLabel('Company selector').selectOption(company)
    await page.getByLabel('Period selector').selectOption(period)
    await page.getByRole('textbox').fill(`${period}利润是否真正转化为经营现金流？`)
    const responsePromise = page.waitForResponse((response) =>
      response.url().endsWith('/result') && response.status() === 200,
    )
    await page.getByRole('button', { name: 'Start Research / 开始研究' }).click()
    const response = await responsePromise
    const result = await response.json() as { executive_summary: string; limitations: string[] }
    await expect(page.getByText(result.executive_summary, { exact: true })).toBeVisible()
    for (const section of ['Financial Facts', 'Calculations', 'Supporting Evidence', 'Research Trace']) {
      await page.locator('details').filter({ hasText: section }).locator('summary').press('Enter')
    }
    await expect(page.locator('.stage-item')).toHaveCount(10)
    await expect(page.getByText(result.limitations[0], { exact: true })).toBeVisible()
    const issues = await new AxeBuilder({ page }).analyze()
    expect(issues.violations.filter((issue) => issue.impact === 'critical')).toEqual([])
  })
}
