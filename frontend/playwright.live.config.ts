import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e-live',
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:4175',
    trace: 'retain-on-failure',
    launchOptions: process.env.PLAYWRIGHT_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH }
      : {},
  },
  webServer: [
    {
      command: 'uv run --project .. uvicorn researchforge.api.app:create_app --factory --host 127.0.0.1 --port 8015',
      url: 'http://127.0.0.1:8015/healthz',
      reuseExistingServer: false,
      env: {
        RESEARCHFORGE_REASONING_MODE: 'deterministic',
        RESEARCHFORGE_DATABASE_ENABLED: '0',
        RESEARCHFORGE_DATA_NAMESPACE: 'product',
        RESEARCHFORGE_DATA_ROOT: '../data/product/packages',
        RESEARCHFORGE_ARTIFACT_ROOT: '../artifacts/e2e-live',
      },
    },
    {
      command: 'npm run dev -- --port 4175 --strictPort',
      url: 'http://127.0.0.1:4175',
      reuseExistingServer: false,
      env: { RESEARCHFORGE_API_PROXY: 'http://127.0.0.1:8015' },
    },
  ],
})
