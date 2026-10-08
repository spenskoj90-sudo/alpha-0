'use client';

import { useEffect, useRef, useState } from 'react';
import { useLocale } from './locale-provider';
import { loadProductData, type ProductData } from './product-data';

export function ProductOverview() {
  const { t, locale } = useLocale();
  const [data, setData] = useState<ProductData>({ state: 'SIGNED_OUT' });
  const [busy, setBusy] = useState(false);
  const generation = useRef(0);

  useEffect(() => {
    const revisions = generation;
    let active = true;
    const update = async (event: Event) => {
      const revision = ++generation.current;
      const session = (event as CustomEvent<boolean | null>).detail;
      if (session !== true) {
        setData(session === false ? { state: 'SIGNED_OUT' } : { state: 'ERROR', message: 'Account data is unavailable. Check your connection and retry.' });
        setBusy(false);
        return;
      }
      setBusy(true);
      const snapshot = await loadProductData();
      if (active && revision === generation.current) { setData(snapshot); setBusy(false); }
    };
    window.addEventListener('sentinel-session-changed', update);
    return () => { active = false; revisions.current++; window.removeEventListener('sentinel-session-changed', update); };
  }, []);

  async function refresh() {
    const revision = ++generation.current;
    setBusy(true);
    const snapshot = await loadProductData();
    if (revision === generation.current) { setData(snapshot); setBusy(false); }
  }

  const status = busy ? 'Loading verified data…' : data.state === 'SIGNED_OUT' ? 'Sign in to view your account data.' : data.state === 'ERROR' ? data.message : '';
  return (
    <section className="surface-grid" aria-label={t("Control plane surfaces")} aria-busy={busy}>
      <article className="card surface-card" id="games">
        <h2>{t("Games")}</h2>
        {status ? <p role={data.state === 'ERROR' ? 'alert' : 'status'}>{t(status)}</p> : data.state === 'READY' && (<>
          <p className="microcopy">{t("Catalog entries describe account integration. Exact game support remains unverified; no game actions are enabled.")}</p>
          {data.games.length ? <ul className="product-list">{data.games.map(game => <li key={game.id}>
            <strong>{game.name}</strong><span className="muted">{game.family} · {game.platform}</span>
            <span className="state">{t("Catalog foundation · environment unverified")}</span>
          </li>)}</ul> : <p>{t("No games are available in the current catalog.")}</p>}
          <details>
            <summary>{t("Research and observer profiles")} ({data.research.length})</summary>
            <p className="microcopy">{t("Research profiles do not grant access. Each target needs separate version, source and environment verification.")}</p>
            {data.research.length ? <ul className="product-list">{data.research.map(profile => <li key={profile.id}>
              <strong>{profile.name}</strong><span className="muted">{profile.platform}{profile.patch ? ` · ${profile.patch}` : ''} · {profile.environment}</span>
              <span className="state">{t(profile.implementation_status === 'observer_pilot' ? 'Observer pilot · calibration pending' : profile.implementation_status === 'adapter_foundation' ? 'Adapter foundation · environment unverified' : 'Research only · environment unverified')}</span>
            </li>)}</ul> : <p>{t("No research profiles are available.")}</p>}
          </details>
        </>)}
        <button className="ghost-btn" disabled={busy} onClick={() => void refresh()}>{t("Refresh product data")}</button>
      </article>
      <article className="card surface-card" id="security">
        <h2>{t("Security")}</h2>
        {status ? <p>{t(status)}</p> : data.state === 'READY' && <dl className="product-facts">
          <div><dt>{t("Email")}</dt><dd>{data.security.email_verified ? t("Verified") : t("Verification pending")}</dd></div>
          <div><dt>{t("Password")}</dt><dd>{data.security.password_enabled ? t("Enabled") : t("Not enabled")}</dd></div>
          <div><dt>{t("Two-factor authentication")}</dt><dd>{data.security.mfa_enabled ? t("Enabled") : t("Not enabled")}</dd></div>
          <div><dt>{t("Recovery codes remaining")}</dt><dd>{data.security.mfa_recovery_codes_remaining}</dd></div>
          <div><dt>{t("Linked providers")}</dt><dd>{data.security.providers.join(', ') || t("None linked")}</dd></div>
        </dl>}
      </article>
      <article className="card surface-card" id="devices">
        <h2>{t("Devices")}</h2>
        {status ? <p>{t(status)}</p> : data.state === 'READY' && <>
          {data.devices.length ? <ul className="product-list">{data.devices.map(device => <li key={device.device_id}>
            <div className="row-between"><strong>{device.platform}</strong><span className="state">{device.state === 'ACTIVE' ? t("Registered") : device.state === 'SUSPENDED' ? t("Suspended") : t("Revoked")}</span></div>
            <span className="microcopy">{t("Device ID:")}{' '}{device.device_id}</span>
            <span className="muted">{t("Registered")}{' '}{new Date(device.bound_at).toLocaleString(locale === 'ru' ? 'ru-RU' : 'en-US')}</span>
            <span className="microcopy">{device.last_seen_at ? `${t("Last seen")} ${new Date(device.last_seen_at).toLocaleString(locale === 'ru' ? 'ru-RU' : 'en-US')}` : t("No activity recorded yet")}</span>
          </li>)}</ul> : <p>{t("No devices are registered. Sign in on Android and complete device setup to register your device.")}</p>}
          {data.devicesTruncated && <p role="status">{t("Showing the 100 most recent registrations.")}</p>}
          <p className="microcopy">{t("Registration status does not establish that a device is currently online.")}</p>
        </>}
      </article>
      <article className="card surface-card" id="activity">
        <h2>{t("Activity")}</h2>
        {status ? <p>{t(status)}</p> : data.state === 'READY' && (
          data.events.length ? <ol className="product-list">{data.events.map((event, i) => <li key={i}>
            <div className="row-between"><strong>{event.action}</strong><span className="state">{event.decision}</span></div>
            <span className="muted">{event.reason_code.replaceAll('_', ' ')} · {event.resource}</span>
            {event.created_at && <time className="microcopy" dateTime={event.created_at}>{new Date(event.created_at).toLocaleString(locale === 'ru' ? 'ru-RU' : 'en-US')}</time>}
          </li>)}</ol> : <p>{t("No account activity has been recorded.")}</p>
        )}
      </article>
    </section>
  );
}
