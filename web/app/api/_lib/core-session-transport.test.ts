import { afterEach, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { proxyAuthenticated, authenticateWeb } from './core-session';

const request = () => new NextRequest('https://app.example/api/account', { headers: { cookie: 'sentinel_access=private-token' } });
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); });

it('denies credential-bearing, non-http and path-bearing Core configuration before fetch', async () => {
  const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({ ok: true }));
  for (const url of ['ftp://core.example', 'https://secret@core.example', 'https://core.example/path', 'https://core.example?query=1', 'https://core.example/#fragment']) {
    vi.stubEnv('SENTINEL_CORE_URL', url);
    expect((await proxyAuthenticated(request(), '/v1/account')).status).toBe(503);
  }
  expect(fetch).not.toHaveBeenCalled();
});

it('applies a 45-second deadline and rejects redirects on authenticated transport', async () => {
  vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  const timeout = vi.spyOn(AbortSignal, 'timeout');
  const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 302, headers: { location: 'https://other.example' } }));
  const result = await proxyAuthenticated(request(), '/v1/account', { redirect: 'follow' });
  expect(result.status).toBe(502);
  expect(fetch.mock.calls[0][1]?.redirect).toBe('manual');
  expect(fetch.mock.calls[0][1]?.signal).toBeInstanceOf(AbortSignal);
  expect(timeout).toHaveBeenCalledWith(45_000);
  expect(result.headers.has('set-cookie')).toBe(false);
});

it('limits streamed response bytes even without content-length', async () => {
  vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  const stream = new ReadableStream({ start(controller) { controller.enqueue(new Uint8Array(1_048_577)); controller.close(); } });
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(stream));
  const result = await proxyAuthenticated(request(), '/v1/account');
  expect(result.status).toBe(502);
  expect(await result.json()).toEqual({ error: 'SENTINEL_CORE_UNAVAILABLE' });
});

it('cancels a stalled body when the transport deadline expires', async () => {
  vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  const controller = new AbortController();
  vi.spyOn(AbortSignal, 'timeout').mockReturnValue(controller.signal);
  const canceled = vi.fn();
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(new ReadableStream({ cancel: canceled })));
  const pending = proxyAuthenticated(request(), '/v1/account');
  setTimeout(() => controller.abort(), 5);
  const result = await pending;
  expect(result.status).toBe(502);
  expect(canceled).toHaveBeenCalled();
});

it('bounds auth response bodies before parsing token payloads', async () => {
  vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('x'.repeat(1_048_577)));
  const result = await authenticateWeb(new NextRequest('https://app.example/api/session/login', { method: 'POST', headers: { origin: 'https://app.example', cookie: `sentinel_web_session=transport-${'t'.repeat(40)}; sentinel_web_generation=0` }, body: '{}' }), 'login');
  expect(result.status).toBe(502);
  expect(await result.json()).toEqual({ error: 'SENTINEL_CORE_UNAVAILABLE' });
});
