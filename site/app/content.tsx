"use client";

import { publicSections } from "./components/public-sections";
import { useLocale } from "./components/locale-provider";
import Image from "next/image";
import Link from "next/link";
import { PublicFooter } from "./components/public-footer";
import { PublicHeader } from "./components/public-header";

export default function PublicHome() {
  const { t, locale } = useLocale();
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
                <Link className="button-primary" href="/features/">{t("Explore the product")}</Link>
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

        <section id="product" className="section-block section-muted">
          <div className="site-shell">
            <div className="section-heading compact-heading">
              <h2>{locale === 'ru' ? 'Начните с того, что важно вам.' : 'Start with what matters to you.'}</h2>
            </div>
            <div className="route-grid">
              {publicSections.map(section => <Link className="feature-card route-card" key={section.path} href={`/${section.path}/`}>
                <h3>{locale === 'ru' ? section.ru : section.en}<span aria-hidden="true"> →</span></h3>
              </Link>)}
            </div>
          </div>
        </section>
      </main>
      <PublicFooter />
    </>
  );
}
