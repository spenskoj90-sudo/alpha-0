# SENTINEL Cross-Surface Design System v1

**Status:** ACTIVE  
**Machine-readable contract:** `design/sentinel-design-system.v1.json`  
**Visual design anchor:** https://www.figma.com/design/vRIHsesWZNMEEEjNJu8TjB  
**Purpose:** keep Web, Android and Companion visually coherent and semantically equivalent without erasing platform-specific implementation constraints.

## Authority model

The design system is **semantic-first**. A semantic role such as `primary`, `signal`, `danger`, `surface`, `focus` or `observational` has one product meaning across surfaces, but its raw visual alias may differ by platform.

This is deliberate. Web and Companion currently share the dark green/blue operational palette. Android has an established Compose palette with violet primary, cyan signal, Outfit display type, Inter body type and JetBrains Mono data type. The contract does not rewrite one mature surface merely to make hexadecimal values identical. It prevents semantic drift instead.

The executable source of truth is the combination of:

1. `design/sentinel-design-system.v1.json` — semantic roles, aliases, component mappings and acceptance partition;
2. `scripts/test_design_system.py` — drift verification against live implementation sources;
3. this document — human-readable design and accessibility contract;
4. the Figma file above — visual design anchor and reusable component workspace.

Live code and exact-SHA CI remain implementation evidence. Figma alone is never proof that a runtime implements a design.

## Figma structure

The canonical Figma file was created for SENTINEL and contains repository-derived foundations and reusable component states. At minimum the authored design inventory contains:

- `00 Foundations` — repository-bound color foundations and design principles;
- `01 Components` — primary/secondary/focus actions, status states, operational/fail-closed/observational card states.

The design file is intended to grow as a visual workspace, but screen completeness in Figma is not allowed to become a hidden release gate. Screen behavior, accessibility and authority semantics are bound directly to code by the machine-readable manifest and CI test. This avoids treating a design-tool service quota or stale mockup as stronger evidence than repository reality.

## Shared product principles

All interactive surfaces must preserve these meanings:

- **security-first / default-deny:** unavailable authority is shown as unavailable; the UI must not infer permission from stale local state;
- **server-authoritative state:** billing, entitlement, session and other authority-bearing state comes from Core or the owning trusted boundary;
- **observational recommendations:** recommendation and overlay output is presentation-only and never implies autonomous gameplay authority;
- **explicit state:** color may reinforce state but text/semantics must carry the meaning;
- **visible focus:** keyboard focus is visually explicit;
- **accessible dynamic state:** live updates use the surface-appropriate announcement semantics;
- **bounded responsive behavior:** narrower layouts collapse rather than clipping critical authority/status content.

## Surface aliases

### Web personal control plane

Implementation anchors:

- `web/app/globals.css`
- `web/app/page.tsx`
- `web/app/components/account-control.tsx`
- `web/app/components/recommendation-panel.tsx`

The current Web palette uses:

- background `#070A0D`;
- panel `#0D1217`;
- raised panel `#111820`;
- text `#E7EDF2`;
- secondary text `#8996A3`;
- primary/healthy accent `#9ACB52`;
- focus/information `#4CA3FF`;
- danger `#FF6B6B`;
- border `#1D2832`.

Cards use a 16 px outer radius, nested operational surfaces use 12 px, ordinary controls use 10 px. The layout collapses to one column below the current 800 px breakpoint.

The Web surface must retain skip navigation, a focusable main landmark, visible focus, forced-colors behavior and live status/error semantics.

### Android

Implementation anchors:

- `app/src/main/java/com/alpha0/app/ui/DesignTokens.kt`
- `app/src/main/java/com/alpha0/app/ui/SentinelTheme.kt`
- `app/src/main/java/com/alpha0/app/ui/AccessibilitySemantics.kt`
- `app/src/main/java/com/alpha0/app/ui/CharacterDashboard.kt`

Android deliberately retains its platform palette:

- background `#0D1117`;
- surface `#161B22`;
- border `#30363D`;
- primary `#B356FF`;
- signal `#00E5FF`;
- danger `#FF3366`;
- primary text `#F0F6FC`;
- secondary text `#8B949E`.

Typography roles are Outfit for display, Inter for body and JetBrains Mono for data. `StatusBadge`, `SentinelCard`, `PrimaryButton`, `DangerButton` and accessibility semantic modifiers are the reusable Compose anchors.

API 35 instrumentation is the routine automated device-level gate. Physical TalkBack/device acceptance is deliberately deferred to final pre-release validation.

### Companion launcher and overlay

Implementation anchors:

- `launcher/index.html`
- `launcher/overlay.html`
- launcher renderer/runtime files for state transitions.

The launcher shares the Web operational palette and interaction language. It must retain skip navigation, visible focus, live status regions, forced-colors support and explicit disabled states.

The overlay is a distinct transparent presentation surface. It is click-through/read-only, announces presentation changes politely, accepts only sanitized presentation state from the trusted runtime path, and must not visually imply game-write authority.

## Reusable semantic component map

| Semantic component | Web | Android | Companion |
| --- | --- | --- | --- |
| Primary action | `.btn` | `PrimaryButton` | `.btn` |
| Destructive/terminal action | explicit danger action/state | `DangerButton` | `STOP / KILL SWITCH` |
| Dynamic status | `.state` / `.status-message` | `StatusBadge` + semantics | `.status` |
| Operational card | `.card` | `SentinelCard` / Material Card | `.panel` / `.card` |
| Recommendation/presentation | `RecommendationPanel` | presentation UI only | read-only overlay presentation list |

A mapping is valid only if both visual state and authority semantics remain equivalent. Matching color alone is insufficient.

## Accessibility contract

Repository-automated acceptance now covers the semantics that can be verified deterministically:

- Web/Companion keyboard focus and skip navigation;
- Web forced-colors behavior;
- Web/Companion live status regions;
- Android live-region/progress/button/card semantics;
- API 35 emulator instrumentation;
- responsive source contracts and disabled-state behavior;
- text-bearing status states rather than color-only status.

The following are intentionally final pre-release physical acceptance, not current implementation blockers:

- TalkBack on the selected Android release device;
- NVDA/JAWS and keyboard/switch behavior on the selected packaged Windows host;
- real packaged overlay positioning/click-through behavior on the selected host;
- physical microphone/driver/acoustic-quality acceptance;
- exact WoW 3.3.5a/private-server L3 acceptance.

## Drift policy

`scripts/test_design_system.py` fails if canonical aliases or key accessibility/component anchors stop matching implementation. `verify.sh` executes that test as part of routine repository verification.

Changing a semantic role therefore requires changing the manifest, implementation and documentation coherently in the same engineering pass. Cosmetic Figma exploration may precede implementation, but it is not an implementation claim until the repository contract moves with it.

## Non-claims

This contract does not claim physical-device certification, production provider readiness, signed release execution, publication, or live deployment. Those gates remain separate and are intentionally deferred to the final release phase where applicable.
