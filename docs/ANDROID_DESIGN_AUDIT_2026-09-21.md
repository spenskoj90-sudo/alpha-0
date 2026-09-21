# SENTINEL Android visual-system audit — 2026-09-21

## Scope

This audit is based on the current Compose implementation, launcher surfaces, navigation chrome, typography, shared components, and the Owner's physical-device feedback. It does not claim pixel-level review of runtime states that have not been captured as screenshots.

## Executive finding

The functional shell is coherent, but the shared visual layer was still communicating developer tooling / game HUD rather than a finished security product. The main causes were the angular launcher mark, purple/cyan gaming palette, four-dp cards with a bright scanning rail, heavy uppercase treatment, and a separate green/black Companion language.

The target direction is **calm security instrumentation**: dark naval blue, steel blue, cyan signal, restrained teal success, larger continuous radii, fewer decorative effects, and one recognizable shield/signal/S mark.

## Implemented in this pass

- Replaced the old angular launcher mark with the Owner-selected shield + S/radar concept.
- Added Android adaptive foreground/background and Android 13 monochrome icon support.
- Added the same mark as the Next.js web icon and Companion header identity.
- Replaced the purple gaming accent with a blue/cyan/teal security palette.
- Reworked shared cards from 4 dp angular HUD panels to 20 dp product surfaces.
- Removed the moving scan-line visual from the shared card component.
- Standardized primary/destructive controls around 52 dp minimum touch height and 16 dp radius.
- Reduced excessive headline tracking and improved text line-height.
- Brought Android navigation chrome and Companion surfaces into the same palette.

## Current UI/UX priorities

### P0 — trust and continuity

1. Physical-test APKs must form one stable update channel: same package, stable dedicated test signer, monotonic versionCode.
2. Authentication/session transitions must never leave stale authenticated UI after server-side revocation.
3. Diagnostics must remain exportable in physical-test builds and must be reviewed after each physical acceptance pass.

### P1 — product shell

1. Login/register/MFA should use a single centered authentication composition with explicit progress and error hierarchy.
2. Home should answer three questions immediately: account state, device state, and next required action.
3. Security/device details should separate account security from hardware identity; today they are visually dense in one long flow.
4. Loading, empty, warning, blocked, and destructive-confirmation states should use shared components rather than per-screen text.
5. Settings/help/about should use consistent section headers and row components instead of bespoke spacing.

### P2 — polish

1. Introduce a shared 8 dp spacing grid and screen content-width policy.
2. Add motion only for state continuity; avoid decorative scanner/HUD motion.
3. Add screenshot-based golden tests for primary Android states.
4. Add an explicit accessibility pass for dynamic type, contrast, TalkBack order, and one-handed reach.

## Design principles

- **Security without aggression** — trustworthy and precise, not military or alarmist.
- **Signal, not spectacle** — cyan/teal is used for actionable signal and verified state, not decorative neon.
- **One source of truth** — Android, web, and Companion share the same brand mark, color semantics, terminology, and state hierarchy.
- **Calm density** — operational data may be dense, but grouping and whitespace make priority obvious.
- **Fail-closed visually** — unavailable or unverifiable state is explicit; it is never made to look healthy.

## Human-designer handoff

A human UI/UX designer may use this document as the constraints brief. Deliverables should be editable Figma frames/components, not raster-only mockups. The designer should preserve existing security semantics and flows and should not change authentication, entitlement, device-proof, voice-authority, or kill-switch behavior without Owner approval.

Required frame set: sign in/register/reset/email verification/MFA; device setup/proof; home; games/game details; security/account/MFA/device details; activity; settings; update; quality report; help/about; loading/empty/error/offline/revoked states.

Required component set: app bar, bottom navigation, cards, section headers, buttons, text fields, selection controls, status badges, alerts, progress, empty states, security rows, device identity rows, recovery-code presentation, modal confirmation, and destructive confirmation.

The canonical implementation remains the repository. Visual mockups are advisory until reconciled against product/security behavior.
