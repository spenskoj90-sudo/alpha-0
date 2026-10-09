import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from './route';

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); });
const id = 'd6d38c4b-9aea-4b41-bb72-75eb7caaf610';
const req = (origin: string, cookie = '') => new NextRequest('https://app.example/api/devices/' + id + '/revoke', {
  method: 'POST', headers: { origin, cookie },
});
const post = (request: NextRequest, deviceId: string) =>
  POST(request, { params: Promise.resolve({ deviceId }) });

describe('owned device revocation route', () => {
  it('rejects cross-origin writes before session and Core lookup', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch');
    expect((await post(req('https://external.example'), id)).status).toBe(403);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('rejects path traversal/invalid device identifiers before network', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch');
    for (const bad of ['', '../sessions', 'not-a-uuid', id + '/rotate']) {
      const response = await post(req('https://app.example'), bad);
      expect(response.status).toBe(400);
    }
    expect(fetch).not.toHaveBeenCalled();
  });

  it('requires authenticated SENTINEL session, never a caller supplied user-id', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetch = vi.spyOn(globalThis, 'fetch');
    const result = await post(req('https://app.example'), id);
    expect(result.status).toBe(401);
    expect(fetch).not.toHaveBeenCalled();
  });
});
