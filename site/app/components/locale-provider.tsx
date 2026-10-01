"use client";

import { createContext, useContext, useEffect, useSyncExternalStore } from "react";
import { usePathname } from "next/navigation";
import { russianCopy, type CopyKey } from "./locale-dictionary";
import { LOCALE_STORAGE_KEY, resolveLocale, type Locale } from "./locale-store";

const CHANGE_EVENT = "sentinel-locale-change";
let transientLocale: Locale | undefined;

function readLocale(): Locale {
  if (transientLocale) return transientLocale;
  let stored: string | null = null;
  try { stored = window.localStorage.getItem(LOCALE_STORAGE_KEY); } catch { /* Browsing without storage remains usable. */ }
  return resolveLocale(stored, navigator.languages.length ? navigator.languages : [navigator.language]);
}

function subscribe(onChange: () => void) {
  const onStorage = (event: StorageEvent) => {
    if (event.key === LOCALE_STORAGE_KEY || event.key === null) {
      transientLocale = undefined;
      onChange();
    }
  };
  window.addEventListener("storage", onStorage);
  window.addEventListener(CHANGE_EVENT, onChange);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener(CHANGE_EVENT, onChange);
  };
}

const LocaleContext = createContext({
  locale: "en" as Locale,
  t: (key: CopyKey): string => key,
  setLocale: (_locale: Locale) => {},
});

const pageMetadata: Record<string, [CopyKey, CopyKey]> = {
  "/": ["SENTINEL — Trusted Intelligence for Players", "SENTINEL is a pre-release trusted intelligence platform spanning Android, Web Control Plane, Windows Companion and player-facing guidance."],
  "/security": ["Security", "The security and authority principles behind SENTINEL."],
  "/privacy": ["Privacy principles", "Pre-release privacy engineering principles for SENTINEL."],
  "/status": ["Release status", "Current high-level pre-release status for SENTINEL surfaces."],
};

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  // Static export and hydration always start in EN. Browser preference is read after hydration.
  const locale = useSyncExternalStore(subscribe, readLocale, (): Locale => "en");
  const pathname = usePathname();
  const t = (key: CopyKey): string => locale === "ru" ? russianCopy[key] : key;

  useEffect(() => {
    document.documentElement.lang = locale;
    const route = pathname.replace(/\/$/, "") || "/";
    const metadata = pageMetadata[route];
    document.title = metadata
      ? `${locale === "ru" ? russianCopy[metadata[0]] : metadata[0]}${route === "/" ? "" : " · SENTINEL"}`
      : `${locale === "ru" ? russianCopy["Page not found"] : "Page not found"} · SENTINEL`;
    if (metadata) {
      const description = document.querySelector<HTMLMetaElement>('meta[name="description"]');
      if (description) description.content = locale === "ru" ? russianCopy[metadata[1]] : metadata[1];
    }
  }, [locale, pathname]);

  function setLocale(next: Locale) {
    transientLocale = next;
    try { window.localStorage.setItem(LOCALE_STORAGE_KEY, next); } catch { /* Preserve the session selection when persistence is unavailable. */ }
    window.dispatchEvent(new Event(CHANGE_EVENT));
  }

  return <LocaleContext.Provider value={{ locale, t, setLocale }}>{children}</LocaleContext.Provider>;
}

export function useLocale() { return useContext(LocaleContext); }

export function LanguageSwitch() {
  const { locale, t, setLocale } = useLocale();
  return (
    <div className="language-switch" role="group" aria-label={t("Language")}>
      <button type="button" lang="en" aria-pressed={locale === "en"} onClick={() => setLocale("en")}>English</button>
      <button type="button" lang="ru" aria-pressed={locale === "ru"} onClick={() => setLocale("ru")}>Русский</button>
    </div>
  );
}
