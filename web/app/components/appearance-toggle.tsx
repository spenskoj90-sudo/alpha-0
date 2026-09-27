'use client';

import { useEffect, useSyncExternalStore } from 'react';

type Appearance = 'system' | 'dark' | 'light';
const STORAGE_KEY = 'sentinel.web.appearance';
const CHANGE_EVENT = 'sentinel-appearance-change';

function readAppearance(): Appearance {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored === 'dark' || stored === 'light' || stored === 'system' ? stored : 'system';
}

function subscribe(onStoreChange: () => void) {
  const onStorage = (event: StorageEvent) => {
    if (event.key === STORAGE_KEY) onStoreChange();
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
  const appearance = useSyncExternalStore<Appearance>(subscribe, readAppearance, (): Appearance => 'system');

  useEffect(() => {
    applyAppearance(appearance);
  }, [appearance]);

  function cycle() {
    const next: Appearance = appearance === 'system' ? 'dark' : appearance === 'dark' ? 'light' : 'system';
    window.localStorage.setItem(STORAGE_KEY, next);
    window.dispatchEvent(new Event(CHANGE_EVENT));
  }

  const readable = appearance === 'system' ? 'System' : appearance === 'dark' ? 'Dark' : 'Light';
  return (
    <button
      type="button"
      className="appearance-toggle"
      onClick={cycle}
      aria-label={`Switch appearance. Current mode: ${readable}`}
      title="Appearance follows System → Dark → Light"
    >
      Appearance · {readable}
    </button>
  );
}
