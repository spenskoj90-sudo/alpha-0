import { AccountControl } from './components/account-control';
import { RecommendationPanel } from './components/recommendation-panel';

export default function Dashboard() {
  return (
    <>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <main id="main-content" className="shell" tabIndex={-1}>
        <header className="top">
          <div>
            <h1 className="brand">SENTINEL</h1>
            <div className="label">PERSONAL CONTROL PLANE</div>
          </div>
          <div className="top-actions" aria-label="Control plane navigation">
            <a className="badge" href="/admin">ADMIN CONTROL</a>
            <span className="badge">SECURITY FIRST / DEFAULT DENY</span>
          </div>
        </header>

        <AccountControl />

        <section className="section recommendation-section" aria-labelledby="intelligence-title">
          <h2 id="intelligence-title" className="sr-only">Intelligence and runtime boundary</h2>
          <RecommendationPanel />
          <article className="card" aria-labelledby="runtime-boundary-title">
            <div className="label">RUNTIME BOUNDARY</div>
            <h3 id="runtime-boundary-title" className="sr-only">Runtime authority boundaries</h3>
            <div className="item"><span className="ok" aria-hidden="true">●</span> Billing state comes from Core</div>
            <div className="item"><span className="ok" aria-hidden="true">●</span> Game entitlements are server-authoritative</div>
            <div className="item"><span className="ok" aria-hidden="true">●</span> Recommendation retrieval uses the authenticated Core boundary</div>
            <div className="item"><span className="info" aria-hidden="true">●</span> Provider activation is external</div>
            <div className="item"><span className="info" aria-hidden="true">●</span> Recommendation output remains observational</div>
          </article>
        </section>
      </main>
    </>
  );
}
