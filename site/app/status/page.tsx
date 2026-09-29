import type { Metadata } from "next";
import { PublicFooter } from "../components/public-footer";
import { PublicHeader } from "../components/public-header";

export const metadata: Metadata = {
  title: "Release status",
  description: "Current high-level pre-release status for SENTINEL surfaces.",
};

const rows = [
  ["Android", "Repository implementation advanced", "Physical exact-candidate acceptance remains pending"],
  ["Web Control Plane", "Core account/intelligence/billing boundaries implemented", "Full product UX consolidation continues against the active design reference"],
  ["Windows Companion", "Runtime, overlay and voice foundations implemented", "Target Windows host acceptance remains pending"],
  ["WoW integration", "Conservative passive adapter path implemented", "Exact 3.3.5a/private-server environment evidence remains pending"],
  ["Voice", "Explicit-consent provider-neutral runtime implemented", "Selected STT/TTS network and physical microphone acceptance remain pending"],
  ["Public release", "Release evidence and signing pipeline implemented", "Signing, publication and production deployment remain final Owner gates"],
];

export default function StatusPage() {
  return (
    <>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <PublicHeader />
      <main id="main-content" className="document-main">
        <div className="site-shell document-shell">
          <div className="eyebrow">RELEASE STATUS</div>
          <h1>Pre-release, with evidence kept explicit.</h1>
          <p className="document-lead">
            This page intentionally avoids converting repository implementation into claims of
            physical or production acceptance.
          </p>
          <div className="status-table" role="table" aria-label="SENTINEL release readiness">
            <div className="status-header" role="row">
              <span role="columnheader">Surface</span>
              <span role="columnheader">Repository state</span>
              <span role="columnheader">Remaining evidence</span>
            </div>
            {rows.map(([surface, implemented, pending]) => (
              <div className="status-record" role="row" key={surface}>
                <div role="cell">
                  <span className="record-label">Surface</span>
                  <strong>{surface}</strong>
                </div>
                <div role="cell">
                  <span className="record-label">Repository state</span>
                  <span>{implemented}</span>
                </div>
                <div role="cell">
                  <span className="record-label">Remaining evidence</span>
                  <span>{pending}</span>
                </div>
              </div>
            ))}
          </div>
          <p className="status-footnote">
            Mutable implementation truth remains the protected repository main branch and its
            exact-SHA validation evidence.
          </p>
        </div>
      </main>
      <PublicFooter />
    </>
  );
}
