import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 60_000,
  use: { ...devices['Desktop Safari'], headless: true },
  projects: [{ name: 'webkit', use: { browserName: 'webkit' } }]
})
