"use client";

import { useLocale } from "../components/locale-provider";
import { PublicFooter } from "../components/public-footer";
import { PublicHeader } from "../components/public-header";


export default function SecurityPage() {
  const { t } = useLocale();
  const principles = [
    [t("Server-authoritative decisions"), t("Authorization, entitlement and privileged state are decided by Core rather than trusted to browser or local presentation state.")],
    [t("Bounded credentials"), t("Opaque sessions, device proof and provider integrations are designed to keep sensitive credentials outside ordinary UI state.")],
    [t("Default deny"), t("Missing authority, provider configuration or capability evidence fails closed instead of silently broadening access.")],
    [t("Evidence before claims"), t("Physical-device, exact-game-environment and production-provider claims remain unverified until evidence exists for the exact candidate.")],
  ];

  return (
    <>
      <a className="skip-link" href="#main-content">{t("Skip to main content")}</a>
      <PublicHeader />
      <main id="main-content" className="document-main">
        <div className="site-shell document-shell">
          <div className="eyebrow">{t("SECURITY")}</div>
          <h1>{t("Trust is a product boundary, not a visual badge.")}</h1>
          <p className="document-lead">{t("SENTINEL separates presentation from authority. The public website is intentionally a separate surface from the authenticated Web Control Plane and has no account, billing or admin API boundary.")}</p>
          <div className="principle-grid">
            {principles.map(([title, body]) => (
              <article className="feature-card" key={title}>
                <h2>{title}</h2>
                <p>{body}</p>
              </article>
            ))}
          </div>
          <aside className="callout">
            <strong>{t("Pre-release status")}</strong>
            <p>{t("Security architecture and repository tests do not replace final physical, provider-network, signed-candidate or production acceptance.")}</p>
          </aside>
        </div>
      </main>
      <PublicFooter />
    </>
  );
}
