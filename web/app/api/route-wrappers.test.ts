import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

import { GET as getEntitlements } from './account/entitlements/route';
import { GET as getPlans } from './billing/plans/route';
import { POST as logout } from './session/logout/route';
import { POST as register } from './session/register/route';

describe('thin Web route bindings', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
  });

  it('binds account and billing reads to authenticated Core proxying', async () => {
    const entitlements = await getEntitlements(new NextRequest('http://localhost/api/account/entitlements'));
    expect(entitlements.status).toBe(401);
    await expect(entitlements.json()).resolves.toEqual({ error: 'WEB_SESSION_REQUIRED' });

    const plans = await getPlans(new NextRequest('http://localhost/api/billing/plans'));
    expect(plans.status).toBe(401);
    await expect(plans.json()).resolves.toEqual({ error: 'WEB_SESSION_REQUIRED' });
  });

  it('binds registration to the same-origin authentication boundary', async () => {
    const response = await register(new NextRequest('http://localhost/api/session/register', {
      method: 'POST',
      headers: { origin: 'https://attacker.example', 'content-type': 'application/json' },
      body: '{}',
    }));
    expect(response.status).toBe(403);
  });

  it('binds logout to the same-origin revocation boundary', async () => {
    const response = await logout(new NextRequest('http://localhost/api/session/logout', {
      method: 'POST',
      headers: { origin: 'https://attacker.example' },
    }));
    expect(response.status).toBe(403);
  });
});
