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

type QualityReport = {
  id: string;
  user_id?: string;
  device_id?: string | null;
  category: string;
  title: string;
  description: string;
  status: string;
  diagnostics_consent: boolean;
  quality_program_opt_in: boolean;
  diagnostics_retained: boolean;
  diagnostics_bytes: number;
  diagnostics_expires_at: string | null;
  created_at: string;
  updated_at: string;
  diagnostics?: unknown;
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
  const [qualityReports, setQualityReports] = useState<QualityReport[]>([]);
  const [selectedReport, setSelectedReport] = useState<QualityReport | null>(null);
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
      const [gamesResponse, entitlementsResponse, qualityResponse] = await Promise.all([
        fetch('/api/admin/games', { headers, cache: 'no-store' }),
        fetch('/api/admin/entitlements', { headers, cache: 'no-store' }),
        fetch('/api/admin/quality?limit=100', { headers, cache: 'no-store' }),
      ]);
      if (!gamesResponse.ok) {
        setStatus(`CATALOG DENIED (${gamesResponse.status})`);
        return;
      }
      if (!entitlementsResponse.ok) {
        setStatus(`ENTITLEMENTS DENIED (${entitlementsResponse.status})`);
        return;
      }
      if (!qualityResponse.ok) {
        setStatus(`QUALITY QUEUE DENIED (${qualityResponse.status})`);
        return;
      }
      const gamePayload = await readJson<{ games: Game[] }>(gamesResponse);
      const loadedGames = gamePayload?.games ?? [];
      setGames(loadedGames);
      if (!gameId && loadedGames.length > 0) setGameId(loadedGames[0].id);

      const entitlementPayload = await readJson<{ entitlements: Entitlement[] }>(entitlementsResponse);
      setEntitlements(entitlementPayload?.entitlements ?? []);
      const qualityPayload = await readJson<{ reports: QualityReport[] }>(qualityResponse);
      setQualityReports(qualityPayload?.reports ?? []);
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

  async function inspectQualityReport(reportId: string) {
    if (!token) return;
    setBusy(true);
    setStatus('LOADING QUALITY EVIDENCE');
    try {
      const response = await fetch(`/api/admin/quality/${encodeURIComponent(reportId)}`, {
        headers: { 'x-sentinel-admin-token': token },
        cache: 'no-store',
      });
      if (!response.ok) {
        setStatus(`QUALITY REPORT DENIED (${response.status})`);
        return;
      }
      const payload = await readJson<{ report: QualityReport }>(response);
      setSelectedReport(payload?.report ?? null);
      setStatus('QUALITY REPORT LOADED');
    } finally {
      setBusy(false);
    }
  }

  async function updateQualityStatus(reportId: string, nextStatus: 'TRIAGED' | 'IN_PROGRESS' | 'RESOLVED' | 'WONT_FIX') {
    if (!token) return;
    setBusy(true);
    setStatus(`SETTING ${nextStatus}`);
    try {
      const response = await fetch(`/api/admin/quality/${encodeURIComponent(reportId)}`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-sentinel-admin-token': token },
        body: JSON.stringify({ status: nextStatus }),
      });
      if (!response.ok) {
        setStatus(`QUALITY STATUS DENIED (${response.status})`);
        return;
      }
      const payload = await readJson<{ report: QualityReport }>(response);
      if (payload?.report) {
        setSelectedReport(current => current?.id === reportId ? { ...current, ...payload.report } : current);
        setQualityReports(current => current.map(item => item.id === reportId ? { ...item, ...payload.report } : item));
      }
      setStatus(`QUALITY REPORT ${nextStatus}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <header className="top">
        <div><div className="brand">SENTINEL ADMIN</div><div className="label">SECURITY + QUALITY CONTROL PLANE</div></div>
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
          <div className="status-message" aria-live="polite">STATUS: {status}</div>
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

      <article className="card entitlement-card">
        <div className="label">QUALITY REPORT QUEUE</div>
        <p className="boundary-copy">User-submitted reports stay in the private Core support plane. Diagnostic snapshots are explicit-consent attachments and expire independently of the ticket.</p>
        {qualityReports.length === 0 && <p className="muted">No quality reports loaded.</p>}
        {qualityReports.map(report => <div className="item" key={report.id}>
          <div className="row-between"><strong>{report.title}</strong><span className="state">{report.status}</span></div>
          <div className="muted">{report.category} · {new Date(report.created_at).toLocaleString()}</div>
          <div className="microcopy">Diagnostics: {report.diagnostics_retained ? `${Math.ceil(report.diagnostics_bytes / 1024)} KiB retained` : 'not retained'} · quality program {report.quality_program_opt_in ? 'opt-in' : 'support only'}</div>
          <button className="ghost-btn" onClick={() => void inspectQualityReport(report.id)} disabled={busy || !token}>INSPECT REPORT</button>
        </div>)}
      </article>

      {selectedReport && <article className="card entitlement-card">
        <div className="label">QUALITY REPORT DETAIL</div>
        <div className="row-between"><strong>{selectedReport.title}</strong><span className="state">{selectedReport.status}</span></div>
        <p>{selectedReport.description}</p>
        <div className="muted">Category: {selectedReport.category} · User: {selectedReport.user_id ?? 'not exposed'} · Device: {selectedReport.device_id ?? 'none'}</div>
        <div className="microcopy">Diagnostics consent: {selectedReport.diagnostics_consent ? 'yes' : 'no'} · Quality program: {selectedReport.quality_program_opt_in ? 'opt-in' : 'support only'} · Expires: {selectedReport.diagnostics_expires_at ? new Date(selectedReport.diagnostics_expires_at).toLocaleString() : 'n/a'}</div>
        {selectedReport.diagnostics !== undefined && selectedReport.diagnostics !== null && <details>
          <summary>Sanitized diagnostic snapshot</summary>
          <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: '28rem', overflow: 'auto' }}>{JSON.stringify(selectedReport.diagnostics, null, 2)}</pre>
        </details>}
        <div className="top-actions">
          {(['TRIAGED', 'IN_PROGRESS', 'RESOLVED', 'WONT_FIX'] as const).map(nextStatus =>
            <button className="ghost-btn" key={nextStatus} onClick={() => void updateQualityStatus(selectedReport.id, nextStatus)} disabled={busy || !token || selectedReport.status === nextStatus}>{nextStatus}</button>
          )}
        </div>
      </article>}
    </main>
  );
}
