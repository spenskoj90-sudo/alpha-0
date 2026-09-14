import { describe, expect, it } from 'vitest';

import { normalizeCorrelationId } from './core-session';

describe('Core web correlation boundary', () => {
  it('preserves bounded safe request ids', () => {
    expect(normalizeCorrelationId('web-flow.123:retry')).toBe('web-flow.123:retry');
  });

  it('replaces unsafe or header-injection request ids with UUIDs', () => {
    const value = normalizeCorrelationId('unsafe id\nAuthorization: secret');
    expect(value).toMatch(/^[0-9a-f-]{36}$/i);
    expect(value).not.toContain('secret');
  });
});
