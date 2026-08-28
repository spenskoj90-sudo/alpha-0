# SENTINEL — Technical Handover Document

Date: 2026-08-28  
Project: SENTINEL / ALPHA-0  
Repository: `spenskoj90-sudo/alpha-0`

## 0. Canonical live state

The previous handover recorded an older `origin/main` SHA. The live GitHub `main` state is authoritative. At recovery time, `main` = `6f75c94f82e4da2e85f723bf1c587cf139cbd89f`.

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

## 5. Release signing / Play Integrity

Release key alias: `sentinel_release`  
Valid until: 29 Dec 2053  
Official SHA-256 certificate fingerprint:

`2A:CD:1C:FF:F4:F3:4D:B1:25:0D:3F:6C:81:F0:88:74:93:C4:60:2D:3C:FA:65:31:09:93:C0:58:08:9D:B8:8E`

Keystore source: Google Drive `Sentinel/keys/release.keystore.gpg`. The encrypted keystore and passphrase must never be committed to Git.

Decryption template:

`gpg --batch --yes --pinentry-mode loopback --passphrase-file <passphrase_file> --output release.keystore --decrypt release.keystore.gpg`

The release workflow must verify the resulting APK certificate fingerprint against the canonical fingerprint above and reject debug/non-release APKs.

## 6. Development constraints

- Work from GitHub Codespaces / Web Terminal on mobile.
- AI output for implementation is DIFF/PATCH or changed functions, not large complete files.
- No screenshots; use textual logs and tracebacks.
- Development proceeds atomically and each task is fixed by tests.
- Live `origin/main` is the source of truth over historical handovers.

## 7. Definition of Done

Project is ready only when:

- CI is green.
- All unit/integration/security tests pass.
- Signed APK builds successfully.
- Play Integrity is verified.
- Release APK is confirmed on a physical device.

## 8. Recovery baseline

Current live main commit message: `Merge SENTINEL final integrator corrections`.

The commit states that final repository corrections followed green product CI, security, P1 evidence, Android CI, and emulator instrumentation. Any current CI regression must be diagnosed from the live workflow/run state rather than from this document.
