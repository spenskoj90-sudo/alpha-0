'use client';

import { useEffect, useSyncExternalStore } from 'react';
import { useLocale } from './locale-provider';

type Appearance = 'system' | 'dark' | 'light';
const STORAGE_KEY = 'sentinel.web.appearance';
const CHANGE_EVENT = 'sentinel-appearance-change';
let transientAppearance: Appearance | null = null;

export function readAppearance(): Appearance {
  if (transientAppearance) return transientAppearance;
  let stored: string | null = null;
  try { stored = window.localStorage.getItem(STORAGE_KEY); } catch { /* System mode remains usable when storage is blocked. */ }
  return stored === 'dark' || stored === 'light' || stored === 'system' ? stored : 'system';
}

function subscribe(onStoreChange: () => void) {
  const onStorage = (event: StorageEvent) => {
    if (event.key === STORAGE_KEY || event.key === null) { transientAppearance = null; onStoreChange(); }
  };
  window.addEventListener('storage', onStorage);
  window.addEventListener(CHANGE_EVENT, onStoreChange);
  return () => {
    window.removeEventListener('storage', onStorage);
    window.removeEventListener(CHANGE_EVENT, onStoreChange);
  };
}

function applyAppearance(value: Appearance) {
  if (value === 'system') {
    delete document.documentElement.dataset.theme;
  } else {
    document.documentElement.dataset.theme = value;
  }
}

export function AppearanceToggle() {
  const { t } = useLocale();
  const appearance = useSyncExternalStore<Appearance>(subscribe, readAppearance, (): Appearance => 'system');

  useEffect(() => {
    applyAppearance(appearance);
  }, [appearance]);

  function cycle() {
    const next: Appearance = appearance === 'system' ? 'dark' : appearance === 'dark' ? 'light' : 'system';
    transientAppearance = next;
    try { window.localStorage.setItem(STORAGE_KEY, next); } catch { /* Apply the selected mode for this session. */ }
    window.dispatchEvent(new Event(CHANGE_EVENT));
  }

  const readable = appearance === 'system' ? 'System' : appearance === 'dark' ? 'Dark' : 'Light';
  return (
    <button
      type="button"
      className="appearance-toggle"
      onClick={cycle}
      aria-label={`${t("Switch appearance. Current mode:")} ${t(readable)}`}
      title={t("Appearance follows System → Dark → Light")}
    >{t("Appearance ·")}{' '}{t(readable)}
    </button>
  );
}
