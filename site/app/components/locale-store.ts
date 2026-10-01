export type Locale = "en" | "ru";
export const LOCALE_STORAGE_KEY = "sentinel.locale";

/** A persisted supported locale wins; otherwise use the browser language. */
export function resolveLocale(stored: string | null, languages: readonly string[]): Locale {
  if (stored === "en" || stored === "ru") return stored;
  return languages[0]?.toLowerCase().split(/[-_]/)[0] === "ru" ? "ru" : "en";
}
