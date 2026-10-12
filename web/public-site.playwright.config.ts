import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './e2e', testMatch: 'public-navigation.spec.ts', timeout: 60_000,
  expect: { timeout: 10_000 }, workers: 1, retries: 0, reporter: 'list',
  use: { launchOptions: process.env.SENTINEL_BROWSER_EXECUTABLE ? { executablePath: process.env.SENTINEL_BROWSER_EXECUTABLE, args: ['--no-sandbox'] } : undefined, trace: 'off', screenshot: 'off', video: 'off' },
  projects: [
    { name: 'desktop-dark', use: { ...devices['Desktop Chrome'], colorScheme: 'dark' } },
    { name: 'desktop-light', use: { ...devices['Desktop Chrome'], colorScheme: 'light' } },
    { name: 'mobile-light', use: { ...devices['Pixel 7'], colorScheme: 'light' } },
    { name: 'mobile-dark', use: { ...devices['Pixel 7'], colorScheme: 'dark' } },
  ],
  webServer: { command: 'python scripts/serve_static_acceptance.py', cwd: '..', url: 'http://127.0.0.1:3001', reuseExistingServer: false },
});
