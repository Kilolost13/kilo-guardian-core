import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 30 * 1000,
  retries: 1,
  use: {
    baseURL: 'http://127.0.0.1:4200',
    headless: true,
  },
  webServer: {
    // Start backend (uvicorn) in background and then the static proxy server which serves frontend and proxies /api -> backend
    command: 'bash -lc "KILO_API_KEY=kilo-dev-key-2025 PYTHONPATH=.. python3 -m uvicorn kilo_v2.server_core:app --port 8001 >/tmp/uvicorn-e2e.log 2>&1 & npm run start:test-server"',
    port: 4200,
    timeout: 180 * 1000,
    reuseExistingServer: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
