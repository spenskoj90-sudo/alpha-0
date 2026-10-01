'use client';

import { createContext, useContext, useEffect, useSyncExternalStore } from 'react';
import { resolveLocale, translate, type Locale } from './locale';

const KEY = 'sentinel.locale';
const EVENT = 'sentinel-locale-change';
let preference: Locale | null = null;

function read(): Locale {
  if (preference) return preference;
  let saved: string | null = null;
  try { saved = window.localStorage.getItem(KEY); } catch { /* Session-only fallback. */ }
  return resolveLocale(saved, navigator.languages.length ? navigator.languages : [navigator.language]);
}
function subscribe(notify: () => void) {
  const storage = (event: StorageEvent) => { if (event.key === KEY || event.key === null) { preference = null; notify(); } };
  window.addEventListener('storage', storage);
  window.addEventListener(EVENT, notify);
  return () => { window.removeEventListener('storage', storage); window.removeEventListener(EVENT, notify); };
}
function select(locale: Locale) {
  preference = locale;
  try { window.localStorage.setItem(KEY, locale); } catch { /* Keep selected language for this session. */ }
  window.dispatchEvent(new Event(EVENT));
}

const LocaleContext = createContext<Locale>('en');
export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const locale = useSyncExternalStore(subscribe, read, (): Locale => 'en');
  useEffect(() => { document.documentElement.lang = locale; }, [locale]);
  return <LocaleContext.Provider value={locale}>{children}</LocaleContext.Provider>;
}
export function useLocale() {
  const locale = useContext(LocaleContext);
  return { locale, t: (text: string) => translate(locale, text) };
}
export function LanguageSwitch() {
  const { locale } = useLocale();
  return <label className="language-switch">{locale === 'ru' ? 'Язык' : 'Language'}
    <select aria-label={locale === 'ru' ? 'Язык интерфейса' : 'Interface language'} value={locale} onChange={event => select(event.target.value === 'ru' ? 'ru' : 'en')}>
      <option value="en" lang="en">English</option><option value="ru" lang="ru">Русский</option>
    </select>
  </label>;
}
