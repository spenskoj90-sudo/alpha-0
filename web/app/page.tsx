'use client';

import { AccountControl } from './components/account-control';
import { useLocale, LanguageSwitch } from './components/locale-provider';
import { AppearanceToggle } from './components/appearance-toggle';
import { BrandMark } from './components/brand-mark';
import { RecommendationPanel } from './components/recommendation-panel';
import { ProductNavigation } from './components/product-navigation';
import { ProductOverview } from './components/product-overview';

export default function Dashboard() {
  const { t } = useLocale();
  return (
    <>
      <a className="skip-link" href="#main-content">{t("Skip to main content")}</a>
      <div className="product-shell">
        <aside className="side-nav" aria-label={t("SENTINEL navigation")}>
          <div className="brand-lockup">
            <BrandMark className="brand-mark" />
            <div>
              <div className="brand">SENTINEL</div>
              <div className="brand-caption">{t("Trusted intelligence control plane")}</div>
            </div>
          </div>
          <ProductNavigation />
          <div className="nav-footer">
            <a className="utility-link" href="/admin">{t("Privileged admin utility")}</a>
            <span className="microcopy">{t("Server-authoritative state")}</span>
          </div>
        </aside>

        <main id="main-content" className="dashboard-main" tabIndex={-1}>
          <header className="page-header">
            <div>
              <div className="eyebrow">{t("CONTROL PLANE / OVERVIEW")}</div>
              <h1>{t("Overview")}</h1>
              <p>{t("Your account, security and connected runtime in one place.")}</p>
            </div>
            <div className="top-actions">
              <LanguageSwitch />
              <AppearanceToggle />
            </div>
          </header>

          <section id="account" aria-label={t("Account and access")}>
            <AccountControl />
          </section>

          <section id="intelligence" className="section recommendation-section" aria-labelledby="intelligence-title">
            <div>
              <h2 id="intelligence-title" className="section-title">{t("Intelligence")}</h2>
              <RecommendationPanel />
            </div>
            <article className="card boundary-card" aria-labelledby="runtime-boundary-title">
              <h2 id="runtime-boundary-title" className="section-title">{t("You stay in control")}</h2>
              <div className="item"><span className="status-dot status-success" aria-hidden="true">✓</span>{' '}{t("Billing state comes from Core")}</div>
              <div className="item"><span className="status-dot status-success" aria-hidden="true">✓</span>{' '}{t("Game entitlements are server-authoritative")}</div>
              <div className="item"><span className="status-dot status-active" aria-hidden="true">●</span>{' '}{t("Intelligence retrieval uses the authenticated Core boundary")}</div>
              <div className="item"><span className="status-dot status-warning" aria-hidden="true">!</span>{' '}{t("Missing provider data remains explicit")}</div>
              <div className="item"><span className="status-dot status-active" aria-hidden="true">●</span>{' '}{t("Intelligence output remains observational")}</div>
            </article>
          </section>

          <ProductOverview />

          <section className="surface-grid" aria-label={t("Control plane surfaces")}>
            <article className="card surface-card" id="settings">
              <h2>{t("Settings")}</h2>
              <p className="muted">{t("Choose System, Dark or Light. Your preference is saved on this browser.")}</p>
              <AppearanceToggle />
            </article>
            <article className="card surface-card" id="support">
              <h2>{t("Support")}</h2>
              <p className="muted">{t("Review service status and privacy guidance, or download the Web build identity when reporting a problem.")}</p>
              <ul className="product-list">
                <li><a href="https://sentinel-public-site-staging.onrender.com/status">{t("Service status")}</a></li>
                <li><a href="https://sentinel-public-site-staging.onrender.com/privacy">{t("Privacy and data handling")}</a></li>
                <li><a href="/api/health" download="sentinel-web-diagnostics.json">{t("Download Web build diagnostics")}</a></li>
              </ul>
              <p className="microcopy">{t("Build diagnostics contain no account data, cookies or credentials.")}</p>
            </article>
          </section>
        </main>
      </div>
    </>
  );
}
