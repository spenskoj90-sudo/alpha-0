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


## Reviewed 2026-09-29 orchestration/design cleanup ledger

| Branch | Exact reviewed tip | Classification | Evidence |
| --- | --- | --- | --- |
| `docs/consolidate-orchestration-governance-20260929` | `fdfb6afc942ba067de9430ac60cead3b6224957f` | MERGED_EXACT | PR #398 merged to `main`; live tip equals exact PR head |
| `docs/design-lab-reconcile-20260929` | `031586fdb773814cdaab9bed79763e0f0809cbd8` | MERGED_EXACT | PR #396 merged to `main`; live tip equals exact PR head. This is the completed `a281479…` design-reference import only; later unfinished Lovable work is not included |
| `fix/remove-duplicate-recommendation-route-20260929` | `146ff38dbab317584f168447a6ba2bd4ecfb5685` | MERGED_EXACT | PR #395 merged to `main`; live tip equals exact PR head |
| `chore/consolidate-operating-model-20260929` | `3f27f8d98532110ca1ba3baaaa2a0635212d08b6` | CONTENT_SUPERSEDED | RECONCILED: PR #398 is the canonical GPT-controlled governance consolidation. This older parallel lane duplicates the same operating-model cleanup and adds extra current-memory/v2 instruction surfaces that are intentionally not retained because the compact active Project/Work instructions and v1 machine contract already encode the approved model |
| `docs/project-memory-orchestration-v2-20260929` | `5bda869a57394ecc5123f25a264fa7471e11f37a` | CONTENT_SUPERSEDED | RECONCILED: its branch-only `CHATGPT_PROJECT_MEMORY.md` and `ai-orchestration.v2.json` duplicate the canonical active instruction surfaces merged by PR #398. Keeping a second mutable memory/governance layer would recreate the stale-context problem this cleanup removes |


The current PR branch that carries this ledger is intentionally omitted from the table: after merge, the workflow's independent same-repository merge-lineage gate handles that exact head automatically.

The older detailed reconciliation history remains preserved in Git history and `BRANCH_DELETION_MANIFEST_2026-09-23.md` as historical evidence; it is not live deletion authority.

## Reviewed 2026-10-01 dependency reconciliation

The 13 dependency PRs were evaluated from exact patches. Accepted fixes are incorporated by #420/#426; incompatible or unused changes are deliberately rejected for the current RC and retained as historical PR evidence. No useful unique implementation is discarded. This ledger is executable only after #426 passes exact-HEAD CI and is merged; the existing protected-main workflow revalidates every exact live ref and refuses changed/protected refs.

| Branch | Exact reviewed tip | Classification | Evidence |
| --- | --- | --- | --- |
| `dependabot/pip/server/sqlalchemy-2.1.1` | `bd07f9bb4cbae40964bea50866ebfd43f1b824df` | CONTENT_SUPERSEDED | RECONCILED: PR #400 evaluated and rejected for this RC: SQLAlchemy 2.1 changes unconditional autoflush around FORCE-RLS transaction sequencing. Retain 2.0.54; explicit hold recorded in PR #426 and PLATFORM_MODERNIZATION_2026Q3. |
| `dependabot/pip/server/uvicorn-0.54.0` | `3609218a8c80e37457edd1f2ced6cd92d01af276` | CONTENT_SUPERSEDED | RECONCILED: PR #401 evaluated and rejected for this RC: 0.54 adds opt-in experimental HTTP/2 features unused by Core. Retain 0.53; explicit hold recorded in PR #426. |
| `dependabot/npm_and_yarn/web/vitest/coverage-v8-5.0.2` | `f8a5cbec6f0fa7d48b558e3007748d6040272bf8` | CONTENT_SUPERSEDED | RECONCILED: PR #402 exact coverage-v8 5.0.2 update is superseded by merged coupled PR #420 across Web and Site, with matching Vitest and regenerated lockfiles. |
| `dependabot/npm_and_yarn/web/vitest-5.0.2` | `a05e901e282f5b511cfb426af7de00b0c290caa0` | CONTENT_SUPERSEDED | RECONCILED: PR #403 exact Vitest 5.0.2 update is superseded by merged coupled PR #420 across Web and Site, with matching coverage provider and regenerated lockfiles. |
| `dependabot/gradle/io.sentry-sentry-android-8.58.0` | `bbbee7b4635f0b97ad7c9b8520a6a0af8e1bfe95` | CONTENT_SUPERSEDED | RECONCILED: PR #404 Sentry 8.58.0 update is fully incorporated in PR #426; existing PII defaults and scrubber remain unchanged. |
| `dependabot/npm_and_yarn/web/types/node-26.6.3` | `bf5a69eac0384b7f2d69ed935bc30b6e97ca9082` | CONTENT_SUPERSEDED | RECONCILED: PR #405 Node 26 declaration-only update deliberately rejected because both Web and Site select Node 24 runtime and matching declarations; PR #426 records the shared hold. |
| `dependabot/gradle/gradle-wrapper-9.8.0` | `3217149ff799963080ed709934bacf8f1e6276dc` | CONTENT_SUPERSEDED | RECONCILED: PR #406 deliberately rejected: Gradle 9.8 patch replaces the verified bootstrap with a missing-wrapper-JAR invocation; JDK25/AGP9.4 retains tested9.7.1; hold recorded in PR #426. |
| `dependabot/github_actions/gradle/actions/setup-gradle-6.4.0` | `e4a7c65e0eb2dc44c5cd5cae9c9f1b1220b43c91` | CONTENT_SUPERSEDED | RECONCILED: PR #419 setup-gradle6.4.0 exact verified pin3f5f9adaf7d9fecd50b5935e54106014257a94e6 is fully incorporated in all affected workflows by PR #426. |
| `dependabot/npm_and_yarn/site/typescript-7.0.2` | `34fb0537173e589fb694a883d5d0fc239fe04db8` | CONTENT_SUPERSEDED | RECONCILED: PR #421 TypeScript7.0.2 update rejected: current TypeScript ESLint plugin8.70.0 requires >=4.8.4 <6.1.0; retain6.0.3 under the coordinated PR #426 tooling hold. |
| `dependabot/npm_and_yarn/site/types/node-26.6.3` | `7c0cd01dcbc7777f10c0ecded51243f2a93becd4` | CONTENT_SUPERSEDED | RECONCILED: PR #422 Node26 declaration-only update deliberately rejected for the Node24 runtime, same reconciled shared hold as #405 in PR #426. |
| `dependabot/npm_and_yarn/site/eslint-10.11.0` | `3f4c7a718c9cf76b737a3e8319a5b0e85c2223a1` | CONTENT_SUPERSEDED | RECONCILED: PR #423 ESLint10.11 update rejected: current eslint-plugin-react7.37.5 supports through ^9.7, excluding10; retain9.39.5 under PR #426 tooling hold. |
| `dependabot/npm_and_yarn/web/eslint-10.11.0` | `5c4cf1f252e58004803cd7925d0f433599fcef36` | CONTENT_SUPERSEDED | RECONCILED: PR #424 ESLint10.11 update rejected: current eslint-plugin-react7.37.5 supports through ^9.7, excluding10; retain9.39.5 under PR #426 tooling hold. |
| `dependabot/npm_and_yarn/web/typescript-7.0.2` | `d89b54759193d801d013a82f64bce190eabb9ffc` | CONTENT_SUPERSEDED | RECONCILED: PR #425 TypeScript7.0.2 update rejected: current TypeScript ESLint plugin8.70.0 requires >=4.8.4 <6.1.0; retain6.0.3 under PR #426 tooling hold. |
