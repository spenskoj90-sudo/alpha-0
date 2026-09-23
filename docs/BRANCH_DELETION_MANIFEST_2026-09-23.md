# BRANCH_DELETION_MANIFEST — 2026-09-23

**Status:** ACTIVE AUDIT RECORD  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Baseline main:** `b218cab8130afbe3e413a9e7f2beb53e034a8daa`

Remote branch deletion is an **Owner-only irreversible gate**. This manifest does not delete anything and is deliberately conservative: a diverged branch that is not proven redundant is `UNIQUE_MUST_PRESERVE`.

## Method

- Enumerated every current remote branch through the GitHub API.
- `MERGED` requires a closed merged PR whose stored exact PR head SHA is identical to the branch's current tip. This avoids treating squash ancestry as proof and also proves no post-merge branch mutation.
- `PURE_BEHIND` was established by live compare against `main` with `ahead=0`.
- Generated `ci/state-sync-auto-*` branches are `CONTENT_SUPERSEDED` because their only branch-only path is the generated current-state document; current state is intentionally repository/live-evidence driven.
- All other non-merged diverged branches are preserved. The three specifically requested physical/device branches are therefore **not deletion candidates** merely because newer code exists; their current file blobs differ from main and require explicit content reconciliation before deletion.
- `ACTIVE_RECENT` covers the current integration branch and the parallel GPT-only same-day consolidation branch while useful work is reconciled.

## Totals

- total remote branches: 170
- non-main branches: 169
- MERGED: 124
- PURE_BEHIND: 10
- CONTENT_SUPERSEDED: 8
- UNIQUE_MUST_PRESERVE: 25
- ACTIVE_RECENT: 2
- UNKNOWN: 0
- potential deletion candidates after one explicit Owner bulk approval: 142

## Branch-by-branch classification

