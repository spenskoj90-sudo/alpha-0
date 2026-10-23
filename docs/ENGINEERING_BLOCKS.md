# SENTINEL — инженерные блоки A–I

**Status:** ACTIVE
**Owner-approved:** 2026-10-23
**Machine contract:** [engineering-blocks.v1.json](engineering-blocks.v1.json)
**Authority:** Human Owner → root AGENTS.md → current governance/security/release contracts → relevant scoped AGENTS.md → live protected main at an exact SHA.

## Permanent block registry

| ID | Block | End-to-end ownership |
| --- | --- | --- |
| **A** | **REPOSITORY** | GitHub branches, safe branch reconciliation, files/folders, current vs historical docs, issue/task state, dependencies, audits, CI and policy drift |
| **B** | **ANDROID** | Complete Android app, connected games, permissions/video capture/OCR, intelligent recommendations, opt-in active assistance, game modules, Keystore/privacy, Android/OEM version support, native design and physical performance |
| **C** | **WINDOWS / PC** | Windows packaged Companion/Overlay/Voice, PC games and WoW: characters, talents/glyphs/gear, PvE/PvP rotations and nonstandard builds, opt-in assistance, auction/trading/economy, gathering/crafting/professions, quests/leveling and security/host performance |
| **D** | **WEB CONTROL** | Authenticated web account/device/game/security/entitlement/admin workflows, native web design and testing |
| **E** | **PUBLIC WEBSITE** | Public product/game pages, pricing/availability truth, safe downloads, navigation, accessibility and responsive UX |
| **F** | **CORE / CLOUD** | Shared API, identity/policy, PostgreSQL/RLS, providers, billing, event workers, staging/operations, recovery and observability |
| **G** | **INTELLIGENCE ENGINE** | Shared knowledge/game-state/provenance contracts, versioned modules, inference, replay/evaluation, action-policy boundaries |
| **H** | **DESIGN SYSTEM** | Five comparable visual studies, single Owner-approved brand system, component/tokens, native platform adaptation and optical/accessibility review |
| **I** | **RELEASE / DISTRIBUTION** | Artifact generation, update channels, signer/credential custody boundary, attestation, exact-candidate acceptance, publication/deployment |

The machine contract specifies stable sub-block IDs (**B1–B10**, **C1–C14**, etc.). Block names are **work ownership**, not instructions to rename the existing `app/`, `server/`, `web/`, `site/`, `launcher/` or `wow-addon/` source folders.

## Selection and delivery

The Owner may choose any block at any time, e.g. “Блок B — Android”, “C5 — WoW PvP”, or “A — привести репозиторий в порядок”. GPT performs one compact live reconciliation and works on that selected direction. The user-facing platform owns each feature **through completion**: implementation, its **native design/UI**, security/privacy, OS/device/game/version compatibility, performance and resources, localization/accessibility, tests, staging/device evidence and current documentation. When a platform vertical needs API, shared AI logic, design tokens or packaging work, those F/G/H/I changes are included in the same coherent platform pass, not deferred as a half-finished future block. General shared-platform improvements can also be selected independently under F/G/H/I.

Work on one game must include that game's actual capability/profile status, user-visible provenance, missing-source failure state, version-specific checks and all relevant platform quality gates. A catalog entry, screenshot, simulated replay or green build does not prove supported realtime gameplay, installed content or Owner acceptance. Do not treat old **Block B/C/D productization** entries in TASKS.md as completion of these newly named blocks. Historical issue closure is not acceptance.

## Owner-approved optional active game assistance

**2026-10-23 product decision:** actively develop a **switchable** assistant for Android games (B) and Windows/WoW (C): OFF, advisory, user-confirmed actions, and bounded active mode **only for verified permitted environments**. The desired PC scope includes combat, health/resource management, PvE and PvP tactical rotations and alternative talent builds, quests/leveling, auction/trade, gathering and crafting/professions; Android adapts each scenario to the actual selected game's lawful capabilities. Each assistance module must expose its own toggle and a reachable Stop.

**Implementation truth:** `AUTOMATIC_EXECUTION_DISABLED` remains in force. This product authorization is **not** permission to circumvent anti-cheat, impersonate server authority, inject into arbitrary games, automate on a server against operator rules or unilaterally enable game:write. An execution slice requires exact source/environment verification, explicit user consent and lawful operator/game permission, entitlement/policy/Action Gateway checks, fresh observable state, limits and immediate Stop/manual override, revocation handling, bounded action outcomes and independent physical/synthetic evidence. Start with a permitted owned stand and one action; fail closed on unknowns. SavedVariables are passive checkpoints, not realtime WoW IPC. Android MediaProjection has its own session-consent and version requirements.

As of the adoption review, Android's Shattered Pixel Dungeon source is a diagnostic OCR observer pilot only; field freshness/physical calibration and stable-signer upgrade acceptance remain unresolved. Windows WoW private-server 3.3.5a exact L3 and actual active gameplay are **unverified**. Other catalogue items must retain their distinct research-only/unverified status. See [TASKS.md](TASKS.md), [PLAYER_INTELLIGENCE_ROADMAP_V1.md](PLAYER_INTELLIGENCE_ROADMAP_V1.md) and game source contracts.

## H — Design selection (not yet approved)

Five candidates will be compared on the **same** Android Dashboard/Game Assistant, Windows Companion/WoW Overlay, Web Control and Public Website screens: **Calm Precision** (incumbent Design System v3), **Sentinel Command**, **Tactical Slate**, **Signal Minimal**, **Intelligence Atlas**. Include RU/EN, readable dark/light themes or compatible host mode, device responsiveness, warnings/unknown/Stop, accessibility and actual native interactions. The Owner then approves one; GPT translates it into each platform's native UI. **Until that approval, Design System v3 and its machine token contract remain ACTIVE.** Do not import unfinished Lovable/design-lab work.

## Release and evidence boundaries

The workflow contract and protected-main exact-SHA PR/CI checks are unchanged. Keep SOURCE, BUILD, RUNTIME, OWNER-VISIBLE, OWNER-ACCEPTED and RELEASE-ACCEPTED distinct. Existing `publication` candidate requirements cover Android, packaged Windows Companion, exact WoW L3, voice and Owner-visible accessibility/UX. Routing work by platform does **not** implicitly split the release acceptance profile or waive signing, physical, operator/legal, credentials or Owner-only gates.

## Block A maintenance policy

A inspects the **live** GitHub ref list, PR merge metadata, semantic branch-only diffs and release documents; cleans stale duplicate working-tree material only after canonical replacements are active. A dated Git inventory is evidence, never a permanent authority. A branch with unique/unreviewed commits remains held even if other branches are merged. Do not update a deletion manifest or trigger irreversible cleanup merely from an old snapshot or a squash merge's `ahead` count. The 2026-09 branch ledger is historical; main is authoritative. Preserve Git history instead of adding tombstone docs.

Recommended opening sequence: **A → H → any Owner-selected platform**. This recommendation is not a scheduling lock: the Owner can choose B/C/D/E/F/G/I immediately.
