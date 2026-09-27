# SENTINEL — Active Remote Branch Inventory

**Status:** ACTIVE  
**Repository:** `spenskoj90-sudo/alpha-0`

## Durable cleanup model

Branch state is decided from live GitHub refs, exact PR metadata and semantic reconciliation evidence. This document is the reviewed cleanup ledger consumed by the protected-main Branch Hygiene workflow; it is not a substitute for live enumeration.

The workflow now runs after **every push to protected `main`**. It may delete only:

- `MERGED_EXACT` — the live branch tip still equals the exact head SHA of a merged same-repository PR targeting `main`;
- `PURE_BEHIND` — the live tip is proven to be an ancestor of the exact protected-main SHA;
- `CONTENT_SUPERSEDED` — useful branch-only content was explicitly reconciled elsewhere and the live tip still equals the reviewed SHA.

The current merge's same-repository PR head is also self-cleaned only after GitHub independently proves merged state, `base=main`, exact PR head, exact merge commit and an unprotected non-`main` ref. Ref mutation, protection, missing reconciliation evidence or any other ambiguity fails closed.

The historical 2026-09-25 cleanup remains preserved as evidence: Branch Hygiene job `108131226210` reported `BRANCH_HYGIENE deleted=40 already_absent=0`. Later work created new short-lived branches, which are reconciled below. Once a listed ref is absent, later runs report it as already absent and never recreate it.

## Classification rules

- `ACTIVE` — intentionally retained current branch.
- `MERGED_EXACT` — live branch tip equals the stored exact head SHA of a merged PR.
- `PURE_BEHIND` — live branch tip is an ancestor of protected `main` and has no branch-only commit.
- `CONTENT_SUPERSEDED` — branch-only content was explicitly reconciled and no unique useful implementation/evidence remains.
- `UNIQUE_RECONCILE` — useful or uncertain branch-only content remains; deletion prohibited.
- `UNKNOWN` — deletion prohibited.

Deletion requires full live-tip revalidation. `MERGED_EXACT` additionally requires live PR-head equality. `CONTENT_SUPERSEDED` requires an explicit `RECONCILED:` reason. Protected refs are never deletion targets and any ref mutation aborts cleanup.

## Protected durable branch

| Branch | Classification | Evidence |
| --- | --- | --- |
| `main` | ACTIVE | protected production source of truth |

## Reviewed 2026-09-27 cleanup ledger

| Branch | Exact reviewed tip | Classification | Evidence |
| --- | --- | --- | --- |
| `chore/runtime-truth-reconcile-20260927` | `01052ae1c9d052cf8c40cda49759aeba7821e842` | MERGED_EXACT | PR #365 merged; live tip equals exact PR head |
| `design/android-access-provider-readiness-20260927` | `98c9d0fbfd60b7414c9db5efe595e05fe4d3210d` | CONTENT_SUPERSEDED | RECONCILED: PR #363 was intentionally closed after its same six-file change set was reapplied from current protected main and merged as PR #364; PR #363 closure comments record the supersession and stale-base avoidance |
| `design/android-access-provider-readiness-rebased-20260927` | `b5867e4d445c81f9b9c4a2a4af012549a5c85f0f` | MERGED_EXACT | PR #364 merged; live tip equals exact PR head |
| `design/companion-resilience-voice-admin-20260927` | `3f46fe220a40b354267f6435a57b7cab8bc8ab69` | CONTENT_SUPERSEDED | RECONCILED: PR #361 closure records that overlapping Companion work was superseded by merged PR #360 and its remaining Web Admin/documentation work was rebuilt from current main and merged as PR #362 |
| `design/companion-voice-resilience-20260927` | `2d80f743928af9af1572669c0544b892f77066de` | MERGED_EXACT | PR #360 merged; live tip equals exact PR head |
| `design/web-admin-operations-20260927` | `1ae8dddc2fef37d6d8e7ed2879899f4135877607` | MERGED_EXACT | PR #362 merged; live tip equals exact PR head |
| `feat/design-sync-free-test-infra-20260927` | `bcffdbc76c0c2f658c27c1383c473d5edd9b8369` | MERGED_EXACT | PR #359 merged; live tip equals exact PR head |
| `fix/account-email-delivery-truth-20260926` | `a2cdbeb9e41d9dde0962063951fdc8a247f4146e` | MERGED_EXACT | PR #356 merged; live tip equals exact PR head |
| `fix/android-core-readiness-20260926` | `6c1821d63629ad59ff8cce0dc49f509f56c9d8ae` | MERGED_EXACT | PR #358 merged; live tip equals exact PR head |
| `fix/android-diagnostic-export-handoff-20260926` | `30a035dd91f7d41aa866c831c2fbfebb2c7b5554` | MERGED_EXACT | PR #357 merged; live tip equals exact PR head |
| `fix/android-dns-failover-20260926` | `5665c8a806fa865eda28495adda15dc9540ac36f` | MERGED_EXACT | PR #355 merged; live tip equals exact PR head |
| `fix/android-landscape-adaptive-shell-2026-09-26` | `df939b6910ffc067000f7721489f6e25ddf5e3b7` | CONTENT_SUPERSEDED | RECONCILED: the five post-PR #351 compact-landscape commits were rebuilt from protected main and merged through PR #352, whose accepted scope explicitly covers merged forensic top-bar identity, the 48dp side rail and Compose/repository regression coverage |
| `fix/android-landscape-viewport-followup-2026-09-26` | `0939f79891ca7ae63e91ad58a0632e586943623a` | MERGED_EXACT | PR #352 merged; live tip equals exact PR head |
| `fix/android-loading-polish-20260926` | `8c180a4db8afc381b31a98de510bd616e8649b4e` | MERGED_EXACT | PR #354 merged; live tip equals exact PR head |
| `fix/android-product-gaps-20260926` | `ecc84f9004a5b6c8dce3e13ac53bf9c5c0820798` | MERGED_EXACT | PR #353 merged; live tip equals exact PR head |
| `fix/android-navigation-optical-polish-20260927` | `dbe3c880f78ac783d46813ee8b9c29f17ebf88d1` | MERGED_EXACT | PR #367 merged; live tip equals exact PR head |
| `feat/email-http-provider-fallback-20260927` | `f10f099a188d002dbd87d82490f2bfb144e462ee` | CONTENT_SUPERSEDED | RECONCILED: PR #368 was intentionally closed after protected main advanced; the reviewed email fallback change set was reapplied from current main and merged as PR #369 |
| `feat/email-http-provider-fallback-rebased-20260927` | `21cd506cd8a975d62a94e62b7f435cddcef18ac6` | MERGED_EXACT | PR #369 merged; live tip equals exact PR head |

The current PR branch that carries this ledger is intentionally omitted from the table: after merge, the workflow's independent same-repository merge-lineage gate handles that exact head automatically.

The older detailed reconciliation history remains preserved in Git history and `BRANCH_DELETION_MANIFEST_2026-09-23.md` as historical evidence; it is not live deletion authority.
