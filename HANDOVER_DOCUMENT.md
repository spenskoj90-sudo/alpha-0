# SENTINEL — Technical Handover Document

Date: 2026-08-28  
Project: SENTINEL / ALPHA-0  
Repository: `spenskoj90-sudo/alpha-0`

## 0. Canonical live state (SOURCE OF TRUTH)

**Live `origin/main` HEAD (verified 2026-08-28):**  
`8e09e6835647792258713b572011f17ba9acdd0a`

Commit: `chore/docs: remove CI touch artifact + sync HANDOVER to live main`

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

**VERIFIED (CI evidence):** On main HEAD `7a32ceff` and post-merge `8e09e683`, Build & Test job successfully decoded the release keystore, validated alias, assembled signed release APK, and verified certificate fingerprint against the canonical value above. Keystore secrets are present in CI.

## 6. Live CI status (verified against GitHub Actions on HEAD 8e09e683)

| Workflow              | Status on current main | Evidence run ID      |
|-----------------------|------------------------|----------------------|
| Build & Test          | success                | 33186523492          |
| Security              | success                | 33186523418          |
| ALPHA-0 Android CI    | success                | 33186523501          |
| P1 Evidence           | success                | 33186523480          |
| Deploy                | failure (expected)     | 33186522362          |

Deploy workflow requires external DEPLOY_* secrets and production host. Failure is EXTERNAL BLOCKER, not a repository defect.

## 7. CURRENT ACTIVE TASK

**Priority 1 — Physical device acceptance of signed release APK**

Signed APK production + certificate fingerprint verification already SUCCEEDED in CI. Remaining gate: Owner installs the CI-produced signed release APK on a physical device and confirms acceptance.

Until physical device validation is complete, project remains **NOT RELEASE READY**.

## 8. Remaining roadmap (priority order)

1. Physical device acceptance of signed APK (Owner action) — CURRENT ACTIVE TASK.
2. Supply production DATABASE_URL + C1 role / infrastructure (Owner action).
3. Supply live Play Integrity Google Cloud credentials for production attestation (Owner action).
4. Optional: remote Deploy secrets (DEPLOY_HOST / USER / KEY) if production rollout required.
5. Optional (later): restore real coverage gate once `--cov` package path is corrected and measured ≥ 80%.
6. Keep HANDOVER_DOCUMENT.md synchronized after every main merge.

## 9. Definition of Done

Project is RELEASE READY only when:

- CI green (product workflows).
- All unit/integration/security tests pass.
- Coverage >= 80% (currently diagnostic-only due to package path).
- Signed APK builds successfully — **VERIFIED in CI**.
- Release APK certificate verified against canonical fingerprint — **VERIFIED in CI**.
- Play Integrity verified (live production path still requires Owner credentials).
- Physical device validation PASS — **BLOCKED on Owner**.

Current status: **NOT RELEASE READY** (physical device + production DB + live Play Integrity remain).

## 10. Development constraints

- Do not change `main` directly; use PR branches.
- Live `origin/main` is the sole source of truth.
- Never commit secrets, keystores, or plaintext credentials.
- AI has no authorization authority.
