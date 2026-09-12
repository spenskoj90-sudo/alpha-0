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
**Status:** Superseded by **D-016** and **D-017**. No non-main branches remain as of 2026-09-01 (feature leftovers after #115 cleaned by Owner).

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
**Original decision:** Merge only after exact-head product CI green and explicit Owner accept; agents must not merge.  
**Status:** **SUPERSEDED by the GPT-only governance adopted 2026-09-06.** Current rule is the exact-SHA merge gate in `docs/GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md`: GPT may merge when all required checks succeed on the exact PR HEAD SHA and repository protections permit the merge. Protected Owner gates remain unchanged.

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

## D-020 — Issue #63 closed as completed

**Date:** 2026-09-01  
**Decision:** Owner directed close of #63 after D-019 reconciliation. Residual optional work (deeper IDOR, Android process-death/revoke) explicitly out of scope. Schema-domain continues under #107. FTL remains optional via #59 / D-013.  
**Effect:** #63 marked COMPLETE in TASKS and CURRENT_STATE; next priority is #107 Phase 1 MVP (characters/game-state read APIs).

## D-021 — Issue #107 Phase 1 accepted on main

**Date:** 2026-09-02  
**Decision:** Phase 1 of #107 (store character methods + GET characters/games/access + IDOR/auth + tests) is merged via PR #115 at `a261389f589c0d281c3f45a772fa6ee17abade42`. Product CI green on exact HEAD. Phase 2 is event → character projection only; no direct public character write API (events remain the write path per ARCHITECTURE_V4).  
**Effect:** TASKS marks Phase 1 complete; #107 remains open for Phase 2.

## D-022 — Issue #107 Phase 2 implementation

**Date:** 2026-09-02  
**Decision:** Phase 2 projects `character.snapshot` / `character.upsert` / `character.state` events from `/v1/events:batch` into the `characters` store via `apply_character_projections` after a successful batch with `accepted > 0`. Required payload fields: `game_id`, `external_id`, `name`. Invalid payloads skip projection without failing the batch. Natural-key upsert reuses Phase 1 `store.upsert_character`. No public mutable character write API.  
**Evidence:** PR #118 merged at `f5b342310a0278b318b434976cc0d33e15fe10a6`.

## D-023 — Issue #107 closed as completed

**Date:** 2026-09-02  
**Decision:** Owner accepted Phase 1 + Phase 2 on main. #107 characters/game-state domain is COMPLETE.  
**Effect:** TASKS and CURRENT_STATE mark #107 closed; next backlog items remain #59 (optional) and #13/#11/#10/#8 unless Owner prioritizes otherwise.

## D-024 — Deploy workflow must not email on routine pushes

**Date:** 2026-09-02  
**Decision:** `deploy.yml` triggers only on `release` (published) and `workflow_dispatch`. Do not use `secrets.*` in job-level `if` (GitHub evaluates that poorly and produced repeated Failure runs + Gmail noise). Optional remote rollout is gated on repository variable `DEPLOY_ENABLED=true`; secrets are checked only inside the job when enabled. Deploy is not a required status check.

## D-025 — Repository-first engineering state (current)

**Date:** 2026-09-07  
**Decision:** Git `main` at an exact SHA is the authoritative source of actual repository/product implementation state. `SENTINEL_CURRENT_STATE.md` is an orientation document, not a live mirror or acceptance authority. Architecture documents/ADRs define intended design and constraints; TASKS defines work intent; CI/tests/runtime evidence prove implementation. Ordinary code changes do not require generated HEAD-sync documentation commits or PRs.

**Reason:** The project now has one AI engineering participant (GPT/ChatGPT) with direct repository access. Maintaining mutable state snapshots as a mandatory synchronization mechanism creates stale-document risk and unnecessary commits without adding technical evidence.

## D-026 — Short-lived, independently verifiable change sets

**Date:** 2026-09-07  
**Decision:** Use trunk-oriented development with short-lived branches and independently verifiable change sets. Work may be organized into larger coherent architectural blocks, but each PR should remain self-contained, testable, reviewable and integrable. Long-lived feature branches and artificial documentation-sync steps are avoided.

**Reason:** This preserves the user's requirement for coherent architectural progress while adopting established continuous-integration/trunk-based practices that reduce integration risk and feedback delay.

## D-027 — Vertical-block Definition of Done

**Date:** 2026-09-07  
**Decision:** A substantive SENTINEL architectural/product block is not considered complete merely because its code compiles or its backend tests pass. A block is complete only when its required vertical concerns are addressed together: implementation, applicable UX/design/visualization, security/privacy, performance/resource behavior, automated regression evidence, and required runtime/device/integration evidence. Documentation and acceptance criteria are updated in the same logical change set whenever the block changes product or architectural meaning.

**Operating rule:** Large architectural blocks may be delivered through several short-lived PRs, but every increment must remain independently testable, reviewable and integrable. No known required concern is intentionally deferred as a "later polish" item when it belongs to the block being implemented.

**Minimum completion dimensions:**
- implementation and contract boundaries;
- UX/design/visualization when the block has a user-facing surface;
- security, privacy and failure/degradation behavior;
- performance and resource characteristics appropriate to the block;
- automated tests and regression coverage;
- runtime/device/integration evidence where applicable;
- semantic documentation/decision records when architecture or product meaning changes.

**Reason:** SENTINEL is intended to be a durable, user-facing system rather than a collection of disconnected technical prototypes. Completing each block as a coherent vertical slice prevents deferred design, security, performance and validation work from becoming long-lived technical debt.

## D-028 — First SENTINEL Vertical Slice

**Date:** 2026-09-07  
**Decision:** The next implementation program is the first complete game-to-user vertical slice. Its ordered foundation is: UGS runtime validation → deterministic replay → conservative WoW adapter slice → Companion protocol/runtime → Policy Engine / Action Gateway boundary → context/recommendation/confidence/provenance → Command Center/overlay UX → observability/performance → real-device/integration acceptance.

**Scope rule:** The first slice remains deliberately conservative. It does not introduce autonomous combat, broad multi-version game support, production infrastructure or release publication. Exact-environment capabilities remain UNVERIFIED until the required L3 evidence exists.

**Reason:** This creates one complete, measurable SENTINEL path from game observation to safe user-facing intelligence before expanding breadth. Later features must build on this verified path rather than creating parallel unfinished subsystems.

## D-029 — Routine CI and release-signing separation

**Date:** 2026-09-12  
**Decision:** Pull-request validation builds/tests only debug and instrumentation Android artifacts and never loads release-keystore secrets. Signed APK creation and certificate verification exist only in manual release-candidate or Owner-triggered tag release workflows. Existing protected-check names remain stable.

**Reason:** Untrusted or routine PR execution does not need signing custody. Separating the boundary reduces secret exposure without weakening Android build, unit or emulator coverage.

## D-030 — Immutable CI dependencies and deterministic web install

**Date:** 2026-09-12  
**Decision:** Third-party GitHub Actions are pinned to full commit SHAs with readable release comments. Web dependencies use a committed npm lockfile and `npm ci`; Vitest is required before lint and production build. Repository verification rejects mutable Action references and regression to non-deterministic web CI installation.

**Reason:** Mutable Action tags and dependency resolution without a lockfile make exact-SHA repository evidence non-reproducible and expand supply-chain risk.

## D-031 — Canonical release-candidate version source

**Date:** 2026-09-12  
**Decision:** Root `VERSION` is the canonical cross-surface release-candidate version. Android reads it directly; repository verification requires equivalent npm and Python package versions. The release workflow rejects a tag that does not match it. Release tag creation and publication remain Owner-only.

**Reason:** Android already carried the monotonic RC2 build (`versionCode 10002`) while web/Core metadata and RC1-labelled documents lagged. Reconciliation must not downgrade an installed Android build or silently publish a version.
