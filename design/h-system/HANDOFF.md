# H pass evidence and continuation — 2026-10-24

## Source and implementation boundaries

Base main: `5e8a2b3a1001b81dad462ab9ceede9299acb8c55`.
Branch: `design/h-interactive-system-20261024`.
Owner contract: `docs/DESIGN_PROGRAM_H_V2.md` / `design/h-design-program.v2.json`.
Only the isolated H study, its evidence and a preview-verification workflow are added.
Production app/site/Web/Companion code, v3 tokens, permission policies and releases
are untouched. AUTOMATIC_EXECUTION_DISABLED remains in force.

## Results that were actually verified

- Browser: 276 direct route × locale × viewport checks (69 routes × RU/EN ×
  390/1440), internal links checked against authored routes; no page errors.
- 14 scenario checks: explicit consent, observation, revoke, persistent Stop,
  stale/recovery without resume, MFA rejection/success, denied Admin, update
  failure/rollback-unavailable, Overlay density/Stop, menu/history/locale,
  legal-page section links, named dialogs/Escape/focus return, reduced motion,
  Windows demo exit and resolved light-theme foreground/background.
- Six model/contrast tests: stop/revoke/stale and direct routing plus AA text token
  pairs and 3:1 input-boundary pairs in both provisional light/dark themes.
  This is a limited measured token check, not full accessibility certification.
- `bash verify.sh`: 84 passed / 0 failed locally.
- Visual browser inspection: home, brand comparison, Android capture, Windows
  overview and corrected mobile light theme; screenshots in `qa/`.
- Figma: 166 route/state frames, 23 component sets, 108 variants, 955 instances,
  no image-filled UI nodes, no horizontal overflow among direct screen children.
  Actual font families: Onest, Inter, JetBrains Mono.
- Figma EN audit found twelve inherited bilingual strings; all were corrected
  through component properties, remaining Cyrillic in EN route/state frames: zero.
- Figma screenshots inspected: primary brand studies, component buttons,
  Android permission, revoked state and public homepage. Further full-screen
  and state-by-state visual QA remains open.

## Defects found and corrected during the pass

- Mobile Windows navigation expanded its grid column to content width: sidebar
  min-width now permits contained horizontal navigation without page overflow.
- SPA interception discarded legal-page hash links: same-page anchors now retain
  native browser scrolling/hash behavior.
- Light theme changed variables under a root-computed foreground/background:
  body now resolves and paints its own theme values. Regression test fails on
  the original behavior and passes after the fix.
- Independent reviewer found Windows demo sign-out targeted an absent sign-in
  route: Windows exits to Launcher. Browser regression verifies Stop plus route.
- Dialog accessible-name association and keyboard focus return were added.
- Initial identity geometry was too fragmented at small sizes: Confluence and
  Waypoint were redrawn before their final exports.
- Figma paint aliases could display their temporary fallback color: concrete
  fallback colors and explicit provisional modes were repaired and visually checked.

## External limit reached, not an Owner action request

Figma Starter exhausted its MCP call allowance after the major authoring pass.
The final attempt to raise Figma border contrast and reinforce focus variants was
rejected by the provider and did not apply. Browser token fixes are applied and
pass; Figma still needs matching border/focus calibration. No paid upgrade was made
or requested. Resume when provider calls are available, using the saved node IDs.

## Next bounded implementation pass

1. Match Figma border tokens to browser `#647990` dark / `#687c95` light and verify
   focus rings. Repeat the specific component screenshot after the change.
2. Develop the 23 families beyond baseline templates: interactive switch/checkbox
   state reactions, complete variant applicability, dialog/menu behavior, dense
   tables, content-aware game metrics and larger text. A generic UNKNOWN card is
   a truthful skeleton, not a finished gameplay module.
3. Create tablet/master-detail frames and desktop window breakpoints, native
   system inset/keyboard designs, detailed WoW module flows and full brand
   splash/tray/installer/PWA compositions. Retain current production v3.
4. Refine bespoke wordmarks and optical corrections for all 55 icons; compare
   the full journeys across all five directions, not just accent changes.
5. Complete light/dark and high-contrast/responsive visual coverage, native
   TalkBack/NVDA/OEM/high-DPI testing when translated to real platform apps.
6. Only after the full interactive system reaches the Owner's stated quality gate,
   present the brand/direction choice. Do not ask for palette selection now.

No native runtime, physical host/device, Owner-visible, Owner-accepted or release
acceptance has been inferred from these source/prototype results.
