import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchAccountSnapshot } from './account-control';

afterEach(() => vi.restoreAllMocks());

describe('account loading failure recovery', () => {
  it('returns an actionable error when the browser loses its connection', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'));
    await expect(fetchAccountSnapshot()).resolves.toMatchObject({ view: 'ERROR' });
  });

  it('does not turn malformed successful responses into an empty authenticated account', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('not json', { status: 200 }));
    await expect(fetchAccountSnapshot()).resolves.toMatchObject({ view: 'ERROR' });
  });

  it('rejects collection-shaped objects instead of crashing the account UI', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response(JSON.stringify({
      plans: {}, subscriptions: {}, entitlements: {},
    }), { status: 200 }));
    await expect(fetchAccountSnapshot()).resolves.toMatchObject({ view: 'ERROR' });
  });

  it('loads real empty collections without inventing unavailable data', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response(JSON.stringify({
      plans: [], subscriptions: [], entitlements: [],
    }), { status: 200 }));
    await expect(fetchAccountSnapshot()).resolves.toEqual({
      view: 'READY', plans: [], subscriptions: [], entitlements: [],
    });
  });

  it('keeps an unauthenticated response distinct from network failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}', { status: 401 }));
    await expect(fetchAccountSnapshot()).resolves.toEqual({ view: 'SIGNED_OUT' });
  });
});
