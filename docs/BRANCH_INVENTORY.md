# SENTINEL — Active Remote Branch Inventory

**Status:** ACTIVE  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Reconciliation baseline:** protected `main` at `053cf559971b6e3e10b4ad9b94ca83ba7fefa1e7`  
**Live branch count before this reconciliation branch was created:** 40

This file is the current branch-hygiene contract. It replaces the dated 2026-09-23 deletion manifest as an active source; the dated manifest remains a historical evidence record.

## Classification rules

- `ACTIVE` — intentionally retained current branch.
- `MERGED_EXACT` — current live branch tip equals the stored exact head SHA of a merged PR.
- `PURE_BEHIND` — live branch tip is an ancestor of protected `main` and has no branch-only commit.
- `CONTENT_SUPERSEDED` — branch-only content was explicitly reconciled and no unique useful implementation/evidence remains.
- `UNIQUE_RECONCILE` — useful or uncertain branch-only content remains and deletion is prohibited.
- `UNKNOWN` — deletion is prohibited.

Deletion is permitted only after the workflow revalidates the **full live tip SHA**. `MERGED_EXACT` additionally re-reads the merged PR and requires exact head equality. `CONTENT_SUPERSEDED` additionally requires an explicit `RECONCILED:` evidence statement in this file. A ref mutation aborts deletion.

The temporary branch carrying this reconciliation PR is intentionally not listed as a deletion candidate because its final tip is not knowable until the PR content is complete. The cleanup workflow may delete the branch that produced the current main merge commit only after independently proving same-repository head, `base=main`, merged state, exact PR-head equality and exact merge-commit identity.

## Live inventory before cleanup

