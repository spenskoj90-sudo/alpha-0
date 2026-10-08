import { createHash } from 'node:crypto';
import { afterEach, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { authenticateWeb, logoutWeb, proxyAuthenticated } from './core-session';

const family = `legacy-bootstrap-${'x'.repeat(40)}`;
const key = createHash('sha256').update(family).digest('hex').slice(0, 16);
const bootstrap = `sentinel_web_session_${key}=${family}`;
const request = (path: string, cookie = bootstrap) => new NextRequest(`https://app.example/api/${path}`, {
  method: 'POST', headers: { origin: 'https://app.example', cookie: `sentinel_refresh=legacy-root; ${cookie}` }, body: '{}',
});
const session = { session_token: 'new-access', refresh_token: 'new-refresh', expires_at: '2030-01-01T00:00:00Z', scopes: ['game:read'] };
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); });

it('uses legacy access only to revoke an expired refresh lineage, never to authorize a read', async () => {
  vi.stubEnv('SENTINEL_CORE_URL', 'https://stale-legacy.core.example');
  const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_url, init) => {
    const authorization = new Headers(init?.headers).get('authorization');
    return authorization === 'Bearer legacy-access'
      ? Response.json({ revoked: true }, { headers: { 'x-sentinel-web-generation': '1' } })
      : Response.json({ code: 'WEB_SESSION_SUPERSEDED' }, { status: 409 });
  });
  const response = await logoutWeb(request('session/logout', `${bootstrap}; sentinel_access=legacy-access`));
  expect(response.status).toBe(200);
  expect(await response.json()).toEqual({ authenticated: false, server_revoked: true });
  expect(response.cookies.get('sentinel_access')?.maxAge).toBe(0);
  expect(response.cookies.get('sentinel_refresh')?.maxAge).toBe(0);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('presents the pre-family refresh proof on the logout retry after bootstrap', async () => {
  vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({ revoked: true }, { headers: { 'x-sentinel-web-generation': '1' } }));
  const response = await logoutWeb(request('session/logout'));
  expect(response.status).toBe(200);
  expect(JSON.parse(fetch.mock.calls[0][1]?.body as string)).toEqual({ refresh_token: 'legacy-root' });
  expect(response.cookies.get('sentinel_refresh')?.maxAge).toBe(0);
});

it.each(['login', 'register'] as const)('retires the legacy lineage before %s can issue replacement credentials', async mode => {
  const core = `https://${mode}.core.example`;
  vi.stubEnv('SENTINEL_CORE_URL', core);
  const fetch = vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(Response.json({ revoked: true }, { headers: { 'x-sentinel-web-generation': '1' } }))
    .mockResolvedValueOnce(Response.json(session, { headers: { 'x-sentinel-web-generation': '2' } }));
  const response = await authenticateWeb(request(`session/${mode}`), mode);
  expect(response.status).toBe(200);
  expect(fetch.mock.calls.map(([url]) => String(url))).toEqual([`${core}/v1/sessions/web/revoke`, `${core}/v1/auth/${mode}`]);
  expect(JSON.parse(fetch.mock.calls[0][1]?.body as string)).toEqual({ refresh_token: 'legacy-root' });
  expect(new Headers(fetch.mock.calls[0][1]?.headers).get('x-sentinel-web-session')).toBe(family);
  expect(new Headers(fetch.mock.calls[1][1]?.headers).get('x-sentinel-web-session')).toBe(family);
  expect(new Headers(fetch.mock.calls[1][1]?.headers).get('x-sentinel-web-expected-generation')).toBe('1');
  expect(response.cookies.get('sentinel_refresh')?.maxAge).toBe(0);
  expect(response.cookies.get('sentinel_access')?.maxAge).toBe(0);
  expect(response.cookies.get(`sentinel_refresh_${key}_2`)?.value).toBe('new-refresh');
});

