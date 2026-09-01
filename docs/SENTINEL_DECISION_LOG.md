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
**Status:** Superseded by **D-016** and **D-017**. No non-main branches remain as of 2026-09-01.

## D-006 — Signing/keystore handling

**Date:** 2026-08-17  
**Decision:** No keystore recreation.  
**Reason:** Empty/unavailable keystore env is not proof of keystore corruption.

## D-007 — Security findings require stack-correct evidence

**Date:** 2026-08-17  
**Decision:** Security findings must reference the actual current backend stack and exact source paths.

## D-008 — Product work may proceed independently from backend reconciliation

**Date:** 2026-08-17  
**Decision:** UX/design exploration may proceed in parallel; backend integration waits for canonical-state reconciliation.

## D-009 — Recommendation authorization (historical)

**Date:** 2026-08-17  
**Decision (superseded by later main):** Gap remediated; negative regression present.

## D-010 — Challenge lifecycle finding from DeepSeek rejected against main

**Date:** 2026-08-17  
**Decision:** Main already implements consume/expiry; do not re-implement as new feature.

## D-011 — Idempotency finding must be narrowed

**Date:** 2026-08-17  
**Decision:** Schema presence and runtime enforcement are different claims.

## D-012 — RLS finding must distinguish enabled from policy-protected

**Date:** 2026-08-17  
**Decision:** RLS enablement and FORCE RLS are distinct; remediated via 002 + 004.

## D-013 — Emulator replaces blocking FTL for routine CI

**Date:** 2026-08-27  
**Decision:** Build & Test instrumentation uses GitHub-hosted Android Emulator (API 35). FTL remains optional when GCP is restored.  
**Evidence:** PR #68, Build & Test run `33069908061`.

## D-014 — Play Integrity remains fail-closed without audience

**Date:** 2026-08-27  
**Decision:** Keep fail-closed / UNKNOWN when audience unset; no mock production proof.

## D-015 — PR #68 merge gate

**Date:** 2026-08-27  
**Decision:** Merge only after exact-head product CI green and explicit Owner accept. Agents must not merge.

## D-016 — Historical branch cleanup groups 1+2 (issue #22)

**Date:** 2026-09-01  
**Decision:** Owner approved deletion of groups 1+2 (10 branches). Executed by Owner.

## D-017 — Historical branch cleanup group 3 (issue #22)

**Date:** 2026-09-01  
**Decision:** Owner deleted group 3 after comparison; only `main` remains.

## D-018 — Branch protection required checks (issue #22 complete)

**Date:** 2026-09-01  
**Decision:** Human Owner configured required status checks on `main` (require up-to-date branches). Required job names:
- Secret and image scan
- Core tests and coverage
- Android build and tests
- Dependency audit
- Web build
- CodeQL
- Build Android APK
- P1 evidence artifacts
- PostgreSQL integration and recovery
- Repository verification  
**Not required:** Deploy (external secrets).  
**Effect:** Issue #22 governance scope is complete (cleanup + protection).

## D-019 — Issue #63 backlog reconciliation

**Date:** 2026-09-01  
**Decision:** Reconcile #63 against live main without treating historical audit text as incomplete work:
- Done: client refresh lifecycle (#96), rate-limit bound/evict (#104), most Postgres security-negative / concurrent refresh coverage, minimal web admin entitlements regression.
- Moved: schema-domain reconciliation → #107.
- Blocked/optional: FTL expansion → #59 + D-013.
- Residual optional: deeper IDOR negatives; Android process-death + revoke session tests.  
**Reason:** Avoid re-implementing work already on main; keep #63 open only for explicit residual Owner chooses.
