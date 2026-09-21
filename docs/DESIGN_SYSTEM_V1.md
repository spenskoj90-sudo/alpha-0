# SENTINEL Cross-Surface Design System v1

**Status:** ACTIVE  
**Machine-readable contract:** `design/sentinel-design-system.v1.json`  
**Visual design anchor:** https://www.figma.com/design/vRIHsesWZNMEEEjNJu8TjB  
**Purpose:** keep Web, Android and Companion visually coherent and semantically equivalent without erasing platform-specific implementation constraints.

## Authority model

The design system is **semantic-first**. A semantic role such as `primary`, `signal`, `danger`, `surface`, `focus` or `observational` has one product meaning across surfaces, but its raw visual alias may differ by platform.

The current system deliberately converges all product surfaces on one calm security-instrumentation family: deep naval backgrounds, steel-blue surfaces, cyan primary signal, restrained teal secondary signal/success, and soft red danger. Platform-specific implementation remains appropriate, but the product no longer uses a separate violet Android identity or green Companion identity.

The executable source of truth is the combination of:

1. `design/sentinel-design-system.v1.json` — semantic roles, aliases, implementation mappings, exact known Figma-node mappings and acceptance partition;
2. `scripts/test_design_system.py` — drift verification against live implementation sources and the repository-side Figma inventory contract;
3. this document — human-readable design and accessibility contract;
4. the canonical Figma file above — visual foundations anchor and future reusable-component workspace.

Live code and exact-SHA CI remain implementation evidence. Figma alone is never proof that a runtime implements a design, and repository text must not claim Figma nodes that do not exist.

## Figma structure and current mapping

Connected Figma inspection on 2026-09-16 found one authored top-level page in the canonical file:

- `00 Foundations` (`0:1`) — repository-bound Web/Companion color foundations and product principles;
- `SENTINEL Foundations` frame (`1:4`) — the concrete token frame used by the repository mapping.

The previously documented `01 Components` page is **not present in the connected canonical Figma file**. The machine-readable contract therefore no longer claims it. Reusable component semantics still exist in code and in the manifest, but their Figma field is explicitly `UNAUTHORED` until concrete component nodes are actually created and inspectable.

The current foundations mapping is explicit rather than inferred:

| Semantic role | Figma frame / swatch | Web code anchor |
| --- | --- | --- |
| background | `1:8` / `1:9` | `--bg` |
| surface | `1:11` / `1:12` | `--panel` |
| raised surface | `1:14` / `1:15` | `--panel-2` |
| primary text | `1:17` / `1:18` | `--text` |
| secondary text | `1:20` / `1:21` | `--muted` |
| primary action | `1:23` / `1:24` | `--accent` |
| signal / focus | `1:26` / `1:27` | `--accent-2` |
| danger | `1:29` / `1:30` | `--danger` |
| border | `1:32` / `1:33` | `--border` |

This is intentionally a narrow truth claim. Screen completeness in Figma is not a hidden release gate. Screen behavior, accessibility and authority semantics are bound directly to code by the machine-readable manifest and CI test.

## Shared product principles

All interactive surfaces must preserve these meanings:

- **security-first / default-deny:** unavailable authority is shown as unavailable; the UI must not infer permission from stale local state;
- **server-authoritative state:** billing, entitlement, session and other authority-bearing state comes from Core or the owning trusted boundary;
- **observational recommendations:** recommendation and overlay output is presentation-only and never implies autonomous gameplay authority;
- **explicit state:** color may reinforce state but text/semantics must carry the meaning;
- **visible focus:** keyboard focus is visually explicit;
- **accessible dynamic state:** live updates use the surface-appropriate announcement semantics; operation progress is exposed as busy state where applicable and failures requiring attention use assertive/error semantics;
- **bounded responsive behavior:** narrower layouts collapse rather than clipping critical authority/status content.

## Surface aliases

### Web personal control plane

Implementation anchors:

- `web/app/globals.css`
- `web/app/page.tsx`
- `web/app/components/account-control.tsx`
- `web/app/components/recommendation-panel.tsx`

The current Web palette uses:

- background `#07121F`;
- panel `#0D1B2A`;
- raised panel `#13263A`;
- text `#F1F8FC`;
- secondary text `#9EB4C5`;
- primary action `#70DBFF`;
- signal/focus `#5BE3D0`;
- danger `#FF6F82`;
- border `#27445D`.

