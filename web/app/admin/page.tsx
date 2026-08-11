'use client';

import { useState } from 'react';

const games = [
  ['diablo-1-pc', 'Diablo', 'Windows'],
  ['diablo-2-pc', 'Diablo II', 'Windows'],
  ['diablo-2-resurrected-pc', 'Diablo II: Resurrected', 'Windows'],
  ['diablo-3-pc', 'Diablo III', 'Windows'],
  ['diablo-4-pc', 'Diablo IV', 'Windows'],
  ['diablo-immortal-android', 'Diablo Immortal', 'Android'],
];

export default function AdminPage() {
  const [token, setToken] = useState('');
  const [userId, setUserId] = useState('');
  const [gameId, setGameId] = useState(games[0][0]);
  const [status, setStatus] = useState('READY');

  async function grant() {
    setStatus('PROCESSING');
    const response = await fetch('/api/admin/entitlements', {
      method: 'POST', headers: { 'content-type': 'application/json', 'x-sentinel-admin-token': token },
      body: JSON.stringify({ user_id: userId, game_id: gameId, source: 'admin', valid_from: new Date().toISOString(), valid_until: new Date(Date.now() + 30 * 86400000).toISOString() }),
    });
    setStatus(response.ok ? 'ENTITLEMENT GRANTED' : `DENIED (${response.status})`);
  }

  return <main className="shell"><header className="top"><div><div className="brand">SENTINEL ADMIN</div><div className="label">SECURITY CONTROL PLANE</div></div><div className="badge">FAIL-CLOSED</div></header><section className="section"><article className="card"><div className="label">ADMIN TOKEN</div><input value={token} onChange={e => setToken(e.target.value)} type="password" placeholder="Environment-issued token" /><div className="label" style={{marginTop:20}}>USER</div><input value={userId} onChange={e => setUserId(e.target.value)} placeholder="User ID" /><div className="label" style={{marginTop:20}}>GAME</div><select value={gameId} onChange={e => setGameId(e.target.value)}>{games.map(([id,name,platform]) => <option key={id} value={id}>{name} — {platform}</option>)}</select><button className="btn" onClick={grant}>GRANT 30-DAY ENTITLEMENT</button><div className="label" style={{marginTop:18}}>STATUS: {status}</div></article><article className="card"><div className="label">CATALOG</div>{games.map(([id,name,platform]) => <div className="item" key={id}><strong>{name}</strong><span className="label"> {platform}</span></div>)}</article></section></main>;
}
