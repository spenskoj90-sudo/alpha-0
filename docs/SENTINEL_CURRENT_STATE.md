# SENTINEL — Canonical Current State

**State record:** 2026-08-31  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Canonical HEAD (main):** `38184d3cb8b81c1ff2470327de104e1cc57e50a9`  
**Current product change on main:** PR #105 — Sentry Android runtime observability (merged)

> Git/main is authoritative for product state. Historical branch evidence is not current product state unless merged.
> Exact CI/release claims require the exact SHA plus workflow Run ID; unresolved evidence is recorded as **UNVERIFIED**.

## 1. Current repository facts

- Android client exists under `app/`.
- FastAPI backend exists under `server/`.
- Web control-plane source exists under `web/`.
- Electron launcher exists under `launcher/`.
- WoW addon sources exist under `wow-addon/` with Classic and Retail implementations.
- Device identity uses Android Keystore / EC P-256 with SHA-256 public-key fingerprinting.
- Sessions use opaque tokens with hashed persistence and one-time refresh rotation.
- Authorization is server-authoritative and default-deny.
- PostgreSQL is the production persistence implementation when `DATABASE_URL` is configured; FORCE RLS is applied by migration `004_p1_rls_force.sql`.
- In-process `RateLimiter` is bounded by `RATE_LIMIT_MAX_BUCKETS` (default 10000), evicts inactive buckets before capacity enforcement, and never displaces active buckets; implemented by PR #104.
- Android backup and cleartext traffic are disabled; release signing/fingerprint gates are enforced in CI.
- Sentry Android SDK 8.54.0 is integrated for release runtime observability by PR #105. `SENTRY_DSN` is supplied only to release assembly jobs; debug/PR builds use an empty default. Privacy scrubbing is implemented in `SentinelApplication`, and Sentry auto-init is disabled so initialization is controlled by application code.

## 2. Exact-HEAD evidence

Current `main` HEAD is `38184d3cb8b81c1ff2470327de104e1cc57e50a9`, the merge commit for PR #105.

Exact current-HEAD CI status and numeric coverage are **UNVERIFIED** in this state sync until fresh workflow Run IDs are independently extracted for this SHA. Historical green runs are not current evidence.

## 3. Module verification state

### `server/`
Current exact-head CI verification: **UNVERIFIED** pending fresh run-ID evidence. Rate-limit bounding/eviction is merged in PR #104.

### `app/`
Sentry Android runtime observability is merged in PR #105. Current exact-head Android CI verification: **UNVERIFIED** pending fresh run-ID evidence.

### `web/`
Current exact-head CI verification: **UNVERIFIED** pending fresh run-ID evidence.

### `launcher/`
Dedicated test/coverage evidence: **UNVERIFIED**.

### `wow-addon/`
Dedicated test/coverage evidence: **UNVERIFIED**.

## 4. External activation state

- Google Play Integrity audience/package/certificate and Google API authorization credentials.
- Production `DATABASE_URL` and deployment secrets.
- Real-device acceptance before public distribution.
- Release tag and GitHub Release publication when chosen by Owner.
- Firebase Test Lab GCS `storage.objects.create` permission (issues #59/#62).
- GitHub repository secret `SENTRY_DSN` before release builds emit Sentry events.
- Branch-protection required-status configuration remains an operator/governance concern unless independently verified.

## 5. Explicit security invariants

Do not silently change opaque-token sessions, Android Keystore P-256 identity, default-deny authorization, production `DATABASE_URL` / enrollment-token requirements, migration checksum enforcement, service-role/RLS boundaries, transactional refresh rotation, signing secrets or production credentials.

## 6. Completed workflow state

- **Issue #7 / PR #105 — Sentry Android runtime observability: COMPLETE / MERGED.** Merge commit `38184d3cb8b81c1ff2470327de104e1cc57e50a9`.
- **Issue #97 / PR #104 — bounded and evicted process-local rate-limit state: COMPLETE / MERGED.**
- **PR #100 — CI state-sync enforcement: COMPLETE / MERGED.** Merge commit `1df91de661c8bb0946d68f1671cbabf5f9714455`.
- **PR #101 — repository documentation hygiene/state synchronization: COMPLETE / MERGED.**
- **PR #103 — Android emulator runner pin: COMPLETE / MERGED.**

## 7. Open work

Open issues remain backlog candidates and require reconciliation before implementation. Current open issues are #63, #59, #22, #13, #12, #11, #10, #8 and #107.

- **#107 — Backend: implement characters/game-state domain (per ARCHITECTURE_V4): OPEN / planning.** The architectural target describes the character/game-state domain and candidate endpoints, but current runtime does not implement that domain. Implementation scope is intentionally tracked in #107 rather than inferred from `docs/API.md`.
- #59 is the external Firebase Test Lab IAM blocker.
- #22 is governance/administrative work.
- #63, #13, #12, #11, #10 and #8 remain planning/backlog items unless separately approved.

## 8. Evidence discipline

For CI, tests, coverage and release claims use exact commit SHA + workflow Run ID. For unresolved facts record **UNVERIFIED** rather than infer state from historical evidence.

**Final Integrator:** GPT / ChatGPT.  
**Human Owner:** absolute final authority for acceptance, scope, release, credentials, and destructive repository cleanup.