it.each([409, 429, 500, 'missing-generation', 'network'] as const)('does not authenticate when legacy retirement fails (%s)', async failure => {
  vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  const fetch = vi.spyOn(globalThis, 'fetch');
  if (failure === 'network') fetch.mockRejectedValue(new Error('offline'));
  else fetch.mockResolvedValue(Response.json({ revoked: true }, { status: typeof failure === 'number' ? failure : 200 }));
  const response = await authenticateWeb(request('session/login'), 'login');
  expect(response.status).toBe(failure === 409 ? 409 : 502);
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(String(fetch.mock.calls[0][0])).toContain('/sessions/web/revoke');
  expect(response.cookies.get(`sentinel_refresh_${key}_1`)).toBeUndefined();
  // An invalid/consumed proof can be retried without trapping the browser on it.
  expect(response.cookies.get('sentinel_refresh')?.maxAge).toBe(failure === 409 ? 0 : undefined);
});

it.each([401, 429, 500, 'network'] as const)('clears consumed legacy proof even when subsequent auth fails (%s)', async failure => {
  vi.stubEnv('SENTINEL_CORE_URL', `https://auth-failure-${failure}.core.example`);
  const fetch = vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(Response.json({ revoked: true }, { headers: { 'x-sentinel-web-generation': '1' } }));
  if (failure === 'network') fetch.mockRejectedValueOnce(Error('offline'));
  else fetch.mockResolvedValueOnce(Response.json({ code: 'INVALID_CREDENTIALS' }, { status: failure }));
  const response = await authenticateWeb(request('session/login'), 'login');
  expect(response.status).toBe(failure === 'network' ? 502 : failure);
  expect(response.cookies.get('sentinel_refresh')?.maxAge).toBe(0);
  expect(response.cookies.get('sentinel_access')?.maxAge).toBe(0);
});

it('never falls back to a legacy refresh proof after a positive versioned generation', async () => {
  vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({ revoked: true }, { headers: { 'x-sentinel-web-generation': '3' } }));
  const response = await logoutWeb(request('session/logout', `sentinel_web_session=${family}; sentinel_web_generation_${key}_2=1`));
  expect(response.status).toBe(200);
  expect(fetch.mock.calls[0][1]?.body).toBeUndefined();
});

it.each(['login', 'register'] as const)('keeps logout authoritative while a migrated %s body is delayed', async mode => {
  vi.stubEnv('SENTINEL_CORE_URL', `https://gap-${mode}.core.example`);
  let generation = 0;
  let release!: (body: string) => void;
  let retired!: () => void;
  const retirement = new Promise<void>(resolve => { retired = resolve; });
  const body = new Promise<string>(resolve => { release = resolve; });
  const login = request(`session/${mode}`);
  vi.spyOn(login, 'text').mockImplementation(async () => { retired(); return body; });
  const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, init) => {
    if (String(url).endsWith('/sessions/web/revoke')) {
      return Response.json({ revoked: true }, { headers: { 'x-sentinel-web-generation': String(++generation) } });
    }
    const expected = Number(new Headers(init?.headers).get('x-sentinel-web-expected-generation'));
    expect(expected).toBe(1);
    if (expected !== generation) return Response.json({ code: 'WEB_SESSION_SUPERSEDED' }, { status: 409 });
    throw new Error('logout must prevent identity mutation');
  });
  const pending = authenticateWeb(login, mode);
  await retirement;
  const logout = await logoutWeb(request('session/logout'));
  expect(logout.status).toBe(200);
  release('{"email":"u@example.com","password":"safe-password-123"}');
  const response = await pending;
  expect(response.status).toBe(409);
  expect(fetch).toHaveBeenCalledTimes(3);
  expect(response.cookies.getAll().some(cookie => cookie.value === 'new-refresh')).toBe(false);
});

it('never turns a legacy access cookie into ongoing bootstrap authority', async () => {
  vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({ code: 'INVALID_REFRESH' }, { status: 401 }));
  const response = await proxyAuthenticated(new NextRequest('https://app.example/api/account', {
    headers: { cookie: `${bootstrap}; sentinel_access=legacy-access; sentinel_refresh=legacy-root` },
  }), '/v1/account');
  expect(response.status).toBe(401);
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(String(fetch.mock.calls[0][0])).toContain('/sessions/refresh');
});
