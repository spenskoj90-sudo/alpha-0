import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from './route';

describe('POST /api/intelligence/recommendations', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  });

  it('requires a same-origin authenticated Web session', async () => {
    const crossSite = await POST(new NextRequest('http://localhost/api/intelligence/recommendations', {
      method: 'POST',
      headers: { origin: 'https://attacker.example' },
    }));
    expect(crossSite.status).toBe(403);

    const signedOut = await POST(new NextRequest('http://localhost/api/intelligence/recommendations', {
      method: 'POST',
      headers: { origin: 'http://localhost' },
    }));
    expect(signedOut.status).toBe(401);
    await expect(signedOut.json()).resolves.toEqual({ error: 'WEB_SESSION_REQUIRED' });
  });

  it('forwards only the bounded command-center context and server-held access token', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      recommendations: [{
        kind: 'recommendation',
        text: 'Insufficient evidence for a specific progression recommendation; review recent character events first.',
        confidence: 0.4,
        provenance: ['knowledge:insufficient-context', 'recommendation:suppressed-low-evidence'],
        provider_id: 'sentinel-core',
        model_id: 'context-baseline-v1',
      }],
    }), { status: 200, headers: { 'content-type': 'application/json' } }));

    const response = await POST(new NextRequest('http://localhost/api/intelligence/recommendations', {
      method: 'POST',
      headers: {
        origin: 'http://localhost',
        cookie: 'sentinel_access=access-secret',
        'x-recommendation-provider': 'browser-provider-must-not-forward',
        'x-request-id': 'web-intelligence-1',
      },
      body: JSON.stringify({ context: { player: { level: 80 } } }),
    }));

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe('https://core.example/v1/recommendations');
    const init = fetchMock.mock.calls[0][1];
    const headers = new Headers(init?.headers);
    expect(headers.get('authorization')).toBe('Bearer access-secret');
    expect(headers.get('x-request-id')).toBe('web-intelligence-1');
    expect(headers.get('x-recommendation-provider')).toBeNull();
    expect(init?.body).toBe(JSON.stringify({
      context: {
        surface: 'web-command-center',
        data_quality: 'UNKNOWN',
        provenance: ['web-command-center:live-request'],
      },
    }));
    expect(response.headers.get('set-cookie') ?? '').not.toContain('access-secret');
  });

  it('preserves one correlation id across access-token refresh and retry', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response('{"code":"INVALID_SESSION"}', { status: 401, headers: { 'content-type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        session_token: 'new-access',
        refresh_token: 'new-refresh',
        expires_at: '2030-01-01T00:00:00Z',
        scopes: ['knowledge:recommend'],
      }), { status: 200, headers: { 'content-type': 'application/json' } }))
      .mockResolvedValueOnce(new Response('{"recommendations":[]}', { status: 200, headers: { 'content-type': 'application/json' } }));

    const response = await POST(new NextRequest('http://localhost/api/intelligence/recommendations', {
      method: 'POST',
      headers: {
        origin: 'http://localhost',
        cookie: 'sentinel_access=expired; sentinel_refresh=refresh-secret',
        'x-request-id': 'web-intelligence-refresh',
      },
    }));

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    for (const call of fetchMock.mock.calls) {
      expect(new Headers(call[1]?.headers).get('x-request-id')).toBe('web-intelligence-refresh');
    }
    expect(new Headers(fetchMock.mock.calls[2][1]?.headers).get('authorization')).toBe('Bearer new-access');
    const setCookie = response.headers.get('set-cookie') ?? '';
    expect(setCookie).toContain('sentinel_access=new-access');
    expect(setCookie).toContain('sentinel_refresh=new-refresh');
  });
});
