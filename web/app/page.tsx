import { AccountControl } from './components/account-control';
import { BrandMark } from './components/brand-mark';
import { RecommendationPanel } from './components/recommendation-panel';

const surfaces = [
  ['games', 'Games', 'Game catalog and capability state remain server-authoritative.'],
  ['activity', 'Activity', 'Operational and security activity is shown only when authoritative data is available.'],
  ['security', 'Security', 'MFA, sessions, provider links and recovery state stay inside the existing account-security boundary.'],
  ['devices', 'Devices', 'Device identity, proof and revocation state are not inferred from local browser state.'],
  ['subscription', 'Subscription', 'Subscription state comes from Core billing lifecycle data.'],
  ['billing', 'Billing', 'Billing mutations remain authenticated and provider-authoritative.'],
  ['settings', 'Settings', 'Presentation preferences never change server authorization semantics.'],
  ['support', 'Support', 'Support and diagnostics remain evidence-bound and privacy-scoped.'],
] as const;

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
            <a className="nav-item" href="#subscription">Subscription</a>
            <a className="nav-item" href="#settings">Settings</a>
            <a className="nav-item" href="#support">Support</a>
            <a className="nav-item" href="#billing">Billing</a>
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
              <p>Calm, explicit security and intelligence state. Missing data is never rendered as healthy or zero.</p>
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

          <section className="surface-grid" aria-label="Control plane surfaces">
            {surfaces.map(([id, title, description]) => (
              <article className="card surface-card" id={id} key={id}>
                <span className="surface-state">AUTHORITATIVE DATA ONLY</span>
                <h2>{title}</h2>
                <p className="muted">{description}</p>
              </article>
            ))}
          </section>
        </main>
      </div>
    </>
  );
}
