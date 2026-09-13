import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from './route';

describe('POST /api/session/login', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it('rejects cross-site credential submission before calling Core', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch');
    const response = await POST(new NextRequest('http://localhost/api/session/login', {
      method: 'POST',
      headers: { origin: 'https://attacker.example', 'content-type': 'application/json' },
      body: JSON.stringify({ email: 'user@example.com', password: 'correct-horse-battery-staple' }),
    }));
    expect(response.status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('keeps opaque Core tokens out of client-visible JSON and stores them in HttpOnly cookies', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      session_token: 'access-secret',
      refresh_token: 'refresh-secret',
      expires_at: '2030-01-01T00:00:00Z',
      scopes: ['game:read'],
    }), { status: 200, headers: { 'content-type': 'application/json' } }));

    const response = await POST(new NextRequest('http://localhost/api/session/login', {
      method: 'POST',
      headers: { origin: 'http://localhost', 'content-type': 'application/json' },
      body: JSON.stringify({ email: 'user@example.com', password: 'correct-horse-battery-staple' }),
    }));

    expect(response.status).toBe(200);
    const body = await response.text();
    expect(body).toContain('"authenticated":true');
    expect(body).not.toContain('access-secret');
    expect(body).not.toContain('refresh-secret');
    const setCookie = response.headers.get('set-cookie') ?? '';
    expect(setCookie).toContain('sentinel_access=access-secret');
    expect(setCookie).toContain('sentinel_refresh=refresh-secret');
    expect(setCookie.toLowerCase()).toContain('httponly');
    expect(setCookie.toLowerCase()).toContain('samesite=strict');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('fails closed when Core is not configured', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', '');
    const response = await POST(new NextRequest('http://localhost/api/session/login', {
      method: 'POST',
      headers: { origin: 'http://localhost', 'content-type': 'application/json' },
      body: '{}',
    }));
    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({ error: 'SENTINEL_CORE_URL_NOT_CONFIGURED' });
  });
});
