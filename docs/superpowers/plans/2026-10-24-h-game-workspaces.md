# H game workspaces continuation

Spec: docs/DESIGN_PROGRAM_H_V2.md and design/h-system/HANDOFF.md.
Execution: Owner already approved autonomous implementation and deferred selection.
Base main: f81f70da743fa1528b919f198f1a34cf9fdaf5c5; nine post-merge workflows successful.

## Design decisions
- Extend isolated dependency-free preview. Never change native production v3.
- Distinct character/builds/talents/PvE/PvP/rotation/auction/profession/quest/economy/battle compositions.
- Default missing-source state. Opt-in fixture switch reveals invented illustrative data, never a live source.
- Local filters, pagination, compare selection, bounded talent allocation, recipe quantity and quest checklist persist across SPA navigation/locale/theme. Never enable game execution.
- Tablet Android shell uses navigation rail and master/detail; phone remains mobile-specific. Preview chrome exposes phone/tablet study sizing explicitly.
- Preserve source/freshness/compatibility/Stop. Figma synchronization is externally blocked by Starter quota; save editable HTML/SVG/specification in git for later translation.

## Implementation/checks
- [ ] Add pure workspace reducer and module fixtures; test bounds, independent module state, reset and execution-disabled invariant first.
- [ ] Create module renderer in a separate file, using escaped content and semantic controls. Integrate local event handling without production APIs.
- [ ] Add tablet layout and purposeful controls; test desktop/mobile, RU/EN, history/theme persistence, keyboard, unknown/stale/Stop, no horizontal overflow.
- [ ] Expand browser journeys and visual screenshots. Run full existing matrix plus new scenarios and repository checks.
- [ ] Independent final review; commit/PR and exact-SHA CI integration under existing gates. Production deployment/release/Owner selection remain separate.

## Ledger
- Workspace implementation and tablet shell added in isolated study only.
- Independent review found cross-page download progress corruption; reproduced RED and fixed via specific #update-progress target.
- Ruling: preserve daily integration policy; prepare follow-up draft for next batch after today's merged #523, without a second same-day merge.
- Figma quota probe still rejected; do not claim new workspaces are synchronized.
