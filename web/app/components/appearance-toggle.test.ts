import { afterEach, expect, test, vi } from 'vitest';
import { readAppearance } from './appearance-toggle';

afterEach(() => vi.unstubAllGlobals());

test('blocked browser storage preserves a usable system appearance', () => {
  vi.stubGlobal('window', { get localStorage() { throw new Error('Storage blocked'); } });
  expect(readAppearance()).toBe('system');
});

test('invalid stored appearance uses system and valid preference is retained', () => {
  vi.stubGlobal('window', { localStorage: { getItem: () => 'unexpected' } });
  expect(readAppearance()).toBe('system');
  vi.stubGlobal('window', { localStorage: { getItem: () => 'light' } });
  expect(readAppearance()).toBe('light');
});
