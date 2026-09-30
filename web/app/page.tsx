import { AccountControl } from './components/account-control';
import { AppearanceToggle } from './components/appearance-toggle';
import { BrandMark } from './components/brand-mark';
import { RecommendationPanel } from './components/recommendation-panel';
import { ProductOverview } from './components/product-overview';

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
              <div className="brand-caption">Trusted intelligence control plane</div>
            </div>
          </div>
          <nav className="nav-list">
            <a className="nav-item nav-item-active" href="#main-content">Overview</a>
            <a className="nav-item" href="#intelligence">Intelligence</a>
            <a className="nav-item" href="#games">Games</a>
            <a className="nav-item" href="#activity">Activity</a>
            <a className="nav-item" href="#security">Security</a>
            <a className="nav-item" href="#devices">Devices</a>
            <a className="nav-item" href="#account">Account</a>
            <a className="nav-item" href="#account">Subscription</a>
            <a className="nav-item" href="#settings">Settings</a>
            <a className="nav-item" href="#support">Support</a>
            <a className="nav-item" href="#account">Billing</a>
          </nav>
          <div className="nav-footer">
            <a className="utility-link" href="/admin">Privileged admin utility</a>
            <span className="microcopy">Server-authoritative state</span>
          </div>
        </aside>

        <main id="main-content" className="dashboard-main" tabIndex={-1}>
          <header className="page-header">
            <div>
              <div className="eyebrow">CONTROL PLANE / OVERVIEW</div>
              <h1>Overview</h1>
              <p>Calm, explicit security and intelligence state. Missing data is never rendered as healthy or zero.</p>
            </div>
            <div className="top-actions">
              <AppearanceToggle />
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
              <div className="item"><span className="status-dot status-active" aria-hidden="true">●</span> Intelligence retrieval uses the authenticated Core boundary</div>
              <div className="item"><span className="status-dot status-warning" aria-hidden="true">!</span> Missing provider data remains explicit</div>
              <div className="item"><span className="status-dot status-active" aria-hidden="true">●</span> Intelligence output remains observational</div>
            </article>
          </section>

          <ProductOverview />

          <section className="surface-grid" aria-label="Control plane surfaces">
            <article className="card surface-card" id="settings">
              <h2>Settings</h2>
              <p className="muted">Choose System, Dark or Light. Your preference is saved on this browser.</p>
              <AppearanceToggle />
            </article>
            <article className="card surface-card" id="support">
              <h2>Support</h2>
              <p className="muted">Review service status and privacy guidance, or download the Web build identity when reporting a problem.</p>
              <ul className="product-list">
                <li><a href="https://sentinel-public-site-staging.onrender.com/status">Service status</a></li>
                <li><a href="https://sentinel-public-site-staging.onrender.com/privacy">Privacy and data handling</a></li>
                <li><a href="/api/health" download="sentinel-web-diagnostics.json">Download Web build diagnostics</a></li>
              </ul>
              <p className="microcopy">Build diagnostics contain no account data, cookies or credentials.</p>
            </article>
          </section>
        </main>
      </div>
    </>
  );
}
