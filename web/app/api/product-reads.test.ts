import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { GET as devices } from './devices/route';
import { GET as games } from './games/route';
import { GET as activity } from './activity/route';
import { GET as security } from './account/security/route';

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); });

describe.each([
  ['devices', devices, '/v1/devices'],
  ['games', games, '/v1/games'],
  ['activity', activity, '/v1/audit'],
  ['security', security, '/v1/account/security'],
] as const)('%s product read', (name, read, corePath) => {
  it('denies unsigned reads without contacting Core', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const upstream = vi.spyOn(globalThis, 'fetch');
    const result = await read(new NextRequest(`https://web.example/api/${name}`));
    expect(result.status).toBe(401);
    expect(upstream).not.toHaveBeenCalled();
  });
  it('reads the fixed Core route using only the HttpOnly session', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const payload = { status: 'authoritative' };
    const upstream = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(payload)));
    const result = await read(new NextRequest(`https://web.example/api/${name}`, {
      headers: { cookie: 'sentinel_access=opaque-test-token', authorization: 'Bearer attacker' },
    }));
    expect(result.status).toBe(200);
    await expect(result.json()).resolves.toEqual(payload);
    expect(upstream.mock.calls[0]?.[0]).toBe(`https://core.example${corePath}`);
    const headers = new Headers(upstream.mock.calls[0]?.[1]?.headers);
    expect(headers.get('authorization')).toBe('Bearer opaque-test-token');
    expect(result.headers.get('cache-control')).toBe('no-store');
  });
});
