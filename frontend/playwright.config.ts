import { defineConfig, devices } from '@playwright/test'

/**
 * End-to-end tests against a running site. Configure with environment variables:
 *   ET_BASE_URL       site URL, e.g. https://admin.dreamtechsolution.com (required)
 *   ET_USER           a user with the "Expense User" role (required; use a dedicated test user)
 *   ET_PASSWORD       that user's password (required)
 *   ET_RESOLVE        optional Chromium host-resolver rule, e.g. "MAP admin.example.com 127.0.0.1"
 * Tests create uniquely named data through the API and delete it afterwards.
 */
const args = process.env.ET_RESOLVE ? [`--host-resolver-rules=${process.env.ET_RESOLVE}`] : []

export default defineConfig({
  testDir: './e2e',
  // One shared test user: run serially so tests don't see each other's data.
  workers: 1,
  fullyParallel: false,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  globalSetup: './e2e/global-setup.ts',
  use: {
    baseURL: process.env.ET_BASE_URL,
    storageState: 'e2e/.auth/state.json',
    ignoreHTTPSErrors: true,
    launchOptions: { args },
    actionTimeout: 20_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1360, height: 900 } }, testIgnore: /mobile\.spec/ },
    { name: 'mobile', use: { ...devices['Pixel 7'] }, testMatch: /mobile\.spec/ },
  ],
})
