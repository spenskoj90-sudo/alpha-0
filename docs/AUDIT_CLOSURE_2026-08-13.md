# SENTINEL audit closure evidence — 2026-08-13

## Release baseline

Selected baseline: `sentinel-1.0.0-rc1-final` at the exact current release candidate HEAD, not `main`.

- `main`: `70702f3f992097cea9553c406b5d8febb3a47539`
- RC baseline before this closure commit: `8d333557e7dca813f763d90437719013d479baa7`
- Reason: the RC contains the PostgreSQL/runtime, CI, Android and release-gate work required by the audit; mixing main and RC would invalidate exact-HEAD evidence.

## P0 implementation status

### PostgreSQL/runtime
Production mode is fail-closed when `DATABASE_URL` is absent and selects `PostgresStore` when it is present. The PostgreSQL integration workflow runs the real API flow through registration → device proof → session → event persistence → refresh → audit, followed by backup/restore smoke testing.

`MemoryStore` remains only as a deterministic test/development implementation; it is not selected by the production environment.

### Authorization
`POST /v1/recommendations` now passes through `authorize_request()` with action `knowledge:recommend` and resource `recommendation`, requiring `game:read`. The decision is audited before the endpoint returns data.

### Negative security suite
The P0 suite explicitly exercises:

- invalid nonce
- reused nonce
- expired nonce
- invalid signature
- altered signed payload / request ID
- stale timestamp
- revoked device
- rotated device key
- expired session
- revoked session
- missing scope
- wrong role
- explicit deny
- direct unauthorized recommendation API call
- cross-device event submission
- duplicate event
- sequence replay

### Android instrumentation
The full Build & Test workflow contains a dedicated `android-instrumentation` job using `reactivecircus/android-emulator-runner@v2` and `connectedDebugAndroidTest`. It is part of the release validation workflow rather than a documentation-only check.

## Evidence rule
This document records implementation intent and mapping only. It does not itself constitute a green gate. Final gate status must reference the exact GitHub Actions run for the final commit.

## Remaining P1 audit scope
The following remain separate P1 work unless exact runtime evidence is added: device/session lifecycle APIs beyond the currently implemented refresh/revoke flow, entitlement expansion, billing runtime/Stripe production configuration, outbox/worker manager, real RLS policy evidence, dependency/SCA report artifact, reproducible deployment test beyond smoke, performance baseline, operational alert evidence, and production backup/restore evidence.

Production credentials, live Stripe integrations, live infrastructure and external keystore secrets are intentionally not touched by this change set.
