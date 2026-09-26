import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

import { GET, POST } from './route';

function ctx(...path: string[]) {
  return { params: Promise.resolve({ path }) };
}

describe('/api/mobile-core/[...path]', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it('relays an allowlisted login without exposing a new authority boundary', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('{"mfa_required":true}', {
        status: 200,
        headers: {
          'content-type': 'application/json',
          'x-request-id': 'android-request-1',
        },
      }),
    );
    const request = new NextRequest('https://web.example/api/mobile-core/v1/auth/login', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'authorization': 'Bearer opaque',
        'x-request-id': 'android-request-1',
        'idempotency-key': 'idem-1',
        'cookie': 'must-not-forward=1',
      },
      body: '{"email":"user@example.test","password":"redacted"}',
    });

    const response = await POST(request, ctx('v1', 'auth', 'login'));

    expect(response.status).toBe(200);
    expect(await response.text()).toBe('{"mfa_required":true}');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('https://core.example/v1/auth/login');
    expect(init?.method).toBe('POST');
    expect(init?.cache).toBe('no-store');
    expect(init?.redirect).toBe('manual');
    const headers = new Headers(init?.headers);
    expect(headers.get('authorization')).toBe('Bearer opaque');
    expect(headers.get('x-request-id')).toBe('android-request-1');
    expect(headers.get('idempotency-key')).toBe('idem-1');
    expect(headers.get('cookie')).toBeNull();
  });

  it('allows caller-scoped mobile reads', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{"events":[]}', { status: 200 }));
    const response = await GET(
      new NextRequest('https://web.example/api/mobile-core/v1/audit', {
        headers: { authorization: 'Bearer access', 'x-request-id': 'audit-request' },
      }),
      ctx('v1', 'audit'),
    );
    expect(response.status).toBe(200);
    expect(fetchMock.mock.calls[0][0]).toBe('https://core.example/v1/audit');
  });

  it('denies admin and other non-mobile Core paths before network access', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch');
    const response = await GET(
      new NextRequest('https://web.example/api/mobile-core/v1/admin/games'),
      ctx('v1', 'admin', 'games'),
    );
    expect(response.status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('rejects oversized request bodies before forwarding', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch');
    const response = await POST(
      new NextRequest('https://web.example/api/mobile-core/v1/events%3Abatch', {
        method: 'POST',
        headers: { 'content-length': '1048577' },
        body: '{}',
      }),
      ctx('v1', 'events:batch'),
    );
    expect(response.status).toBe(413);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('fails closed when the upstream Core origin is invalid', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'http://core.example');
    const response = await GET(
      new NextRequest('https://web.example/api/mobile-core/v1/audit'),
      ctx('v1', 'audit'),
    );
    expect(response.status).toBe(503);
  });
});
