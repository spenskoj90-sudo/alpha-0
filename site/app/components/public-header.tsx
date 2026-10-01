"use client";

import { LanguageSwitch, useLocale } from "./locale-provider";
import Image from "next/image";
import Link from "next/link";

export function PublicHeader() {
  const { t } = useLocale();
  return (
    <header className="site-header">
      <div className="site-shell site-header-inner">
        <Link className="brand-lockup" href="/" aria-label={t("SENTINEL home")}>
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
        <nav className="site-nav" aria-label={t("Public website")}>
          <Link href="/#product">{t("Product")}</Link>
          <Link href="/security/">{t("Security")}</Link>
          <Link href="/status/">{t("Status")}</Link>
          <Link href="/privacy/">{t("Privacy")}</Link>
        </nav>
        <LanguageSwitch />
      </div>
    </header>
  );
}