| Branch | Tip SHA | Classification | Evidence |
| --- | --- | --- | --- |
| `acceptance/staging-mfa-e2e-2026-09-21` | `3eb7d0133cec` | MERGED | PR #319 merged 2026-09-21; current branch tip equals exact merged PR head |
| `architecture/sentinel-adapter-contract-v1` | `ecb71379e4d6` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `architecture/sentinel-master-v0.3` | `ecb71379e4d6` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `architecture/vertical-block-definition` | `e333dda95311` | MERGED | PR #186 merged 2026-09-07; current branch tip equals exact merged PR head |
| `chore/audit-modernization-2026-09-23` | `4b260ee65f13` | MERGED | PR #334 merged 2026-09-23; current branch tip equals exact merged PR head |
| `chore/platform-dependency-modernization` | `482e9b1cb0a8` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `chore/platform-modernization-2026q3` | `cd94df40cd81` | MERGED | PR #307 merged 2026-09-18; current branch tip equals exact merged PR head |
| `chore/remove-sentry-smoke-temp-2026-09-06` | `e876a0e06ae3` | MERGED | PR #163 merged 2026-09-06; current branch tip equals exact merged PR head |
| `chore/runtime-modernization-2026q3` | `1260c991b602` | MERGED | PR #308 merged 2026-09-19; current branch tip equals exact merged PR head |
| `ci/finalize-workflow-cleanup` | `025d4a97807d` | MERGED | PR #184 merged 2026-09-07; current branch tip equals exact merged PR head |
| `ci/fix-auto-sync-required-checks-154` | `499425e61822` | MERGED | PR #155 merged 2026-09-05; current branch tip equals exact merged PR head |
| `ci/fix-sync-if-expression-syntax-2026-09-05` | `e6fa4a9698e7` | MERGED | PR #157 merged 2026-09-06; current branch tip equals exact merged PR head |
| `ci/fix-sync-reentrancy-filter-2026-09-05` | `3f7dd81073ed` | MERGED | PR #156 merged 2026-09-05; current branch tip equals exact merged PR head |
| `ci/issue-165-sync-pat` | `e9b895d428f0` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `ci/restore-sync-working-if-2026-09-06` | `10b2d593cec7` | MERGED | PR #158 merged 2026-09-06; current branch tip equals exact merged PR head |
| `ci/state-sync-auto-0b0c7b7bf15ce3e7345cf00c927f6fb870149c5a` | `682c69256476` | CONTENT_SUPERSEDED | branch-only change is generated docs/SENTINEL_CURRENT_STATE.md; current semantic state is repository/live-evidence driven |
| `ci/state-sync-auto-2b8c4b40aefc6e99f1ff7ef6a6c3a9fc82693d16` | `b9300d55556e` | CONTENT_SUPERSEDED | branch-only change is generated docs/SENTINEL_CURRENT_STATE.md; current semantic state is repository/live-evidence driven |
| `ci/state-sync-auto-16d2d16542fa7f0d269af2083ac9282cedd35cc0` | `613c7085a713` | MERGED | PR #172 merged 2026-09-06; current branch tip equals exact merged PR head |
| `ci/state-sync-auto-75d8bb19d415d0a8d6242987be43cd4d127b8191` | `721618f4be65` | CONTENT_SUPERSEDED | branch-only change is generated docs/SENTINEL_CURRENT_STATE.md; current semantic state is repository/live-evidence driven |
| `ci/state-sync-auto-179a889ce9c30d1fc0c1c08963eaf8b8fbda514c` | `9be940dfbb48` | CONTENT_SUPERSEDED | branch-only change is generated docs/SENTINEL_CURRENT_STATE.md; current semantic state is repository/live-evidence driven |
| `ci/state-sync-auto-280d1bb1a05e9878fffe7dc380beb5d1875b2857` | `6ceff5488598` | CONTENT_SUPERSEDED | branch-only change is generated docs/SENTINEL_CURRENT_STATE.md; current semantic state is repository/live-evidence driven |
| `ci/state-sync-auto-410ff49d5ad8974e29fbce50cb24dc9a9a06e388` | `c6178375869b` | CONTENT_SUPERSEDED | branch-only change is generated docs/SENTINEL_CURRENT_STATE.md; current semantic state is repository/live-evidence driven |
| `ci/state-sync-auto-713f602d0d3b86a836e6c7dcd093f5d7d59adefe` | `b7a5b3008111` | MERGED | PR #178 merged 2026-09-06; current branch tip equals exact merged PR head |
| `ci/state-sync-auto-33934d4d3d9c4655372fa159820f79ba90ed490d` | `b365e2ad2ab7` | CONTENT_SUPERSEDED | branch-only change is generated docs/SENTINEL_CURRENT_STATE.md; current semantic state is repository/live-evidence driven |
| `ci/state-sync-auto-c3d9ca55eb4437fa2fe709d69bf00726b9f1d586` | `4d3c604dfff6` | CONTENT_SUPERSEDED | branch-only change is generated docs/SENTINEL_CURRENT_STATE.md; current semantic state is repository/live-evidence driven |
| `ci/workflow-and-doc-state-cleanup` | `cefc8582bd69` | MERGED | PR #183 merged 2026-09-07; current branch tip equals exact merged PR head |
| `core/action-gateway-boundary` | `a51ae0de77d4` | MERGED | PR #189 merged 2026-09-07; current branch tip equals exact merged PR head |
| `core/companion-protocol-v1` | `e9b5d46c422e` | MERGED | PR #190 merged 2026-09-07; current branch tip equals exact merged PR head |
| `core/companion-runtime-v1` | `c135c79cd09b` | MERGED | PR #191 merged 2026-09-07; current branch tip equals exact merged PR head |
| `core/companion-tcp-transport-v1-current` | `f1f610bb8462` | MERGED | PR #202 merged 2026-09-08; current branch tip equals exact merged PR head |
| `core/companion-tcp-transport-v1` | `97794a6fc0f1` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `core/companion-transport-health-v1` | `f2cf08334fb8` | MERGED | PR #192 merged 2026-09-07; current branch tip equals exact merged PR head |
| `core/ugs-runtime-replay-foundation` | `05f75ba704a5` | MERGED | PR #187 merged 2026-09-07; current branch tip equals exact merged PR head |
| `core/wow-conservative-adapter` | `911e83802b10` | MERGED | PR #188 merged 2026-09-07; current branch tip equals exact merged PR head |
| `docs/coverage-policy-final` | `b35bda0183ef` | PURE_BEHIND | live compare against main: ahead=0; no branch-only files |
| `docs/gpt-only-autonomous-engineering-167` | `92e0eef11455` | MERGED | PR #168 merged 2026-09-06; current branch tip equals exact merged PR head |
| `docs/issue-146-current-state-snapshot` | `806adb445d1a` | MERGED | PR #148 merged 2026-09-05; current branch tip equals exact merged PR head |
| `docs/mark-simulation-harness-complete` | `02c29010a882` | MERGED | PR #205 merged 2026-09-09; current branch tip equals exact merged PR head |
| `docs/neon-pg18-target-ready-2026-09-19` | `733b1e4fa426` | MERGED | PR #313 merged 2026-09-19; current branch tip equals exact merged PR head |
| `docs/performance-baseline-2026-09-06` | `f0411fa657b4` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `docs/pg18-pre-release-cutover-2026-09-21` | `de031bf20a51` | MERGED | PR #318 merged 2026-09-21; current branch tip equals exact merged PR head |
| `docs/product-vision-context-194-main` | `0adaefe69217` | MERGED | PR #200 merged 2026-09-08; current branch tip equals exact merged PR head |
| `docs/product-vision-context-194-refresh` | `f4daf2c03cbe` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `docs/product-vision-context-194` | `b30503edcb76` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `docs/quality-coverage-policy` | `b35bda0183ef` | PURE_BEHIND | live compare against main: ahead=0; no branch-only files |
| `docs/reconcile-retired-ftl-status` | `ec3d5b12519a` | MERGED | PR #287 merged 2026-09-15; current branch tip equals exact merged PR head |
| `docs/reconcile-task-board-after-181` | `c1be41e70b6f` | MERGED | PR #203 merged 2026-09-09; current branch tip equals exact merged PR head |
| `docs/repository-first-governance-cleanup` | `64ee31cbb58c` | MERGED | PR #185 merged 2026-09-07; current branch tip equals exact merged PR head |
| `docs/retire-ftl-dependency` | `85e83bfa1e1b` | MERGED | PR #286 merged 2026-09-15; current branch tip equals exact merged PR head |
| `docs/sentinel-block-status` | `e43e8aa67bae` | MERGED | PR #262 merged 2026-09-12; current branch tip equals exact merged PR head |
| `docs/staging-mfa-accepted-2026-09-21` | `e5b77b762fb5` | MERGED | PR #320 merged 2026-09-21; current branch tip equals exact merged PR head |
| `docs/staging-mfa-runtime-reconcile-2026-09-19` | `cb26c1c5a580` | MERGED | PR #310 merged 2026-09-19; current branch tip equals exact merged PR head |
| `docs/telemetry-contract-v1` | `75162b599971` | MERGED | PR #174 merged 2026-09-06; current branch tip equals exact merged PR head |
| `feat/accessibility-hardening` | `2286f990d89d` | MERGED | PR #278 merged 2026-09-14; current branch tip equals exact merged PR head |
| `feat/account-mfa-totp-2026-09-19` | `88a79cf1c28f` | MERGED | PR #309 merged 2026-09-19; current branch tip equals exact merged PR head |
| `feat/account-security-lifecycle` | `b32ea4bef7bc` | MERGED | PR #304 merged 2026-09-18; current branch tip equals exact merged PR head |
| `feat/ai-provider-abstraction-v1` | `64ca8ecbe975` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `feat/ai-provider-abstraction-v2` | `5b1fb256da24` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `feat/ai-provider-abstraction-v3` | `3e266a569ac9` | MERGED | PR #212 merged 2026-09-09; current branch tip equals exact merged PR head |
| `feat/android-product-shell` | `9bd99c622577` | MERGED | PR #301 merged 2026-09-18; current branch tip equals exact merged PR head |
| `feat/billing-account-productization` | `cfba7eca9cef` | MERGED | PR #263 merged 2026-09-13; current branch tip equals exact merged PR head |
| `feat/billing-provider-entitlement-enforcement` | `9989cc0ddb7f` | MERGED | PR #264 merged 2026-09-13; current branch tip equals exact merged PR head |
| `feat/block-d-observability-resilience` | `7d5ee1f105c2` | PURE_BEHIND | live compare against main: ahead=0; no branch-only files |
| `feat/block-d-operational-plane` | `350f3d48de1c` | MERGED | PR #273 merged 2026-09-14; current branch tip equals exact merged PR head |
| `feat/canonical-design-system` | `c5386652d2c1` | MERGED | PR #283 merged 2026-09-14; current branch tip equals exact merged PR head |
| `feat/command-center-recommendation-panel-v1` | `d6e4d89236b1` | MERGED | PR #234 merged 2026-09-10; current branch tip equals exact merged PR head |
| `feat/companion-compatibility-profile-v1` | `26945d8bd3de` | PURE_BEHIND | live compare against main: ahead=0; no branch-only files |
| `feat/companion-compatibility-v1-rerun` | `0e674a31b42d` | MERGED | PR #216 merged 2026-09-09; current branch tip equals exact merged PR head |
| `feat/companion-compatibility-v1` | `0748dbcbb61d` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `feat/companion-correlation-observability` | `473e86d2cad4` | PURE_BEHIND | live compare against main: ahead=0; no branch-only files |
| `feat/companion-interaction-contract-v1` | `6c38d8b42552` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `feat/companion-interaction-contract-v2` | `eaf007f33809` | MERGED | PR #213 merged 2026-09-09; current branch tip equals exact merged PR head |
| `feat/companion-kill-switch-v1` | `cdfe64994fb9` | MERGED | PR #199 merged 2026-09-08; current branch tip equals exact merged PR head |
| `feat/companion-latency-health-integration-v1` | `21bed602e712` | MERGED | PR #238 merged 2026-09-10; current branch tip equals exact merged PR head |
| `feat/companion-latency-stats-v1` | `ca4fddc47dad` | MERGED | PR #237 merged 2026-09-10; current branch tip equals exact merged PR head |
| `feat/companion-network-transport-196` | `e6d6f7e7ecb2` | MERGED | PR #197 merged 2026-09-08; current branch tip equals exact merged PR head |
| `feat/companion-observability-seam` | `835e05d75e3b` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `feat/companion-observability-seam-v2` | `ca8ee78c234c` | MERGED | PR #209 merged 2026-09-09; current branch tip equals exact merged PR head |
| `feat/companion-overlay-presentation-runtime` | `327b91c279d2` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `feat/companion-peer-auth-seam` | `9e954020023d` | MERGED | PR #208 merged 2026-09-09; current branch tip equals exact merged PR head |
| `feat/companion-peer-session-integration-v1` | `985a89575c61` | PURE_BEHIND | live compare against main: ahead=0; no branch-only files |
| `feat/companion-persistent-observability-v1` | `e7297aab60fb` | MERGED | PR #220 merged 2026-09-10; current branch tip equals exact merged PR head |
| `feat/companion-runtime-evidence` | `f80092a48719` | MERGED | PR #270 merged 2026-09-13; current branch tip equals exact merged PR head |
| `feat/companion-runtime-telemetry-composition-v1` | `b19d9adc37dc` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `feat/companion-telemetry-fanout-v1` | `6401b366b1d0` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `feat/companion-voice-runtime` | `8d0f2df536e6` | MERGED | PR #272 merged 2026-09-13; current branch tip equals exact merged PR head |
| `feat/design-system-v2-implementation-2026-09-22` | `76d1edd1f4c6` | MERGED | PR #333 merged 2026-09-23; current branch tip equals exact merged PR head |
| `feat/deterministic-simulation-harness` | `ca21fc407455` | MERGED | PR #204 merged 2026-09-09; current branch tip equals exact merged PR head |
| `feat/exact-environment-l3-evidence` | `fb3d87210e70` | MERGED | PR #276 merged 2026-09-14; current branch tip equals exact merged PR head |
| `feat/federated-auth-providers` | `df46bd70ac6b` | MERGED | PR #305 merged 2026-09-18; current branch tip equals exact merged PR head |
| `feat/game-adapter-contract-v1` | `36aa67796f0c` | MERGED | PR #173 merged 2026-09-06; current branch tip equals exact merged PR head |
| `feat/game-adapter-registry-v1` | `5b31182c1075` | MERGED | PR #176 merged 2026-09-07; current branch tip equals exact merged PR head |
| `feat/intelligence-recommendation-routing-v1-rerun` | `ad1d6b38e40c` | MERGED | PR #219 merged 2026-09-10; current branch tip equals exact merged PR head |
| `feat/intelligence-recommendation-routing-v1` | `65b150a101df` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `feat/launcher-companion-runtime` | `05b975a61271` | MERGED | PR #265 merged 2026-09-13; current branch tip equals exact merged PR head |
| `feat/launcher-overlay-runtime` | `507c34db52bb` | MERGED | PR #268 merged 2026-09-13; current branch tip equals exact merged PR head |
| `feat/live-intelligence-command-center` | `09e7b59a9a69` | MERGED | PR #274 merged 2026-09-14; current branch tip equals exact merged PR head |
| `feat/observability-resilience-runtime` | `7483de21a750` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `feat/overlay-voice-interaction-contract-v1` | `38801f65cc32` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `feat/packaged-companion-host` | `47af7140e3bb` | MERGED | PR #275 merged 2026-09-14; current branch tip equals exact merged PR head |
| `feat/pre-release-free-infrastructure-hardening` | `0be674016851` | MERGED | PR #291 merged 2026-09-16; current branch tip equals exact merged PR head |
| `feat/pre-release-operations-and-sandbox` | `7ab5f8b0b146` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `feat/pre-release-runtime-completion` | `7e0892d8e677` | MERGED | PR #292 merged 2026-09-16; current branch tip equals exact merged PR head |
| `feat/presecret-release-binding` | `37d6bc16a6d3` | MERGED | PR #281 merged 2026-09-14; current branch tip equals exact merged PR head |
| `feat/provider-sandbox-runtime-hardening` | `162ba94ae428` | MERGED | PR #294 merged 2026-09-16; current branch tip equals exact merged PR head |
| `feat/quality-diagnostics-physical-test` | `f41beffe3ae4` | MERGED | PR #289 merged 2026-09-15; current branch tip equals exact merged PR head |
| `feat/recommendation-delivery-v1` | `b4ff4e6a87c2` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `feat/release-evidence-preflight` | `d5d6b892b40e` | MERGED | PR #279 merged 2026-09-14; current branch tip equals exact merged PR head |
| `feat/runtime-observability-contract` | `f577f123ac9c` | MERGED | PR #284 merged 2026-09-14; current branch tip equals exact merged PR head |
| `feat/supply-chain-evidence` | `1434efc50530` | MERGED | PR #280 merged 2026-09-14; current branch tip equals exact merged PR head |
| `feat/wow-passive-snapshot-ingestion` | `93953caee8d3` | MERGED | PR #266 merged 2026-09-13; current branch tip equals exact merged PR head |
| `feature/sentry-smoke-login-screen-2026-09-06` | `dc21c9e5a9df` | MERGED | PR #161 merged 2026-09-06; current branch tip equals exact merged PR head |
| `feature/sentry-smoke-verify-2026-09-06` | `d388c0bb847d` | MERGED | PR #159 merged 2026-09-06; current branch tip equals exact merged PR head |
| `fix/android-device-rebind-after-mfa-2026-09-21` | `df431487990e` | MERGED | PR #321 merged 2026-09-21; current branch tip equals exact merged PR head |
| `fix/android-device-rotation-crash-consistency-2026-09-22` | `6d635de1daea` | MERGED | PR #329 merged 2026-09-22; current branch tip equals exact merged PR head |
| `fix/android-identity-entitlements-recovery` | `c2a9a189a319` | MERGED | PR #302 merged 2026-09-18; current branch tip equals exact merged PR head |
| `fix/android-session-lifecycle-runtime-refresh-2026-09-22` | `dfc37ac8a6df` | MERGED | PR #324 merged 2026-09-22; current branch tip equals exact merged PR head |
| `fix/android-session-refresh-error-classification-2026-09-22` | `a9f85b7e7f61` | MERGED | PR #325 merged 2026-09-22; current branch tip equals exact merged PR head |
| `fix/android-staging-cold-start` | `06da3ecc07bc` | MERGED | PR #300 merged 2026-09-17; current branch tip equals exact merged PR head |
| `fix/companion-presentation-wire-isolation` | `779bd29c765e` | MERGED | PR #271 merged 2026-09-13; current branch tip equals exact merged PR head |
| `fix/device-bound-last-seen-metadata-2026-09-22` | `199012b24d54` | MERGED | PR #332 merged 2026-09-22; current branch tip equals exact merged PR head |
| `fix/device-rotation-crash-recovery-327` | `359e3fed1918` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `fix/exact-pr-head-checkout-2026-09-22` | `c73201998f6d` | MERGED | PR #323 merged 2026-09-22; current branch tip equals exact merged PR head |
| `fix/issue-149-current-state-sync` | `86cd974f5fd4` | MERGED | PR #150 merged 2026-09-05; current branch tip equals exact merged PR head |
| `fix/issue-151-current-state-sync-rerun` | `fc3db6c14327` | MERGED | PR #152 merged 2026-09-05; current branch tip equals exact merged PR head |
| `fix/physical-test-signer-evidence-2026-09-22` | `07f47dcfafa5` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `fix/physical-test-signer-lineage-2026-09-22` | `868d323e81b1` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `fix/post-merge-current-state-sync-2026-09-06` | `67baca0f74df` | MERGED | PR #169 merged 2026-09-06; current branch tip equals exact merged PR head |
| `fix/quality-cluster-root-hardening` | `6e46b59988f6` | MERGED | PR #290 merged 2026-09-16; current branch tip equals exact merged PR head |
| `fix/sync-pat-current-state-2026-09-06` | `f8c34312495a` | MERGED | PR #171 merged 2026-09-06; current branch tip equals exact merged PR head |
| `gpt/master-product-consolidation-v3-2026-09-23` | `b844d68b987d` | ACTIVE_RECENT | same-day GPT-only consolidation branch; useful content still being reconciled into PR #335 |
| `hardening/android-physical-test-readiness` | `22d52fe831a6` | MERGED | PR #299 merged 2026-09-17; current branch tip equals exact merged PR head |
| `hardening/design-system-reality-sync` | `7aa7dac9a132` | MERGED | PR #297 merged 2026-09-16; current branch tip equals exact merged PR head |
| `hardening/diagnostic-schema-alias` | `1c786d585a11` | UNIQUE_MUST_PRESERVE | non-merged diverged tip; deletion prohibited until branch-only content is explicitly reconciled or proven superseded |
| `hardening/final-acceptance-maintenance-v2` | `51ccf5c5e7af` | MERGED | PR #293 merged 2026-09-16; current branch tip equals exact merged PR head |
| `hardening/provider-runtime-reality-sync` | `ac1120d01ba1` | MERGED | PR #295 merged 2026-09-16; current branch tip equals exact merged PR head |
| `integration/block-a-rebaseline-supply-chain` | `dcd9a312d2a5` | MERGED | PR #257 merged 2026-09-12; current branch tip equals exact merged PR head |
| `integration/block-b-monetization-entitlement` | `97981fdefbce` | MERGED | PR #259 merged 2026-09-12; current branch tip equals exact merged PR head |
| `integration/block-c-companion-experience` | `4ba4ad2512a1` | MERGED | PR #260 merged 2026-09-12; current branch tip equals exact merged PR head |
| `integration/block-d-observability-resilience` | `e1ed0ae85a75` | MERGED | PR #261 merged 2026-09-12; current branch tip equals exact merged PR head |
| `integration/pass-1-ugs-completion` | `1f28c270bd84` | MERGED | PR #251 merged 2026-09-12; current branch tip equals exact merged PR head |
| `integration/pass-2-event-runtime` | `10a564f31040` | MERGED | PR #252 merged 2026-09-12; current branch tip equals exact merged PR head |
| `integration/pass-3-wow-vertical` | `17764e0001f8` | MERGED | PR #253 merged 2026-09-12; current branch tip equals exact merged PR head |
| `integration/pass-4-intelligence-completion` | `3219764ff92b` | MERGED | PR #254 merged 2026-09-12; current branch tip equals exact merged PR head |
| `integration/pass-4-intelligence-completion-quality` | `cb92df3ecf12` | PURE_BEHIND | live compare against main: ahead=0; no branch-only files |
| `integration/pass-5-companion-hardening` | `79b51a9a2366` | MERGED | PR #255 merged 2026-09-12; current branch tip equals exact merged PR head |
| `integration/pass-6-android-core-loop` | `2a08daa8c545` | MERGED | PR #256 merged 2026-09-12; current branch tip equals exact merged PR head |
| `integration/vertical-blocks-v1` | `e097b6d8e68c` | MERGED | PR #240 merged 2026-09-10; current branch tip equals exact merged PR head |
| `integration/vertical-blocks-v2` | `1f180d4d596d` | MERGED | PR #241 merged 2026-09-11; current branch tip equals exact merged PR head |
| `integration/vertical-blocks-v3` | `5a9c35e54f75` | MERGED | PR #242 merged 2026-09-11; current branch tip equals exact merged PR head |
| `integration/vertical-blocks-v4` | `ca1316dd30dd` | MERGED | PR #243 merged 2026-09-11; current branch tip equals exact merged PR head |
| `integration/vertical-blocks-v5` | `bc71ee7a8541` | MERGED | PR #244 merged 2026-09-11; current branch tip equals exact merged PR head |
| `integration/vertical-blocks-v6` | `8bbaa37fc7a0` | MERGED | PR #245 merged 2026-09-11; current branch tip equals exact merged PR head |
| `integration/vertical-blocks-v7` | `feb51cdd8023` | MERGED | PR #246 merged 2026-09-11; current branch tip equals exact merged PR head |
| `integration/vertical-blocks-v8` | `e61a650cbb1e` | MERGED | PR #247 merged 2026-09-11; current branch tip equals exact merged PR head |
| `integration/vertical-blocks-v9` | `57bb0dc50516` | MERGED | PR #248 merged 2026-09-11; current branch tip equals exact merged PR head |
| `integration/vertical-blocks-v10` | `f02ebbf27eeb` | MERGED | PR #249 merged 2026-09-11; current branch tip equals exact merged PR head |
| `integration/vertical-blocks-v11` | `73942eebf599` | MERGED | PR #250 merged 2026-09-11; current branch tip equals exact merged PR head |
| `noop` | `a3ace3607a4f` | PURE_BEHIND | live compare against main: ahead=0; no branch-only files |
| `polish/brand-design-update-channel-2026-09-21` | `eece9bcf6c41` | MERGED | PR #322 merged 2026-09-21; current branch tip equals exact merged PR head |
| `quality/coverage-policy` | `b35bda0183ef` | PURE_BEHIND | live compare against main: ahead=0; no branch-only files |
| `refactor/android-shared-http-transport` | `656f76d529d9` | MERGED | PR #269 merged 2026-09-13; current branch tip equals exact merged PR head |
| `refactor/auth-transport-222` | `da0bd9fa5fae` | MERGED | PR #223 merged 2026-09-10; current branch tip equals exact merged PR head |
| `release/delayed-host-acceptance-retention` | `c3e182731a0a` | MERGED | PR #288 merged 2026-09-15; current branch tip equals exact merged PR head |
| `release/final-acceptance-binding` | `97735b76ae8e` | MERGED | PR #285 merged 2026-09-15; current branch tip equals exact merged PR head |
| `security/admin-totp-mfa` | `afb297935c01` | MERGED | PR #303 merged 2026-09-18; current branch tip equals exact merged PR head |
| `security/attested-release-provenance` | `d9d3407b2352` | MERGED | PR #282 merged 2026-09-14; current branch tip equals exact merged PR head |
| `sentinel-v3-consolidation` | `f6fc94c63ad3` | ACTIVE_RECENT | active integration branch for PR #335 |
| `tmp/performance-baseline-10-sync` | `a60e10854576` | PURE_BEHIND | live compare against main: ahead=0; no branch-only files |

## Explicitly preserved requested branches

The following are `UNIQUE_MUST_PRESERVE` in this audit:

- `fix/device-rotation-crash-recovery-327`
- `fix/physical-test-signer-evidence-2026-09-22`
- `fix/physical-test-signer-lineage-2026-09-22`

Their live compares show branch-only commits and their affected file blobs are not byte-identical to current main. They must not be deleted until their branch-only semantics are reconciled against the newer implementation and evidence.

## Deletion gate

No remote branch is deleted by this pass. If the Human Owner later gives one explicit bulk approval, deletion may include only rows classified `MERGED`, `PURE_BEHIND` or `CONTENT_SUPERSEDED` at that time, after re-checking tips for mutation immediately before deletion. `UNIQUE_MUST_PRESERVE`, `ACTIVE_RECENT` and `UNKNOWN` remain excluded.
