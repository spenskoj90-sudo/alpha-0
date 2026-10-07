# Audit remediation Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Owner authorized execution on 2026-10-07; preserve one integration writer and resume this plan without duplicate work.

**Goal:** Remove the reproduced security/session/evidence defects and establish a truthful continuation queue for unfinished product work.

**Architecture:** Keep Core authoritative and one-use refresh unchanged. Web joins only currently pending refresh requests in a process; denied requests cannot erase newer browser cookies. A durable browser-family operation/generation row serializes credential mutations across BFF processes and makes late tokens fail closed without replay grace. All upstream responses are buffered within explicit time and byte limits. Bridge remains a read-only summary, never a release verifier.

**Tech Stack:** Node 24 / Next / Vitest; Python / pytest; repository CI and Render staging.

**Spec:** Owner audit authorization, root/scoped AGENTS, GAME_KNOWLEDGE_RUNTIME_V1, USER_VISIBLE_ACCEPTANCE_CONTRACT; audit checkpoint 77f5c742 / Library libfile_8d2a84772940819194211efbd74da2c5.

## Global Constraints

- One writer, one daily integration PR; exact-HEAD required checks with App binding before merge.
- Never weaken replay protection, RLS, action authority, security thresholds, physical or Owner acceptance.
- No production deployment, release/tag publication, credentials/signing custody or policy changes.
- WIP companion consumer ad51886eefa6bd223586a257f6ee08904f517db6 must survive.

## Review Focus

- Concurrent and late failed refresh responses cannot clear a newer session.
- Pending refresh is origin-bound, bounded and removed after settlement; no successful-token replay cache.
- Redirects, stalled headers/body and oversized upstream bodies fail closed without token output.
- Checklist edits cannot turn Bridge summary into release acceptance.
- Scoped dependency routing must retain security/evidence lanes and full unknown/shared fallback.

### Task 1: Web session safety and dependencies

**Files:** web/app/api/_lib/core-session.ts, core-session.test.ts, core-session-concurrency.test.ts, core-session-transport.test.ts, web/site package-lock.json.
**Interfaces:** proxyAuthenticated retains its signature; joins pending refresh only. coreFetch returns an already bounded Response; Core protocol unchanged.

- [x] Reproduce concurrent one-use refresh and delayed-denial cookie loss; add timeout, redirect, origin and oversized-body regression tests. Run targeted Vitest; expect assertion failures against baseline.
- [x] Implement process-shared pending refresh coordination, no cookie deletion on passive denial, HTTP(S) origin validation, 45-second upstream deadline, manual redirect rejection and 1 MiB streamed response cap. No credential result retained after pending refresh settles.
- [x] Upgrade sharp to fixed compatible 0.35.5 or newer patched version through locks. Fresh npm audit must contain no high/critical finding; run Web tests/coverage/lint/build and Site build.
- [x] Commit verified change and record exact results in checkpoint.

### Task 2: Bridge evidence truth

**Files:** control-bridge/sentinel_bridge/state.py, tests/test_state.py, docs/CONTROL_BRIDGE_ARCHITECTURE.md.
**Interfaces:** provider_state keeps configured booleans scoped to bridge environment, uses canonical names, never values; release_readiness explicitly remains unverified without canonical attestation verification.

- [x] Add regressions: fully checked metadata is still not release-ready; canonical provider variables report presence without leaking secrets; unknown/malformed surfaces fail closed. Run pytest; expect baseline failures.
- [x] Separate checklist summary from verified release evidence; correct canonical keys and document config presence versus provider enablement/Core state.
- [x] Run complete Bridge pytest/compileall and commit.

### Task 3: CI routing and current documentation

**Files:** scripts/change_classification.py, test_change_classification.py, test_provider_runtime_state.py; docs/TASKS.md, SENTINEL_CURRENT_STATE.md, API.md, DESIGN_SYSTEM_V3.md, USER_VISIBLE_ACCEPTANCE_CONTRACT.md; design/user-visible-acceptance.v1.json.
**Interfaces:** classify keeps all fixed keys and full push/unknown fallback; known package metadata scopes to its owning surface plus audit, supply-chain, P1 and release evidence.

- [x] Add known scoped metadata regressions plus shared/unknown/mixed fallback; run classifier tests, expect failures.
- [x] Implement conservative scoped dependency routing; acceptance checker validates IDs only within acceptance section.
- [x] Record open engineering work separately, current migration inventory and native production design authority; preserve historical DB checkpoints, imported asset pins and all release gates. Add knowledge API inventory; mark old handoff historical.
- [x] Run repository verification and complete relevant test suites; commit.

### Task 4: Integration and continuation

**Files:** docs/AUDIT_REMEDIATION_2026-10-07.md and remaining engineering queue.

- [ ] Whole-branch correctness/security review, regressions for material findings, exact-HEAD CI, protected merge and post-merge staging checks.
- [ ] Continue WIP Companion lifecycle only after a trusted exact-profile seam is available; then Android consumer, product catalog and Web security/device workflows as independently testable increments. Physical/source verification cannot be fabricated.
- [ ] Keep remaining program tasks unchecked with concrete next steps until implemented and verified; scheduling is continuation, not completion evidence.

### Task 5: F02 durable browser-session generation

**Files:** `server/migrations/017_web_session_generation.sql`, Core store/session routes, Web Core-session BFF, session concurrency/auth/PostgreSQL tests.
**Interfaces:** opaque browser-family cookie remains HttpOnly; BFF forwards it only to Core. Core returns a monotonic generation header. Access/refresh tokens remain opaque and one-use refresh remains strict.

- [x] Reproduce the late successful response and superseded store-operation cases with failing Web/MemoryStore regressions.
- [x] Implement atomic begin/commit generation checks for login/register, MFA, password-reset confirmation, refresh and logout; validate active generation on every Core session lookup.
- [x] Add migration FORCE RLS policy and PostgreSQL concurrency/logout regression; run local Web test/lint/build and non-PostgreSQL Core suite.
- [x] Resolve review races for legacy-refresh logout, failed duplicate registration reservations and post-mutation password-reset tombstones with RED/GREEN regressions.
- [x] Preserve independent pre-family browser sessions with an inherited hashed refresh-lineage identifier and concurrent rotate-vs-logout regressions.
- [ ] Require exact-HEAD PostgreSQL 18/RLS CI, independent final review, protected merge and post-merge staging verification before marking F02 integration-verified.
