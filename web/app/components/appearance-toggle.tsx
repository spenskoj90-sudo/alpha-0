'use client';

import { useEffect, useState } from 'react';

type Appearance = 'system' | 'dark' | 'light';
const STORAGE_KEY = 'sentinel.web.appearance';

function applyAppearance(value: Appearance) {
  if (value === 'system') {
    delete document.documentElement.dataset.theme;
  } else {
    document.documentElement.dataset.theme = value;
  }
}

export function AppearanceToggle() {
  const [appearance, setAppearance] = useState<Appearance>('system');

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    const next: Appearance = stored === 'dark' || stored === 'light' || stored === 'system' ? stored : 'system';
    setAppearance(next);
    applyAppearance(next);
  }, []);

  function cycle() {
    const next: Appearance = appearance === 'system' ? 'dark' : appearance === 'dark' ? 'light' : 'system';
    setAppearance(next);
    window.localStorage.setItem(STORAGE_KEY, next);
    applyAppearance(next);
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
