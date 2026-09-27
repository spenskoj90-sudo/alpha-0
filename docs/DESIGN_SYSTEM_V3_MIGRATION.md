# Design System v3 migration

SENTINEL Design System v3.0 is the active visual authority. v2.1 remains historical reference.

The migration preserves authentication, session, device proof, MFA, entitlement, localization and API authority semantics. It replaces shared visual primitives, Android primary navigation and physical-test chrome, calibrates Web and Companion geometry, constrains Overlay to one meaningful presentation at a time, and applies FACT / INFERENCE / RECOMMENDATION grammar.

Production remains native to alpha-0. The design laboratory is reference-only and no Lovable/TanStack application architecture is imported into production.

Initial v3 reference: `spenskoj90-sudo/sentinel-aware-companion@60629603299fd8af035c6f05991482cde0363c33`.

Current reconciled reference: `spenskoj90-sudo/sentinel-aware-companion@a6fc9d4c513dde9d549e5dd70159b1365a76b95c` (2026-09-27). The 13-commit design-laboratory delta adds Voice, Admin, Access, Billing and Resilience studies plus expanded handoff documentation. It does **not** supersede native production architecture or security authority.

The follow-up production calibration adopts the reference's operation-oriented Admin tabs, explicit audited admin shell, Companion resilience state strip and true hold/release push-to-talk semantics. These changes remain native to Next.js/Electron and preserve all existing Core/runtime authority boundaries.
