import { chromium } from '@playwright/test'
import { mkdir } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const assets = resolve(here, '../../docs/assets')
const webUrl = process.env.RESEARCHFORGE_WEB_URL ?? 'http://127.0.0.1:4173'
const n8nUrl = process.env.RESEARCHFORGE_N8N_FORM_URL ?? 'http://127.0.0.1:5678/form/researchforge-v15-form'
const executablePath = process.env.PLAYWRIGHT_EXECUTABLE_PATH
await mkdir(assets, { recursive: true })

const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) })
const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, deviceScaleFactor: 1 })

try {
  const web = await context.newPage()
  await web.goto(webUrl)
  await web.getByRole('heading', { name: '开始公司研究' }).waitFor()
  await web.getByLabel('Company selector').selectOption('cn_300750')
  await web.getByLabel('Period selector').selectOption('2024H1')
  await web.screenshot({ path: resolve(assets, 'research-page-v1.5-final-start.png'), fullPage: true })
  await web.getByRole('button', { name: 'Start Research / 开始研究' }).click()
  await web.locator('.summary-card').waitFor({ timeout: 30_000 })
  await web.screenshot({ path: resolve(assets, 'research-page-v1.5-final-result.png'), fullPage: true })

  const form = await context.newPage()
  await form.goto(n8nUrl)
  await form.getByRole('heading', { name: /ResearchForge/ }).waitFor()
  await form.screenshot({ path: resolve(assets, 'n8n-form-v1.5.png'), fullPage: true })
  await form.getByLabel('Company / 公司').selectOption('宁德时代 · 300750.SZSE')
  await form.getByLabel('Period / 报告期').selectOption('2024H1')
  await form.getByLabel('Research Question / 研究问题').fill('2024年上半年利润是否真正转化成了经营现金流?')
  await form.getByRole('button', { name: 'Start Research / 开始研究' }).click()
  await form.getByRole('heading', { name: 'ResearchForge 研究完成' }).waitFor({ timeout: 30_000 })
  await form.screenshot({ path: resolve(assets, 'n8n-result-v1.5.png'), fullPage: true })

  await form.goto(n8nUrl)
  await form.getByLabel('Company / 公司').selectOption('比亚迪 · 002594.SZSE')
  await form.getByLabel('Period / 报告期').selectOption('2024FY')
  await form.getByLabel('Research Question / 研究问题').fill('该不支持期间应当明确拒绝且不生成研究结论。')
  await form.getByRole('button', { name: 'Start Research / 开始研究' }).click()
  await form.getByRole('heading', { name: '研究未生成' }).waitFor({ timeout: 30_000 })
  await form.screenshot({ path: resolve(assets, 'n8n-abstention-v1.5.png'), fullPage: true })
} finally {
  await browser.close()
}

console.log(`Captured final product screenshots in ${assets}`)
