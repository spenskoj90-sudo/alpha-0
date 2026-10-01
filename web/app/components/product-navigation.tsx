'use client';

import { useEffect, useState } from 'react';
import { useLocale } from './locale-provider';

const destinations = [
  { id: 'main-content', label: 'Overview', path: 'M3.5 10.5 12 3.5l8.5 7M5.5 9v11h5v-6h3v6h5V9' },
  { id: 'games', label: 'Games', path: 'M8 7h8a4 4 0 0 1 3.9 3.2l1.3 6.1a2.5 2.5 0 0 1-4.2 2.3L15 17H9l-2 1.6a2.5 2.5 0 0 1-4.2-2.3l1.3-6.1A4 4 0 0 1 8 7ZM7 10v4m-2-2h4m7-1h.01m2 3h.01' },
  { id: 'security', label: 'Security', path: 'M12 3.5 20 7v5c0 4.2-3.1 7-8 9-4.9-2-8-4.8-8-9V7l8-3.5Zm-4 8 2.5 2.5 5-5' },
  { id: 'activity', label: 'Activity', path: 'M3 12h4l2.7-5.5 4.6 11L17 12h4' },
  { id: 'intelligence', label: 'Intelligence', path: 'M12 3v3m0 12v3M3 12h3m12 0h3M5.6 5.6l2.1 2.1m8.6 8.6 2.1 2.1m0-12.8-2.1 2.1m-8.6 8.6-2.1 2.1M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z' },
  { id: 'devices', label: 'Devices', path: 'M3 4h13v11H3V4Zm4 15h5m-2.5-4v4M18 9h4v12h-4V9Z' },
  { id: 'account', label: 'Account', path: 'M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm-8 18v-2a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v2' },
  { id: 'settings', label: 'Settings', path: 'M4 7h16M4 17h16M8 4v6m8 4v6' },
  { id: 'support', label: 'Support', path: 'M4 14v-2a8 8 0 0 1 16 0v5a4 4 0 0 1-4 4h-4M4 12H2v6h4v-6H4Zm16 0h2v6h-4v-6h2Z' },
];

export function ProductNavigation() {
  const { t } = useLocale();
  const [active, setActive] = useState('main-content');

  useEffect(() => {
    const sync = () => setActive(window.location.hash.slice(1) || 'main-content');
    sync();
    window.addEventListener('hashchange', sync);
    return () => window.removeEventListener('hashchange', sync);
  }, []);

  return (
    <nav className="nav-list" aria-label={t("Product sections")}>
      {destinations.map(destination => (
        <a
          key={destination.id}
          className={`nav-item${active === destination.id ? ' nav-item-active' : ''}`}
          href={`#${destination.id}`}
          aria-current={active === destination.id ? 'location' : undefined}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="nav-icon">
            <path d={destination.path} />
          </svg>
          <span>{t(destination.label)}</span>
        </a>
      ))}
    </nav>
  );
}
