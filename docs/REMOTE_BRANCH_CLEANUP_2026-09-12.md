# SENTINEL Remote Branch Cleanup Classification — 2026-09-12

**Status:** HISTORICAL SNAPSHOT / OWNER ACTION REQUIRED  
**Baseline:** `main` at `c3ad1e16a354624a1fdd78893a6998c2727586d0`  
**Open pull requests at inspection:** none

This is a read-only cleanup classification. No remote branch was deleted. Branch deletion is destructive and remains an Owner-only operation. Re-fetch and re-run ancestry/PR checks immediately before any deletion because this snapshot can become stale.

## Method

For every remote head other than `main`, compare `origin/<branch>` to the baseline with `git merge-base --is-ancestor` and `git rev-list --left-right --count main...origin/<branch>`.

- **SAFE TO DELETE:** the branch head is an ancestor of baseline `main`; it has zero commits unique to the branch.
- **RETAIN:** protected/canonical or active work.
- **MANUAL REVIEW:** the branch is not an ancestor and contains unique commits, even when later work may have replaced or reimplemented it.

## RETAIN

- `main` — canonical protected branch.

## SAFE TO DELETE — 46 branches

- `core/companion-runtime-v1`
- `core/companion-tcp-transport-v1-current`
- `core/companion-transport-health-v1`
- `docs/coverage-policy-final`
- `docs/gpt-only-autonomous-engineering-167`
- `docs/mark-simulation-harness-complete`
- `docs/product-vision-context-194-main`
- `docs/quality-coverage-policy`
- `docs/reconcile-task-board-after-181`
- `feat/command-center-recommendation-panel-v1`
- `feat/companion-compatibility-profile-v1`
- `feat/companion-compatibility-v1-rerun`
- `feat/companion-interaction-contract-v2`
- `feat/companion-kill-switch-v1`
- `feat/companion-latency-health-integration-v1`
- `feat/companion-latency-stats-v1`
- `feat/companion-observability-seam-v2`
- `feat/companion-peer-auth-seam`
- `feat/companion-peer-session-integration-v1`
- `feat/companion-persistent-observability-v1`
- `feat/deterministic-simulation-harness`
- `feat/intelligence-recommendation-routing-v1-rerun`
- `fix/post-merge-current-state-sync-2026-09-06`
- `fix/sync-pat-current-state-2026-09-06`
- `integration/pass-1-ugs-completion`
- `integration/pass-2-event-runtime`
- `integration/pass-3-wow-vertical`
- `integration/pass-4-intelligence-completion`
- `integration/pass-4-intelligence-completion-quality`
- `integration/pass-5-companion-hardening`
- `integration/pass-6-android-core-loop`
- `integration/vertical-blocks-v1` through `integration/vertical-blocks-v11`
- `noop`
- `quality/coverage-policy`
- `refactor/auth-transport-222`
- `tmp/performance-baseline-10-sync`

The range `integration/vertical-blocks-v1` through `v11` denotes eleven exact branch names, making the section total 46.

## MANUAL REVIEW — 50 branches

These branches contain between 1 and 15 commits not ancestral to the inspected `main`. Do not infer product value solely from branch names; inspect the unique patch and related closed PR before deletion.

- `architecture/sentinel-adapter-contract-v1`
- `architecture/sentinel-master-v0.3`
- `architecture/vertical-block-definition`
- `chore/remove-sentry-smoke-temp-2026-09-06`
- `ci/finalize-workflow-cleanup`
- `ci/fix-auto-sync-required-checks-154`
- `ci/fix-sync-if-expression-syntax-2026-09-05`
- `ci/fix-sync-reentrancy-filter-2026-09-05`
- `ci/issue-165-sync-pat`
- `ci/restore-sync-working-if-2026-09-06`
- `ci/state-sync-auto-0b0c7b7bf15ce3e7345cf00c927f6fb870149c5a`
- `ci/state-sync-auto-16d2d16542fa7f0d269af2083ac9282cedd35cc0`
- `ci/state-sync-auto-179a889ce9c30d1fc0c1c08963eaf8b8fbda514c`
- `ci/state-sync-auto-280d1bb1a05e9878fffe7dc380beb5d1875b2857`
- `ci/state-sync-auto-2b8c4b40aefc6e99f1ff7ef6a6c3a9fc82693d16`
- `ci/state-sync-auto-33934d4d3d9c4655372fa159820f79ba90ed490d`
- `ci/state-sync-auto-410ff49d5ad8974e29fbce50cb24dc9a9a06e388`
- `ci/state-sync-auto-713f602d0d3b86a836e6c7dcd093f5d7d59adefe`
- `ci/state-sync-auto-75d8bb19d415d0a8d6242987be43cd4d127b8191`
- `ci/state-sync-auto-c3d9ca55eb4437fa2fe709d69bf00726b9f1d586`
- `ci/workflow-and-doc-state-cleanup`
- `core/action-gateway-boundary`
- `core/companion-protocol-v1`
- `core/companion-tcp-transport-v1`
- `core/ugs-runtime-replay-foundation`
- `core/wow-conservative-adapter`
- `docs/issue-146-current-state-snapshot`
- `docs/performance-baseline-2026-09-06`
- `docs/product-vision-context-194`
- `docs/product-vision-context-194-refresh`
- `docs/repository-first-governance-cleanup`
- `docs/telemetry-contract-v1`
- `feat/ai-provider-abstraction-v1`
- `feat/ai-provider-abstraction-v2`
- `feat/ai-provider-abstraction-v3`
- `feat/companion-compatibility-v1`
- `feat/companion-interaction-contract-v1`
- `feat/companion-network-transport-196`
- `feat/companion-observability-seam`
- `feat/companion-runtime-telemetry-composition-v1`
- `feat/companion-telemetry-fanout-v1`
- `feat/game-adapter-contract-v1`
- `feat/game-adapter-registry-v1`
- `feat/intelligence-recommendation-routing-v1`
- `feat/overlay-voice-interaction-contract-v1`
- `feat/recommendation-delivery-v1`
- `feature/sentry-smoke-login-screen-2026-09-06`
- `feature/sentry-smoke-verify-2026-09-06`
- `fix/issue-149-current-state-sync`
- `fix/issue-151-current-state-sync-rerun`

## Owner action boundary

If cleanup is desired, the minimum safe sequence is: refresh refs → confirm no open PR or active automation uses the branch → repeat ancestry/unique-commit checks → delete only explicitly approved names. This document is classification evidence, not deletion authorization.