Cards use a 20 px outer radius, nested operational surfaces use 16 px, ordinary controls use 14 px. The layout collapses to one column below the current 800 px breakpoint.

The Web surface must retain skip navigation, a focusable main landmark, visible focus, forced-colors behavior, live status/error semantics, operation busy state and plan-specific accessible names for repeated billing actions. Password requirements must be programmatically associated with the password field rather than existing only as an implicit validation rule.

### Android

Implementation anchors:

- `app/src/main/java/com/alpha0/app/ui/DesignTokens.kt`
- `app/src/main/java/com/alpha0/app/ui/SentinelTheme.kt`
- `app/src/main/java/com/alpha0/app/ui/AccessibilitySemantics.kt`
- `app/src/main/java/com/alpha0/app/ui/CharacterDashboard.kt`

Android uses the same semantic visual family as Web and Companion:

- background `#07121F`;
- surface `#0D1B2A`;
- raised surface `#13263A`;
- border `#27445D`;
- primary `#70DBFF`;
- signal `#5BE3D0`;
- danger `#FF6F82`;
- primary text `#F1F8FC`;
- secondary text `#9EB4C5`.

The shared Compose card radius is 20 dp and action radius is 16 dp. Decorative scan-line/HUD motion is intentionally absent from the shared card primitive.

Typography roles are Outfit for display, Inter for body and JetBrains Mono for data. `StatusBadge`, `SentinelCard`, `PrimaryButton`, `DangerButton` and accessibility semantic modifiers are the reusable Compose anchors.

API 35 instrumentation is the routine automated device-level gate. Physical TalkBack/device acceptance is deliberately deferred to final pre-release validation.

### Companion launcher and overlay

Implementation anchors:

- `launcher/index.html`
- `launcher/renderer.js`
- `launcher/overlay.html`

The launcher shares the Web naval/cyan/teal palette, the shield/S/radar identity, and the same interaction language. It must retain skip navigation, visible focus, live status regions, forced-colors support, explicit disabled states and an `aria-busy` operation boundary for account work. Routine status changes remain polite; bounded runtime failures that require immediate user awareness are promoted to assertive alert semantics and return to polite status semantics on the next normal update.

The overlay is a distinct transparent presentation surface. It is click-through/read-only, announces presentation changes politely, accepts only sanitized presentation state from the trusted runtime path, and must not visually imply game-write authority.

## Reusable semantic component map

| Semantic component | Web | Android | Companion | Figma |
| --- | --- | --- | --- | --- |
| Primary action | `.btn` | `PrimaryButton` | `.btn` | `UNAUTHORED` |
| Destructive/terminal action | explicit danger action/state | `DangerButton` | `STOP / KILL SWITCH` | `UNAUTHORED` |
| Dynamic status | `.state` / `.status-message` | `StatusBadge` + semantics | `.status` | `UNAUTHORED` |
| Operational card | `.card` | `SentinelCard` / Material Card | `.panel` / `.card` | `UNAUTHORED` |
| Recommendation/presentation | `RecommendationPanel` | presentation UI only | read-only overlay presentation list | `UNAUTHORED` |

A mapping is valid only if both visual state and authority semantics remain equivalent. Matching color alone is insufficient. `UNAUTHORED` means there is deliberately no claimed Figma component node yet; it does not mean the runtime component is absent.

## Accessibility contract

Repository-automated acceptance covers the semantics that can be verified deterministically:

- Web/Companion keyboard focus and skip navigation;
- Web forced-colors behavior;
- Web/Companion live status regions and explicit busy state for bounded async work;
- assertive error semantics for failures requiring attention while ordinary runtime status remains polite;
- Web password requirement association and repeated plan-action accessible names;
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

`scripts/test_design_system.py` fails if canonical aliases, known Figma inventory metadata or key accessibility/component anchors stop matching implementation. `verify.sh` executes that test as part of routine repository verification.

Changing a semantic role therefore requires changing the manifest, implementation and documentation coherently in the same engineering pass. Figma may evolve independently as a visual workspace, but a repository claim that a Figma page/component exists must be backed by an inspectable node mapping before it is treated as authored.

## Non-claims

This contract does not claim physical-device certification, production provider readiness, signed release execution, publication, or live production deployment. Those gates remain separate and are intentionally deferred to the final release phase where applicable.
