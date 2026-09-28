import Link from "next/link";

export function PublicFooter() {
  return (
    <footer className="site-footer">
      <div className="site-shell footer-grid">
        <div>
          <div className="brand-word">SENTINEL</div>
          <p className="footer-copy">
            Pre-release trusted intelligence platform. Public release and production
            activation remain separate acceptance gates.
          </p>
        </div>
        <nav className="footer-nav" aria-label="Footer">
          <Link href="/security/">Security</Link>
          <Link href="/privacy/">Privacy</Link>
          <Link href="/status/">Release status</Link>
        </nav>
      </div>
    </footer>
  );
}
