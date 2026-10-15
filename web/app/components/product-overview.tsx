'use client';

import { useEffect, useRef, useState } from 'react';
import { useLocale } from './locale-provider';
import { loadProductData, type ProductData } from './product-data';
import { EmailVerification } from './email-verification';

export function ProductOverview() {
  const { t, locale } = useLocale();
  const [data, setData] = useState<ProductData>({ state: 'SIGNED_OUT' });
  const [busy, setBusy] = useState(false);
  const [confirmDevice, setConfirmDevice] = useState<{ id: string; action: 'revoke' | 'suspend' } | null>(null);
  const [deviceActionError, setDeviceActionError] = useState('');
  const [verifyingEmail, setVerifyingEmail] = useState(false);
  const generation = useRef(0);

  useEffect(() => {
    const revisions = generation;
    let active = true;
    const update = async (event: Event) => {
      const revision = ++generation.current;
      setConfirmDevice(null);
      setVerifyingEmail(false);
      setDeviceActionError('');
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

  async function changeDevice(deviceId: string, action: 'revoke' | 'suspend') {
    if (confirmDevice?.id !== deviceId || confirmDevice.action !== action || busy) return;
    // Fence a late result against logout, new login or another product refresh.
    const operationGeneration = ++generation.current;
    setBusy(true);
    setDeviceActionError('');
    setConfirmDevice(null);
    const uncertain = action === 'revoke'
      ? 'Device revocation is unconfirmed. Refresh status before deciding to try again.'
      : 'Device suspension is unconfirmed. Refresh status before deciding to try again.';
    // A response may be lost AFTER Core has committed. Never replay a
    // destructive action on a timeout, 409 or malformed response; first read
    // back the server-authoritative state through the current Web session.
    async function reconcile() {
      if (operationGeneration !== generation.current) return;
      const snapshot = await loadProductData();
      if (operationGeneration !== generation.current) return;
      if (snapshot.state === 'SIGNED_OUT') {
        setData(snapshot);
        window.dispatchEvent(new CustomEvent('sentinel-session-changed', { detail: false }));
        return;
      }
      if (snapshot.state !== 'READY') {
        setDeviceActionError(uncertain);
        return;
      }
      setData(snapshot);
      const actual = snapshot.devices.find(device => device.device_id === deviceId)?.state;
      const completed = action === 'revoke' ? actual === 'REVOKED'
        : actual === 'SUSPENDED' || actual === 'REVOKED'; // Concurrent revoke wins.
      if (!completed) setDeviceActionError(uncertain);
    }
    try {
      const response = await fetch('/api/devices/' + encodeURIComponent(deviceId) + '/' + action, {
        method: 'POST',
        cache: 'no-store',
        signal: AbortSignal.timeout(45_000),
      });
      if (response.status === 401) {
        if (operationGeneration === generation.current) {
          setData({ state: 'SIGNED_OUT' });
          setBusy(false);
          window.dispatchEvent(new CustomEvent('sentinel-session-changed', { detail: false }));
        }
        return;
      }
      // Release the response even when it is a denial. Core readback, not the
      // acknowledged body, is the source of truth for the displayed outcome.
      await response.body?.cancel().catch(() => {});
    } catch {
      // Network/body failures may hide a committed mutation. Do not retry POST.
    }
    try {
      await reconcile();
    } catch {
      if (operationGeneration === generation.current) setDeviceActionError(uncertain);
    } finally {
      if (operationGeneration === generation.current) setBusy(false);
    }
  }

  const status = busy ? 'Loading verified data…' : data.state === 'SIGNED_OUT' ? 'Sign in to view your account data.' : data.state === 'ERROR' ? data.message : '';
  return (
    <section className="surface-grid" aria-label={t("Control plane surfaces")} aria-busy={busy}>
      <article className="card surface-card" id="games">
        <h2>{t("Games")}</h2>
        {status ? <p role={data.state === 'ERROR' ? 'alert' : 'status'}>{t(status)}</p> : data.state === 'READY' && (<>
          <p className="microcopy">{t("No game has verified exact-environment support. Read-only pilots and catalog records do not grant game actions.")}</p>
          {data.research.some(profile => profile.implementation_status === 'observer_pilot') ? <ul className="product-list" aria-label={t("Diagnostic observer pilots")}>
            {data.research.filter(profile => profile.implementation_status === 'observer_pilot').map(profile => <li key={profile.id}>
              <strong>{profile.name}</strong><span className="muted">{profile.platform}{profile.patch ? ` · ${profile.patch}` : ''} · {profile.environment}</span>
              <span className="state">{t("Observer pilot · calibration pending")}</span>
            </li>)}
          </ul> : <p>{t("No diagnostic observer is available.")}</p>}
          <details>
            <summary>{t("Catalog foundations, not verified support")} ({data.games.length})</summary>
            <p className="microcopy">{t("Catalog entries describe account integration. Exact game support remains unverified; no game actions are enabled.")}</p>
            {data.games.length ? <ul className="product-list">{data.games.map(game => <li key={game.id}>
              <strong>{game.name}</strong><span className="muted">{game.family} · {game.platform}</span>
              <span className="state">{t("Catalog foundation · environment unverified")}</span>
            </li>)}</ul> : <p>{t("No games are available in the current catalog.")}</p>}
          </details>
          <details>
            <summary>{t("Research and observer profiles")} ({data.research.filter(profile => profile.implementation_status !== 'observer_pilot').length})</summary>
            <p className="microcopy">{t("Research profiles do not grant access. Each target needs separate version, source and environment verification.")}</p>
            {data.research.some(profile => profile.implementation_status !== 'observer_pilot') ? <ul className="product-list">{data.research.filter(profile => profile.implementation_status !== 'observer_pilot').map(profile => <li key={profile.id}>
              <strong>{profile.name}</strong><span className="muted">{profile.platform}{profile.patch ? ` · ${profile.patch}` : ''} · {profile.environment}</span>
              <span className="state">{t(profile.implementation_status === 'adapter_foundation' ? 'Adapter foundation · environment unverified' : 'Research only · environment unverified')}</span>
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
        {data.state === 'READY' && <>
          {!data.security.email_verified && data.security.email && (verifyingEmail ?
            <div className="security-email-verification" aria-label={t("Verify account email")}>
              <EmailVerification initialEmail={data.security.email} lockedEmail
                cancelLabel="Back to security" onCancel={() => setVerifyingEmail(false)}
                onComplete={() => { setVerifyingEmail(false); void refresh(); }} />
            </div> :
            <button type="button" className="ghost-btn" disabled={busy}
              onClick={() => setVerifyingEmail(true)}>{t("Verify account email")}</button>)}
          <p className="microcopy">{t("MFA enrollment, recovery-code management and provider linking require a proven device session. Use Android Security; a Web login alone cannot authorize these changes.")}</p>
        </>}
      </article>
      <article className="card surface-card" id="devices">
        <h2>{t("Devices")}</h2>
        {deviceActionError && <p className="status-message" role="alert">{t(deviceActionError)}</p>}
        {status ? <p>{t(status)}</p> : data.state === 'READY' && <>
          {data.devices.length ? <ul className="product-list">{data.devices.map(device => <li key={device.device_id}>
            <div className="row-between"><strong>{device.platform}</strong><span className="state">{device.state === 'ACTIVE' ? t("Registered") : device.state === 'SUSPENDED' ? t("Suspended") : t("Revoked")}</span></div>
            <span className="microcopy">{t("Device ID:")}{' '}{device.device_id}</span>
            <span className="muted">{t("Registered")}{' '}{new Date(device.bound_at).toLocaleString(locale === 'ru' ? 'ru-RU' : 'en-US')}</span>
            <span className="microcopy">{device.last_seen_at ? `${t("Last seen")} ${new Date(device.last_seen_at).toLocaleString(locale === 'ru' ? 'ru-RU' : 'en-US')}` : t("No activity recorded yet")}</span>
            {device.state !== 'REVOKED' && (confirmDevice?.id === device.device_id ? (
              <div className="device-revoke-confirm" role="group" aria-label={t(confirmDevice.action === "revoke" ? "Confirm device revocation" : "Confirm device suspension")}>
                <p className="microcopy">{t(confirmDevice.action === "revoke" ? "Revoking a device terminates its sessions. You may need to sign in again on that device." : "Suspending a device ends its sessions and blocks device access. Restoring access requires a separate verified process.")}</p>
                <div className="button-row">
                  <button type="button" className="ghost-btn" disabled={busy} onClick={() => void changeDevice(device.device_id, confirmDevice.action)}>
                    {t(confirmDevice.action === "revoke" ? "Confirm revoke" : "Confirm suspension")}
                  </button>
                  <button type="button" className="text-btn" disabled={busy} onClick={() => setConfirmDevice(null)}>
                    {t("Cancel")}
                  </button>
                </div>
              </div>
            ) : (
              <div className="button-row">
                {device.state === 'ACTIVE' && <button type="button" className="text-btn" disabled={busy} onClick={() => {
                  setConfirmDevice({ id: device.device_id, action: 'suspend' }); setDeviceActionError('');
                }}>{t("Suspend device")}</button>}
                <button type="button" className="text-btn" disabled={busy} onClick={() => {
                  setConfirmDevice({ id: device.device_id, action: 'revoke' }); setDeviceActionError('');
                }}>{t("Revoke device")}</button>
              </div>
            ))}

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
