'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';

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
  problem_group_id?: string | null;
  inferred_severity?: string | null;
  related_report_count?: number | null;
  diagnostics_consent: boolean;
  quality_program_opt_in: boolean;
  diagnostics_retained: boolean;
  diagnostics_bytes: number;
  diagnostics_expires_at: string | null;
  created_at: string;
  updated_at: string;
  diagnostics?: unknown;
};

type QualityCluster = {
  id: string;
  fingerprint: string;
  signature_kind: 'DIAGNOSTIC' | 'TEXT';
  category: string;
  canonical_title: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  severity_locked: boolean;
  status: 'RECEIVED' | 'TRIAGED' | 'IN_PROGRESS' | 'RESOLVED' | 'WONT_FIX';
  priority_score: number;
  occurrence_count: number;
  affected_user_count: number;
  affected_device_count: number;
  affected_version_count: number;
  first_seen_at: string;
  last_seen_at: string;
  last_app_version: string | null;
  last_source_sha: string | null;
  merged_into_id: string | null;
  reports?: QualityReport[];
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
  const [qualityClusters, setQualityClusters] = useState<QualityCluster[]>([]);
  const [selectedReport, setSelectedReport] = useState<QualityReport | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<QualityCluster | null>(null);
  const [clusterStatusFilter, setClusterStatusFilter] = useState('ALL');
  const [clusterSeverityFilter, setClusterSeverityFilter] = useState('ALL');
  const [clusterCategoryFilter, setClusterCategoryFilter] = useState('ALL');
  const [mergeTarget, setMergeTarget] = useState('');
  const [status, setStatus] = useState('TOKEN REQUIRED');
  const [busy, setBusy] = useState(false);

  const visibleClusters = useMemo(() => qualityClusters.filter(cluster =>
    (clusterStatusFilter === 'ALL' || cluster.status === clusterStatusFilter)
    && (clusterSeverityFilter === 'ALL' || cluster.severity === clusterSeverityFilter)
    && (clusterCategoryFilter === 'ALL' || cluster.category === clusterCategoryFilter)
  ), [qualityClusters, clusterStatusFilter, clusterSeverityFilter, clusterCategoryFilter]);

  async function loadControlData() {
    if (!token) {
      setStatus('ADMIN TOKEN REQUIRED');
      return;
    }
    setBusy(true);
    setStatus('LOADING');
    try {
      const headers = { 'x-sentinel-admin-token': token };
      const [gamesResponse, entitlementsResponse, qualityResponse, clustersResponse] = await Promise.all([
        fetch('/api/admin/games', { headers, cache: 'no-store' }),
        fetch('/api/admin/entitlements', { headers, cache: 'no-store' }),
        fetch('/api/admin/quality?limit=100', { headers, cache: 'no-store' }),
        fetch('/api/admin/quality/clusters?limit=100', { headers, cache: 'no-store' }),
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
      if (!clustersResponse.ok) {
        setStatus(`QUALITY INTELLIGENCE DENIED (${clustersResponse.status})`);
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
      const clusterPayload = await readJson<{ clusters: QualityCluster[] }>(clustersResponse);
      setQualityClusters(clusterPayload?.clusters ?? []);
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

  async function inspectQualityCluster(clusterId: string) {
    if (!token) return;
    setBusy(true);
    setStatus('LOADING PROBLEM GROUP');
    try {
      const response = await fetch(`/api/admin/quality/clusters/${encodeURIComponent(clusterId)}`, {
        headers: { 'x-sentinel-admin-token': token },
        cache: 'no-store',
      });
      if (!response.ok) {
        setStatus(`PROBLEM GROUP DENIED (${response.status})`);
        return;
      }
      const payload = await readJson<{ cluster: QualityCluster }>(response);
      setSelectedCluster(payload?.cluster ?? null);
      setMergeTarget('');
      setStatus('PROBLEM GROUP LOADED');
    } finally {
      setBusy(false);
    }
  }

  async function updateQualityCluster(clusterId: string, change: { status?: QualityCluster['status']; severity?: QualityCluster['severity'] }) {
    if (!token) return;
    setBusy(true);
    setStatus('UPDATING PROBLEM GROUP');
    try {
      const response = await fetch(`/api/admin/quality/clusters/${encodeURIComponent(clusterId)}`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-sentinel-admin-token': token },
        body: JSON.stringify(change),
      });
      if (!response.ok) {
        setStatus(`PROBLEM GROUP UPDATE DENIED (${response.status})`);
        return;
      }
      const payload = await readJson<{ cluster: QualityCluster }>(response);
      if (payload?.cluster) {
        setSelectedCluster(current => current?.id === clusterId ? { ...current, ...payload.cluster } : current);
        setQualityClusters(current => current.map(item => item.id === clusterId ? { ...item, ...payload.cluster } : item)
          .sort((a, b) => b.priority_score - a.priority_score || Date.parse(b.last_seen_at) - Date.parse(a.last_seen_at)));
      }
      setStatus('PROBLEM GROUP UPDATED');
    } finally {
      setBusy(false);
    }
  }

  async function mergeQualityCluster(sourceId: string, targetId: string) {
    if (!token || !targetId || sourceId === targetId) return;
    setBusy(true);
    setStatus('MERGING CONFIRMED PROBLEM GROUPS');
    try {
      const response = await fetch(`/api/admin/quality/clusters/${encodeURIComponent(sourceId)}/merge`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-sentinel-admin-token': token },
        body: JSON.stringify({ target_cluster_id: targetId }),
      });
      if (!response.ok) {
        setStatus(`PROBLEM GROUP MERGE DENIED (${response.status})`);
        return;
      }
      const payload = await readJson<{ cluster: QualityCluster }>(response);
      if (payload?.cluster) {
        setQualityClusters(current => current.filter(item => item.id !== sourceId).map(item => item.id === targetId ? { ...item, ...payload.cluster } : item));
        setSelectedCluster(payload.cluster);
        setMergeTarget('');
      }
      setStatus('PROBLEM GROUPS MERGED');
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
        <div className="label">QUALITY PROBLEM GROUPS · PRIORITY QUEUE</div>
        <p className="boundary-copy">Operational triage happens at the problem-group level. Duplicate reports remain preserved evidence while frequency, user breadth, affected versions and severity drive priority.</p>
        <div className="top-actions">
          <select aria-label="Problem group status filter" value={clusterStatusFilter} onChange={event => setClusterStatusFilter(event.target.value)}>
            {['ALL', 'RECEIVED', 'TRIAGED', 'IN_PROGRESS', 'RESOLVED', 'WONT_FIX'].map(value => <option key={value} value={value}>{value}</option>)}
          </select>
          <select aria-label="Problem group severity filter" value={clusterSeverityFilter} onChange={event => setClusterSeverityFilter(event.target.value)}>
            {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(value => <option key={value} value={value}>{value}</option>)}
          </select>
          <select aria-label="Problem group category filter" value={clusterCategoryFilter} onChange={event => setClusterCategoryFilter(event.target.value)}>
            {['ALL', 'DESIGN', 'FUNCTIONALITY', 'GAME_INTEGRATION', 'PERFORMANCE', 'ACCESSIBILITY', 'VOICE_AUDIO', 'SECURITY_PRIVACY', 'OTHER'].map(value => <option key={value} value={value}>{value}</option>)}
          </select>
        </div>
        {visibleClusters.length === 0 && <p className="muted">No problem groups match the current filters.</p>}
        {visibleClusters.map(cluster => <div className="item" key={cluster.id}>
          <div className="row-between">
            <strong>{cluster.canonical_title}</strong>
            <span className="state">P{cluster.priority_score} · {cluster.severity}</span>
          </div>
          <div className="muted">{cluster.category} · {cluster.status} · {cluster.signature_kind.toLowerCase()} fingerprint</div>
          <div className="microcopy">{cluster.occurrence_count} reports · {cluster.affected_user_count} users · {cluster.affected_device_count} devices · {cluster.affected_version_count} versions · last seen {new Date(cluster.last_seen_at).toLocaleString()}</div>
          <button className="ghost-btn" onClick={() => void inspectQualityCluster(cluster.id)} disabled={busy || !token}>TRIAGE GROUP</button>
        </div>)}
      </article>

      {selectedCluster && <article className="card entitlement-card">
        <div className="label">PROBLEM GROUP DETAIL</div>
        <div className="row-between"><strong>{selectedCluster.canonical_title}</strong><span className="state">P{selectedCluster.priority_score} · {selectedCluster.severity}</span></div>
        <div className="muted">{selectedCluster.category} · {selectedCluster.status} · fingerprint {selectedCluster.fingerprint.slice(0, 12)}…</div>
        <div className="microcopy">Frequency: {selectedCluster.occurrence_count} reports · breadth: {selectedCluster.affected_user_count} users / {selectedCluster.affected_device_count} devices · versions: {selectedCluster.affected_version_count} · first {new Date(selectedCluster.first_seen_at).toLocaleString()} · last {new Date(selectedCluster.last_seen_at).toLocaleString()}</div>
        <div className="top-actions">
          {(['TRIAGED', 'IN_PROGRESS', 'RESOLVED', 'WONT_FIX'] as const).map(nextStatus =>
            <button className="ghost-btn" key={nextStatus} onClick={() => void updateQualityCluster(selectedCluster.id, { status: nextStatus })} disabled={busy || !token || selectedCluster.status === nextStatus}>{nextStatus}</button>
          )}
        </div>
        <div className="label field-gap">SEVERITY OVERRIDE</div>
        <div className="top-actions">
          {(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const).map(nextSeverity =>
            <button className="ghost-btn" key={nextSeverity} onClick={() => void updateQualityCluster(selectedCluster.id, { severity: nextSeverity })} disabled={busy || !token || selectedCluster.severity === nextSeverity}>{nextSeverity}</button>
          )}
        </div>
        <div className="label field-gap">MERGE CONFIRMED DUPLICATE</div>
        <p className="boundary-copy">Merge is manual because fuzzy similarity is evidence, not permission to collapse distinct defects. All source reports are reassigned to the target group.</p>
        <select value={mergeTarget} onChange={event => setMergeTarget(event.target.value)}>
          <option value="">Select target group</option>
          {qualityClusters.filter(item => item.id !== selectedCluster.id).map(item =>
            <option key={item.id} value={item.id}>P{item.priority_score} · {item.severity} · {item.canonical_title}</option>
          )}
        </select>
        <button className="ghost-btn" onClick={() => void mergeQualityCluster(selectedCluster.id, mergeTarget)} disabled={busy || !token || !mergeTarget}>MERGE INTO TARGET</button>
        {selectedCluster.reports && selectedCluster.reports.length > 0 && <details>
          <summary>Member reports ({selectedCluster.reports.length} shown)</summary>
          {selectedCluster.reports.map(report => <div className="item" key={report.id}>
            <div className="row-between"><strong>{report.title}</strong><span className="state">{report.status}</span></div>
            <div className="muted">{new Date(report.created_at).toLocaleString()} · {report.inferred_severity ?? 'severity n/a'}</div>
            <button className="ghost-btn" onClick={() => void inspectQualityReport(report.id)} disabled={busy || !token}>INSPECT EVIDENCE</button>
          </div>)}
        </details>}
      </article>}

      <article className="card entitlement-card">
        <div className="label">INDIVIDUAL QUALITY REPORTS · EVIDENCE QUEUE</div>
        <p className="boundary-copy">Individual reports stay available for evidence inspection and exceptional per-report handling. Routine prioritization should use problem groups above.</p>
        {qualityReports.length === 0 && <p className="muted">No quality reports loaded.</p>}
        {qualityReports.map(report => <div className="item" key={report.id}>
          <div className="row-between"><strong>{report.title}</strong><span className="state">{report.status}</span></div>
          <div className="muted">{report.category} · {report.inferred_severity ?? 'unscored'} · {new Date(report.created_at).toLocaleString()}</div>
          <div className="microcopy">Group: {report.problem_group_id ?? 'none'} · diagnostics {report.diagnostics_retained ? `${Math.ceil(report.diagnostics_bytes / 1024)} KiB retained` : 'not retained'} · quality program {report.quality_program_opt_in ? 'opt-in' : 'support only'}</div>
          <button className="ghost-btn" onClick={() => void inspectQualityReport(report.id)} disabled={busy || !token}>INSPECT REPORT</button>
        </div>)}
      </article>

      {selectedReport && <article className="card entitlement-card">
        <div className="label">QUALITY REPORT DETAIL</div>
        <div className="row-between"><strong>{selectedReport.title}</strong><span className="state">{selectedReport.status}</span></div>
        <p>{selectedReport.description}</p>
        <div className="muted">Category: {selectedReport.category} · Severity: {selectedReport.inferred_severity ?? 'n/a'} · Group: {selectedReport.problem_group_id ?? 'none'} · User: {selectedReport.user_id ?? 'not exposed'} · Device: {selectedReport.device_id ?? 'none'}</div>
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