| Branch | Exact tip SHA | Classification | Evidence |
| --- | --- | --- | --- |
| `main` | `053cf559971b6e3e10b4ad9b94ca83ba7fefa1e7` | ACTIVE | protected production source of truth |
| `architecture/sentinel-adapter-contract-v1` | `ecb71379e4d67b49926db7a2907e8400f93f6a09` | CONTENT_SUPERSEDED | RECONCILED: same tip as the old master-architecture branch; capability matrix and reference-failure audit are retained on main, while the architecture/task state is newer and the adapter/UGS program was merged through #173 and subsequent vertical passes |
| `architecture/sentinel-master-v0.3` | `ecb71379e4d67b49926db7a2907e8400f93f6a09` | CONTENT_SUPERSEDED | RECONCILED: capability matrix/reference audit are retained; current master architecture and task board supersede the old gap list and later merged passes implement those gaps |
| `chore/android-warning-cleanup-2026-09-25` | `4fb70c52142c444fd729b1762fe8932f8a2cda72` | MERGED_EXACT | PR #346 merged; live tip equals exact PR head |
| `chore/platform-dependency-modernization` | `482e9b1cb0a8ec0eb592cda9982f768a4f691e16` | CONTENT_SUPERSEDED | RECONCILED: later platform/runtime modernization #307/#308 and maintenance #344/#346/#347 contain newer validated runtime, action, Android, Web, Core and Companion pins; the branch's older design-v1/baseline state is not authoritative |
| `ci/issue-165-sync-pat` | `e9b895d428f0b0ceef1d9fe48f00e970ed2c2817` | CONTENT_SUPERSEDED | RECONCILED: the mutable CURRENT_STATE-head sync model was retired; current state is repository/live-evidence driven and repository verification rejects embedding a mutable main SHA |
| `ci/state-sync-auto-0b0c7b7bf15ce3e7345cf00c927f6fb870149c5a` | `682c69256476d1981fb12c281fa2383c11a58c25` | CONTENT_SUPERSEDED | RECONCILED: generated-only historical CURRENT_STATE snapshot; canonical current state intentionally does not mirror a mutable head SHA |
| `ci/state-sync-auto-2b8c4b40aefc6e99f1ff7ef6a6c3a9fc82693d16` | `b9300d55556e9483ba1a29297cab3d0b12483bb2` | CONTENT_SUPERSEDED | RECONCILED: generated-only historical CURRENT_STATE snapshot; canonical current state intentionally does not mirror a mutable head SHA |
| `ci/state-sync-auto-75d8bb19d415d0a8d6242987be43cd4d127b8191` | `721618f4be65c3189350db03119a73bc2a608fb0` | CONTENT_SUPERSEDED | RECONCILED: generated-only historical CURRENT_STATE snapshot; canonical current state intentionally does not mirror a mutable head SHA |
| `ci/state-sync-auto-179a889ce9c30d1fc0c1c08963eaf8b8fbda514c` | `9be940dfbb4804553aab866d4da969bb36f2d036` | CONTENT_SUPERSEDED | RECONCILED: generated-only historical CURRENT_STATE snapshot; canonical current state intentionally does not mirror a mutable head SHA |
| `ci/state-sync-auto-280d1bb1a05e9878fffe7dc380beb5d1875b2857` | `6ceff54885980995643b32a67e9a4fdf786c53d1` | CONTENT_SUPERSEDED | RECONCILED: generated-only historical CURRENT_STATE snapshot; canonical current state intentionally does not mirror a mutable head SHA |
| `ci/state-sync-auto-410ff49d5ad8974e29fbce50cb24dc9a9a06e388` | `c6178375869b3b92f3da06abc13433a799568293` | CONTENT_SUPERSEDED | RECONCILED: generated-only historical CURRENT_STATE snapshot; canonical current state intentionally does not mirror a mutable head SHA |
| `ci/state-sync-auto-33934d4d3d9c4655372fa159820f79ba90ed490d` | `b365e2ad2ab7cc1d6e36ff564a28eff40caf8c06` | CONTENT_SUPERSEDED | RECONCILED: generated-only historical CURRENT_STATE snapshot; canonical current state intentionally does not mirror a mutable head SHA |
| `ci/state-sync-auto-c3d9ca55eb4437fa2fe709d69bf00726b9f1d586` | `4d3c604dfff6a38dc1ecdb7186957fb59d405db7` | CONTENT_SUPERSEDED | RECONCILED: generated-only historical CURRENT_STATE snapshot; canonical current state intentionally does not mirror a mutable head SHA |
| `core/companion-tcp-transport-v1` | `97794a6fc0f17f1b2b9b30fd3d94234048751a63` | CONTENT_SUPERSEDED | RECONCILED: PR #202 merged the successor transport; current main retains `CompanionTcpTransport`, the same v1 contract document, and substantially expanded transport implementation/tests |
| `docs/performance-baseline-2026-09-06` | `f0411fa657b4e9043c7ee6a4fcd0490a0689d86a` | CONTENT_SUPERSEDED | RECONCILED: current `SENTINEL_PERFORMANCE_BASELINE.md` is newer and expanded; the branch's accompanying architecture/task snapshots are historical and no longer authoritative |
| `docs/product-vision-context-194-refresh` | `f4daf2c03cbebef18aabbcb0ed17dbc457e9278b` | CONTENT_SUPERSEDED | RECONCILED: canonical main product-vision content is equivalent apart from trailing newline/Markdown spacing normalization |
| `docs/product-vision-context-194` | `b30503edcb76a34235629f77b2b93d0135b8d577` | CONTENT_SUPERSEDED | RECONCILED: canonical main product-vision content is equivalent apart from Markdown hard-break/trailing-newline normalization and was later merged through #200 |
| `docs/v3-post-merge-evidence-2026-09-23` | `41c9d9bc118eb1176a4a011d77c53bc721fb91ad` | MERGED_EXACT | PR #344 merged; live tip equals exact PR head |
| `feat/ai-provider-abstraction-v1` | `64ca8ecbe97578984a75112a5348de900decfe82` | CONTENT_SUPERSEDED | RECONCILED: later merged provider abstraction #212 and current main retain all public provider symbols with additional validation/hardening |
| `feat/ai-provider-abstraction-v2` | `5b1fb256da24e8cbc10fdc6300fdc7db90ee05e1` | CONTENT_SUPERSEDED | RECONCILED: later merged provider abstraction #212 and current main retain all public provider symbols with additional validation/hardening |
| `feat/companion-compatibility-v1` | `0748dbcbb61d03068b2c8dd23b2f7f92e59c89a1` | CONTENT_SUPERSEDED | RECONCILED: retry successor PR #216 merged; current main contains the same compatibility implementation and newer integration state |
| `feat/companion-interaction-contract-v1` | `6c38d8b4255232ccd59755b2483b5ade36a4a1b4` | CONTENT_SUPERSEDED | RECONCILED: v2 successor PR #213 merged; current main retains the v1 implementation symbols and newer interaction contract |
| `feat/companion-observability-seam` | `835e05d75e3b86d78434eb475f00c41b93182ffa` | CONTENT_SUPERSEDED | RECONCILED: successor PR #209 merged; current main retains all telemetry public types and expands scrubbing/runtime behavior |
| `feat/companion-overlay-presentation-runtime` | `327b91c279d24389e7854d9685b195e95343b1f0` | CONTENT_SUPERSEDED | RECONCILED: read-only launcher overlay was productized by merged PR #268; current main retains the branch's Core experience/protocol public surface with later isolation and voice hardening |
| `feat/companion-runtime-telemetry-composition-v1` | `b19d9adc37dc63a628a15ffe6c3e49447f52b54c` | CONTENT_SUPERSEDED | RECONCILED: current main retains `compose_companion_telemetry` and `FanoutCompanionTelemetrySink`; later persistent observability and Block D merges supersede the branch composition |
| `feat/companion-telemetry-fanout-v1` | `6401b366b1d07a91061b04b7911c593673bfc561` | CONTENT_SUPERSEDED | RECONCILED: current main retains the same fanout sink implementation contract and later merged observability composition supersedes the isolated precursor |
| `feat/intelligence-recommendation-routing-v1` | `65b150a101df704e660bd04824f735ad84029259` | CONTENT_SUPERSEDED | RECONCILED: retry successor PR #219 merged and current main retains the recommendation engine implementation |
| `feat/observability-resilience-runtime` | `7483de21a750e436d7d1c2263037cfa3b0f9737d` | CONTENT_SUPERSEDED | RECONCILED: Block D PR #261 and operational-plane PR #273 merged; current main refactors/extends correlation, bounded metrics, failure injection and runtime observability beyond this precursor |
| `feat/overlay-voice-interaction-contract-v1` | `38801f65cc324019a359882fb78f7907645b4f75` | CONTENT_SUPERSEDED | RECONCILED: interaction-contract v2 PR #213 merged and current main retains the same interaction authority boundary |
| `feat/pre-release-operations-and-sandbox` | `7ab5f8b0b14675b326b9f86ac712efb7fa24b7fa` | CONTENT_SUPERSEDED | RECONCILED: merged pre-release infrastructure/runtime/provider passes #291/#292/#293/#294 and current final-acceptance tooling are newer and strictly more complete |
| `feat/recommendation-delivery-v1` | `b4ff4e6a87c22691ebb4de18de9ad3b6d02f84bd` | CONTENT_SUPERSEDED | RECONCILED: current main retains the same delivery class/result behavior; code was compacted/evolved without removing the branch contract |
| `fix/brand-master-physical-ui-2026-09-24` | `a9828d3cd13452418946fbaab088a6d0516bc323` | MERGED_EXACT | PR #345 merged; live tip equals exact PR head |
| `fix/device-rotation-crash-recovery-327` | `359e3fed1918091a81d9578635eb0081a63537b5` | CONTENT_SUPERSEDED | RECONCILED: crash-consistent rotation was merged through PR #329 and fail-closed device revocation/metadata through #332; current Android rotation implementation is the later accepted version |
| `fix/physical-test-signer-evidence-2026-09-22` | `07f47dcfafa5db69fbace4f220129f8d281c881b` | CONTENT_SUPERSEDED | RECONCILED: although PR #328 was not merged, current main implements its useful signer-continuity semantics: pinned `PHYSICAL_TEST_SIGNER_SHA256`, apksigner extraction, exact comparison, manifest lineage flags and repository-verifier assertions |
| `fix/physical-test-signer-lineage-2026-09-22` | `868d323e81b16de9f80f23ff0e33aabc5786d819` | CONTENT_SUPERSEDED | RECONCILED: although PR #326 was not merged, current main contains the stable-test signer pin/lineage validation and stronger release-candidate/final-acceptance signer binding |
| `gpt/final-master-doc-runtime-reconcile-2026-09-25` | `b73f3855f48fe75f6cf4e956ef00efeeca172013` | MERGED_EXACT | PR #348 merged; live tip equals exact PR head |
| `gpt/final-master-release-readiness-2026-09-25` | `ec446bc889a1f090ceff2bd4484272873432c01f` | MERGED_EXACT | PR #347 merged; live tip equals exact PR head |
| `gpt/master-product-consolidation-v3-2026-09-23` | `b844d68b987d137562af82f9f5f2f34e07c3b19f` | CONTENT_SUPERSEDED | RECONCILED: parallel v3 work was superseded by Owner-approved production Design System v3 merged in #335 and hardened by #344–#348; its added v3 asset/surface paths exist on main and current canonical v3 deliberately wins where variants differ |
| `hardening/diagnostic-schema-alias` | `1c786d585a112cb072971125b14cbe88f5d1241c` | CONTENT_SUPERSEDED | RECONCILED: branch-only change is a diagnostic schema-alias test; current main has the newer `schema_name` alias fixture and stronger warning assertion, so no unique implementation remains |

## Expected post-cleanup state

After exact-tip revalidation and deletion, only protected `main` plus any branch carrying an in-flight PR may remain. No branch classified `UNIQUE_RECONCILE` or `UNKNOWN` exists in this inventory.
