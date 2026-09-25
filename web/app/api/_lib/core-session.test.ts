import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest, NextResponse } from 'next/server';

import {
  ACCESS_COOKIE,
  MFA_COOKIE,
  REFRESH_COOKIE,
  applySessionCookies,
  authenticateWeb,
  clearMfaCookie,
  clearSessionCookies,
  completeMfaWeb,
  logoutWeb,
  proxyAuthenticated,
  sameOriginWrite,
} from './core-session';

const SESSION = {
  session_token: 'new-access',
  refresh_token: 'new-refresh',
  expires_at: '2030-01-01T00:00:00Z',
  scopes: ['game:read'],
};

function writeRequest(
  url: string,
  body = '{}',
  headers: Record<string, string> = {},
): NextRequest {
  return new NextRequest(url, {
    method: 'POST',
    headers: {
      origin: new URL(url).origin,
      'content-type': 'application/json',
      ...headers,
    },
    body,
  });
}

describe('Web Core session boundary', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it('enforces explicit same-origin writes including configured public origin', () => {
    vi.stubEnv('SENTINEL_WEB_ORIGIN', 'https://app.example/');
    expect(sameOriginWrite(new NextRequest('http://internal/api', {
      headers: { origin: 'https://app.example' },
    }))).toBe(true);
    expect(sameOriginWrite(new NextRequest('http://internal/api', {
      headers: { origin: 'https://attacker.example' },
    }))).toBe(false);
    expect(sameOriginWrite(new NextRequest('http://internal/api'))).toBe(false);
  });

  it('applies and clears bounded HttpOnly session/MFA cookies', () => {
    vi.stubEnv('SENTINEL_WEB_REFRESH_MAX_AGE_SECONDS', '45');
    const response = NextResponse.json({ ok: true });
    applySessionCookies(response, { ...SESSION, expires_at: 'not-a-date' });
    clearMfaCookie(response);
    const cookie = response.headers.get('set-cookie') ?? '';
    expect(cookie).toContain(`${ACCESS_COOKIE}=new-access`);
    expect(cookie).toContain(`${REFRESH_COOKIE}=new-refresh`);
    expect(cookie).toContain('Max-Age=45');
    expect(cookie).toContain(`${MFA_COOKIE}=`);
    expect(cookie.toLowerCase()).toContain('httponly');
    expect(cookie.toLowerCase()).toContain('samesite=strict');

    const cleared = NextResponse.json({ ok: true });
    clearSessionCookies(cleared);
    const clearedCookie = cleared.headers.get('set-cookie') ?? '';
    expect(clearedCookie).toContain(`${ACCESS_COOKIE}=`);
    expect(clearedCookie).toContain(`${REFRESH_COOKIE}=`);
    expect(clearedCookie).toContain('Max-Age=0');
  });

  it('copies bounded upstream failures and trusted correlation without exposing MFA state', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example/');
    const trace = 'a'.repeat(32);
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('rate-limited', {
      status: 429,
      headers: {
        'content-type': 'text/plain',
        'x-request-id': 'upstream-request',
        'x-sentinel-trace-id': trace,
      },
    }));

    const response = await authenticateWeb(writeRequest(
      'http://localhost/api/session/login',
      JSON.stringify({ email: 'u@example.com', password: 'secret' }),
      { 'x-request-id': 'browser-request' },
    ), 'login');

    expect(response.status).toBe(429);
    expect(await response.text()).toBe('rate-limited');
    expect(response.headers.get('x-request-id')).toBe('upstream-request');
    expect(response.headers.get('x-sentinel-trace-id')).toBe(trace);
    expect(response.headers.get('set-cookie') ?? '').toContain(`${MFA_COOKIE}=`);
  });

  it('fails closed on invalid Core URL, malformed session payload and network failure', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'not a url');
    const invalidConfig = await authenticateWeb(writeRequest('http://localhost/api/session/login'), 'login');
    expect(invalidConfig.status).toBe(503);

    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(new Response('{}', {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }));
    const malformed = await authenticateWeb(writeRequest('http://localhost/api/session/login'), 'login');
    expect(malformed.status).toBe(502);
    await expect(malformed.json()).resolves.toEqual({ error: 'INVALID_CORE_SESSION_RESPONSE' });

    vi.restoreAllMocks();
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network down'));
    const unavailable = await authenticateWeb(writeRequest('http://localhost/api/session/login'), 'login');
    expect(unavailable.status).toBe(502);
    await expect(unavailable.json()).resolves.toEqual({ error: 'SENTINEL_CORE_UNAVAILABLE' });
  });

  it('validates MFA configuration, challenge and code before Core', async () => {
    const challenge = 'mfa-' + 'x'.repeat(44);
    vi.stubEnv('SENTINEL_CORE_URL', '');
    const noCore = await completeMfaWeb(writeRequest(
      'http://localhost/api/session/mfa',
      JSON.stringify({ code: '123456' }),
      { cookie: `${MFA_COOKIE}=${challenge}` },
    ));
    expect(noCore.status).toBe(503);

    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch');
    const badJson = await completeMfaWeb(writeRequest(
      'http://localhost/api/session/mfa',
      '{',
      { cookie: `${MFA_COOKIE}=${challenge}` },
    ));
    expect(badJson.status).toBe(400);
    const tooLong = await completeMfaWeb(writeRequest(
      'http://localhost/api/session/mfa',
      JSON.stringify({ code: 'x'.repeat(65) }),
      { cookie: `${MFA_COOKIE}=${challenge}` },
    ));
    expect(tooLong.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('copies rejected MFA completion and fails closed on malformed success', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const challenge = 'mfa-' + 'x'.repeat(44);
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response('{"error":"MFA_INVALID"}', {
        status: 401,
        headers: { 'content-type': 'application/json' },
      }))
      .mockResolvedValueOnce(new Response('{}', {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }));

    const rejected = await completeMfaWeb(writeRequest(
      'http://localhost/api/session/mfa',
      JSON.stringify({ code: '123456' }),
      { cookie: `${MFA_COOKIE}=${challenge}` },
    ));
    expect(rejected.status).toBe(401);

    const malformed = await completeMfaWeb(writeRequest(
      'http://localhost/api/session/mfa',
      JSON.stringify({ code: '654321' }),
      { cookie: `${MFA_COOKIE}=${challenge}` },
    ));
    expect(malformed.status).toBe(502);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('maps MFA network failure to a bounded unavailable response', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const challenge = 'mfa-' + 'x'.repeat(44);
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network down'));
    const response = await completeMfaWeb(writeRequest(
      'http://localhost/api/session/mfa',
      JSON.stringify({ code: '123456' }),
      { cookie: `${MFA_COOKIE}=${challenge}` },
    ));
    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toEqual({ error: 'SENTINEL_CORE_UNAVAILABLE' });
  });

  it('refreshes a missing access token once and persists the rotated session', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify(SESSION), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }))
      .mockResolvedValueOnce(new Response('{"ok":true}', {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }));

    const response = await proxyAuthenticated(new NextRequest('http://localhost/api/resource', {
      headers: { cookie: `${REFRESH_COOKIE}=old-refresh` },
    }), '/v1/resource');

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0]?.[0]).toBe('https://core.example/v1/sessions/refresh');
    expect(new Headers(fetchMock.mock.calls[1]?.[1]?.headers).get('authorization')).toBe('Bearer new-access');
    const cookie = response.headers.get('set-cookie') ?? '';
    expect(cookie).toContain(`${ACCESS_COOKIE}=new-access`);
    expect(cookie).toContain(`${REFRESH_COOKIE}=new-refresh`);
  });

  it('clears stale refresh state when refresh cannot establish a session', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{"error":"INVALID_REFRESH"}', {
      status: 401,
      headers: { 'content-type': 'application/json' },
    }));
    const response = await proxyAuthenticated(new NextRequest('http://localhost/api/resource', {
      headers: { cookie: `${REFRESH_COOKIE}=bad-refresh` },
    }), '/v1/resource');
    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ error: 'WEB_SESSION_REQUIRED' });
    const cookie = response.headers.get('set-cookie') ?? '';
    expect(cookie).toContain(`${ACCESS_COOKIE}=`);
    expect(cookie).toContain(`${REFRESH_COOKIE}=`);
  });

  it('retries one 401 with refresh and clears cookies when rotation fails', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response('{"error":"INVALID_SESSION"}', {
        status: 401,
        headers: { 'content-type': 'application/json' },
      }))
      .mockResolvedValueOnce(new Response('{"error":"INVALID_REFRESH"}', {
        status: 401,
        headers: { 'content-type': 'application/json' },
      }));

    const response = await proxyAuthenticated(new NextRequest('http://localhost/api/resource', {
      headers: { cookie: `${ACCESS_COOKIE}=expired; ${REFRESH_COOKIE}=bad-refresh` },
    }), '/v1/resource');

    expect(response.status).toBe(401);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(response.headers.get('set-cookie') ?? '').toContain('Max-Age=0');
  });

  it('enforces same-origin proxy writes and handles missing/unavailable Core', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const denied = await proxyAuthenticated(new NextRequest('http://localhost/api/resource', {
      method: 'POST',
      headers: {
        origin: 'https://attacker.example',
        cookie: `${ACCESS_COOKIE}=access`,
      },
    }), '/v1/resource', { method: 'POST' }, true);
    expect(denied.status).toBe(403);

    vi.stubEnv('SENTINEL_CORE_URL', '');
    const unconfigured = await proxyAuthenticated(new NextRequest('http://localhost/api/resource', {
      headers: { cookie: `${ACCESS_COOKIE}=access` },
    }), '/v1/resource');
    expect(unconfigured.status).toBe(503);

    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network down'));
    const unavailable = await proxyAuthenticated(new NextRequest('http://localhost/api/resource', {
      headers: { cookie: `${ACCESS_COOKIE}=access` },
    }), '/v1/resource');
    expect(unavailable.status).toBe(502);
  });

  it('revokes server session on logout and always clears browser credentials', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 204 }));
    const response = await logoutWeb(writeRequest(
      'http://localhost/api/session/logout',
      '{}',
      { cookie: `${ACCESS_COOKIE}=access-secret; ${REFRESH_COOKIE}=refresh-secret; ${MFA_COOKIE}=challenge` },
    ));
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ authenticated: false, server_revoked: true });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const cookie = response.headers.get('set-cookie') ?? '';
    expect(cookie).toContain(`${ACCESS_COOKIE}=`);
    expect(cookie).toContain(`${REFRESH_COOKIE}=`);
    expect(cookie).toContain(`${MFA_COOKIE}=`);
  });

  it('keeps logout local and fail-closed when revoke is unavailable', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network down'));
    const failedRevoke = await logoutWeb(writeRequest(
      'http://localhost/api/session/logout',
      '{}',
      { cookie: `${ACCESS_COOKIE}=access-secret` },
    ));
    await expect(failedRevoke.json()).resolves.toEqual({ authenticated: false, server_revoked: false });

    vi.restoreAllMocks();
    const noSessionFetch = vi.spyOn(globalThis, 'fetch');
    const localOnly = await logoutWeb(writeRequest('http://localhost/api/session/logout'));
    await expect(localOnly.json()).resolves.toEqual({ authenticated: false, server_revoked: false });
    expect(noSessionFetch).not.toHaveBeenCalled();
  });

  it('denies cross-site logout before touching browser or Core state', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch');
    const response = await logoutWeb(new NextRequest('http://localhost/api/session/logout', {
      method: 'POST',
      headers: { origin: 'https://attacker.example', cookie: `${ACCESS_COOKIE}=access` },
    }));
    expect(response.status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
