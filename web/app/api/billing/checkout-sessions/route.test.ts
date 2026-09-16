import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { POST } from './route';

describe('/api/billing/checkout-sessions', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  });

  it('denies cross-site checkout creation before contacting Core', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch');
    const response = await POST(new NextRequest('http://localhost/api/billing/checkout-sessions', {
      method: 'POST',
      headers: {
        origin: 'https://attacker.example',
        'content-type': 'application/json',
        cookie: 'sentinel_access=access-secret',
      },
      body: JSON.stringify({ plan_code: 'core-plus' }),
    }));

    expect(response.status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('forwards only the canonical plan code and confines the opaque token to Core', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      provider: 'stripe',
      subscription_id: 'local-subscription',
      checkout_session_id: 'cs_test_123',
      checkout_url: 'https://checkout.stripe.com/c/pay/cs_test_123',
      livemode: false,
    }), { status: 200, headers: { 'content-type': 'application/json' } }));

    const response = await POST(new NextRequest('http://localhost/api/billing/checkout-sessions', {
      method: 'POST',
      headers: {
        origin: 'http://localhost',
        'content-type': 'application/json',
        cookie: 'sentinel_access=access-secret',
      },
      body: JSON.stringify({
        plan_code: 'core-plus',
        price_id: 'price_attacker',
        provider: 'attacker-provider',
        livemode: true,
        success_url: 'https://attacker.example/success',
      }),
    }));

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe('https://core.example/v1/billing/checkout-sessions');
    const init = fetchMock.mock.calls[0][1];
    expect(init?.body).toBe(JSON.stringify({ plan_code: 'core-plus' }));
    const headers = new Headers(init?.headers);
    expect(headers.get('authorization')).toBe('Bearer access-secret');
    expect(await response.json()).toMatchObject({ provider: 'stripe', livemode: false });
    expect(response.headers.get('set-cookie') ?? '').not.toContain('access-secret');
  });

  it('rejects malformed plan codes without contacting Core', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch');
    const response = await POST(new NextRequest('http://localhost/api/billing/checkout-sessions', {
      method: 'POST',
      headers: {
        origin: 'http://localhost',
        'content-type': 'application/json',
        cookie: 'sentinel_access=access-secret',
      },
      body: JSON.stringify({ plan_code: '../price_override' }),
    }));

    expect(response.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
