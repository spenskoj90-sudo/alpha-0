# SENTINEL — Canonical Current State

**State record:** 2026-08-31  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD (main):** `1df91de661c8bb0946d68f1671cbabf5f9714455`  
**Current branch:** `feature/sentry-android-observability-7`  
**Current branch HEAD:** `85695dd2409030e49f428766e88b75d1bee47d12`  
**Current product change on main:** PR #100 state-sync gate + emulator pin (merged as `1df91de…`)

> Git/main is authoritative for product state. Historical branch evidence is not current product state unless merged.

## Current work

### Issue #7 — Sentry Android observability — IN PROGRESS

Branch `feature/sentry-android-observability-7`. The branch contains the Sentry Android SDK integration, privacy scrubbing, observability documentation, release-only `SENTRY_DSN` injection, Kotlin DSL BuildConfig interpolation fixes, and AndroidManifest Sentry auto-init disabled so initialization is controlled by `SentinelApplication.onCreate()`. No merge performed.

## Evidence discipline

For CI, tests and release claims use exact commit SHA + workflow Run ID. For unresolved facts record **UNVERIFIED** rather than infer state from historical evidence.

## External blockers

- Google Play Integrity audience/package/certificate and Google API authorization credentials.
- Production `DATABASE_URL` and deployment secrets.
- Real-device acceptance before public distribution.
- Release tag and GitHub Release publication when chosen by Owner.
- Firebase Test Lab `storage.objects.create` permission (issues #59/#62).
- GitHub secret `SENTRY_DSN` before release builds emit Sentry events.

## Security invariants

Do not silently change opaque-token sessions, Android Keystore P-256 identity, default-deny authorization, production `DATABASE_URL` / enrollment-token requirements, migration checksum enforcement, service-role/RLS boundaries, transactional refresh rotation, signing secrets or production credentials.
