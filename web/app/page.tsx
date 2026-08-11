const metrics = [
  ["DEVICE", "ACTIVE", "ok"],
  ["SESSION", "12h", "info"],
  ["ENTITLEMENT", "CORE", "ok"],
  ["SYNC QUEUE", "0", "ok"],
] as const;

export default function Dashboard() {
  return (
    <main className="shell">
      <header className="top">
        <div><div className="brand">SENTINEL</div><div className="label">PERSONAL CONTROL PLANE</div></div>
        <div className="badge">SECURITY FIRST / DEFAULT DENY</div>
      </header>
      <section className="grid">
        {metrics.map(([label, value, tone]) => <article className="card" key={label}><div className="label">{label}</div><div className={`value ${tone}`}>{value}</div></article>)}
      </section>
      <section className="section">
        <article className="card">
          <div className="label">CHARACTER</div>
          <h2>Operator</h2>
          <div className="item"><span className="label">LEVEL</span><strong> 27</strong></div>
          <div className="item"><span className="label">HEALTH</span><strong> 94%</strong></div>
          <div className="item"><span className="label">LAST EVENT</span><strong> 2 min ago</strong></div>
        </article>
        <article className="card">
          <div className="label">SECURITY</div>
          <div className="item"><span className="ok">●</span> Device key active</div>
          <div className="item"><span className="ok">●</span> Replay protection active</div>
          <div className="item"><span className="ok">●</span> Audit trail enabled</div>
          <div className="item"><span className="info">●</span> No pending actions</div>
        </article>
      </section>
    </main>
  );
}
