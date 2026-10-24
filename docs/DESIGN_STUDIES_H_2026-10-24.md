# SENTINEL — Block H design directions, Owner visual review

**Status:** DRAFT_FOR_OWNER_REVIEW — five design studies, not a production change.
**Created:** 2026-10-24
**Source basis:** protected main `67b79a451c6508b1d61621097270689e6c9c784f`
**Editable Figma:** https://www.figma.com/design/BdF9XW7eYmZrOkdnnH98Jc
**Machine registry:** [h-design-studies.v1.json](../design/h-design-studies.v1.json)

## What is ready for comparison

The Figma file has **five boards in Russian and five boards in English**. Each board contains four identical product scenarios: **B Android** (game observer), **C Windows/World of Warcraft** (Companion and Overlay), **D authenticated Web Control** and **E Public Website**. Total: **40 editable native Figma-layer screens**, not flat screenshots. Both locale pages were visually inspected; no Russian UI copy remains in the EN page's editable text nodes.

The content is deliberately truthful: Android observation is an OCR diagnostic PILOT, WoW 3.3.5a live-source support is UNVERIFIED, active game execution is DISABLED and public downloads are not advertised as available. This design evidence does NOT equal a runnable Android build, packaged Windows app, actual browser acceptance or visual Owner acceptance.

## Five directions

| ID | Visual concept | Strong use | Tradeoff |
| --- | --- | --- | --- |
| **H01** | **Calm Precision** — current navy/cyan/teal v3 | Engineering trust and current production continuity | Less game-specific |
| **H02** | **Sentinel Command** — graphite, ice-blue, tight operational structure | Windows operations and urgent control | Can be dense on mobile |
| **H03** | **Tactical Slate** — charcoal, muted tactical green | Readable game/Overlay information | Operational signal needs distinct semantics |
| **H04** | **Signal Minimal** — light canvas, dark teal and whitespace | Android, account, public site | Needs dedicated night/overlay styling |
| **H05** | **Intelligence Atlas** — ink/indigo, lilac intelligence and teal signals | Build recommendations and replay analysis | Added accents require strict state meanings |

Both pages use the same facts, statuses, navigation and CTAs to make comparisons fair. Figma board references and colors are bound in the machine study manifest.

## Quality and limitations

The five sample palettes passed a calculated **WCAG 2.1 AA contrast ratio of at least 4.5:1** for these five specified pairs: main text/background, muted text/surface, accent/background, operational signal/surface and warning/raised surface. Exact values are stored in the JSON manifest. **This is a limited token contrast measurement, not comprehensive accessible-interface certification**.

Current studies are representative **compact cross-platform compositions**: they do not yet include every desktop breakpoint, native Figma component library, physical TalkBack/NVDA testing or clickable runtime. Native screens must later verify minimum Android 48dp and Web/Companion 44px targets, focus, forced colors, reduced motion, RU/EN string wrapping, privacy, unavailable states, and readable Stop/consent. No logo replacement is approved; studies use text SENTINEL, retaining the existing shield/S/signal production asset authority.

## 2026-10-24 Owner refinement — selection postponed

The Owner approved a wider **[H1–H11 design program](DESIGN_PROGRAM_H_V2.md)** before choosing a visual direction. These 40 Figma compact RU/EN comparison screens remain useful preliminary palette studies, but are not enough to request approval. Produce the new brand/app-icon options, coherent icon system, interactive component variants, page navigation and real multi-route Web/Website, Android and PC product architecture first. Existing production shield/S artwork remains installed until a new identity has been accepted and translated; do not mistake creative deprecation for approval to delete a production asset. No visual style or color has been selected.

## Owner selection and subsequent engineering

The Owner should view both Figma pages and select **exactly one** visual direction (or specify modifications). Selection is currently **PENDING**; v3 **remains ACTIVE** in `design/sentinel-design-system.v3.json`, `docs/DESIGN_SYSTEM_V3.md` and all product apps. No source code or production tokens were changed by these mockups.

After Owner selection: freeze one stable approved Figma reference; write an explicit native design token/component contract; translate each B/C/D/E screen to Compose/Electron/Next.js/site; run exact-source and UI visual/runnable tests; obtain actual Owner-visible acceptance separately. Release/physical/signing/production gates are unchanged. No unfinished Lovable import or game input activation.

## Visual review criteria

Brand recognition across all four surfaces; Android readability; WoW overlay and always-reachable Stop; meaningful status/provenance/UNKNOWN; Web security clarity; public site's non-misleading availability; bilingual copy; dark/light suitability; keyboard/TalkBack readiness and maintainability. Figma files are reference designs, not a final acceptance artifact.
