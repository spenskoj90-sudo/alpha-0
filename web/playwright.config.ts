import { defineConfig, devices } from '@playwright/test';
import { randomBytes } from 'node:crypto';

const staging = process.env.SENTINEL_BROWSER_TARGET === 'staging';
export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  expect: { timeout: 60_000 },
  workers: 1,
  retries: 0,
  reporter: [['list'], ['json', { outputFile: 'test-results/browser-results.json' }]],
  use: {
    baseURL: staging ? 'https://sentinel-web-staging-fxhn.onrender.com' : 'http://127.0.0.1:3000',
    // Auth traffic contains disposable credentials. Never persist traces, cookies or response bodies.
    trace: 'off', screenshot: 'off', video: 'off',
  },
  projects: [
    { name: 'desktop-dark', use: { ...devices['Desktop Chrome'], colorScheme: 'dark' } },
    { name: 'desktop-light', use: { ...devices['Desktop Chrome'], colorScheme: 'light' } },
    { name: 'mobile-light', use: { ...devices['Pixel 7'], colorScheme: 'light' } },
    { name: 'mobile-dark', use: { ...devices['Pixel 7'], colorScheme: 'dark' } },
  ],
  webServer: staging ? undefined : [
    { command: 'python -m uvicorn app.main:app --host 127.0.0.1 --port 8000', cwd: '../server', url: 'http://127.0.0.1:8000/healthz', reuseExistingServer: false,
      env: { SENTINEL_ENV: 'development', DATABASE_URL: '', SENTINEL_ACCOUNT_MFA_KEY: randomBytes(32).toString('base64url') } },
    { command: 'npm run start', url: 'http://127.0.0.1:3000', reuseExistingServer: false,
      env: { SENTINEL_CORE_URL: 'http://127.0.0.1:8000', SENTINEL_WEB_ORIGIN: 'http://127.0.0.1:3000' } },
    { command: 'python scripts/serve_static_acceptance.py', cwd: '..', url: 'http://127.0.0.1:3001', reuseExistingServer: false },
  ],
});
