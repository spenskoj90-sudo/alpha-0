"use client";

import { useLocale } from "./components/locale-provider";
import Link from "next/link";
import { PublicFooter } from "./components/public-footer";
import { PublicHeader } from "./components/public-header";

export default function NotFound() {
  const { t } = useLocale();
  return (
    <>
      <PublicHeader />
      <main className="document-main">
        <div className="site-shell document-shell">
          <div className="eyebrow">404</div>
          <h1>{t("Surface not found.")}</h1>
          <p className="document-lead">{t("The requested public SENTINEL page does not exist.")}</p>
          <Link className="button-primary inline-button" href="/">{t("Return home")}</Link>
        </div>
      </main>
      <PublicFooter />
    </>
  );
}
