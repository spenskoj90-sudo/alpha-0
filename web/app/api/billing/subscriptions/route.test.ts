import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { GET, POST } from './route';

describe('/api/billing/subscriptions', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  });

  it('requires a Web session', async () => {
    const response = await GET(new NextRequest('http://localhost/api/billing/subscriptions'));
    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ error: 'WEB_SESSION_REQUIRED' });
  });

  it('forwards the opaque access token only to Core', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{"subscriptions":[]}', {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }));
    const response = await GET(new NextRequest('http://localhost/api/billing/subscriptions', {
      headers: { cookie: 'sentinel_access=access-secret' },
    }));
    expect(response.status).toBe(200);
    expect(await response.text()).toBe('{"subscriptions":[]}');
    const [, init] = fetchMock.mock.calls[0];
    expect(new Headers(init?.headers).get('authorization')).toBe('Bearer access-secret');
    expect(response.headers.get('set-cookie') ?? '').not.toContain('access-secret');
  });

  it('rotates an expired access token once and retries with the refreshed session', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response('{"code":"INVALID_SESSION"}', { status: 401, headers: { 'content-type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        session_token: 'new-access',
        refresh_token: 'new-refresh',
        expires_at: '2030-01-01T00:00:00Z',
        scopes: ['game:read'],
      }), { status: 200, headers: { 'content-type': 'application/json' } }))
      .mockResolvedValueOnce(new Response('{"subscriptions":[{"id":"s1"}]}', { status: 200, headers: { 'content-type': 'application/json' } }));

    const response = await GET(new NextRequest('http://localhost/api/billing/subscriptions', {
      headers: { cookie: 'sentinel_access=expired; sentinel_refresh=refresh-secret' },
    }));

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    const refreshCall = fetchMock.mock.calls[1];
    expect(refreshCall[0]).toBe('https://core.example/v1/sessions/refresh');
    expect(refreshCall[1]?.body).toBe(JSON.stringify({ refresh_token: 'refresh-secret' }));
    const retryHeaders = new Headers(fetchMock.mock.calls[2][1]?.headers);
    expect(retryHeaders.get('authorization')).toBe('Bearer new-access');
    const setCookie = response.headers.get('set-cookie') ?? '';
    expect(setCookie).toContain('sentinel_access=new-access');
    expect(setCookie).toContain('sentinel_refresh=new-refresh');
  });

  it('denies cross-site subscription writes and forces the browser provider boundary to manual', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch');
    const denied = await POST(new NextRequest('http://localhost/api/billing/subscriptions', {
      method: 'POST',
      headers: { origin: 'https://attacker.example', 'content-type': 'application/json', cookie: 'sentinel_access=access-secret' },
      body: JSON.stringify({ plan_code: 'core-plus' }),
    }));
    expect(denied.status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();

    fetchMock.mockResolvedValue(new Response('{"id":"s1","status":"PENDING"}', { status: 200, headers: { 'content-type': 'application/json' } }));
    const accepted = await POST(new NextRequest('http://localhost/api/billing/subscriptions', {
      method: 'POST',
      headers: { origin: 'http://localhost', 'content-type': 'application/json', cookie: 'sentinel_access=access-secret' },
      body: JSON.stringify({ plan_code: 'core-plus', provider: 'spoofed-provider' }),
    }));
    expect(accepted.status).toBe(200);
    const [, init] = fetchMock.mock.calls[0];
    expect(init?.body).toBe(JSON.stringify({ plan_code: 'core-plus', provider: 'manual' }));
  });
});
