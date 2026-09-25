import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

import { GET } from './route';

const ADMIN_HEADERS = {
  'x-sentinel-admin-token': 'admin-token',
  'x-sentinel-admin-totp': '123456',
};

describe('/api/admin/games', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it('fails closed without a valid upstream configuration', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'not a url');
    const response = await GET(new NextRequest('http://localhost/api/admin/games', {
      headers: ADMIN_HEADERS,
    }));
    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({ error: 'SENTINEL_CORE_URL_NOT_CONFIGURED' });
  });

  it('requires both admin authentication factors', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch');
    const response = await GET(new NextRequest('http://localhost/api/admin/games'));
    expect(response.status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('forwards an authorized read with no-store semantics', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example/');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{"games":[]}', {
      status: 200,
    }));
    const response = await GET(new NextRequest('http://localhost/api/admin/games', {
      headers: ADMIN_HEADERS,
    }));
    expect(response.status).toBe(200);
    expect(await response.text()).toBe('{"games":[]}');
    expect(response.headers.get('content-type')).toBe('application/json');
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('https://core.example/v1/admin/games');
    expect(init?.cache).toBe('no-store');
    const headers = new Headers(init?.headers);
    expect(headers.get('x-sentinel-admin-token')).toBe('admin-token');
    expect(headers.get('x-sentinel-admin-totp')).toBe('123456');
  });

  it('maps upstream transport failure to a bounded 502', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network down'));
    const response = await GET(new NextRequest('http://localhost/api/admin/games', {
      headers: ADMIN_HEADERS,
    }));
    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toEqual({ error: 'SENTINEL_CORE_UNAVAILABLE' });
  });
});
