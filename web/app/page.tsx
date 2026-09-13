import { AccountControl } from './components/account-control';
import { RecommendationPanel } from './components/recommendation-panel';

export default function Dashboard() {
  return (
    <main className="shell">
      <header className="top">
        <div>
          <div className="brand">SENTINEL</div>
          <div className="label">PERSONAL CONTROL PLANE</div>
        </div>
        <div className="top-actions">
          <a className="badge" href="/admin">ADMIN CONTROL</a>
          <span className="badge">SECURITY FIRST / DEFAULT DENY</span>
        </div>
      </header>

      <AccountControl />

      <section className="section recommendation-section">
        <RecommendationPanel />
        <article className="card">
          <div className="label">RUNTIME BOUNDARY</div>
          <div className="item"><span className="ok">●</span> Billing state comes from Core</div>
          <div className="item"><span className="ok">●</span> Game entitlements are server-authoritative</div>
          <div className="item"><span className="info">●</span> Provider activation is external</div>
          <div className="item"><span className="info">●</span> Recommendation card remains observational</div>
        </article>
      </section>
    </main>
  );
}
