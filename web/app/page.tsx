const games = [
  ['Diablo', 'Windows', 'diablo-1-pc'],
  ['Diablo II', 'Windows', 'diablo-2-pc'],
  ['Diablo II: Resurrected', 'Windows', 'diablo-2-resurrected-pc'],
  ['Diablo III', 'Windows', 'diablo-3-pc'],
  ['Diablo IV', 'Windows', 'diablo-4-pc'],
  ['Diablo Immortal', 'Android', 'diablo-immortal-android'],
] as const;

export default function Dashboard() {
  return (
    <main className="shell">
      <header className="top">
        <div><div className="brand">SENTINEL</div><div className="label">PERSONAL CONTROL PLANE</div></div>
        <div><a className="badge" href="/admin">ADMIN CONTROL</a> <span className="badge">SECURITY FIRST / DEFAULT DENY</span></div>
      </header>
      <section className="grid">
        {[["DEVICE", "ACTIVE", "ok"], ["SESSION", "12h", "info"], ["ENTITLEMENT", "SERVER-AUTH", "ok"], ["SYNC QUEUE", "0", "ok"]].map(([label, value, tone]) => <article className="card" key={label}><div className="label">{label}</div><div className={`value ${tone}`}>{value}</div></article>)}
      </section>
      <section className="section">
        <article className="card"><div className="label">SUPPORTED DIABLO CATALOG</div>{games.map(([name, platform, id]) => <div className="item" key={id}><strong>{name}</strong><span className="label"> {platform} · {id}</span></div>)}</article>
        <article className="card"><div className="label">SECURITY</div><div className="item"><span className="ok">●</span> Device key active</div><div className="item"><span className="ok">●</span> Replay protection active</div><div className="item"><span className="ok">●</span> Server authorization active</div><div className="item"><span className="info">●</span> Audit trail enabled</div></article>
      </section>
    </main>
  );
}
