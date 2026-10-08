import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from './route';

function invoke(step: string, body: unknown, origin = 'http://localhost') {
  return POST(new NextRequest(`http://localhost/api/session/password-reset/${step}`, {
    method: 'POST', headers: {
      origin,
      'content-type': 'application/json',
      cookie: `sentinel_web_session=recovery-${'r'.repeat(40)}; sentinel_web_generation=1`,
    }, body: JSON.stringify(body),
  }), { params: Promise.resolve({ step }) });
}

describe('Web password recovery boundary', () => {
  beforeEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example'); });

  it('preserves committed reset success when Core cannot publish the family tombstone', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({ status: 'PASSWORD_UPDATED' }, {
      headers: { 'x-sentinel-web-reset-revocation': 'identity' },
    }));
    const response = await invoke('confirm', { token: 'x'.repeat(40), password: 'valid-password-123' });
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ status: 'PASSWORD_UPDATED' });
    expect(response.cookies.get('sentinel_access')?.maxAge).toBe(0);
    expect(response.cookies.get('sentinel_refresh')?.maxAge).toBe(0);
    // No invented generation may replace a concurrently established context.
    expect(response.cookies.get('sentinel_web_session')).toBeUndefined();
    expect(response.cookies.get('sentinel_web_generation')).toBeUndefined();
  });

  it('rejects cross-site writes and unknown steps without forwarding', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch');
    expect((await invoke('request', { email: 'user@example.com' }, 'https://attacker.example')).status).toBe(403);
    expect((await invoke('arbitrary', {})).status).toBe(404);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('accepts only bounded fields and keeps request responses enumeration-safe', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ status: 'ACCEPTED', token: 'must-not-reflect' }), { status: 202 }));
    const response = await invoke('request', { email: 'user@example.com', token: 'ignored' });
    expect(response.status).toBe(202);
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(await response.json()).toEqual({ status: 'ACCEPTED' });
    expect(fetch.mock.calls[0][0]).toBe('https://core.example/v1/auth/password-reset/request');
    expect(JSON.parse(fetch.mock.calls[0][1]!.body as string)).toEqual({ email: 'user@example.com' });
    expect(fetch.mock.calls[0][1]!.headers).not.toHaveProperty('authorization');
    expect((await invoke('confirm', { token: 'x'.repeat(513), password: 'valid-password-123' })).status).toBe(400);
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('clears all local session/challenge cookies only after verified password update', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ status: 'PASSWORD_UPDATED' }), {
      headers: { 'x-sentinel-web-generation': '2' },
    }));
    const response = await invoke('confirm', { token: 'x'.repeat(40), password: 'valid-password-123' });
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ status: 'PASSWORD_UPDATED' });
    for (const name of ['sentinel_access', 'sentinel_refresh', 'sentinel_mfa']) {
      expect(response.cookies.get(name)?.value).toBe('');
      expect(response.cookies.get(name)?.maxAge).toBe(0);
    }
  });

  it('fails closed on malformed success and never echoes provider errors or submitted secrets', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ status: 'ACCEPTED' })));
    const malformed = await invoke('confirm', { token: 'x'.repeat(40), password: 'valid-password-123' });
    expect(malformed.status).toBe(502);
    expect(malformed.headers.get('set-cookie')).toBeNull();
    fetch.mockResolvedValue(new Response(JSON.stringify({ detail: 'secret-token-provider-diagnostic' }), { status: 400 }));
    const invalid = await invoke('confirm', { token: 'x'.repeat(40), password: 'valid-password-123' });
    expect(invalid.status).toBe(400);
    expect(await invalid.json()).toEqual({ error: 'AUTH_ACTION_TOKEN_INVALID' });
    expect(invalid.headers.get('set-cookie')).toBeNull();
    fetch.mockRejectedValue(new Error('provider-secret'));
    const offline = await invoke('request', { email: 'user@example.com' });
    expect(offline.status).toBe(502);
    expect(await offline.json()).toEqual({ error: 'SENTINEL_CORE_UNAVAILABLE' });
  });

  it('handles unavailable configuration, malformed/bounded input, throttling and validation safely', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch');
    vi.stubEnv('SENTINEL_CORE_URL', '');
    expect((await invoke('request', { email: 'user@example.com' })).status).toBe(503);
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    for (const body of [null, { email: 42 }, { email: 'a' }, { email: 'x'.repeat(321) }, { email: 'x'.repeat(2049) }]) {
      expect((await invoke('request', body)).status).toBe(400);
    }
    const malformed = await POST(new NextRequest('http://localhost/api/session/password-reset/request', { method: 'POST', headers: { origin: 'http://localhost' }, body: '{' }), { params: Promise.resolve({ step: 'request' }) });
    expect(malformed.status).toBe(400);
    for (const body of [{ token: 42, password: 'valid-password-123' }, { token: 'x'.repeat(31), password: 'valid-password-123' }, { token: 'x'.repeat(40), password: 42 }, { token: 'x'.repeat(40), password: 'short' }, { token: 'x'.repeat(40), password: 'x'.repeat(257) }]) {
      expect((await invoke('confirm', body)).status).toBe(400);
    }
    expect(fetch).not.toHaveBeenCalled();
    for (const [status, error] of [[429, 'RECOVERY_RATE_LIMITED'], [422, 'RECOVERY_INPUT_INVALID'], [503, 'SENTINEL_CORE_UNAVAILABLE']] as const) {
      fetch.mockResolvedValue(new Response('{}', { status }));
      expect(await (await invoke('request', { email: 'user@example.com' })).json()).toEqual({ error });
    }
    fetch.mockResolvedValue(new Response('not-json', { status: 202 }));
    expect((await invoke('request', { email: 'user@example.com' })).status).toBe(502);
    fetch.mockResolvedValue(new Response('{"status":"ACCEPTED"}', { status: 200 }));
    expect((await invoke('request', { email: 'user@example.com' })).status).toBe(502);
  });
  it('binds short codes to email and forwards normalized whole-code paste without authority extras', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{"status":"PASSWORD_UPDATED"}', {
      headers: { 'x-sentinel-web-generation': '2' },
    }));
    for (const body of [
      { token: '00001234', password: 'valid-password-123' },
      { token: '00001234', email: 'invalid', password: 'valid-password-123' },
      { token: '１２３４５６７８', email: 'user@example.com', password: 'valid-password-123' },
    ]) expect((await invoke('confirm', body)).status).toBe(400);
    expect(fetch).not.toHaveBeenCalled();
    expect((await invoke('confirm', { token: '0000 1234', email: ' User@Example.com ', password: 'valid-password-123', user_id: 'other', scopes: ['admin:*'] })).status).toBe(200);
    expect(JSON.parse(fetch.mock.calls[0][1]!.body as string)).toEqual({ token: '00001234', email: 'user@example.com', password: 'valid-password-123' });
  });

  it('forwards only supported email presentation language', async () => {
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{"status":"ACCEPTED"}', { status: 202 }));
    await POST(new NextRequest('http://localhost/api/session/password-reset/request', {
      method: 'POST', headers: { origin: 'http://localhost', 'content-type': 'application/json', 'accept-language': 'ru-RU,en;q=0.5' }, body: '{"email":"user@example.com"}',
    }), { params: Promise.resolve({ step: 'request' }) });
    expect(new Headers(fetch.mock.calls[0][1]!.headers).get('accept-language')).toBe('ru');
  });

});
