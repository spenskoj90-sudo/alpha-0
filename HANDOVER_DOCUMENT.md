# SENTINEL — Technical Handover Document

Date: 2026-08-28  
Project: SENTINEL / ALPHA-0  
Repository: `spenskoj90-sudo/alpha-0`

## 0. Canonical live state (SOURCE OF TRUTH)

**Live `origin/main` HEAD (verified 2026-08-28):**  
`7a32ceff2a7b58e0254b7a777335287c581eca81`

Commit: `chore: remove legacy/obsolete utility files`

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

- Backend: Python, FastAPI, PostgreSQL, Docker, Docker Compose, pytest. Minimum coverage: 80%.
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

Decryption template:

`gpg --batch --yes --pinentry-mode loopback --passphrase-file <passphrase_file> --output release.keystore --decrypt release.keystore.gpg`

The release workflow must verify the resulting APK certificate fingerprint against the canonical fingerprint above and reject debug/non-release APKs.

## 6. Live CI status (verified against GitHub Actions on HEAD 7a32ceff)

| Workflow              | Status on current main | Evidence run ID      |
|-----------------------|------------------------|----------------------|
| Build & Test          | success                | 33176003577          |
| Security              | success                | 33176003543          |
| ALPHA-0 Android CI    | success                | 33176003634          |
| P1 Evidence           | success                | 33176003631          |
| Deploy                | failure (expected)     | 33176002437          |

Deploy workflow is release-triggered / requires external DEPLOY_* secrets and production host. Failure is EXTERNAL BLOCKER, not a repository defect.

## 7. CURRENT ACTIVE TASK

**Priority 1 — External release signing secrets + signed APK production**

Android keystore secrets (release.keystore.gpg passphrase + keystore) must be available to CI release workflow so a real signed APK can be produced and certificate fingerprint verified.

Until this is complete, project remains **NOT RELEASE READY**.

## 8. Remaining roadmap (priority order)

1. Supply Android release keystore secrets to CI (Owner action).
2. Supply production DATABASE_URL + C1 role / infrastructure (Owner action).
3. Supply Play Integrity Google Cloud credentials (Owner action).
4. Execute physical device acceptance of signed APK (Owner action).
5. Optional: remote Deploy secrets (DEPLOY_HOST / USER / KEY) if production rollout required.
6. Keep HANDOVER_DOCUMENT.md synchronized after every main merge.

## 9. Definition of Done

Project is RELEASE READY only when:

- CI green (product workflows).
- All unit/integration/security tests pass.
- Coverage >= 80%.
- Signed APK builds successfully.
- Play Integrity verified.
- Release APK certificate verified against canonical fingerprint.
- Physical device validation PASS.

Current status: **NOT RELEASE READY** (external blockers remain).

## 10. Development constraints

- Do not change `main` directly; use PR branches.
- Live `origin/main` is the sole source of truth.
- Never commit secrets, keystores, or plaintext credentials.
- AI has no authorization authority.
