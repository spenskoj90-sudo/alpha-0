"use client";

import { useLocale } from "./components/locale-provider";
import Image from "next/image";
import Link from "next/link";
import { PublicFooter } from "./components/public-footer";
import { PublicHeader } from "./components/public-header";

export default function PublicHome() {
  const { t } = useLocale();
  const capabilities = [
    {
      eyebrow: t("INTELLIGENCE"),
      title: t("Know what a recommendation is based on."),
      body:
        t("See the source, freshness and confidence behind a recommendation. Facts and inference stay distinct, and uncertainty stays visible."),
    },
    {
      eyebrow: t("SECURITY"),
      title: t("Your account. Your control."),
      body:
        t("Review account security, connected devices and access in one place. Recommendations remain observational; SENTINEL does not turn them into hidden actions."),
    },
    {
      eyebrow: t("PLAYER EXPERIENCE"),
      title: t("One system across mobile, web and desktop."),
      body:
        t("Check context on your phone, manage your account on the Web, and connect the desktop Companion for overlay, diagnostics and voice workflows."),
    },
  ];

  const surfaces = [
    ["Android", t("Immediate context, security, games and activity"), t("IMPLEMENTED \u00b7 PHYSICAL ACCEPTANCE PENDING")],
    [t("Web Control Plane"), t("Account, intelligence, billing, devices and administration"), t("IMPLEMENTED \u00b7 UX CONSOLIDATION ACTIVE")],
    ["Windows Companion", t("Runtime, adapters, overlay, diagnostics and voice"), t("IMPLEMENTED \u00b7 HOST ACCEPTANCE PENDING")],
    [t("Game integration"), t("Conservative passive observation through explicit adapter boundaries"), t("WOW EXACT-ENVIRONMENT ACCEPTANCE PENDING")],
  ];

  return (
    <>
      <a className="skip-link" href="#main-content">{t("Skip to main content")}</a>
      <PublicHeader />
      <main id="main-content">
        <section className="hero" data-design-direction="CALM PRECISION / TRUSTED INTELLIGENCE">
          <div className="site-shell hero-grid">
            <div className="hero-copy">
              <div className="eyebrow">{t("PRE-RELEASE \u00b7 TRUSTED INTELLIGENCE")}</div>
              <h1>{t("A clearer view.")}<br />{t("You stay in control.")}</h1>
              <p className="hero-lead">{t("SENTINEL is being built to bring game context, account security and useful recommendations together across your phone, Web and desktop. Understand what is known, see where uncertainty remains, and choose your next step.")}</p>
              <div className="hero-actions">
                <a className="button-primary" href="#product">{t("Explore the product")}</a>
                <Link className="button-secondary" href="/status/">{t("View release status")}</Link>
              </div>
              <p className="release-note">{t("No public download is offered yet. Release testing is still in progress.")}</p>
            </div>
            <div className="hero-visual" aria-label={t("SENTINEL brand identity")}>
              <div className="hero-mark-frame">
                <Image
                  src="/brand/sentinel-master-512.png"
                  alt={t("SENTINEL shield and signal mark")}
                  width={512}
                  height={512}
                  priority
                />
              </div>
              <div className="signal-card">
                <span className="status">{t("BUILT FOR PLAYERS")}</span>
                <strong>{t("Clear signals. Informed decisions.")}</strong>
                <span>{t("Useful context, visible uncertainty and access you control.")}</span>
              </div>
            </div>
          </div>
        </section>

        <section id="product" className="section-block">
          <div className="site-shell">
            <div className="section-heading">
              <div className="eyebrow">{t("PRODUCT PRINCIPLES")}</div>
              <h2>{t("Useful to the player. Explicit about trust.")}</h2>
              <p>{t("Useful recommendations need a clear foundation. SENTINEL makes the information behind them visible and keeps your account controls within reach.")}</p>
            </div>
            <div className="feature-grid">
              {capabilities.map((item) => (
                <article className="feature-card" key={item.eyebrow}>
                  <div className="eyebrow">{item.eyebrow}</div>
                  <h3>{item.title}</h3>
                  <p>{item.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section-block section-muted">
          <div className="site-shell">
            <div className="section-heading compact-heading">
              <div className="eyebrow">{t("SURFACES")}</div>
              <h2>{t("Designed for phone, Web and desktop.")}</h2>
            </div>
            <div className="surface-list">
              {surfaces.map(([name, description, state]) => (
                <article className="surface-row" key={name}>
                  <div>
                    <h3>{name}</h3>
                    <p>{description}</p>
                  </div>
                  <span className="status">{state}</span>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section-block">
          <div className="site-shell trust-grid">
            <div>
              <div className="eyebrow">{t("WHY SENTINEL")}</div>
              <h2>{t("Confidence starts with clarity.")}</h2>
            </div>
            <div className="trust-copy">
              <p>{t("You should be able to tell what SENTINEL knows, what it infers and what remains unverified. Its security model keeps account access and recommendations within explicit boundaries, so a clearer view does not cost you control.")}</p>
              <Link className="text-link" href="/security/">{t("Read the security model \u2192")}</Link>
            </div>
          </div>
        </section>
      </main>
      <PublicFooter />
    </>
  );
}
