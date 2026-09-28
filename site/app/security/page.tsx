import type { Metadata } from "next";
import { PublicFooter } from "../components/public-footer";
import { PublicHeader } from "../components/public-header";

export const metadata: Metadata = {
  title: "Security",
  description: "The security and authority principles behind SENTINEL.",
};

const principles = [
  ["Server-authoritative decisions", "Authorization, entitlement and privileged state are decided by Core rather than trusted to browser or local presentation state."],
  ["Bounded credentials", "Opaque sessions, device proof and provider integrations are designed to keep sensitive credentials outside ordinary UI state."],
  ["Default deny", "Missing authority, provider configuration or capability evidence fails closed instead of silently broadening access."],
  ["Evidence before claims", "Physical-device, exact-game-environment and production-provider claims remain unverified until evidence exists for the exact candidate."],
];

export default function SecurityPage() {
  return (
    <>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <PublicHeader />
      <main id="main-content" className="document-main">
        <div className="site-shell document-shell">
          <div className="eyebrow">SECURITY</div>
          <h1>Trust is a product boundary, not a visual badge.</h1>
          <p className="document-lead">
            SENTINEL separates presentation from authority. The public website is intentionally
            a separate surface from the authenticated Web Control Plane and has no account,
            billing or admin API boundary.
          </p>
          <div className="principle-grid">
            {principles.map(([title, body]) => (
              <article className="feature-card" key={title}>
                <h2>{title}</h2>
                <p>{body}</p>
              </article>
            ))}
          </div>
          <aside className="callout">
            <strong>Pre-release status</strong>
            <p>
              Security architecture and repository tests do not replace final physical,
              provider-network, signed-candidate or production acceptance.
            </p>
          </aside>
        </div>
      </main>
      <PublicFooter />
    </>
  );
}
