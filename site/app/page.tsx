import Image from "next/image";
import Link from "next/link";
import { PublicFooter } from "./components/public-footer";
import { PublicHeader } from "./components/public-header";

const capabilities = [
  {
    eyebrow: "INTELLIGENCE",
    title: "Know what a recommendation is based on.",
    body:
      "See the source, freshness and confidence behind a recommendation. Facts and inference stay distinct, and uncertainty stays visible.",
  },
  {
    eyebrow: "SECURITY",
    title: "Your account. Your control.",
    body:
      "Review account security, connected devices and access in one place. Recommendations remain observational; SENTINEL does not turn them into hidden actions.",
  },
  {
    eyebrow: "PLAYER EXPERIENCE",
    title: "One system across mobile, web and desktop.",
    body:
      "Check context on your phone, manage your account on the Web, and connect the desktop Companion for overlay, diagnostics and voice workflows.",
  },
];

const surfaces = [
  ["Android", "Immediate context, security, games and activity", "IMPLEMENTED · PHYSICAL ACCEPTANCE PENDING"],
  ["Web Control Plane", "Account, intelligence, billing, devices and administration", "IMPLEMENTED · UX CONSOLIDATION ACTIVE"],
  ["Windows Companion", "Runtime, adapters, overlay, diagnostics and voice", "IMPLEMENTED · HOST ACCEPTANCE PENDING"],
  ["Game integration", "Conservative passive observation through explicit adapter boundaries", "WOW EXACT-ENVIRONMENT ACCEPTANCE PENDING"],
];

export default function PublicHome() {
  return (
    <>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <PublicHeader />
      <main id="main-content">
        <section className="hero" data-design-direction="CALM PRECISION / TRUSTED INTELLIGENCE">
          <div className="site-shell hero-grid">
            <div className="hero-copy">
              <div className="eyebrow">PRE-RELEASE · TRUSTED INTELLIGENCE</div>
              <h1>A clearer view.<br />You stay in control.</h1>
              <p className="hero-lead">
                SENTINEL is being built to bring game context, account security and useful
                recommendations together across your phone, Web and desktop. Understand
                what is known, see where uncertainty remains, and choose your next step.
              </p>
              <div className="hero-actions">
                <a className="button-primary" href="#product">Explore the product</a>
                <Link className="button-secondary" href="/status/">View release status</Link>
              </div>
              <p className="release-note">
                No public download is offered yet. Release testing is still in progress.
              </p>
            </div>
            <div className="hero-visual" aria-label="SENTINEL brand identity">
              <div className="hero-mark-frame">
                <Image
                  src="/brand/sentinel-master-512.png"
                  alt="SENTINEL shield and signal mark"
                  width={512}
                  height={512}
                  priority
                />
              </div>
              <div className="signal-card">
                <span className="status">BUILT FOR PLAYERS</span>
                <strong>Clear signals. Informed decisions.</strong>
                <span>Useful context, visible uncertainty and access you control.</span>
              </div>
            </div>
          </div>
        </section>

        <section id="product" className="section-block">
          <div className="site-shell">
            <div className="section-heading">
              <div className="eyebrow">PRODUCT PRINCIPLES</div>
              <h2>Useful to the player. Explicit about trust.</h2>
              <p>
                Useful recommendations need a clear foundation. SENTINEL makes the information
                behind them visible and keeps your account controls within reach.
              </p>
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
              <div className="eyebrow">SURFACES</div>
              <h2>Designed for phone, Web and desktop.</h2>
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
              <div className="eyebrow">WHY SENTINEL</div>
              <h2>Confidence starts with clarity.</h2>
            </div>
            <div className="trust-copy">
              <p>
                You should be able to tell what SENTINEL knows, what it infers and what remains
                unverified. Its security model keeps account access and recommendations within
                explicit boundaries, so a clearer view does not cost you control.
              </p>
              <Link className="text-link" href="/security/">Read the security model →</Link>
            </div>
          </div>
        </section>
      </main>
      <PublicFooter />
    </>
  );
}
