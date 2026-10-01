import { describe, expect, it } from 'vitest';
import { resolveLocale, translate } from './locale';

describe('product language selection', () => {
  it('uses the saved supported language before browser preference', () => {
    expect(resolveLocale('en', ['ru-RU'])).toBe('en');
    expect(resolveLocale('ru', ['en-US'])).toBe('ru');
  });
  it('ignores corrupt preferences and supports Russian regional locales', () => {
    expect(resolveLocale('<script>', ['ru-EE', 'en'])).toBe('ru');
    expect(resolveLocale(null, ['de-DE'])).toBe('en');
  });
  it('translates forms and bounded failures without inventing provider evidence', () => {
    expect(translate('ru', 'Sign in')).toBe('Войти');
    expect(translate('ru', 'Connection interrupted. Check your network and retry.')).toContain('соединение');
    expect(translate('ru', 'UNREPORTED')).toContain('НЕ УКАЗАНО');
  });
  it('preserves unknown server messages, evidence IDs and English fallback', () => {
    for (const key of ['__proto__', 'constructor', 'toString']) expect(translate('ru', key)).toBe(key);
    expect(translate('ru', 'provider-specific-unknown')).toBe('provider-specific-unknown');
    expect(translate('en', 'Sign in')).toBe('Sign in');
    expect(translate('ru', '0123456789abcdef')).toBe('0123456789abcdef');
  });
});
