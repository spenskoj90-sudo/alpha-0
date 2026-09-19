import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from './route';

describe('POST /api/session/mfa', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it('exchanges the HttpOnly MFA challenge for session cookies without exposing it to JavaScript', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const challenge = 'mfa-' + 'x'.repeat(44);
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      session_token: 'access-secret',
      refresh_token: 'refresh-secret',
      expires_at: '2030-01-01T00:00:00Z',
      scopes: ['game:read'],
    }), { status: 200, headers: { 'content-type': 'application/json' } }));

    const response = await POST(new NextRequest('http://localhost/api/session/mfa', {
      method: 'POST',
      headers: {
        origin: 'http://localhost',
        'content-type': 'application/json',
        cookie: `sentinel_mfa=${challenge}`,
      },
      body: JSON.stringify({ code: '123456' }),
    }));

    expect(response.status).toBe(200);
    const body = await response.text();
    expect(body).toContain('"authenticated":true');
    expect(body).not.toContain('access-secret');
    expect(body).not.toContain('refresh-secret');
    expect(body).not.toContain(challenge);
    const cookie = response.headers.get('set-cookie') ?? '';
    expect(cookie).toContain('sentinel_access=access-secret');
    expect(cookie).toContain('sentinel_mfa=');
    expect(cookie.toLowerCase()).toContain('httponly');
    const upstreamBody = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body ?? '{}'));
    expect(upstreamBody).toEqual({ challenge_token: challenge, code: '123456' });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('fails closed when the browser has no MFA challenge cookie', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch');
    const response = await POST(new NextRequest('http://localhost/api/session/mfa', {
      method: 'POST',
      headers: { origin: 'http://localhost', 'content-type': 'application/json' },
      body: JSON.stringify({ code: '123456' }),
    }));
    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ error: 'WEB_MFA_CHALLENGE_REQUIRED' });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('rejects cross-site MFA completion before calling Core', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch');
    const response = await POST(new NextRequest('http://localhost/api/session/mfa', {
      method: 'POST',
      headers: { origin: 'https://attacker.example', 'content-type': 'application/json' },
      body: '{}',
    }));
    expect(response.status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
