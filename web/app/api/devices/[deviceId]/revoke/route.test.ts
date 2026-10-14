import { createHash } from 'node:crypto';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from './route';
import { ACCESS_COOKIE, WEB_GENERATION_COOKIE, WEB_SESSION_COOKIE } from '../../../_lib/core-session';

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

  it('forwards a confirmed revoke only through the authenticated Core boundary', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const family = 'revoke-' + 'f'.repeat(40);
    const key = createHash('sha256').update(family).digest('hex').slice(0, 16);
    const cookie = [
      `${WEB_SESSION_COOKIE}=${family}`,
      `${WEB_GENERATION_COOKIE}_${key}_1=1`,
      `${ACCESS_COOKIE}_${key}_1=bound-owner-access`,
    ].join('; ');
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({ revoked: true }));

    const response = await post(req('https://app.example', cookie), id.toUpperCase());

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ revoked: true });
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(String(fetch.mock.calls[0][0])).toBe('https://core.example/v1/devices/' + id + '/revoke');
    const init = fetch.mock.calls[0][1] as RequestInit;
    const headers = new Headers(init.headers);
    expect(init.method).toBe('POST');
    expect(init.body).toBeUndefined();
    expect(headers.get('authorization')).toBe('Bearer bound-owner-access');
    expect(headers.get('cookie')).toBeNull();
  });
});
