import { afterEach, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { proxyAuthenticated } from './core-session';

const session = { session_token: 'rotated-access', refresh_token: 'rotated-refresh', expires_at: '2030-01-01T00:00:00Z', scopes: ['game:read'] };
const request = (token: string) => new NextRequest('https://app.example/api/account', {
  headers: { cookie: `sentinel_refresh=${token}` },
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); });

it('joins concurrent refreshes without replaying a settled rotation', async () => {
  vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  let finish!: () => void;
  const pending = new Promise<void>(resolve => { finish = resolve; });
  let used = false;
  const refresh = vi.spyOn(globalThis, 'fetch').mockImplementation(async url => {
    if (String(url).endsWith('/sessions/refresh')) {
      const denied = used;
      used = true;
      await pending;
      return Response.json(denied ? { error: 'INVALID_REFRESH' } : session, { status: denied ? 401 : 200 });
    }
    return Response.json({ ok: true });
  });
  const first = proxyAuthenticated(request('one-use-token'), '/v1/account');
  const second = proxyAuthenticated(request('one-use-token'), '/v1/account');
  finish();
  const responses = await Promise.all([first, second]);
  expect(responses.map(r => r.status)).toEqual([200, 200]);
  for (const result of responses) expect(result.headers.get('set-cookie')).toContain('sentinel_refresh=rotated-refresh');
  expect(refresh.mock.calls.filter(([url]) => String(url).endsWith('/sessions/refresh'))).toHaveLength(1);
  const replay = await proxyAuthenticated(request('one-use-token'), '/v1/account');
  expect(replay.status).toBe(401);
  expect(replay.headers.has('set-cookie')).toBe(false);
});

it('a late denied refresh cannot erase a newer browser session', async () => {
  vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({ error: 'INVALID_REFRESH' }, { status: 401 }));
  const denied = await proxyAuthenticated(request('already-rotated-in-another-worker'), '/v1/account');
  expect(denied.status).toBe(401);
  expect(denied.headers.has('set-cookie')).toBe(false);
});

it('a successful rotation followed by delayed 401 cannot overwrite a newer login', async () => {
  vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  let finish!: () => void;
  const pending = new Promise<void>(resolve => { finish = resolve; });
  vi.spyOn(globalThis, 'fetch').mockImplementation(async url => {
    if (String(url).endsWith('/sessions/refresh')) return Response.json(session);
    await pending;
    return Response.json({ error: 'SESSION_REVOKED' }, { status: 401 });
  });
  const stale = proxyAuthenticated(request('token-before-new-login'), '/v1/account');
  // The browser can receive a new login while this old request is still pending.
  finish();
  const response = await stale;
  expect(response.status).toBe(401);
  expect(response.headers.has('set-cookie')).toBe(false);
});

it('does not join refresh tokens across configured Core origins', async () => {
  let finish!: () => void;
  const pending = new Promise<void>(resolve => { finish = resolve; });
  const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async url => {
    if (String(url).endsWith('/sessions/refresh')) { await pending; return Response.json(session); }
    return Response.json({ ok: true });
  });
  vi.stubEnv('SENTINEL_CORE_URL', 'https://core-a.example');
  const a = proxyAuthenticated(request('origin-token'), '/v1/account');
  vi.stubEnv('SENTINEL_CORE_URL', 'https://core-b.example');
  const b = proxyAuthenticated(request('origin-token'), '/v1/account');
  finish();
  expect((await Promise.all([a, b])).map(r => r.status)).toEqual([200, 200]);
  expect(fetch.mock.calls.filter(([url]) => String(url).endsWith('/sessions/refresh'))).toHaveLength(2);
});
