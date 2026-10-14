import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from './route';

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); });

function req(step: string, body: unknown, origin = 'https://app.example') {
  return new NextRequest('https://app.example/api/session/email-verification/' + step, {
    method: 'POST',
    headers: { origin, 'content-type': 'application/json', 'accept-language': 'ru' },
    body: JSON.stringify(body),
  });
}
const post = (step: string, body: unknown, origin?: string) =>
  POST(req(step, body, origin), { params: Promise.resolve({ step }) });

describe('email verification route boundaries', () => {
  it('rejects cross-origin, unknown routes, and invalid codes without upstream traffic', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetch = vi.spyOn(globalThis, 'fetch');
    expect((await post('request', { email: 'u@example.com' }, 'https://attacker.example')).status).toBe(403);
    expect((await post('wrong', { email: 'u@example.com' })).status).toBe(404);
    for (const token of ['1234567', '123456789', 'invalid', '']) {
      expect((await post('confirm', { email: 'u@example.com', token })).status).toBe(400);
    }
    expect(fetch).not.toHaveBeenCalled();
  });

  it('uses non-enumerating public Core request without passing cookies or arbitrary fields', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({ status: 'ACCEPTED' }, { status: 202 }));
    const response = await post('request', { email: 'USER@EXAMPLE.COM', access_token: 'forged' });
    expect(response.status).toBe(202);
    expect(response.headers.get('set-cookie')).toBeNull();
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(String(fetch.mock.calls[0][0])).toBe('https://core.example/v1/auth/email-verification/request');
    expect(JSON.parse(fetch.mock.calls[0][1]?.body as string)).toEqual({ email: 'user@example.com' });
    const headers = new Headers(fetch.mock.calls[0][1]?.headers);
    expect(headers.get('authorization')).toBeNull();
    expect(headers.get('cookie')).toBeNull();
    expect(headers.get('accept-language')).toBe('ru');
  });

  it('confirms leading-zero numeric code bound to email without issuing session cookies', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({ status: 'VERIFIED' }));
    const response = await post('confirm', { email: 'u@example.com', token: '0012 3456' });
    expect(response.status).toBe(200);
    expect(response.headers.get('set-cookie')).toBeNull();
    expect(String(fetch.mock.calls[0][0])).toBe('https://core.example/v1/auth/email-verification/confirm');
    expect(JSON.parse(fetch.mock.calls[0][1]?.body as string)).toEqual({ email: 'u@example.com', token: '00123456' });
  });

  it('does not report success for Core errors, malformed success or lost connection', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(Response.json({}, { status: 429 }))
      .mockResolvedValueOnce(Response.json({ status: 'ACCEPTED' }))
      .mockRejectedValueOnce(new Error('network down'));
    expect((await post('confirm', { email: 'u@example.com', token: '12345678' })).status).toBe(429);
    expect((await post('confirm', { email: 'u@example.com', token: '12345678' })).status).toBe(502);
    expect((await post('confirm', { email: 'u@example.com', token: '12345678' })).status).toBe(502);
  });
});
