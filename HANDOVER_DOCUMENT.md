# SENTINEL — Technical Handover Document

Date: 2026-08-29  
Project: SENTINEL / ALPHA-0  
Repository: `spenskoj90-sudo/alpha-0`

## 0. Canonical live state (SOURCE OF TRUTH)

**Live `origin/main` HEAD (verified 2026-08-29):**  
`306c1f1f5b735cebe59d809d70fd22387488f625`

Commit: `docs+ci: HANDOVER sync to 9008c121 + simplify workflow triggers` (PR #80).

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

## 6. Live CI status (main @ 306c1f1f — all required checks success)

| Workflow / Check | Status | Run / Notes |
|------------------|--------|-------------|
| Build & Test | success | run 33235721861 |
| Core tests and coverage | success | required |
| PostgreSQL integration and recovery | success | |
| Android build and tests | success | required |
| Android instrumentation (GitHub Emulator) | success | |
| Secret and image scan | success | required |
| Security (CodeQL, dependency audit) | success | run 33235721847 |
| ALPHA-0 Android CI | success | run 33235721860 |
| P1 Evidence | success | run 33235721846 |
| Deploy | failure | EXTERNAL — DEPLOY_* secrets |

## 7. Coverage

- Measured: **82%** (`pytest -m "not postgres" --cov=app`)
- Threshold: >= 80% enforced in CI (`--cov-fail-under=80`)
- Install mode: editable (`pip install -e '.[test]'`)

## 8. Security tests matrix

All required negative scenarios are present and exercised by green CI:

- unauthenticated → DENY
- wrong role / wrong permission → DENY
- wrong device → DENY
- revoked / expired session → DENY
- replayed request / nonce → DENY
- invalid integrity / certificate / package → DENY
- RLS bypass → DENY
- malformed security input → FAIL CLOSED

## 9. Open PRs (unique work remaining)

| PR | Classification | Notes |
|----|----------------|-------|
| #67 | SUPERSEDED | Emulator instrumentation already on main |
| #71 | UNIQUE | Hardening of release.yml + security.yml |
| #74 | UNIQUE | Adds release-candidate.yml for signed APK artifact |

## 10. EXTERNAL BLOCKERS

1. Physical Android device acceptance of signed APK  
2. Production Play Integrity (Google Cloud credentials)  
3. Production DATABASE_URL / infrastructure  
4. Optional DEPLOY_HOST / DEPLOY_USER / DEPLOY_KEY  

## 11. Definition of Done (repository-side)

- [x] CI green for product workflows on current main HEAD  
- [x] Unit / security / PostgreSQL / Android instrumentation pass  
- [x] Coverage >= 80% with real measurement  
- [x] No plaintext secrets in tree  
- [x] Documentation synchronized to live main (this document)  
- [ ] Physical device validation — EXTERNAL  
- [ ] Production deployment — EXTERNAL  

## 12. Development constraints

- Do not change `main` directly; use PR branches.  
- Live `origin/main` is the sole source of truth.  
- Never commit secrets, keystores, or plaintext credentials.  
- AI has no authorization authority.  
