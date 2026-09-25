import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { GET, POST } from './route';

describe('/api/admin/entitlements', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it('denies reads and writes without both admin factors', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const read = await GET(new NextRequest('http://localhost/api/admin/entitlements'));
    expect(read.status).toBe(403);
    const write = await POST(new NextRequest('http://localhost/api/admin/entitlements', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: '{}',
    }));
    expect(write.status).toBe(403);
  });

  it('fails closed when the upstream is not configured', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', '');
    const response = await GET(new NextRequest('http://localhost/api/admin/entitlements', {
      headers: { 'x-sentinel-admin-token': 'test-token', 'x-sentinel-admin-totp': '123456' },
    }));
    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({ error: 'SENTINEL_CORE_URL_NOT_CONFIGURED' });
  });

  it('forwards admin readback without exposing the token in the response', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{"entitlements":[]}', {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }));
    const response = await GET(new NextRequest('http://localhost/api/admin/entitlements', {
      headers: { 'x-sentinel-admin-token': 'test-token', 'x-sentinel-admin-totp': '123456' },
    }));
    expect(response.status).toBe(200);
    expect(await response.text()).toBe('{"entitlements":[]}');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('https://core.example/v1/admin/entitlements');
    expect(new Headers(init?.headers).get('x-sentinel-admin-token')).toBe('test-token');
    expect(new Headers(init?.headers).get('x-sentinel-admin-totp')).toBe('123456');
    expect(response.headers.get('set-cookie') ?? '').not.toContain('test-token');
    expect(response.headers.get('set-cookie') ?? '').not.toContain('123456');
  });

  it('forwards authorized grants and preserves the request body', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{"ok":true}', {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }));
    const body = JSON.stringify({ user_id: 'user-1', game_id: 'diablo-4-pc' });
    const response = await POST(new NextRequest('http://localhost/api/admin/entitlements', {
      method: 'POST',
      body,
      headers: { 'content-type': 'application/json', 'x-sentinel-admin-token': 'test-token', 'x-sentinel-admin-totp': '123456' },
    }));
    expect(response.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('https://core.example/v1/admin/entitlements');
    expect(init?.method).toBe('POST');
    expect(init?.body).toBe(body);
    expect(new Headers(init?.headers).get('x-sentinel-admin-token')).toBe('test-token');
    expect(new Headers(init?.headers).get('x-sentinel-admin-totp')).toBe('123456');
  });
  it('fails closed on malformed Core URL and transport failure', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'not a url');
    const invalid = await GET(new NextRequest('http://localhost/api/admin/entitlements', {
      headers: { 'x-sentinel-admin-token': 'test-token', 'x-sentinel-admin-totp': '123456' },
    }));
    expect(invalid.status).toBe(503);

    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example/');
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network down'));
    const unavailable = await GET(new NextRequest('http://localhost/api/admin/entitlements', {
      headers: { 'x-sentinel-admin-token': 'test-token', 'x-sentinel-admin-totp': '123456' },
    }));
    expect(unavailable.status).toBe(502);
    await expect(unavailable.json()).resolves.toEqual({ error: 'SENTINEL_CORE_UNAVAILABLE' });
  });

  it('uses a safe content-type fallback for upstream responses', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('ok', { status: 200 }));
    const response = await GET(new NextRequest('http://localhost/api/admin/entitlements', {
      headers: { 'x-sentinel-admin-token': 'test-token', 'x-sentinel-admin-totp': '123456' },
    }));
    expect(response.status).toBe(200);
    expect(response.headers.get('content-type')).toBe('application/json');
  });

});
