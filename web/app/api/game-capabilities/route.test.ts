import { afterEach, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { GET } from './route';

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); });

it('requires a server-held session to read the research inventory', async () => {
  vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  const response = await GET(new NextRequest('http://localhost/api/game-capabilities'));
  expect(response.status).toBe(401);
  expect(response.headers.get('set-cookie')).toBeNull();
});

it('reads Core inventory without expanding authority or forwarding browser credentials', async () => {
  vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{"schema_version":1,"profiles":[]}'));
  const response = await GET(new NextRequest('http://localhost/api/game-capabilities', {
    headers: { cookie: 'sentinel_access=fixture', 'x-sentinel-admin-token': 'must-not-forward' },
  }));
  expect(response.status).toBe(200);
  expect(await response.json()).toEqual({ schema_version: 1, profiles: [] });
  expect(fetchMock.mock.calls[0][0]).toBe('https://core.example/v1/game-capabilities');
  expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get('x-sentinel-admin-token')).toBeNull();
  expect(response.headers.get('set-cookie')).toBeNull();
});
