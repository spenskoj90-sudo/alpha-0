# Design System v3 migration

SENTINEL Design System v3.0 is the active visual authority. v2.1 remains historical reference.

The migration preserves authentication, session, device proof, MFA, entitlement, localization and API authority semantics. It replaces shared visual primitives, Android primary navigation and physical-test chrome, calibrates Web and Companion geometry, constrains Overlay to one meaningful presentation at a time, and applies FACT / INFERENCE / RECOMMENDATION grammar.

Production remains native to alpha-0. The design laboratory is reference-only and no Lovable/TanStack application architecture is imported into production.

Initial v3 reference: `spenskoj90-sudo/sentinel-aware-companion@60629603299fd8af035c6f05991482cde0363c33`.

Reviewed native study reference (not the imported registry pin): `spenskoj90-sudo/sentinel-aware-companion@a6fc9d4c513dde9d549e5dd70159b1365a76b95c` (2026-09-27). The 13-commit design-laboratory delta adds Voice, Admin, Access, Billing and Resilience studies plus expanded handoff documentation. It does **not** supersede native production architecture or security authority.


## Companion / Voice / Resilience reconciliation · 2026-09-27

The latest design-reference Voice and Resilience studies are translated into the native Electron launcher without changing runtime authority:

- Companion exposes explicit FULL / DEGRADED / LOCAL-ONLY / OFFLINE connection states;
- Voice uses hold-to-talk semantics with explicit consent, visible microphone/provider state and a bounded assistive-technology fallback;
- moving away from the hold control cancels capture without submission;
- generic voice requests remain presentation-only and action-incapable;
- Overlay empty state now distinguishes normal waiting from DEGRADED / LOCAL-ONLY / OFFLINE authority;
- the kill switch and existing security boundaries remain unchanged.

## Web Admin reconciliation · 2026-09-27

The latest Admin study is translated into the native Next.js control plane rather than imported as prototype code. Admin remains a distinct fail-closed elevated surface with an explicit `ELEVATED ACCESS · AUDITED` boundary and operation-oriented **Catalog / Entitlements / Quality** tabs. The environment-issued admin token and TOTP boundary remains visible across tabs; the change does not broaden Core authorization or persist admin factors in the browser/server.
