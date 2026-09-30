import { afterEach, describe, expect, it, vi } from 'vitest';
import { GET } from './route';

afterEach(() => vi.unstubAllEnvs());
describe('deployed Web identity', () => {
  it('exposes only the validated deployment SHA without reading Core or credentials', async () => {
    vi.stubEnv('RENDER_GIT_COMMIT', 'a'.repeat(40));
    const response = await GET();
    expect(response.headers.get('cache-control')).toBe('no-store');
    await expect(response.json()).resolves.toEqual({ service: 'sentinel-web', sourceSha: 'a'.repeat(40) });
  });
  it('does not report an arbitrary environment value as build evidence', async () => {
    vi.stubEnv('RENDER_GIT_COMMIT', 'not-a-sha');
    vi.stubEnv('GITHUB_SHA', '');
    await expect((await GET()).json()).resolves.toMatchObject({ sourceSha: null });
  });
});
