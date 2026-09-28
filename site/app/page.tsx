import Image from "next/image";
import Link from "next/link";
import { PublicFooter } from "./components/public-footer";
import { PublicHeader } from "./components/public-header";

const capabilities = [
  {
    eyebrow: "INTELLIGENCE",
    title: "Facts, inference and recommendations stay distinct.",
    body:
      "SENTINEL keeps source, freshness and confidence visible so missing or stale information is not presented as certainty.",
  },
  {
    eyebrow: "SECURITY",
    title: "Authority stays server-side.",
    body:
      "Identity, sessions, device proof, entitlement and privileged operations remain bounded by the trusted Core rather than browser or client assumptions.",
  },
  {
    eyebrow: "PLAYER EXPERIENCE",
    title: "One system across mobile, web and desktop.",
    body:
      "Android handles immediate context, Web provides account and control-plane workflows, while Companion, Overlay and Voice extend the player experience on the host.",
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
        <section className="hero">
          <div className="site-shell hero-grid">
            <div className="hero-copy">
              <div className="eyebrow">PRE-RELEASE · TRUSTED INTELLIGENCE</div>
              <h1>Clear signals. Bounded intelligence. One calm system.</h1>
              <p className="hero-lead">
                SENTINEL is being built as a trustworthy intelligence layer for players:
                observe what is known, distinguish what is inferred, and present useful
                recommendations without hiding uncertainty or crossing authority boundaries.
              </p>
              <div className="hero-actions">
                <a className="button-primary" href="#product">Explore the product</a>
                <Link className="button-secondary" href="/status/">View release status</Link>
              </div>
              <p className="release-note">
                No public download is offered yet. Signing, publication and production deployment
                remain explicit final acceptance gates.
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
                <span className="status status-live">ACTIVE DESIGN SYSTEM</span>
                <strong>CALM PRECISION / TRUSTED INTELLIGENCE</strong>
                <span>Design System v3.0 · cross-surface semantic contract</span>
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
                The product is designed around user value without letting presentation invent
                security state, entitlement, game evidence or AI confidence.
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
              <h2>A coordinated platform, not a single screen.</h2>
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
              <h2>Technology → capability → experience → user value.</h2>
            </div>
            <div className="trust-copy">
              <p>
                Security, reliability, correctness and performance are enabling constraints.
                They exist so the product can deliver useful intelligence and differentiated
                player experiences without making unsupported claims.
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
