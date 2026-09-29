# SENTINEL — foundations and implementation handoff

Version 0.1 · Product design foundation and interactive reference implementation.

## Brand principle
SENTINEL observes, interprets, warns, and supports decisions. The approved shield/S/signal-node concept is authoritative. The full-color master icon is for brand, stores, launch and select high-value moments; the reduced single-color glyph is for ≤24px, system tray, notifications, and monochrome/adaptive contexts. Do not use the large icon as a small operational pictogram. The reduced glyph is an implementation study, not an approved vector master; its geometry needs optical sign-off before store publication.

Clear space around the icon: at least one signal-node diameter; preferred minimum full-color icon size: 48px; reduced glyph: 16px; do not crop or rotate. On dark and light surfaces use the same geometry; change only foreground contrast in monochrome instances. Do not add decorative scanning, grids, or random glow.

## Tokens and modes
The source of truth is `src/styles.css`. Semantic CSS variables use OKLCH, supporting dark and independently calibrated light surfaces. Roles: background, surface, raised, subtle; foreground, muted-foreground, dim; primary (action/intelligence), signal (live), success (verified), warning, destructive, info; border, line-strong, ring; chart-1…5. Gradients are restricted to brand and high-value intelligence moments. No color alone encodes state. All product controls use semantic roles. High contrast and forced colors retain borders and labels.

Typography: Onest / brand and major headings, Inter / interface, JetBrains Mono / identifiers, source SHA, timestamps, states. Display 24–40; section 20–22; body 13–15; metadata 10–12. Russian text can grow 30–50%; avoid truncating status or warnings. Numeric metadata uses tabular numerals.

Geometry: 4px small controls, 6px bounded modules, 8px maximum for product cards. Spacing unit 4px; working steps 4/8/12/16/24/32/48. Minimum interactive target 44px for touch. Desktop rail 232px; working content 1240px max; mobile dock four domains only. Breakpoints follow content (mobile <640px; tablet <1024px; desktop ≥1024px). Tables become stacked labeled records on mobile, not horizontal clipping.

Motion: enter 320ms cubic-bezier(.2,.7,.2,1); interactive transition 180ms; signal state changes once, not perpetual pulsation. `prefers-reduced-motion` disables motion. Focus ring always visible, including keyboard use.

## Status grammar
Each status carries text + icon + border/shape + semantic color, never color alone. VERIFIED: shield-check/success; ACTIVE: signal/live; PENDING: clock/info; WARNING: triangle/amber; DENIED: crossed circle/danger; REVOKED: cross/danger; FAILED: alert circle/danger; UNKNOWN: question/neutral; UNAVAILABLE: dash/neutral; STOPPED: crossed circle/neutral. Capabilities: AVAILABLE, LIMITED, UNAVAILABLE, UNVERIFIED. Runtime: FULL, DEGRADED, LOCAL-ONLY, OFFLINE. Policy: ALLOW, CONFIRM, DENY. Policy decisions never reuse runtime labels. Screen readers hear the text label.

## Intelligence grammar
FACT = directly observed, show source and freshness. INFERENCE = derived, show confidence and contributing signals. RECOMMENDATION = actionable, state the recommendation before supporting evidence. Low-quality/stale data must visibly downgrade confidence; unavailable data cannot be quietly interpreted as zero. Recommendation module order: action → priority → reason → confidence → source/time → acknowledgement. Never present AI output as a chat bubble by default.

## Surface roles
- Android: immediate context, four-domain navigation, account/security and onboarding flows. The mock phone is interactive; it is not native Compose output.
- Web: account, games, intelligence, device and security operations, subscription and support. Admin uses a distinct operation-oriented shell when implemented.
- Companion: host, adapter, connection and runtime controls. Stop control is visually isolated and asks for confirmation.
- Overlay: minimal, standard, expanded density. Maximum one priority action plus one system line in minimal; no decorative backdrop or persistent attention-grabbing animation.

## Flow map
1. Android: launch → unauthenticated → sign in → device onboarding → Home.
2. Security: hub → MFA enrollment/challenge → sessions → device detail → revoke confirmation.
3. Game: catalog → configure adapter → Companion connecting → active → overlay.
4. Intelligence: recommendation → explanation/provenance → acknowledgement → history.
5. Voice: consent → ready → press-to-talk → listening → processing → response or error.
6. Connection: active → degraded/local-only/offline → reconnect → restored.
7. Plan: inactive → choose plan → payment → entitlement activation.
8. Diagnostics: runtime → evidence → export → report.

## Screen and state inventory
Production scope includes the brief's Android authentication/recovery/MFA/provider/device, four main domains, settings and diagnostics; responsive web account/security/games/intelligence/subscription/support/admin; Companion overview/runtime/games/adapters/voice/overlay/diagnostics/updates; overlay density and voice states. Each production screen must specify no data, loading, partial, stale, offline, unavailable, permission denied, failed, and unknown as applicable. This repository contains a representative interactive reference, **not** completed production screens for this entire inventory.

