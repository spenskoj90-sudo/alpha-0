"use client";

import { useLocale } from "./locale-provider";
import Link from "next/link";

export function PublicFooter() {
  const { t } = useLocale();
  return (
    <footer className="site-footer">
      <div className="site-shell footer-grid">
        <div>
          <div className="brand-word">SENTINEL</div>
          <p className="footer-copy">{t("Pre-release trusted intelligence platform. Public release and production activation remain separate acceptance gates.")}</p>
        </div>
        <nav className="footer-nav" aria-label={t("Footer")}>
          <Link href="/security/">{t("Security")}</Link>
          <Link href="/privacy/">{t("Privacy")}</Link>
          <Link href="/status/">{t("Release status")}</Link>
        </nav>
      </div>
    </footer>
  );
}
