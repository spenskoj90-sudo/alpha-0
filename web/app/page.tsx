import { AccountControl } from './components/account-control';
import { BrandMark } from './components/brand-mark';
import { RecommendationPanel } from './components/recommendation-panel';

export default function Dashboard() {
  return (
    <>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <div className="product-shell">
        <aside className="side-nav" aria-label="SENTINEL navigation">
          <div className="brand-lockup">
            <BrandMark className="brand-mark" />
            <div>
              <div className="brand">SENTINEL</div>
              <div className="brand-caption">Security instrumentation</div>
            </div>
          </div>
          <nav className="nav-list">
            <a className="nav-item nav-item-active" href="#main-content">Overview</a>
            <a className="nav-item" href="#account">Account</a>
            <a className="nav-item" href="#access">Access</a>
            <a className="nav-item" href="#intelligence">Intelligence</a>
          </nav>
          <div className="nav-footer">
            <a className="utility-link" href="/admin">Privileged admin utility</a>
            <span className="microcopy">Server-authoritative state</span>
          </div>
        </aside>

        <main id="main-content" className="dashboard-main" tabIndex={-1}>
          <header className="page-header">
            <div>
              <h1>Overview</h1>
              <p>Security and access state from authoritative SENTINEL services.</p>
            </div>
          </header>

          <section id="account" aria-label="Account and access">
            <AccountControl />
          </section>

          <section id="intelligence" className="section recommendation-section" aria-labelledby="intelligence-title">
            <div>
              <h2 id="intelligence-title" className="section-title">Intelligence</h2>
              <RecommendationPanel />
            </div>
            <article className="card boundary-card" aria-labelledby="runtime-boundary-title">
              <h2 id="runtime-boundary-title" className="section-title">Authority boundary</h2>
              <div className="item"><span className="status-dot status-success" aria-hidden="true">✓</span> Billing state comes from Core</div>
              <div className="item"><span className="status-dot status-success" aria-hidden="true">✓</span> Game entitlements are server-authoritative</div>
              <div className="item"><span className="status-dot status-active" aria-hidden="true">●</span> Recommendation retrieval uses the authenticated Core boundary</div>
              <div className="item"><span className="status-dot status-warning" aria-hidden="true">!</span> Provider activation may depend on external configuration</div>
              <div className="item"><span className="status-dot status-active" aria-hidden="true">●</span> Recommendation output remains observational</div>
            </article>
          </section>
        </main>
      </div>
    </>
  );
}
