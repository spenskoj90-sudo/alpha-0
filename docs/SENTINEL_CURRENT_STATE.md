# SENTINEL — Canonical Current State

**State record:** 2026-08-26  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD at audit start:** `5e241a2f3d55453bf255a316ca6e31b5f59e7ccf`  
**Remediation branch:** `sentinel/final-audit-remediation-2026-08-26`

> This document is repository-grounded. `main`/Git are authoritative for implementation state; this document records evidence and decisions, not assumptions from AI reports.

## 1. Binding evidence policy

`docs/SENTINEL_EVIDENCE_PROTOCOL.md` v2 is binding. A claim is not accepted as verified merely because it appears in an audit, README, branch, PR, or historical state document.

## 2. Current repository facts

- Android client exists under `app/`.
- FastAPI backend exists under `server/`.
- Web control-plane source exists under `web/`.
- Device identity uses Android Keystore / EC P-256 with SHA-256 public-key fingerprinting.
- Sessions use opaque tokens with hashed persistence and one-time refresh rotation; JWT is not the primary session mechanism.
- Authorization is server-authoritative and default-deny.
- PostgreSQL is the production persistence implementation when `DATABASE_URL` is configured; production startup rejects a missing `DATABASE_URL`.
- `/v1/recommendations` is explicitly authorized through `knowledge:recommend`; a negative regression test expects HTTP 403 without the required scope.
- Android backup is disabled and security response headers are implemented in Core.

## 3. 2026-08-26 independent audit reconciliation

Two clean-room audits were compared: Grok and DeepSeek. Direct repository evidence takes precedence over README/state claims and over audit claims that were not inspected at implementation level.

### Confirmed / accepted

- Current `main` HEAD at the start of this pass is `5e241a2f3d55453bf255a316ca6e31b5f59e7ccf`.
- Backend is FastAPI/Python 3.12, not Kotlin/Ktor.
- Sessions are opaque tokens, not JWT sessions.
- RLS policies exist in `server/migrations/002_p1_rls.sql`.
- `POST /v1/recommendations` authorization is already implemented and regression-tested.
- No P0 security vulnerability is confirmed by the two repository audits.
- FTL is an infrastructure/test execution blocker, not evidence of a product-security P0.

### Remediated in this pass

1. **RLS application connection contract:** `PostgresStore` now sets `app.service_role=true` on every SQLAlchemy/psycopg connection through `connect_args`.
2. **RLS owner-role hardening:** migration `004_p1_rls_force.sql` applies `FORCE ROW LEVEL SECURITY` without mutating the checksum of migration `002_p1_rls.sql`.
3. **RLS regression evidence:** `server/tests/test_rls_policies.py` now verifies both forced RLS and the application connection GUC.
4. **Memory/Postgres refresh parity:** `MemoryStore.rotate_refresh()` now marks the previous access session revoked before issuing the replacement session, matching Postgres semantics.
5. **Refresh regression evidence:** `server/tests/test_store_session_contract.py` verifies old access invalidation and one-time refresh use.
6. **Canonical state documentation:** this file is reconciled to the actual repository HEAD used for the pass and explicitly records the audit reconciliation.

## 4. Governance evidence

At the beginning of this pass, live GitHub branch metadata for `main` reported:

- `protected=true`
- `enforcement_level=non_admins`
- required checks: `Android build and tests`, `Secret and image scan`, `Core tests and coverage`

Therefore the previous TASKS entry claiming `contexts=[]` / `checks=[]` was stale and must not be treated as current truth.

## 5. FTL status

FTL remains a separate infrastructure acceptance item. The repository/application code is not declared broken solely because instrumentation could not execute. The known blocker remains the Google Cloud Tool Results API configuration described in the task board. No additional paid FTL run is justified until that infrastructure prerequisite is confirmed.

## 6. Remaining open evidence

- Exact-main production-equivalent PostgreSQL runtime evidence remains open; repository code and CI PostgreSQL evidence do not prove the actual external deployment configuration.
- Multi-instance rate limiting remains intentionally process-local until horizontal deployment is actually required; this is an architectural scale gate, not a current P0.
- Real-device Android acceptance remains separate from repository QA.
- FTL infrastructure restoration remains separate from application-code correctness.

## 7. Explicit non-actions

Do not silently change:

- opaque-token session architecture;
- Android Keystore P-256 identity model;
- default-deny authorization semantics;
- production `DATABASE_URL` / enrollment-token requirements;
- migration checksum enforcement;
- modular-monolith architecture;
- single-instance rate limiter before there is evidence that horizontal scaling is required.

Do not classify README SHA values as Git HEAD. Always verify `git rev-parse HEAD` / live branch metadata.

## 8. Authority

**Branch-state truth authority:** GPT / Final Integrator.  
**Human Owner:** absolute final authority for acceptance, scope, release, and destructive repository cleanup.
