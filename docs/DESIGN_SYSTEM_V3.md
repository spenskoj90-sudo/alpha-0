# SENTINEL Design System v3.0

**Status:** ACTIVE  
**Direction:** CALM PRECISION / TRUSTED INTELLIGENCE  
**Imported design-reference:** `spenskoj90-sudo/sentinel-aware-companion@a281479677d84de21a24db62b0b13af7ae11c623`
**Reviewed earlier native studies:** `a6fc9d4c513dde9d549e5dd70159b1365a76b95c` (not the imported registry pin)
**Production design owner:** GPT, within the Owner-approved direction.

## Reference refresh · 2026-09-27

The latest design-laboratory reference extends the already-adopted v3 foundations without replacing production architecture. The refreshed reference adds explicit interactive studies for **Voice**, **Admin**, **Access**, **Billing** and **Resilience**, plus a detailed cross-platform screen/state inventory and Compose/Electron handoff guidance. The foundational brand artwork, semantic color direction, typography families, low-radius geometry, status grammar and accessibility rules remain compatible with the existing v3 production contract.

Production adoption is incremental and evidence-bound: reference UI code is never copied wholesale into Android/Next.js/Electron. Each surface is translated into the native production architecture and must pass its existing security/runtime tests.

**Production design authority (2026-10-07):** GPT owns native production design in `alpha-0` under the Owner-approved v3 direction. The laboratory is reference/history only; its unfinished pass does not block production work and no automatic imports or parity requirement apply. Keep the imported asset pin as provenance. Any optional future import requires a stable reviewed reference and native validation; Owner visual acceptance remains separate.

v3.0 is the active cross-surface design authority. v2.1 remains historical reference only.

## Visual language

SENTINEL uses deep structural navy, precise low-radius geometry, restrained material/light effects, cyan for intelligence/primary action and teal for live operational signal. It excludes cyberpunk/HUD decoration, RGB gaming styling, generic Material identity, generic SaaS chrome, arbitrary neon and scanner/grid decoration.

## Brand and iconography

The approved full-color shield/S/signal studio artwork is used for brand, launch and high-value moments. It must not be reconstructed as a primitive VectorDrawable. The studio reduced shield/S glyph is used for compact, monochrome, themed-icon, tray and notification contexts. The earlier hand-drawn-looking reduced S/signal study is rejected after physical review; compact product navigation uses a separate optically consistent domain-icon family rather than repurposing the brand glyph. Reduced-glyph optical approval at 16/20/24/32/48 px and Android launcher masking remains a physical acceptance gate.

Primary domain iconography covers Home, Games, Security, Activity, Intelligence, Companion, Overlay and Signal/Connection. Standard utility actions may retain platform icons when optically calibrated.

## Geometry, typography and motion

Spacing: 4/8/12/16/24/32/48. Product radii: 3–8 px/dp; pill shapes are reserved for semantic badges. Android targets are at least 48dp; Web/Companion controls target at least 44px.

Onest is brand/display, Inter is UI/body, JetBrains Mono is evidence/SHA/timestamps/technical identifiers. Cyrillic and English are first-class; meaning-bearing state text may not be clipped.

Motion is short and purposeful (180ms interaction, 320ms entry). Reduced-motion removes non-essential animation. Persistent decorative pulsing is prohibited.

## State and intelligence grammar

Status: `VERIFIED ACTIVE PENDING WARNING DENIED REVOKED FAILED UNKNOWN UNAVAILABLE STOPPED`.

Capability: `AVAILABLE LIMITED UNAVAILABLE UNVERIFIED`.

Runtime: `CONNECTING ACTIVE DEGRADED LOCAL-ONLY OFFLINE STOPPED`.

Policy: `ALLOW CONFIRM DENY`.

State is always text plus icon/shape/border; color alone is insufficient. Missing or stale data is never rendered as healthy or zero.

**FACT** = directly observed + source + freshness.  
**INFERENCE** = derived + confidence + contributing signals.  
**RECOMMENDATION** = action → priority → reason → confidence → source/time → acknowledgement.

Unavailable upstream fields are shown as unavailable; the UI must not invent provenance, freshness or confidence.

## Platform calibration

Android uses four canonical primary destinations: Home, Games, Security and Activity. Their icons use one consistent 24dp rounded-stroke family with no miniature brand reconstruction. Stock Material `NavigationBar/NavigationBarItem` presentation is not a v3 primitive; selected state is a quiet bounded capsule behind the icon rather than an ornamental top dash.

Web retains the Next.js architecture, uses responsive structural navigation and preserves Admin as a privileged fail-closed utility shell.

Companion remains Electron/runtime-native and exposes Overview, Account, Runtime, Host, Games, Adapters, Voice, Overlay, Diagnostics and Updates. The kill switch is always reachable, visually isolated and confirmed.

Overlay supports Minimal / Standard / Expanded density and Recommendation / Warning / Degraded scenarios. It presents one meaningful message at a time and remains presentation-only.

Voice remains explicit-consent push-to-talk. UI text states that the microphone is not continuously listening.

## Accessibility and contract

Visible focus, screen-reader/TalkBack semantics, forced colors, reduced motion, scalable text, non-color state communication and predictable focus order are mandatory.

`design/sentinel-design-system.v3.json` is the machine contract. `scripts/test_design_system.py` enforces drift across Compose, Web, Companion and Overlay. Values are calibrated per native platform rather than mechanically copied from the design prototype.

## Production refinement · 2026-09-30

Owner has assigned GPT responsibility for the production design direction within Calm Precision / Trusted Intelligence. This native pass corrects drift rather than importing unfinished prototype code:

- Web access uses a bounded form beside a calm account introduction on wide screens, with one column on mobile; authentication, MFA and secure cookie boundaries remain intact.
- Product navigation uses one rounded 24px stroke family, removes duplicate links to the account destination and follows the actual hash through browser history.
- Web, Public Site and packaged Companion reduced assets now match the approved studio geometry in `design/brand/`; the older uneven S/signal geometry is removed from those production copies.
- Companion and Overlay inline marks use that same canonical geometry. The rendered SVG shapes are checked as well as the copied asset files, so a stale inline mark cannot pass asset-only validation.
- Companion navigation follows the selected section and browser history through `aria-current="location"`; Overview is the initial selection rather than a permanently highlighted first item.
- Product surfaces use consistent two-column grids on desktop and one column on mobile; keyboard focus, forced colors, reduced motion and theme contrast remain required.

The imported reference package remains pinned to `a281479677d84de21a24db62b0b13af7ae11c623`. The unfinished laboratory iteration `56e6c9afdff501cc3451352c2b2dcd286b0ecdd1` is not accepted or imported by this refinement. No cross-platform visual parity or Owner optical acceptance is inferred from these changes.
