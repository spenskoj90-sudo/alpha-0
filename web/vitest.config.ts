import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary'],
      include: ['app/api/**/*.ts'],
      exclude: ['app/**/*.test.ts', 'app/**/*.test.tsx'],
      thresholds: {
        statements: 85,
        lines: 85,
        functions: 85,
        branches: 80,
        'app/api/_lib/core-session.ts': {
          statements: 90,
          lines: 90,
          functions: 90,
          branches: 85,
        },
        'app/api/session/**/*.ts': {
          statements: 90,
          lines: 90,
          functions: 90,
          branches: 85,
        },
        'app/api/billing/**/*.ts': {
          statements: 90,
          lines: 90,
          functions: 90,
          branches: 85,
        },
        'app/api/admin/_auth.ts': {
          statements: 95,
          lines: 95,
          functions: 95,
          branches: 90,
        },
        'app/api/admin/entitlements/route.ts': {
          statements: 90,
          lines: 90,
          functions: 90,
          branches: 85,
        },
      },
    },
  },
});
