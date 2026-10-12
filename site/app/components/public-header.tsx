"use client";

import { publicSections } from "./public-sections";
import { usePathname } from "next/navigation";
import { LanguageSwitch, useLocale } from "./locale-provider";
import Image from "next/image";
import Link from "next/link";

export function PublicHeader() {
  const { t, locale } = useLocale();
  const current = usePathname().replace(/\/$/, "") || "/";
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
          {publicSections.map(section => <Link key={section.path} href={`/${section.path}/`} aria-current={current === `/${section.path}` ? "page" : undefined}>{locale === "ru" ? section.ru : section.en}</Link>)}
          <Link href="/security/" aria-current={current === "/security" ? "page" : undefined}>{t("Security")}</Link>
          <Link href="/status/">{t("Status")}</Link>
        </nav>
        <LanguageSwitch />
      </div>
    </header>
  );
}
