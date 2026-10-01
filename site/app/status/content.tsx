"use client";

import { useLocale } from "../components/locale-provider";
import { PublicFooter } from "../components/public-footer";
import { PublicHeader } from "../components/public-header";


export default function StatusPage() {
  const { t } = useLocale();
  const rows = [
    ["Android", t("Repository implementation advanced"), t("Physical exact-candidate acceptance remains pending")],
    [t("Web Control Plane"), t("Core account/intelligence/billing boundaries implemented"), t("Full product UX consolidation continues against the active design reference")],
    ["Windows Companion", t("Runtime, overlay and voice foundations implemented"), t("Target Windows host acceptance remains pending")],
    [t("WoW integration"), t("Conservative passive adapter path implemented"), t("Exact 3.3.5a/private-server environment evidence remains pending")],
    [t("Voice"), t("Explicit-consent provider-neutral runtime implemented"), t("Selected STT/TTS network and physical microphone acceptance remain pending")],
    [t("Public release"), t("Release evidence and signing pipeline implemented"), t("Signing, publication and production deployment remain final Owner gates")],
  ];

  return (
    <>
      <a className="skip-link" href="#main-content">{t("Skip to main content")}</a>
      <PublicHeader />
      <main id="main-content" className="document-main">
        <div className="site-shell document-shell">
          <div className="eyebrow">{t("RELEASE STATUS")}</div>
          <h1>{t("Pre-release, with evidence kept explicit.")}</h1>
          <p className="document-lead">{t("This page intentionally avoids converting repository implementation into claims of physical or production acceptance.")}</p>
          <div className="status-table" role="table" aria-label={t("SENTINEL release readiness")}>
            <div className="status-header" role="row">
              <span role="columnheader">{t("Surface")}</span>
              <span role="columnheader">{t("Repository state")}</span>
              <span role="columnheader">{t("Remaining evidence")}</span>
            </div>
            {rows.map(([surface, implemented, pending]) => (
              <div className="status-record" role="row" key={surface}>
                <div role="cell">
                  <span className="record-label">{t("Surface")}</span>
                  <strong>{surface}</strong>
                </div>
                <div role="cell">
                  <span className="record-label">{t("Repository state")}</span>
                  <span>{implemented}</span>
                </div>
                <div role="cell">
                  <span className="record-label">{t("Remaining evidence")}</span>
                  <span>{pending}</span>
                </div>
              </div>
            ))}
          </div>
          <p className="status-footnote">{t("Mutable implementation truth remains the protected repository main branch and its exact-SHA validation evidence.")}</p>
        </div>
      </main>
      <PublicFooter />
    </>
  );
}
