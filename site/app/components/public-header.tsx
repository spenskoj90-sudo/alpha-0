import Image from "next/image";
import Link from "next/link";

export function PublicHeader() {
  return (
    <header className="site-header">
      <div className="site-shell site-header-inner">
        <Link className="brand-lockup" href="/" aria-label="SENTINEL home">
          <Image
            src="/brand/glyph.svg"
            alt=""
            width={36}
            height={36}
            priority
            aria-hidden="true"
          />
          <span className="brand-word">SENTINEL</span>
        </Link>
        <nav className="site-nav" aria-label="Public website">
          <Link href="/#product">Product</Link>
          <Link href="/security/">Security</Link>
          <Link href="/status/">Status</Link>
          <Link href="/privacy/">Privacy</Link>
        </nav>
      </div>
    </header>
  );
}
