import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from './route';

describe('POST /api/session/mfa', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it('exchanges a short-lived MFA challenge for HttpOnly session cookies', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      session_token: 'access-secret',
      refresh_token: 'refresh-secret',
      expires_at: '2030-01-01T00:00:00Z',
      scopes: ['game:read'],
    }), { status: 200, headers: { 'content-type': 'application/json' } }));

    const response = await POST(new NextRequest('http://localhost/api/session/mfa', {
      method: 'POST',
      headers: { origin: 'http://localhost', 'content-type': 'application/json' },
      body: JSON.stringify({
        challenge_token: 'abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG',
        code: '123456',
      }),
    }));

    expect(response.status).toBe(200);
    const body = await response.text();
    expect(body).toContain('"authenticated":true');
    expect(body).not.toContain('access-secret');
    expect(body).not.toContain('refresh-secret');
    const cookie = response.headers.get('set-cookie') ?? '';
    expect(cookie).toContain('sentinel_access=access-secret');
    expect(cookie.toLowerCase()).toContain('httponly');
    expect(fetchMock).toHaveBeenCalledTimes(1);
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
