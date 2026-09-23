# SENTINEL Design System v3.0

**Status:** ACTIVE  
**Direction:** CALM PRECISION / TRUSTED INTELLIGENCE  
**Design-reference:** `spenskoj90-sudo/sentinel-aware-companion@60629603299fd8af035c6f05991482cde0363c33`

v3.0 is the active cross-surface design authority. v2.1 remains historical reference only.

## Visual language

SENTINEL uses deep structural navy, precise low-radius geometry, restrained material/light effects, cyan for intelligence/primary action and teal for live operational signal. It excludes cyberpunk/HUD decoration, RGB gaming styling, generic Material identity, generic SaaS chrome, arbitrary neon and scanner/grid decoration.

## Brand and iconography

The approved full-color shield/S/signal studio artwork is used for brand, launch and high-value moments. It must not be reconstructed as a primitive VectorDrawable. The studio reduced shield/S/signal glyph is used for compact, monochrome, themed-icon, tray and notification contexts. Reduced-glyph optical approval at 16/20/24/32/48 px and Android launcher masking remains a physical acceptance gate.

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

Android uses four canonical primary destinations: Home, Games, Security and Activity. Stock Material `NavigationBar/NavigationBarItem` presentation is not a v3 primitive.

Web retains the Next.js architecture, uses responsive structural navigation and preserves Admin as a privileged fail-closed utility shell.

Companion remains Electron/runtime-native and exposes Overview, Account, Runtime, Host, Games, Adapters, Voice, Overlay, Diagnostics and Updates. The kill switch is always reachable, visually isolated and confirmed.

Overlay supports Minimal / Standard / Expanded density and Recommendation / Warning / Degraded scenarios. It presents one meaningful message at a time and remains presentation-only.

Voice remains explicit-consent push-to-talk. UI text states that the microphone is not continuously listening.

## Accessibility and contract

Visible focus, screen-reader/TalkBack semantics, forced colors, reduced motion, scalable text, non-color state communication and predictable focus order are mandatory.

`design/sentinel-design-system.v3.json` is the machine contract. `scripts/test_design_system.py` enforces drift across Compose, Web, Companion and Overlay. Values are calibrated per native platform rather than mechanically copied from the design prototype.
