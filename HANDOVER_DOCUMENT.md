# SENTINEL — Technical Handover Document

Date: 2026-08-29  
Project: SENTINEL / ALPHA-0  
Repository: `spenskoj90-sudo/alpha-0`

## 0. Canonical live state (SOURCE OF TRUTH)

**Live `origin/main` HEAD (verified 2026-08-29):**  
`9008c12180e48a3143295980037d48b9c76dcb45`

Commit: docs sync after PR #77 coverage gate (PR #79).

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

- Backend: Python 3.12, FastAPI, PostgreSQL, Docker, pytest. Coverage gate: >=80% (`--cov-fail-under=80`).
- Database: PostgreSQL 17; RLS + FORCE RLS; migrations under `server/migrations`.
- Android: Kotlin, Jetpack Compose, Android Keystore (EC P-256), Play Integrity.
- Web: Next.js (`web/`).

## 4. Repository layout

- `server/` — SENTINEL CORE backend, migrations, tests, Dockerfile.
- `app/` — Android application and tests.
- `web/` — Next.js web interface.
- `.github/workflows/` — build, security, android-build, release, deploy, p1-evidence.
- `docs/` — project documentation.
- `launcher/` — Electron launcher.
- `wow-addon/` — World of Warcraft addons.

## 5. Release signing / Play Integrity

Release key alias: `sentinel_release`  
Official SHA-256 certificate fingerprint:

`2A:CD:1C:FF:F4:F3:4D:B1:25:0D:3F:6C:81:F0:88:74:93:C4:60:2D:3C:FA:65:31:09:93:C0:58:08:9D:B8:8E`

Keystore material is supplied only via GitHub Actions Secrets (`ANDROID_KEYSTORE_BASE64`, passwords, alias). Never committed to Git.

## 6. Live CI status (main @ 9008c121)

| Workflow | Status | Notes |
|----------|--------|-------|
| Build & Test | success | Core coverage + PostgreSQL |
| Security | success | CodeQL, audit, secret scan |
| ALPHA-0 Android CI | success | Debug APK + unit tests |
| P1 Evidence | success | |
| Deploy | failure | EXTERNAL — requires DEPLOY_* secrets |

## 7. Coverage

- Measured: **82%** (`pytest -m "not postgres" --cov=app`)
- Threshold: >= 80% enforced in CI
- Install mode: editable (`pip install -e '.[test]'`) so coverage maps to source tree

## 8. Security tests matrix

All required negative scenarios are present in the test suite:

- unauthenticated → DENY
- wrong role / wrong permission → DENY
- wrong device → DENY
- revoked / expired session → DENY
- replayed request / nonce → DENY
- invalid integrity / certificate / package → DENY
- RLS bypass → DENY
- malformed security input → FAIL CLOSED

## 9. Branch hygiene (2026-08-29)

Deleted 40 fully-merged / superseded temporary branches (ahead_by=0 or squash-merged content already on main).  
Open PRs retained for unique unfinished work: #67, #71, #74. Closed obsolete #61.

## 10. EXTERNAL BLOCKERS

1. Physical Android device acceptance of signed APK  
2. Production Play Integrity (Google Cloud credentials)  
3. Production DATABASE_URL / infrastructure  
4. Optional DEPLOY_HOST / DEPLOY_USER / DEPLOY_KEY  

## 11. Definition of Done (repository-side)

- [x] CI green for product workflows on main  
- [x] Unit / security / PostgreSQL tests pass  
- [x] Coverage >= 80% with real measurement  
- [x] No plaintext secrets in tree  
- [x] Documentation synchronized to live main  
- [ ] Physical device validation — EXTERNAL  
- [ ] Production deployment — EXTERNAL  

## 12. Development constraints

- Do not change `main` directly; use PR branches.  
- Live `origin/main` is the sole source of truth.  
- Never commit secrets, keystores, or plaintext credentials.  
- AI has no authorization authority.  
