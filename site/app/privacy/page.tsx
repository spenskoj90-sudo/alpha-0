import type { Metadata } from "next";
import { PublicFooter } from "../components/public-footer";
import { PublicHeader } from "../components/public-header";

export const metadata: Metadata = {
  title: "Privacy principles",
  description: "Pre-release privacy engineering principles for SENTINEL.",
};

export default function PrivacyPage() {
  return (
    <>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <PublicHeader />
      <main id="main-content" className="document-main">
        <div className="site-shell document-shell">
          <div className="eyebrow">PRIVACY PRINCIPLES</div>
          <h1>Collect deliberately. Bound evidence. Keep authority separate.</h1>
          <p className="document-lead">
            These are engineering principles for the pre-release product, not the final legal
            privacy notice. A jurisdiction-appropriate legal notice must be approved before
            public production launch.
          </p>
          <div className="principle-grid">
            <article className="feature-card">
              <h2>Diagnostics are bounded</h2>
              <p>Diagnostic and operational evidence is scoped, privacy-scrubbed and treated separately from security truth.</p>
            </article>
            <article className="feature-card">
              <h2>Telemetry is constrained</h2>
              <p>Optional telemetry paths remain disabled or environment-bounded unless the active contract explicitly permits them.</p>
            </article>
            <article className="feature-card">
              <h2>Voice is explicit</h2>
              <p>Voice capture is push-to-talk with explicit consent; the interface must never imply that the microphone is continuously listening.</p>
            </article>
            <article className="feature-card">
              <h2>Missing data stays missing</h2>
              <p>Unavailable information is not silently converted into zero, healthy state, confidence or fabricated provenance.</p>
            </article>
          </div>
        </div>
      </main>
      <PublicFooter />
    </>
  );
}
