# SENTINEL — Canonical Current State

**State record:** 2026-08-27  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD (main):** `6ea5af7ffa931826733ad87637959e983d7d05c1`  
**Hardening branch:** `sentinel/release-hardening-2026-08-27`  
**Hardening HEAD:** `5439e715175eb8444c12aa85b81cbb0e9385b2b3`  
**PR:** #68 (open; not product state until merge + Owner accept)

> This document is repository-grounded. `main`/Git are authoritative for product state; branch evidence is not accepted until merged.

## 1. Binding evidence policy

`docs/SENTINEL_EVIDENCE_PROTOCOL.md` v2 is binding. A claim is not accepted as verified merely because it appears in an audit, README, branch, PR, or historical state document.

## 2. Current repository facts

- Android client exists under `app/`.
- FastAPI backend exists under `server/`.
- Web control-plane source exists under `web/`.
- Device identity uses Android Keystore / EC P-256 with SHA-256 public-key fingerprinting; StrongBox preferred, TEE fallback.
- Sessions use opaque tokens with hashed persistence and one-time refresh rotation; JWT is not the primary session mechanism.
- Authorization is server-authoritative and default-deny.
- PostgreSQL is the production persistence implementation when `DATABASE_URL` is configured; production startup rejects a missing `DATABASE_URL`.
- PostgresStore sets `app.service_role=true` via connect_args; FORCE RLS applied by migration `004_p1_rls_force.sql`.
- `/v1/recommendations` is authorized through `knowledge:recommend`.
- Android backup disabled; `usesCleartextTraffic=false`; network security config present.
- Admin endpoints enforce rate limit and failed-attempt lockout (5 failures / 15 min window).

## 3. PR #66 (merged on main)

Merge SHA: `6ea5af7ffa931826733ad87637959e983d7d05c1`

- Wire `app.service_role=true` into PostgresStore connections
- `004_p1_rls_force.sql` (FORCE RLS without mutating 002 checksum)
- RLS regression coverage
- MemoryStore refresh rotation parity with PostgresStore
- Refresh-rotation regression coverage
- Canonical state / audit documentation reconciliation

## 4. PR #68 release hardening (branch evidence; not product until merge)

Branch HEAD: `5439e715175eb8444c12aa85b81cbb0e9385b2b3`

### Implemented

1. Admin lockout / rate limiting on admin endpoints; token never echoed.
2. RLS negative proof via dedicated non-owner role `rls_probe` (no BYPASSRLS).
3. Concurrent refresh rotation: MemoryStore + **PostgresStore** ThreadPool tests assert exactly one successful rotation.
4. Integrity tier policy + one-time server nonce; client verdicts untrusted; live Google verification fail-closed without audience.
5. Android StrongBox with TEE fallback; cleartext disabled.
6. Build & Test instrumentation: GitHub Emulator (Owner-approved design from PR #67).

### Exact-head CI evidence (Build & Test run 33069908061)

| Job | Result |
|-----|--------|
| Repository verification | PASS |
| Core tests and coverage | PASS |
| PostgreSQL integration and recovery | PASS |
| Web build | PASS |
| Container build | PASS |
| Reproducible container comparison | PASS |
| Deployment smoke and health | PASS |
| Android build and tests (incl. signed release + fingerprint) | PASS |
| Android instrumentation (GitHub Emulator API 35) | PASS |
| Security | PASS |
| P1 Evidence | PASS |
| ALPHA-0 Android CI | PASS |

Deploy push-ghost runs remain FAIL and are classified non-product (workflow trigger is `release.published` only).

## 5. Remaining open evidence

- **Play Integrity live Google token verification:** BLOCKED until `SENTINEL_PLAY_INTEGRITY_AUDIENCE` (and related Google credentials) are configured. Policy engine + nonce replay protection exist; mode is fail-closed / UNKNOWN.
- **Production SoR / external deployment configuration:** UNVERIFIED. CI PostgreSQL is not production evidence.
- **Real-device Android acceptance:** Owner manual gate.
- **Required status-check contexts on protected main:** process/governance item (settings not changed by agents).
- **Multi-instance rate limiting:** intentionally process-local until horizontal scale is required.

## 6. Explicit non-actions

Do not silently change:

- opaque-token session architecture;
- Android Keystore P-256 identity model;
- default-deny authorization semantics;
- production `DATABASE_URL` / enrollment-token requirements;
- migration checksum enforcement;
- modular-monolith architecture;
- single-instance rate limiter before horizontal scaling evidence;
- signing secrets, production credentials, or CI governance settings without Owner approval.

## 7. Authority

**Branch-state truth authority:** GPT / Final Integrator.  
**Human Owner:** absolute final authority for acceptance, scope, release, merge, and destructive repository cleanup.
