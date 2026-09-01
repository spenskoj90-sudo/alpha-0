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
**Status:** Superseded for historical cleanup by **D-016** and **D-017**. No non-main branches remain as of 2026-09-01.

## D-006 — Signing/keystore handling

**Date:** 2026-08-17  
**Decision:** No keystore recreation.  
**Reason:** Current CI evidence proves an empty/unavailable `ALPHA0_KEYSTORE_BASE64` environment value, not corruption of the underlying keystore. The existing signing material must not be recreated without a concrete root cause and Human Owner checkpoint.

## D-007 — Security findings require stack-correct evidence

**Date:** 2026-08-17  
**Decision:** Security findings must reference the actual current backend stack and exact source paths.  
**Reason:** A red-team report cited Go-style paths while the canonical backend is Python/FastAPI under `server/`.

## D-008 — Product work may proceed independently from backend reconciliation

**Date:** 2026-08-17  
**Decision:** UX/design exploration may proceed in parallel, but implementation against backend endpoints waits for canonical-state reconciliation.  
**Reason:** Design does not require speculative backend changes; integration does.

## D-009 — Recommendation authorization (historical)

**Date:** 2026-08-17  
**Decision (superseded by later main):** Original gap on `/v1/recommendations` was remediated in main lineage; negative regression present.

## D-010 — Challenge lifecycle finding from DeepSeek rejected against main

**Date:** 2026-08-17  
**Decision:** Do not implement DeepSeek's proposed nonce/expiration fix as a new feature; main already implements consume/expiry.

## D-011 — Idempotency finding must be narrowed

**Date:** 2026-08-17  
**Decision:** Schema presence (`idempotency_keys`) and runtime enforcement are different claims.

## D-012 — RLS finding must distinguish enabled from policy-protected

**Date:** 2026-08-17  
**Decision:** RLS enablement and CREATE POLICY / FORCE RLS are distinct; both later remediated via 002 + 004.

## D-013 — Emulator replaces blocking FTL for routine CI

**Date:** 2026-08-27  
**Decision:** Build & Test instrumentation uses GitHub-hosted Android Emulator (API 35) as the product CI gate. FTL remains optional infra restoration when Cloud Tool Results API is enabled.  
**Evidence:** PR #68, Owner-approved design from PR #67, Build & Test run `33069908061` emulator job PASS.  
**Reason:** FTL was blocking green CI on GCP API configuration; emulator provides deterministic instrumentation without external GCP dependency.

## D-014 — Play Integrity remains fail-closed without audience

**Date:** 2026-08-27  
**Decision:** Do not mock live Google verification as production proof. Keep fail-closed / UNKNOWN when `SENTINEL_PLAY_INTEGRITY_AUDIENCE` is unset. Server nonce + tier policy + replay rejection are implemented and tested.  
**Reason:** Fake credentials or insecure fallbacks would undermine attestation trust.

## D-015 — PR #68 merge gate

**Date:** 2026-08-27  
**Decision:** PR #68 may merge only after exact-head product CI green **and** explicit Owner / Final Integrator accept. Agents must not merge.  
**Evidence:** HEAD `5439e715175eb8444c12aa85b81cbb0e9385b2b3`, Build & Test `33069908061` SUCCESS.

## D-016 — Historical branch cleanup groups 1+2 (issue #22)

**Date:** 2026-09-01  
**Decision:** Human Owner approved deletion of classified historical branches **groups 1+2** (10 branches). **Group 3** initially retained for manual comparison.  
**Execution:** Deletion performed by Human Owner.  
**Reason:** Classification complete; unique product work already on `main`.

## D-017 — Historical branch cleanup group 3 + hygiene complete (issue #22)

**Date:** 2026-09-01  
**Decision:** After content comparison against `main`, Human Owner deleted group 3:
- `feature/physical-device-diagnostics-2026-08-29` — content on main via PR #82 (`DiagnosticLogger` + instrumentation)
- `ui/sentinel-observation-point-2026-08-23` — UI tokens/theme present on main (`DesignTokens.kt`, `SentinelTheme.kt`)
- `ui/sentinel-observation-visual-system-2026-08-23` — same
**Verified live inventory:** only branch `main` remains.  
**Remaining for #22:** branch-protection required status checks (operator-only). Historical branch cleanup is complete.  
**Reason:** No unique product code remained only on those branches.
