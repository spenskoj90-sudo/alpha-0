# H interactive design system implementation plan

> Execute directly under the Owner-approved DESIGN_PROGRAM_H_V2.md. No intermediate palette-selection gate.

Goal: deliver editable identity/icon/component foundations and navigable bilingual product studies without changing production v3.
Architecture: isolated dependency-free design/h-system browser prototype, reusable vector assets and Figma component library; no backend credentials or gameplay execution.
Spec: docs/DESIGN_PROGRAM_H_V2.md and design/h-design-program.v2.json.

## Constraints
- Production v3 remains ACTIVE; brand and palette unselected.
- AUTOMATIC_EXECUTION_DISABLED; all displayed example telemetry is labelled demo.
- No production deployment, release or signing.
- Inter UI, Onest display, JetBrains Mono evidence; RU/EN; 48px study controls.

## Tasks
- [ ] H1/H2: four distinct vector identities and required optical proof sizes; unified domain icon masters. Validate SVG structure and inventory.
- [ ] H3/H4: semantic tokens, editable Figma variables and reusable components with applicable states. Validate component hierarchy and visual screenshots.
- [ ] H5-H9: isolated multi-route preview and detailed platform-specific journeys; public pages individually authored. Test direct routes, history, locale, keyboard, permission revocation, stale recovery and Stop.
- [ ] H10/H11: vector illustrations, responsive/reduced motion/contrast checks and visual QA. Record exact evidence and remaining native/physical gaps.
- [ ] Review branch, PR, exact-HEAD CI, merge only after repository gates pass; post-merge source verification. Keep incomplete H scope explicit.

## Review focus
Revoked permission cannot leave observation active; Stop survives navigation; unknown telemetry cannot appear healthy; direct routes preserve surface/locale; admin demo cannot imply actual authorization.

## Execution ledger
- First vertical pass delivered isolated vector/route/component foundations. Detailed H completion remains open; see design/h-system/HANDOFF.md.
- Browser 276 route/locale/viewport combinations + 14 scenarios passed; six model/contrast tests passed; repository verification 84/84.
- Independent review found a Windows sign-out route defect; fixed and browser-regressed. Named dialogs, focus assertions and internal-link coverage also added.
- Ruling: retain all current production UI and v3; study source remains separate as explicitly required by the Owner.
- Figma external MCP limit prevents the final border/focus calibration; saved exact node IDs enable resumption without rediscovery. No purchase or palette request.
