import { afterEach, expect, it, vi } from 'vitest';
import { coreSetupPost } from './core-setup';

afterEach(() => vi.restoreAllMocks());

it('redacts credentialed request errors before CI reporters receive them', async () => {
  vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Request failed Authorization: Bearer dummy-test-token'));
  await expect(coreSetupPost('http://127.0.0.1:1', {}, 'dummy-test-token')).rejects.toThrow(/^Core test setup failed; sensitive request details redacted\.$/);
});

it('redacts invalid JSON response content', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('dummy-sensitive-response'));
  await expect(coreSetupPost('http://127.0.0.1:1')).rejects.toThrow(/^Core test setup failed; sensitive request details redacted\.$/);
});

it('returns only setup status and parsed data on success', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{"secret":"dummy"}'));
  await expect(coreSetupPost('http://127.0.0.1:1', { code: '000000' }, 'dummy')).resolves.toEqual({ status: 200, data: { secret: 'dummy' } });
  expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:1', expect.objectContaining({ method: 'POST', body: '{"code":"000000"}' }));
});
