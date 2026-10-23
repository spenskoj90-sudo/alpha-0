import { afterEach, describe, expect, it, vi } from 'vitest';
import { loadProductData } from './product-data';
import { reconcileGameInventory } from './game-inventory';

afterEach(() => vi.restoreAllMocks());

describe('product data state', () => {
  it('requires a real session before showing security, games or activity', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}', { status: 401 }));
    await expect(loadProductData()).resolves.toMatchObject({ state: 'SIGNED_OUT' });
  });
  it('keeps a failed read distinct from an empty product', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'));
    await expect(loadProductData()).resolves.toMatchObject({ state: 'ERROR' });
  });
  it('never displays a malformed security response as a protected account', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}'));
    await expect(loadProductData()).resolves.toMatchObject({ state: 'ERROR' });
  });
  it('rejects corrupt device metadata instead of displaying an invalid registration', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      const payload = String(url).endsWith('/security') ? {
        email: null, email_verified: false, password_enabled: true,
        mfa_enabled: false, mfa_recovery_codes_remaining: 0, providers: [],
      } : String(url).endsWith('/games') ? { games: [] } : String(url).endsWith('/game-capabilities') ? { schema_version: 1, profiles: [] } : {
        devices: [{ device_id: 'test', platform: 'android', state: 'ACTIVE', bound_at: 'invalid-date', last_seen_at: null }], truncated: false,
      };
      return new Response(JSON.stringify(payload));
    });
    await expect(loadProductData()).resolves.toMatchObject({ state: 'ERROR' });
  });
  it('loads bounded server data with empty states preserved', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      const payload = String(url).endsWith('/security') ? {
        email: null, email_verified: false, password_enabled: true,
        mfa_enabled: false, mfa_recovery_codes_remaining: 0, providers: [],
      } : String(url).endsWith('/games') ? { games: [] } : String(url).endsWith('/game-capabilities') ? { schema_version: 1, profiles: [] } : String(url).endsWith('/devices') ? { devices: [], truncated: false } : { events: [] };
      return new Response(JSON.stringify(payload));
    });
    await expect(loadProductData()).resolves.toMatchObject({ state: 'READY', games: [], research: [], events: [], devices: [], devicesTruncated: false });
  });
  it('keeps an uncalibrated observer distinct from a verified playable integration', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      const payload = String(url).endsWith('/security') ? {
        email: null, email_verified: false, password_enabled: true,
        mfa_enabled: false, mfa_recovery_codes_remaining: 0, providers: [],
      } : String(url).endsWith('/games') ? { games: [] } : String(url).endsWith('/game-capabilities') ? { schema_version: 1, profiles: [{
        id: 'shattered-android', name: 'Shattered Pixel Dungeon', platform: 'android', patch: null,
        environment: 'stock-offline-pilot', implementation_status: 'observer_pilot', exact_environment_status: 'l3_pending',
        deterministic_automation: false, user_confirmed_actions: [], recommendation_capability: 'calibration_pending',
      }] } : String(url).endsWith('/devices') ? { devices: [], truncated: false } : { events: [] };
      return new Response(JSON.stringify(payload));
    });
    await expect(loadProductData()).resolves.toMatchObject({ state: 'READY', research: [{ implementation_status: 'observer_pilot', exact_environment_status: 'l3_pending' }] });
  });
  it.each([
    { deterministic_automation: true }, { user_confirmed_actions: ['input'] },
    { exact_environment_status: 'verified' }, { implementation_status: 'unknown' },
  ])('rejects research promotion or malformed evidence: %j', async (override) => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      const payload = String(url).endsWith('/security') ? {
        email: null, email_verified: false, password_enabled: true,
        mfa_enabled: false, mfa_recovery_codes_remaining: 0, providers: [],
      } : String(url).endsWith('/games') ? { games: [] } : String(url).endsWith('/game-capabilities') ? { schema_version: 1, profiles: [{
        id: 'research', name: 'Research', platform: 'windows', patch: null, environment: 'unverified-target',
        implementation_status: 'research_only', exact_environment_status: 'l3_pending', deterministic_automation: false,
        user_confirmed_actions: [], recommendation_capability: 'unavailable', ...override,
      }] } : String(url).endsWith('/devices') ? { devices: [], truncated: false } : { events: [] };
      return new Response(JSON.stringify(payload));
    });
    await expect(loadProductData()).resolves.toMatchObject({ state: 'ERROR' });
  });
});

describe('safe combined game status inventory', () => {
  const game = { id: 'diablo-4-pc', name: 'Diablo IV', family: 'Diablo', platform: 'windows', interaction_mode: 'adapter',
    implementation_status: 'catalog_foundation' as const, exact_environment_status: 'unverified' as const, execution_authority: false as const };
  const research = { id: 'shattered-android', name: 'Shattered Pixel Dungeon', platform: 'android' as const,
    patch: null, environment: 'offline-pilot', implementation_status: 'observer_pilot' as const,
    exact_environment_status: 'l3_pending' as const };
  it('preserves unverified state and sorts diagnostic pilot before foundation', () => {
    const items = reconcileGameInventory([game], [research]);
    expect(items.map(x => x.evidence)).toEqual(['observer_pilot', 'catalog_foundation']);
    expect(items.every(x => !x.executable && !x.environmentVerified)).toBe(true);
  });
  it('merges a matching ID only as read-only inventory', () => {
    const items = reconcileGameInventory([game], [{
      id: game.id, name: game.name, platform: 'windows', patch: null,
      environment: 'unverified', implementation_status: 'research_only', exact_environment_status: 'l3_pending',
    }]);
    expect(items).toHaveLength(1);
    expect(items[0]).toMatchObject({ sources: 'both', executable: false, environmentVerified: false, evidence: 'research_only' });
  });
  it('blocks duplicate and conflicting identities', () => {
    expect(() => reconcileGameInventory([game, game], [])).toThrow('INVALID_ACCOUNT_GAME_CATALOG');
    expect(() => reconcileGameInventory([game], [{ ...research, id: game.id }])).toThrow('GAME_PROFILE_IDENTITY_CONFLICT');
    expect(() => reconcileGameInventory([], [research, research])).toThrow('INVALID_RESEARCH_GAME_CATALOG');
  });
});
