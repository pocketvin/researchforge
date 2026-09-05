import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

for (const [company, period] of [
  ['宁德时代', '2024H1'],
  ['宁德时代', '2024FY'],
  ['比亚迪', '2024H1'],
]) {
  test(`autonomous reviewed-cache backend research: ${company}/${period}`, async ({ page }) => {
    await page.goto('/')
    await page.getByLabel('Company search').fill(company)
    await page.getByLabel('Market selector').selectOption('CN')
    await page.getByLabel('Period input').fill(period)
    await page.locator('textarea.question-input').fill(`${period}利润是否真正转化为经营现金流？`)
    const responsePromise = page.waitForResponse((response) =>
      response.url().endsWith('/result') && response.status() === 200,
    )
    await page.getByRole('button', { name: 'Research Company / 开始自主研究' }).click()
    const response = await responsePromise
    const result = await response.json() as {
      executive_summary: string
      limitations: string[]
      synthesis_mode: 'model' | 'evidence_summary_fallback'
    }
    expect(result.synthesis_mode).toBe('evidence_summary_fallback')
    await expect(page.getByText(result.executive_summary, { exact: true })).toBeVisible()
    await expect(page.getByText('EVIDENCE SUMMARY FALLBACK · 未执行 AI 综合分析')).toBeVisible()
    for (const section of ['Financial Facts', 'Calculations', 'Supporting Evidence', 'Research Trace']) {
      await page.locator('details').filter({ hasText: section }).locator('summary').press('Enter')
    }
    await expect(page.locator('.stage-item')).toHaveCount(10)
    await expect(page.getByText(result.limitations[0], { exact: true })).toBeVisible()
    const issues = await new AxeBuilder({ page }).analyze()
    expect(issues.violations.filter((issue) => issue.impact === 'critical')).toEqual([])
  })
}
