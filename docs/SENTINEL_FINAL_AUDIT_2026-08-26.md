ARCHIVED — historical document, not current state. See docs/SENTINEL_CURRENT_STATE.md

# SENTINEL — FINAL CLEAN-ROOM AUDIT RECONCILIATION

**Date:** 2026-08-26  
**Mode:** read-only audit reconciliation followed by controlled remediation branch  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Main HEAD at start:** `5e241a2f3d55453bf255a316ca6e31b5f59e7ccf`

## 1. Audit sources

Two independent clean-room reports were compared:

- Grok — repository clone / implementation-level inspection.
- DeepSeek — independent repository/security/QA architecture review.

Neither report is authoritative by itself. Direct Git state and implementation evidence take precedence.

## 2. Reconciled findings

### Confirmed

- Backend: FastAPI / Python 3.12.
- Database: PostgreSQL.
- Android identity: Android Keystore, P-256/secp256r1, SHA-256 fingerprinting.
- Session model: opaque high-entropy tokens with hashes at rest and one-time refresh rotation.
- Authorization: server-authoritative, default-deny policy engine.
- RLS policies exist in migration `002_p1_rls.sql`.
- `/v1/recommendations` already enforces `knowledge:recommend` authorization and has a negative regression test.
- Production startup requires `DATABASE_URL` and enrollment configuration.
- No P0 application security vulnerability was confirmed by the clean-room reconciliation.

### Audit claims rejected or downgraded

- README/state-document SHA values are not Git HEAD evidence. Live branch metadata showed `5e241a2f3d55453bf255a316ca6e31b5f59e7ccf` at the start of this pass.
- The claim that the backend is Kotlin/Ktor is false for the inspected repository.
- The claim that JWT is the primary session mechanism is false.
- The claim that RLS is absent is false; the repository contains explicit RLS policies.
- FTL authentication/API configuration failure is a test-infrastructure blocker, not a confirmed product-security P0.
- Microservices, Redis, sharding, or a broad architecture rewrite are not justified by the current evidence.

## 3. Remediation completed on branch

### RLS connection enforcement

`server/app/core/store.py` now creates the SQLAlchemy engine with:

`connect_args={"options": "-c app.service_role=true"}`

This makes the service-policy opt-in explicit for application PostgreSQL connections rather than relying on deployment operators to provide `PGOPTIONS`.

### RLS owner-role hardening

The original `002_p1_rls.sql` checksum was deliberately preserved because migration checksums are enforced. A new `004_p1_rls_force.sql` migration applies `FORCE ROW LEVEL SECURITY` to the protected tables.

### RLS regression coverage

`server/tests/test_rls_policies.py` now verifies:

- RLS enabled;
- RLS forced;
- expected service policies present;
- application PostgreSQL connections expose `app.service_role=true`.

### Session-store parity

`MemoryStore.rotate_refresh()` now marks the previous session revoked as well as refresh-used before issuing the replacement session. This aligns MemoryStore security semantics with PostgresStore.

### Refresh regression coverage

`server/tests/test_store_session_contract.py` verifies:

- replacement access/refresh tokens are issued;
- previous access token is no longer accepted;
- old refresh token cannot be reused.

## 4. Governance verification

Live GitHub metadata for `main` at audit start reported branch protection with these required status checks:

- `Android build and tests`
- `Secret and image scan`
- `Core tests and coverage`

The older task-board statement that required contexts/checks were empty was therefore stale and must be superseded by live metadata.

## 5. Remaining evidence gates

These are deliberately not represented as application defects:

1. Production-equivalent PostgreSQL runtime evidence is still required before claiming external deployment persistence is proven.
2. FTL remains an infrastructure acceptance gate; no unnecessary paid reruns should be made while its Google Cloud Tool Results API prerequisite is unresolved.
3. Multi-instance rate limiting remains a scale gate because the current limiter is process-local. It should become distributed before horizontal scaling, not before.
4. Real-device Android acceptance remains separate from repository/CI evidence.

## 6. Protected architectural decisions

No remediation in this pass changes:

- opaque-token sessions;
- Android Keystore P-256 identity;
- default-deny authorization;
- server-authoritative policy evaluation;
- production hard requirements for `DATABASE_URL` and enrollment configuration;
- migration checksum enforcement;
- modular-monolith architecture;
- current single-instance deployment assumptions.

## 7. Acceptance rule

This remediation branch must not be treated as accepted product state until its CI/test evidence passes and the branch is merged by explicit owner decision. A clean-room audit finding is not itself evidence of a passing implementation.
