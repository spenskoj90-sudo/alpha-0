# SENTINEL P1 runtime and evidence contract

This document defines the P1 work that is executable without production Stripe credentials, live infrastructure access, or external Android keystore material.

## Implemented runtime primitives

- Session refresh rotation and session revoke remain server-side and fail closed; existing API tests cover replay and revoked-token rejection.
- Android key lifecycle has explicit `GENERATED -> ACTIVE -> ROTATING -> ACTIVE` and terminal `REVOKED` states.
- `EntitlementEngine` is deterministic and fail-closed for missing, suspended, not-yet-valid and expired entitlements.
- `BillingRuntime` is provider-neutral. It validates state transitions without contacting Stripe or requiring production credentials.
- `OutboxManager` and `WorkerManager` model `PENDING -> PROCESSING -> DONE/FAILED`, attempt counting, duplicate protection and retry semantics.
- PostgreSQL RLS is now explicit policy-backed rather than `ENABLE ROW LEVEL SECURITY` only. The persistence role must explicitly opt into the service policy through `app.service_role=true`; absent that setting, row access fails closed.

## Evidence artifacts

The `P1 Evidence` workflow generates:

- `pip-audit.json`
- `npm-audit.json`
- `gradle-dependencies.txt`
- `p1-performance.txt`

The artifacts are keyed by the exact Git commit SHA and are not treated as evidence for another commit.

## Deployment and backup boundary

The repository already has container build and deployment smoke/health validation. Production-level backup/restore and a real remote deployment remain infrastructure evidence and must be executed against the production-equivalent target; local smoke evidence is intentionally not promoted to production evidence.

Live Stripe/production credentials and external keystore material are intentionally excluded from repository automation.
