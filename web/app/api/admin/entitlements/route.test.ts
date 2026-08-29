import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from './route';

describe('POST /api/admin/entitlements', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it('denies requests without the admin token', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');

    const response = await POST(new NextRequest('http://localhost/api/admin/entitlements', {
      method: 'POST',
      body: JSON.stringify({ user_id: 'user-1' }),
      headers: { 'content-type': 'application/json' },
    }));

    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toEqual({ error: 'ADMIN_ACCESS_DENIED' });
  });

  it('fails closed when the upstream is not configured', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', '');

    const response = await POST(new NextRequest('http://localhost/api/admin/entitlements', {
      method: 'POST',
      body: JSON.stringify({ user_id: 'user-1' }),
      headers: { 'content-type': 'application/json', 'x-sentinel-admin-token': 'test-token' },
    }));

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({ error: 'SENTINEL_CORE_URL_NOT_CONFIGURED' });
  });

  it('forwards an authorized request without exposing the token in the response', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{"ok":true}', {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }));

    const response = await POST(new NextRequest('http://localhost/api/admin/entitlements', {
      method: 'POST',
      body: JSON.stringify({ user_id: 'user-1', product_id: 'wow-1' }),
      headers: { 'content-type': 'application/json', 'x-sentinel-admin-token': 'test-token' },
    }));

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ ok: true });
    expect(await response.text()).not.toContain('test-token');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('https://core.example/v1/admin/entitlements');
    expect(init).toMatchObject({
      method: 'POST',
      cache: 'no-store',
      headers: {
        'content-type': 'application/json',
        'x-sentinel-admin-token': 'test-token',
      },
    });
    expect(init?.body).toBe(JSON.stringify({ user_id: 'user-1', product_id: 'wow-1' }));
  });
});
