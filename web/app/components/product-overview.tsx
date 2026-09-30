'use client';

import { useEffect, useRef, useState } from 'react';
import { loadProductData, type ProductData } from './product-data';

export function ProductOverview() {
  const [data, setData] = useState<ProductData>({ state: 'SIGNED_OUT' });
  const [busy, setBusy] = useState(false);
  const generation = useRef(0);

  useEffect(() => {
    const revisions = generation;
    let active = true;
    const update = async (event: Event) => {
      const revision = ++generation.current;
      if (!(event as CustomEvent<boolean>).detail) {
        setData({ state: 'SIGNED_OUT' });
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
    <section className="surface-grid" aria-label="Control plane surfaces" aria-busy={busy}>
      <article className="card surface-card" id="games">
        <h2>Games</h2>
        {status ? <p role={data.state === 'ERROR' ? 'alert' : 'status'}>{status}</p> : data.state === 'READY' && (
          data.games.length ? <ul className="product-list">{data.games.map(game => <li key={game.id}>
            <strong>{game.name}</strong><span className="muted">{game.family} · {game.platform}</span>
            <span className="microcopy">{game.interaction_mode.replaceAll('_', ' ')}</span>
          </li>)}</ul> : <p>No games are available in the current catalog.</p>
        )}
        <button className="ghost-btn" disabled={busy} onClick={() => void refresh()}>Refresh product data</button>
      </article>
      <article className="card surface-card" id="security">
        <h2>Security</h2>
        {status ? <p>{status}</p> : data.state === 'READY' && <dl className="product-facts">
          <div><dt>Email</dt><dd>{data.security.email_verified ? 'Verified' : 'Verification pending'}</dd></div>
          <div><dt>Password</dt><dd>{data.security.password_enabled ? 'Enabled' : 'Not enabled'}</dd></div>
          <div><dt>Two-factor authentication</dt><dd>{data.security.mfa_enabled ? 'Enabled' : 'Not enabled'}</dd></div>
          <div><dt>Recovery codes remaining</dt><dd>{data.security.mfa_recovery_codes_remaining}</dd></div>
          <div><dt>Linked providers</dt><dd>{data.security.providers.join(', ') || 'None linked'}</dd></div>
        </dl>}
      </article>
      <article className="card surface-card" id="activity">
        <h2>Activity</h2>
        {status ? <p>{status}</p> : data.state === 'READY' && (
          data.events.length ? <ol className="product-list">{data.events.map((event, i) => <li key={i}>
            <div className="row-between"><strong>{event.action}</strong><span className="state">{event.decision}</span></div>
            <span className="muted">{event.reason_code.replaceAll('_', ' ')} · {event.resource}</span>
            {event.created_at && <time className="microcopy" dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time>}
          </li>)}</ol> : <p>No account activity has been recorded.</p>
        )}
      </article>
    </section>
  );
}
