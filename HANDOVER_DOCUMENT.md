# SENTINEL — Technical Handover Document

Date: 2026-08-28  
Project: SENTINEL / ALPHA-0  
Repository: `spenskoj90-sudo/alpha-0`

## 0. Canonical live state (SOURCE OF TRUTH)

**Live `origin/main` HEAD (verified 2026-08-28):**  
`3d4e443b6ef432d4355da08cfeacc40209b7ef35`

Commit: `fix(ci): restore real coverage measurement (>=80% gate)` (PR #77 merged)

This document must track live GitHub `main`. Historical recovery notes and prior handover SHAs are not authoritative.

## 1. Purpose and architecture

SENTINEL is a security-first full-stack system with a central SENTINEL CORE: FastAPI + PostgreSQL + Android Kotlin Keystore + Play Integrity + Next.js.

Architecture: security-first modular monolith with SENTINEL CORE as the single source of truth.

Target model: Android application, Web interface, game adapters, and system operator. AI is recommendation-only and has no authorization authority.

## 2. Security and architectural invariants

- Client is never the authorization source of truth.
- Audit events are append-only.
- Replay protection uses a server-issued nonce/challenge and unique request ID.
- Android private keys never leave Android Keystore (StrongBox -> fallback TEE).
- AI has no authority and does not make security decisions.
- Server is the single source of truth for authorization.
- Fail-closed and default-deny behavior are required.

## 3. Technology stack

- Backend: Python, FastAPI, PostgreSQL, Docker, Docker Compose, pytest. Minimum coverage: 80% (enforced via `--cov-fail-under=80` after PR #77).
- Database: PostgreSQL; users, roles, permissions, devices, sessions, entitlements, audit, outbox; PostgreSQL RLS + FORCE RLS.
- Android: Kotlin, Jetpack Compose, Android Keystore, EC P-256 / secp256r1, Play Integrity verification.
- Web: Next.js (`web/`).

## 4. Repository layout

- `server/` — SENTINEL CORE backend, migrations, tests, Dockerfile.
- `app/` — Android application and instrumentation tests.
- `web/` — Next.js web interface.
- `.github/workflows/` — Android, build, deploy, P1 evidence, release, and security CI/CD workflows.
- `docs/` — project documentation/artifacts.
- `launcher/` — Electron launcher.
- `wow-addon/` — World of Warcraft addons (classic/retail).

## 5. Release signing / Play Integrity

Release key alias: `sentinel_release`  
Valid until: 29 Dec 2053  
Official SHA-256 certificate fingerprint:

`2A:CD:1C:FF:F4:F3:4D:B1:25:0D:3F:6C:81:F0:88:74:93:C4:60:2D:3C:FA:65:31:09:93:C0:58:08:9D:B8:8E`

Keystore source: Google Drive `Sentinel/keys/release.keystore.gpg`. The encrypted keystore and passphrase must never be committed to Git.

The release workflow verifies the resulting APK certificate fingerprint against the canonical fingerprint above and rejects debug/non-release APKs.

## 6. Live CI status (verified against GitHub Actions)

| Workflow              | Status on current main | Notes |
|-----------------------|------------------------|-------|
| Build & Test (Core + coverage) | success (PR #77 head) | Real coverage measurement restored, fail_under=80 |
| Security              | success                | |
| ALPHA-0 Android CI    | success                | |
| P1 Evidence           | success                | |
| Deploy                | failure (expected)     | EXTERNAL BLOCKER — requires DEPLOY_* secrets |

## 7. Coverage (measured)

- Command: `pytest -m "not postgres" --cov=app --cov-report=term-missing`
- Result: **82%** (1312 stmts, 235 miss)
- Threshold: >= 80% enforced in CI after PR #77

## 8. Security tests matrix

All required negative scenarios are covered by existing tests (test_security*.py, test_play_integrity.py, test_rls_policies.py, test_service_role_boundary.py, etc.):

- unauthenticated → DENY
- wrong role / wrong permission → DENY
- wrong device → DENY
- revoked / expired session → DENY
- replayed request / nonce → DENY
- invalid integrity / certificate / package → DENY
- RLS bypass → DENY
- malformed security input → FAIL CLOSED

## 9. CURRENT ACTIVE TASK / EXTERNAL BLOCKERS

**EXTERNAL BLOCKERS (not repository defects):**

1. Physical Android device acceptance of signed APK
2. Production Play Integrity (Google Cloud credentials)
3. Production DATABASE_URL / C1 role / infrastructure
4. Optional remote Deploy secrets (DEPLOY_HOST / USER / KEY)

Repository-side hardening for coverage measurement and documentation is complete as of this document.

## 10. Definition of Done (repository-side)

- [x] CI green for product workflows (Build & Test, Security, Android, P1)
- [x] Unit / security tests pass
- [x] Coverage >= 80% with real measurement
- [ ] Signed APK + fingerprint verified in CI (depends on keystore secrets presence — previously evidenced)
- [ ] Physical device validation — EXTERNAL
- [ ] Production deployment — EXTERNAL

## 11. Development constraints

- Do not change `main` directly; use PR branches.
- Live `origin/main` is the sole source of truth.
- Never commit secrets, keystores, or plaintext credentials.
- AI has no authorization authority.
