import { expect, test } from '@playwright/test'

test('live backend serves only the V2 research web surface', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: '开始一项研究' })).toBeVisible()
  await expect(page.getByLabel('V2 公司')).toHaveValue('宁德时代')
  await expect(page.getByLabel('V2 年份')).toBeVisible()
  await expect(page.getByLabel('V2 报告类型')).toBeVisible()
  await expect(page.getByRole('link', { name: '旧版研究' })).toHaveCount(0)
  await expect(page.getByText('方法与实验')).toHaveCount(0)
})
