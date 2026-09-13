'use client';

import Link from 'next/link';
import { useState } from 'react';

type Game = {
  id: string;
  name: string;
  platform: string;
  family: string;
  versioning: string;
  launcher_supported: boolean;
  interaction_mode: string;
};

type Entitlement = {
  id: string;
  user_id: string;
  game_id: string;
  source: string;
  status: string;
  valid_from: string;
  valid_until: string;
};

async function readJson<T>(response: Response): Promise<T | null> {
  try { return await response.json() as T; } catch { return null; }
}

export default function AdminPage() {
  const [token, setToken] = useState('');
  const [userId, setUserId] = useState('');
  const [gameId, setGameId] = useState('');
  const [games, setGames] = useState<Game[]>([]);
  const [entitlements, setEntitlements] = useState<Entitlement[]>([]);
  const [status, setStatus] = useState('TOKEN REQUIRED');
  const [busy, setBusy] = useState(false);

  async function loadControlData() {
    if (!token) {
      setStatus('ADMIN TOKEN REQUIRED');
      return;
    }
    setBusy(true);
    setStatus('LOADING');
    try {
      const headers = { 'x-sentinel-admin-token': token };
      const gamesResponse = await fetch('/api/admin/games', { headers, cache: 'no-store' });
      if (!gamesResponse.ok) {
        setStatus(`CATALOG DENIED (${gamesResponse.status})`);
        return;
      }
      const gamePayload = await readJson<{ games: Game[] }>(gamesResponse);
      const loadedGames = gamePayload?.games ?? [];
      setGames(loadedGames);
      if (!gameId && loadedGames.length > 0) setGameId(loadedGames[0].id);

      const entitlementsResponse = await fetch('/api/admin/entitlements', { headers, cache: 'no-store' });
      if (!entitlementsResponse.ok) {
        setStatus(`ENTITLEMENTS DENIED (${entitlementsResponse.status})`);
        return;
      }
      const entitlementPayload = await readJson<{ entitlements: Entitlement[] }>(entitlementsResponse);
      setEntitlements(entitlementPayload?.entitlements ?? []);
      setStatus('CONTROL DATA LOADED');
    } finally {
      setBusy(false);
    }
  }

  async function grant() {
    if (!token || !userId || !gameId) {
      setStatus('TOKEN, USER AND GAME REQUIRED');
      return;
    }
    setBusy(true);
    setStatus('PROCESSING');
    try {
      const response = await fetch('/api/admin/entitlements', {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-sentinel-admin-token': token },
        body: JSON.stringify({
          user_id: userId,
          game_id: gameId,
          source: 'admin',
          valid_from: new Date().toISOString(),
          valid_until: new Date(Date.now() + 30 * 86_400_000).toISOString(),
        }),
      });
      if (!response.ok) {
        setStatus(`DENIED (${response.status})`);
        return;
      }
      setStatus('ENTITLEMENT GRANTED');
      await loadControlData();
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <header className="top">
        <div><div className="brand">SENTINEL ADMIN</div><div className="label">SECURITY CONTROL PLANE</div></div>
        <div className="top-actions"><Link className="badge" href="/">USER CONTROL</Link><div className="badge">FAIL-CLOSED</div></div>
      </header>

      <section className="section">
        <article className="card">
          <div className="label">ADMIN TOKEN</div>
          <input value={token} onChange={event => setToken(event.target.value)} type="password" autoComplete="off" placeholder="Environment-issued token" />
          <button className="ghost-btn" onClick={() => void loadControlData()} disabled={busy || !token}>LOAD CORE DATA</button>

          <div className="label field-gap">USER</div>
          <input value={userId} onChange={event => setUserId(event.target.value)} placeholder="User ID" />

          <div className="label field-gap">GAME</div>
          <select value={gameId} onChange={event => setGameId(event.target.value)} disabled={games.length === 0}>
            {games.length === 0 && <option value="">Load Core catalog first</option>}
            {games.map(game => <option key={game.id} value={game.id}>{game.name} — {game.platform}</option>)}
          </select>
          <button className="btn" onClick={() => void grant()} disabled={busy || !token || !userId || !gameId}>GRANT 30-DAY ENTITLEMENT</button>
          <div className="status-message">STATUS: {status}</div>
          <p className="boundary-copy">The admin token stays in this browser session only and is forwarded to the Core control-plane boundary. The Web server does not persist it.</p>
        </article>

        <article className="card">
          <div className="label">CORE GAME CATALOG</div>
          {games.length === 0 && <p className="muted">No catalog loaded.</p>}
          {games.map(game => <div className="item" key={game.id}>
            <strong>{game.name}</strong>
            <div className="muted">{game.platform} · {game.id}</div>
            <div className="microcopy">{game.interaction_mode} · launcher {game.launcher_supported ? 'supported' : 'not supported'}</div>
          </div>)}
        </article>
      </section>

      <article className="card entitlement-card">
        <div className="label">ENTITLEMENT READBACK</div>
        {entitlements.length === 0 && <p className="muted">No entitlement records loaded.</p>}
        {entitlements.map(item => <div className="item" key={item.id}>
          <div className="row-between"><strong>{item.game_id}</strong><span className="state">{item.status}</span></div>
          <div className="muted">User: {item.user_id} · Source: {item.source}</div>
          <div className="microcopy">Valid until {new Date(item.valid_until).toLocaleString()}</div>
        </div>)}
      </article>
    </main>
  );
}
