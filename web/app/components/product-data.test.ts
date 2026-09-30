import { afterEach, describe, expect, it, vi } from 'vitest';
import { loadProductData } from './product-data';

afterEach(() => vi.restoreAllMocks());

describe('product data state', () => {
  it('requires a real session before showing security, games or activity', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}', { status: 401 }));
    await expect(loadProductData()).resolves.toMatchObject({ state: 'SIGNED_OUT' });
  });
  it('keeps a failed read distinct from an empty product', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'));
    await expect(loadProductData()).resolves.toMatchObject({ state: 'ERROR' });
  });
  it('never displays a malformed security response as a protected account', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}'));
    await expect(loadProductData()).resolves.toMatchObject({ state: 'ERROR' });
  });
  it('loads bounded server data with empty states preserved', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      const payload = String(url).endsWith('/security') ? {
        email: null, email_verified: false, password_enabled: true,
        mfa_enabled: false, mfa_recovery_codes_remaining: 0, providers: [],
      } : String(url).endsWith('/games') ? { games: [] } : { events: [] };
      return new Response(JSON.stringify(payload));
    });
    await expect(loadProductData()).resolves.toMatchObject({ state: 'READY', games: [], events: [] });
  });
});
