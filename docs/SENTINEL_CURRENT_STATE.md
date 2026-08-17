# SENTINEL — Canonical Current State

**State record:** 2026-08-17  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD at record creation:** `70702f3f992097cea9553c406b5d8febb3a47539`

> This document is a repository-grounded state record. It intentionally separates what exists on `main` from architecture, historical branch work, and unverified claims.

## 1. Evidence policy

A capability is `VERIFIED` only when all of the following are true:

1. The implementation exists on `main` at the cited commit.
2. The relevant source/configuration path is identified.
3. Executable CI evidence exists for the same commit when a CI gate is applicable.
4. Runtime/device evidence is cited when runtime behavior cannot be established from source/CI alone.

A branch, PR, local checkout, PR description, or historical chat report is **not** evidence that a capability is present on `main`.

## 2. Current repository facts

### VERIFIED on `main`

- Android client exists under `app/`.
- FastAPI backend exists under `server/`.
- Web control-plane source exists under `web/`.
- Android device identity foundation exists, including Keystore/P-256 related security code.
- Authorization engine implements explicit default-deny semantics. Unknown actions/policies deny rather than implicitly allow.
- Challenge state contains expiration/consumption semantics and nonce generation exists in the security primitives.
- PostgreSQL schema exists under `server/migrations/001_initial.sql`.
- The schema includes users, roles, permissions, scopes, policies, devices, device challenges, sessions, entitlements, characters, game events, outbox events, audit events, idempotency keys and worker jobs.
- The schema enables RLS for `characters`, `entitlements` and `audit_events` as defense in depth.
- `main` currently renders the Android `CharacterDashboard` from `MainActivity.kt`.

## 3. Explicitly NOT VERIFIED as current runtime

### PostgreSQL runtime persistence

The current `main` backend still instantiates an in-memory `MemoryStore` in the runtime path. Therefore the PostgreSQL schema must not be described as proof that runtime sessions/devices/events/audit are PostgreSQL-backed.

**Status:** `OPEN / NOT VERIFIED`

### Full product UI

The current `main` Android entry point is still a technical `CharacterDashboard` surface. Login/Register and the later multi-section product navigation must not be described as present on `main` unless their exact files/commit are verified there.

**Status:** `OPEN / PRODUCT TRACK`

### Android CI signing

The Android workflow currently requires `ALPHA0_KEYSTORE_BASE64` and related signing secrets. The latest verified failure for the current baseline stopped at `Prepare signing keystore` because `ALPHA0_KEYSTORE_BASE64` was empty in the workflow environment.

**Status:** `BLOCKED / INFRASTRUCTURE CONFIGURATION`

### Release readiness

No release-readiness claim is valid merely because an RC branch or historical tag passed a subset of checks. Release acceptance requires exact-head validation of the final `main` commit and release artifact evidence.

**Status:** `NOT ACCEPTED`

## 4. Architecture versus implementation

`docs/ARCHITECTURE_V4.md` is the architectural target and contract. It describes PostgreSQL as the authoritative persistence layer and defines broader modules such as workers, outbox, knowledge and telemetry. Those architectural statements must not be read as proof that every described runtime component is already implemented on `main`.

This distinction is now mandatory:

- **Architecture:** what the system is designed to become.
- **Main implementation:** what is actually present at the canonical HEAD.
- **Branch-only:** work present on a non-main branch/PR.
- **Historical evidence:** a previous state that may no longer exist on main.

## 5. Current branch inventory

The repository currently contains multiple long-lived or dated branches in addition to `main`, including:

- `agent/modernize-alpha0`
- `agent/sentinel-complete-platform`
- `automation/sentinel-pipeline`
- `p1-close-2026-08-13`
- `security/public-release-hardening`
- `sentinel/android-http-hardening-2026-08-17`
- `sentinel/android-http-hardening-main-2026-08-17`
- `sentinel/full-stack-builder`
- `sentinel/1.0.0-rc1-gates`
- `sentinel-1.0.0-rc1-final`
- `sentinel-fingerprint-diagnostic`
- `sentinel-ftl-2026-08-13`
- `sentinel-ftl-repair-2026-08-14`
- `sentinel-release-hardening-2026-08`
- `sentinel-user-auth`

Branch cleanup is intentionally deferred until each branch/PR is classified as **merge candidate**, **archive/reference**, or **obsolete**. No useful historical work should be destroyed before that classification is complete.

## 6. Canonical state rule

Whenever a future document says `CURRENT`, `VERIFIED`, `PASS`, `BLOCKED`, `REGRESSION`, or `RELEASE READY`, it must cite the relevant `main` SHA and evidence.

If a previously verified capability is absent from a later `main` commit, it must be called a **REGRESSION** until lineage is explained. It must not silently be treated as a new task.

## 7. Owner

**Branch-state truth authority:** GPT / Final Integrator.

**Human Owner:** absolute final authority for acceptance, scope, release and destructive repository cleanup.
