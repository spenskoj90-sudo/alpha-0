import { afterEach, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { authenticateWeb, proxyAuthenticated, WEB_GENERATION_COOKIE, WEB_SESSION_COOKIE } from './core-session';

const session = { session_token: 'rotated-access', refresh_token: 'rotated-refresh', expires_at: '2030-01-01T00:00:00Z', scopes: ['game:read'] };
const request = (token: string) => new NextRequest('https://app.example/api/account', {
  headers: { cookie: `sentinel_refresh=${token}; ${WEB_SESSION_COOKIE}=family-${'x'.repeat(40)}; ${WEB_GENERATION_COOKIE}=1` },
});
const rotation = () => Response.json(session, { headers: { 'x-sentinel-web-generation': '2' } });
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
      return denied ? Response.json({ error: 'INVALID_REFRESH' }, { status: 401 }) : rotation();
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
    if (String(url).endsWith('/sessions/refresh')) return rotation();
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
    if (String(url).endsWith('/sessions/refresh')) { await pending; return rotation(); }
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

it('suppresses a late successful login response after a newer generation completed', async () => {
  vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  const family = `late-family-${'z'.repeat(40)}`;
  const authRequest = () => new NextRequest('https://app.example/api/session/login', {
    method: 'POST',
    headers: {
      origin: 'https://app.example',
      cookie: `${WEB_SESSION_COOKIE}=${family}; ${WEB_GENERATION_COOKIE}=0`,
    },
    body: '{}',
  });
  let finish!: () => void;
  const pending = new Promise<void>(resolve => { finish = resolve; });
  let calls = 0;
  vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
    calls++;
    if (calls === 1) {
      await pending;
      return Response.json(session, { headers: { 'x-sentinel-web-generation': '1' } });
    }
    return Response.json({ ...session, session_token: 'current-access', refresh_token: 'current-refresh' }, {
      headers: { 'x-sentinel-web-generation': '2' },
    });
  });

  const stale = authenticateWeb(authRequest(), 'login');
  const current = await authenticateWeb(authRequest(), 'login');
  finish();
  const staleResponse = await stale;

  expect(current.status).toBe(200);
  expect(current.headers.get('set-cookie')).toContain('sentinel_refresh=current-refresh');
  expect(staleResponse.status).toBe(409);
  expect(staleResponse.headers.get('set-cookie')).toBeNull();
});
