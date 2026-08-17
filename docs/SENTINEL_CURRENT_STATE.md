# SENTINEL — Canonical Current State

**State record:** 2026-08-17  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD:** `14998ebe8e9d9059014006494014bca4af95e9c7`

> This document is repository-grounded. It separates current `main` implementation from architecture, branch-only work, historical evidence, and unverified AI claims.

## 1. Binding evidence policy

`docs/SENTINEL_EVIDENCE_PROTOCOL.md` v2 is binding. `VERIFIED` requires the seven-part evidence bundle: exact SHA, main-line reachability, relevant implementation paths, applicable CI URL/result for the exact SHA, test detail, and runtime/device evidence where required.

A branch, PR, local checkout, PR description, or historical AI report is not proof of current product state.

## 2. Current repository facts

### CURRENT / VERIFIED AT THIS MAIN HEAD

- Android client exists under `app/`.
- FastAPI backend exists under `server/`.
- Web control-plane source exists under `web/`.
- Android device identity foundation exists, including Keystore/P-256 related security code.
- Authorization engine explicitly returns `DENY` when no matching policy exists.
- Device challenge generation uses a cryptographic nonce, stores its hash, applies a 120-second expiration, and tracks consumption in the current runtime path.
- PostgreSQL schema exists under `server/migrations/001_initial.sql`.
- The schema includes users, roles, permissions, scopes, policies, devices, device challenges, sessions, entitlements, characters, game events, outbox events, audit events, idempotency keys and worker jobs.
- RLS is enabled on `characters`, `entitlements`, and `audit_events` as defense in depth, but the current migration contains no `CREATE POLICY` statements.
- `main` currently renders the Android `CharacterDashboard` surface.

These repository facts are source-level facts. They are not release acceptance claims until the required exact-SHA CI/runtime evidence exists.

## 3. OPEN / NOT ACCEPTED ITEMS

### PostgreSQL runtime persistence — OPEN

`server/app/main.py` still instantiates `MemoryStore`; the current runtime path does not use PostgreSQL persistence. The PostgreSQL schema is therefore not proof of runtime persistence.

### Recommendation authorization — OPEN SECURITY GAP

`POST /v1/recommendations` authenticates the session but currently returns the recommendation without calling `policy_engine.authorize`. This is a real current-main authorization gap and must be fixed with a regression test.

### Full product UI — OPEN PRODUCT TRACK

The current Android entry point is still `CharacterDashboard`. Login/Register and later multi-section product navigation are not current-main capabilities unless exact files and evidence are subsequently verified on `main`.

### Android CI — BLOCKED / INFRASTRUCTURE

The current Android workflow requires `ALPHA0_KEYSTORE_BASE64` and related signing inputs before the debug build. The known failure is an unavailable/empty CI secret. No keystore recreation is authorized without root-cause evidence and Human Owner approval.

### Server CI — OPEN

The current canonical line must gain an authoritative server test/compile CI gate. Existing branch CI in unmerged PRs is branch-only until integrated and revalidated on `main`.

### Instrumentation CI — OPEN

The current Android workflow runs Gradle unit tests but does not establish Android instrumentation as a CI gate. Real-device/emulator evidence is required where behavior cannot be established by source/unit tests.

### Release readiness — NOT ACCEPTED

No RC1 or production-readiness claim is accepted without exact-head validation of the final `main` commit and release artifact evidence.

## 4. AI REPORT RECONCILIATION

### GROK

Grok's main-line findings are broadly consistent with the actual Python/FastAPI tree. In particular, the MemoryStore runtime, missing recommendation authorization, current Android UI surface, schema/runtime distinction, and CI configuration are valid work inputs.

### CLAUDE

Claude's seven-part evidence protocol is adopted as Evidence Protocol v2 and is now binding.

### DEEPSEEK

DeepSeek's report contains useful threat-model questions, but several purported "verified" findings cite Go paths (`internal/store/memory/store.go`, `internal/auth/policy.go`, `internal/challenge/*`, `cmd/server/main.go`, etc.) that are absent from the canonical Python/FastAPI tree. Those claims are therefore not direct evidence for SENTINEL and are rejected/downgraded unless independently reproduced against `main`.

Specific reconciliations:

- MemoryStore persistence concern: **CONFIRMED**, but exact impact must be tested in the Python/FastAPI runtime.
- Default-deny: **ENGINE CONFIRMED**, but endpoint coverage is incomplete; `/v1/recommendations` is the concrete current-main gap.
- Challenge nonce/expiration/consumption: **ALREADY PRESENT** in current main; no duplicate fix should be implemented.
- Rate limiting: **OPEN HYPOTHESIS / TO AUDIT** against actual Python/FastAPI middleware; do not implement based solely on Go-path evidence.
- Audit cryptographic integrity: **OPEN DESIGN/REQUIREMENT QUESTION**; append-only audit behavior and cryptographic tamper evidence must be assessed separately.
- RLS: **PARTIAL** — RLS is enabled for three tables, but no policies exist in the current migration.
- Idempotency: **PARTIAL** — an `idempotency_keys` table exists; runtime enforcement remains to be audited.

## 5. Branch / PR inventory

Historical and feature branches remain intentionally preserved until classification. No destructive cleanup is authorized yet.

Substantive open PRs include the RC1 hardening line (`#17`, `#18`, `#19`), platform completion (`#16`), architecture/Core foundation (`#15`), pipeline/security history (`#1`, `#2`, `#3`), and current repository governance PR history.

The next task is not to blindly merge an RC1 PR. It is to compare its exact diff against current `main`, extract useful commits, remove obsolete/contradictory changes, and integrate only after exact-head validation.

## 6. Canonical state rules

- `main` is the only canonical product state.
- Architecture documents describe target/contract, not proof of runtime implementation.
- `BRANCH-ONLY` work is not accepted product state.
- A bare `PASS` is prohibited.
- A later main commit that breaks an accepted capability is a `REGRESSION`, not a new feature task.
- Destructive branch/PR cleanup occurs only after classification and preservation of useful history.

## 7. Authority

**Branch-state truth authority:** GPT / Final Integrator.  
**Human Owner:** absolute final authority for acceptance, scope, release, and destructive repository cleanup.
