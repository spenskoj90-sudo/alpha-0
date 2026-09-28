# SENTINEL User-Visible Acceptance Contract

**Status:** ACTIVE  
**Effective:** 2026-09-28  
**Authority:** Human Owner instruction + canonical GPT-only engineering OS  
**Issue:** #375

## Purpose

SENTINEL engineering evidence must distinguish a technically valid implementation from a product surface that the Human Owner has actually seen and accepted.

The failure mode this contract prevents is explicit: source exists, CI is green, and the assistant describes a surface as "ready" even though the Owner has never opened the actual product and the visual result is still an early or poor-quality foundation.

## Evidence ladder

User-facing surfaces use the following monotonic states:

1. **SOURCE-PRESENT** — relevant source exists.
2. **BUILD-VERIFIED** — deterministic build/lint/tests/security checks pass for an exact SHA.
3. **RUNNABLE** — an exact build can actually be opened on its target platform.
4. **OWNER-VISIBLE** — the Human Owner has opened that exact runnable surface.
5. **OWNER-VISUAL-ACCEPTED** — the Owner explicitly accepts the visual/product state for the stated scope.
6. **RELEASE-ACCEPTED** — all applicable physical/environment/release gates pass for the exact candidate.

A later state includes the earlier states. Never collapse these labels.

## Prohibited readiness shortcuts

For Android, Web Control Plane, Public Website, Companion, Overlay and Voice:

- CI success is not visual acceptance.
- A source tree is not a product-completion claim.
- A screenshot, generated mock or design prototype is not a substitute for the runnable product.
- A screenshot may help review, but cannot by itself satisfy `OWNER-VISIBLE`.
- Design-reference completion does not prove production implementation parity.
- Backend/API completeness does not prove frontend/product completeness.
- "Implemented" and "build-verified" must not be paraphrased to the Owner as "ready", "almost finished" or a completion percentage unless the corresponding user-visible evidence exists.
- Percentage-complete claims are forbidden unless they are derived from an explicit enumerated scope and evidence matrix.

## Surface-specific evidence

### Android

`RUNNABLE` requires an exact APK/install identity. `OWNER-VISIBLE` requires that exact build on the Owner's physical Android device. Automated emulator evidence is supplemental.

### Web Control Plane

`RUNNABLE` requires an exact browser-openable build with the relevant authenticated flows. `OWNER-VISIBLE` requires the Owner to open it in a browser. API tests and a screenshot are insufficient.

### Public Website

`RUNNABLE` requires an exact browser-openable site build. Preferred evidence is an Owner-approved non-production preview URL bound to the exact SHA; an exact static artifact opened by the Owner is acceptable when preview hosting is not yet authorized. A PNG/JPEG preview alone is insufficient.

### Companion / Overlay / Voice

`RUNNABLE` requires the exact packaged host build on the intended Windows environment. `OWNER-VISIBLE` requires Owner review on that host. CI packaging/smoke evidence remains engineering evidence, not visual acceptance.

## Design-reference synchronization

Production design parity is claimable only when:

1. the design-laboratory pass has a declared final SHA;
2. production records that exact SHA as the adopted reference;
3. screen/component/token/asset registries are reconciled;
4. native Web/Android/Companion/Overlay implementations are migrated;
5. the resulting runnable surfaces receive Owner-visible acceptance.

An in-progress design-lab commit must not be adopted merely to make the repositories look synchronized.

## Reporting rule

Every user-facing status report must state the highest evidenced state, not the most optimistic interpretation.

Examples:

- correct: "Public Website: BUILD-VERIFIED, not Owner-visible, foundation only."
- incorrect: "The website is basically ready."
- correct: "Web Control Plane API/session foundation is implemented; product UX is incomplete and not Owner-visually accepted."
- incorrect: "Web is 90% done."

## Release binding

The final `publication` profile includes the `product-visual` gate. It is all-PASS only after exact-candidate Owner review includes:

- final design-reference reconciliation;
- Android;
- Web Control Plane;
- Public Website;
- Companion;
- Overlay;
- Voice surface;
- responsive target form factors;
- loading/empty/error/offline/degraded states;
- cross-surface brand consistency;
- retained runnable/preview evidence.

This contract does not authorize production/live deployment. Creating a hosted preview remains subject to the Owner's live-deployment authority boundary.
