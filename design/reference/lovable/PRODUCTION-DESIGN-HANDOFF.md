# SENTINEL — Production Design Handoff

Entry point for engineering teams (Android Compose, Web/Next.js, Electron Companion, Overlay).

## Sources of truth
| Area | File |
|---|---|
| Tokens (runtime) | `src/styles.css` |
| Tokens (machine-readable, Compose/Electron export) | `design/tokens.json` |
| Components, variants, states, a11y | `design/components.json` |
| Screen & state inventory (92 screens) | `design/screens.json` |
| Brand assets + status | `design/assets.json` |
| Rules, grammar, flows | `docs/SENTINEL-FOUNDATIONS.md` |
| Interactive reference | `/` (10 surfaces) |

Consistency check: `node scripts/validate-design.mjs` (tokens vs CSS, assets exist, unique screens).

## Implementation order
1. Tokens → platform themes (Compose `ColorScheme` + custom `SentinelColors` for signal/warning/verified; CSS vars for web/Electron).
2. `StatusBadge` enum + metadata (label, icon, tone, shape) — never color alone.
3. Intelligence modules: FACT / INFERENCE (confidence %) / RECOMMENDATION (action first, acknowledge).
4. Navigation: Android 4-domain custom dock (not stock NavigationBar); web/desktop rail 232px, collapsed 72px.
5. State patterns (empty, loading, stale, offline, local-only, degraded, permission, failed) before feature screens.
6. Surfaces in inventory order; each screen lists its required states.

## Non-negotiables
- Legacy blue launcher icon and old bottom navigation are not inherited.
- Physical Test mode = compact 24dp strip (env · version · SHA · diagnostics), never a large red banner.
- Kill switch: isolated region, two-step confirmation, always reachable.
- Microphone never opens without explicit push-to-talk and prior consent.
- Degraded states name missing inputs; they never claim certainty.
- Glow/gradient only for brand, key active state, high-value intelligence.
- Reduced motion and forced colors supported on every surface.

## Brand assets
- Master icon: `src/assets/sentinel-master-icon.png` (raster master).
- Glyphs: `glyph.svg` (≥32px), `glyph-compact.svg` (16–24px, no arcs), `glyph-mono.svg`.
- Glyphs are candidates pending owner optical sign-off. Store, adaptive Android and Windows ICO assets must be exported from an approved vector master.

## Out of scope for this repository
Native Android/Windows builds and Figma files require their own source projects or a connected desktop Figma.