## Engineering transfer
CSS tokens can be translated to Compose color/type/shape schemes and desktop host variables without copying CSS. Centralize status semantics as enum + display metadata. Enforce data provenance and timestamp fields upstream. Android adaptive foreground/background and native Windows ICO/system tray assets require native packaging from an approved optical vector master. No live accounts, payment processing, real-game adapters or runtime telemetry are wired into this design reference; sample values are illustrative only.

## Screen and state inventory (detailed)

### Android
- Pre-auth: launch/splash, unauthenticated shell, sign in, register, email verification, password recovery, MFA challenge, MFA enrollment, recovery codes (shown once, storage confirmation required), provider auth (Google/Telegram/VK), provider linking, device onboarding, device security check.
- Domains: Home, Games (+ game detail, adapter config), Security (hub, account security, MFA, recovery, sessions, devices, device identity, linked providers), Activity (events, alerts, intelligence/recommendations).
- System: Settings (language RU/EN/System, appearance Light/Dark/System, privacy/telemetry), Diagnostics, Updates (available/required), Help, About.
- Physical Test / Staging: compact 24dp indicator strip (environment, version, source SHA, diagnostics/export access). Never a full-width red banner.
- Mandatory states per screen: no data, loading, partial, stale, offline, local-only, reconnecting, provider unavailable, permission missing, unsupported, restricted, failed, unknown, account expired/past-due, session revoked, security warning.

### Web Control Plane
- Overview, Intelligence, Games, Activity, Security hub, Devices, Account, Subscription/Billing (plans, entitlements, lifecycle ACTIVE/PAST-DUE/GRACE/EXPIRED), Settings, Support/quality reporting, Diagnostics.
- Admin (distinct shell): game catalog administration, entitlement management, problem clusters, operational info, diagnostic evidence. Higher density, engineering-oriented, visually separated from the user plane.
- Responsive: large desktop / standard / tablet / mobile; tables become stacked cards on mobile, navigation rail collapses.

### Desktop Companion
- Overview, Account, Runtime, Companion status, Host configuration, Games (+ executable config, launch), Adapters (state, capability discovery), Voice, Overlay config, Diagnostics (logs/evidence export), Updates.
- Runtime states: CONNECTING, ACTIVE, DEGRADED, STOPPED, reconnect, unavailable, entitlement denied.
- Kill switch: always reachable, visually isolated, confirmation-guarded.

### Overlay
- Density profiles: Minimal (one priority action + one system line), Standard, Expanded.
- Patterns: status, warning, recommendation, confidence, threat, objective, brief instruction, voice feedback, connection/degraded. Peripheral-readable, never covers play-critical regions.

### Voice UX
- unavailable, provider unavailable, consent required, ready, press-to-talk, listening, processing, recognized intent, successful response, failed recognition, no speech, timeout, network failure, disabled, privacy. Microphone is never implicitly open; PTT and consent are visually unambiguous.

## Token transfer map (CSS → Compose / Electron)

| Token (styles.css) | Compose | Usage |
|---|---|---|
| --background | colorScheme.background | App canvas |
| --card | colorScheme.surface | Panels, cards |
| --secondary / raised | colorScheme.surfaceVariant | Raised surfaces |
| --primary | colorScheme.primary | Key actions, active states |
| --signal | custom: Signal | Live/trusted signal accent |
| --success / --warning / --destructive | custom semantic colors | Status tones |
| --foreground / --muted-foreground | onBackground / onSurfaceVariant | Text hierarchy |
| --border | outlineVariant | Hairlines |
| radius 4/6/8px | shapes.small/medium/large | Geometry scale |
| spacing 4px grid | 4.dp grid | Layout rhythm |
| touch 44px | 48.dp min touch target | Interactive minimum |
| enter 320ms / transition 180ms | tween(320) / tween(180) | Motion durations |

Statuses transfer as `enum class SentinelStatus` + display metadata (labelRes, icon, tone), never as color-only values. Intelligence items transfer as sealed types Fact/Inference/Recommendation with mandatory provenance and timestamp fields.

## Content design rules
- Calm, precise, non-alarming. State what is known, what is assumed, what is recommended.
- Security language: describe the event and the action available; no fear appeals, no jargon without explanation.
- Destructive actions: name the consequence, require explicit confirmation, offer reversal where possible.
- Errors: what happened, what still works, what to do next. Never a bare error code.
- Status names are stable vocabulary: reuse the exact labels from the status grammar across all surfaces and languages.
- Localization: Russian strings run 30–50% longer than English; layouts must tolerate this without truncation of status labels. Numbers and identifiers use tabular figures and JetBrains Mono.
