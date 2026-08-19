# SENTINEL — Decision Log

## D-001 — Canonical branch

**Date:** 2026-08-17  
**Decision:** `main` is the only canonical product state.  
**Reason:** Historical work exists across many unmerged branches and PRs; branch evidence cannot be treated as product acceptance.

## D-002 — Architecture/implementation separation

**Date:** 2026-08-17  
**Decision:** `docs/ARCHITECTURE_V4.md` is treated as the architectural target/contract, not as a runtime implementation report.  
**Reason:** The document describes PostgreSQL and broader subsystems that are not all active in the current `main` runtime.

## D-003 — Evidence integrity

**Date:** 2026-08-17  
**Decision:** A bare `PASS` is prohibited in engineering handoffs. Status must specify branch/PR/main/release scope and exact SHA. The stricter seven-part evidence bundle in `SENTINEL_EVIDENCE_PROTOCOL.md` is binding.  
**Reason:** Previous project history contained CI-verified work that was not merged into main.

## D-004 — Branch-state ownership

**Date:** 2026-08-17  
**Decision:** GPT / Final Integrator owns canonical branch-state reconciliation. Human Owner retains final acceptance authority.  
**Reason:** A single authority is required to reconcile contradictory agent reports against live repository state.

## D-005 — No destructive branch cleanup yet

**Date:** 2026-08-17  
**Decision:** Do not delete/close historical branches or PRs until current AI handoffs are incorporated and each branch is classified.  
**Reason:** Some branches contain potentially reusable implementation that may be the shortest path to the canonical state.

## D-006 — Signing/keystore handling

**Date:** 2026-08-17  
**Decision:** No keystore recreation.  
**Reason:** Current CI evidence proves an empty/unavailable `ALPHA0_KEYSTORE_BASE64` environment value, not corruption of the underlying keystore. The existing signing material must not be recreated without a concrete root cause and Human Owner checkpoint.

## D-007 — Security findings require stack-correct evidence

**Date:** 2026-08-17  
**Decision:** Security findings must reference the actual current backend stack and exact source paths.  
**Reason:** A red-team report cited Go-style paths such as `internal/store/memory/store.go`, `internal/auth/policy.go`, and `internal/challenge/*`, while the canonical backend is Python/FastAPI under `server/`. Those claims cannot be treated as direct repository evidence without reproduction against the actual tree.

## D-008 — Product work may proceed independently from backend reconciliation

**Date:** 2026-08-17  
**Decision:** UX/design exploration may proceed in parallel, but implementation against backend endpoints waits for canonical-state reconciliation.  
**Reason:** Design does not require speculative backend changes; integration does.

## D-009 — Current main contains real recommendation authorization gap

**Date:** 2026-08-17  
**Decision:** `/v1/recommendations` is an active security/authorization work item because the current `main` handler authenticates the session but does not call `policy_engine.authorize` before returning a recommendation.  
**Evidence:** `server/app/main.py` at the current canonical line.  
**Reason:** This finding is directly reproducible in the actual Python/FastAPI code and is therefore distinct from stack-incompatible red-team claims.

## D-010 — Challenge lifecycle finding from DeepSeek is rejected against main

**Date:** 2026-08-17  
**Decision:** Do not implement DeepSeek's proposed nonce/expiration fix as a new feature. The current `main` code already generates a nonce, stores its hashed form, sets a 120-second expiry, tracks `consumed`, and rejects consumed/expired challenges.  
**Evidence:** `server/app/main.py` at the current canonical line.  
**Reason:** The proposed Go-path finding describes a different codebase and would create duplicate/conflicting work.

## D-011 — Idempotency finding must be narrowed

**Date:** 2026-08-17  
**Decision:** Do not accept the claim that the repository has no idempotency storage. `server/migrations/001_initial.sql` contains `idempotency_keys`. The remaining question is runtime enforcement, which must be audited separately.  
**Reason:** Schema presence and runtime behavior are different claims; neither should be inferred from the other.

## D-012 — RLS finding must distinguish enabled from policy-protected

**Date:** 2026-08-17  
**Decision:** Current migration enables RLS on `characters`, `entitlements`, and `audit_events`, but contains no `CREATE POLICY` statements. This is a real schema-hardening gap, not evidence that RLS is entirely absent.  
**Reason:** The distinction prevents both under-reporting and over-reporting the security state.
