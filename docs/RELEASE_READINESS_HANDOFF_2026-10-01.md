# SENTINEL release-readiness handoff — 2026-10-01

> **HISTORICAL CHECKPOINT.** Describes 2026-10-01 evidence only; old PRs, SHAs, logs and next steps are not the current work queue. Read live main and docs/TASKS.md.

## Reconciliation checkpoint

State: execution in progress; no frozen final candidate or release acceptance.

- Protected main: `e69eab9ed0694c1db0f00624c9aba122f465657e` (merge of #420).
- PR #420: merged after exact HEAD `48dbf730e930c2a331e731488deed72845a9808a`, all 10 required checks and independent review succeeded.
- Other open dependency PRs: #419 setup-gradle, #406 Gradle, #405 Node typings, #404 Sentry, #403/#402 superseded coupled Vitest, #401 Uvicorn, #400 SQLAlchemy.
- Branch inventory: main + #420 branch + 8 dependency branches.
- Open release gates: #371 staging providers, #375 Owner-visible UX, #314 physical Android/Windows Companion, #315 voice/provider microphone, #316 production provider/database/ingress, #317 signing/publication/deployment, #277 exact WoW environment.
- #379 orchestration expansion and #381 cross-model benchmark are optional engineering work; no live release-blocker evidence.

## Runtime

Render workspace: `tea-dal2fcoae00c73faqelg`. Initial reconciliation observed all four LIVE at `ebefe2615c18cec910f919cabfdd3c6cd2433abc`; post-merge runtime identity is not yet final-candidate evidence:

| Surface | Service | Deploy |
| --- | --- | --- |
| Core | srv-dal4iem7bikc73ebtau0 | dep-dav4i1rm8hqs739d0dog |
| Web | srv-dal4imjm8hqs73esuo6g | dep-dav4i1rm8hqs739d0e70 |
| Public Site | srv-dat8kq59fdbs7384ri90 | dep-dav4i1rm8hqs739d0eg0 |
| Control Bridge | srv-dat8i78jo6nc73emaed0 | dep-dav4i1rm8hqs739d0ebg |

Neon expected project `royal-butterfly-62116978`, branch `br-lingering-block-b1qa4fcd`; ready; PostgreSQL 18.6 and 39 FORCE-RLS tables independently verified read-only. No reset performed.

## Providers and design

- Resend: restricted free staging path has historical real delivery and Web password-reset evidence; exact final-candidate revalidation pending. Owned domain deliberately deferred.
- Telegram: Owner reports BotFather completed. Core catalog currently reports disabled; connected cloud Telegram browser shows QR sign-in, not an authenticated account. No BotFather setup restarted. Account sign-in/custody is an external activation gate.
- Google/VK: implemented, current Core catalog reports disabled; registration/callback/distribution/network evidence remains open. Stable Android test signing is Owner-gated.
- PostHog: staging-only by contract; no production activation.
- Stripe: sandbox only, no live payment authority.
- Design laboratory live HEAD: `56e6c9afdff501cc3451352c2b2dcd286b0ecdd1`. Prior current issue #375 records rejected import: TypeScript/lint and disconnected-route defects. No new lab commits.
- Imported production reference: `a281479677d84de21a24db62b0b13af7ae11c623`; some design docs name reviewed study `a6fc9d4c513dde9d549e5dd70159b1365a76b95c`. Provenance reconciliation will distinguish imported assets from reviewed studies and GPT-native production refinements.

## Durable evidence

- Sentinel root: `1a3Paj3Rk4YB5yA8bxfD0I6D6FcXV109p`.
- Release evidence folder: `1vNdOM1SgGpWUy39sQiQ_za5fEQLVdwso`.
- Earlier completion record: `1lrngg6BVH9TuYkfbpeyV55KIU3M0rIM5`; machine evidence: `17P42RvFUQTVpks2gZUWH6I4ByklH4144`. These are historical, not final-candidate evidence.
- Final APK/Companion/source-bound artifact IDs: not selected yet.

## Next execution

Finish #420, classify/reconcile dependency lanes, validate provider/UX/runtime deltas, resolve autonomous defects, then freeze exactly one green protected-main generation with matched artifacts and staging evidence. Physical/Owner/production/legal gates remain separate.

This record contains no credentials, one-time codes, tokens, signing material or credential-bearing URLs.

## Implementation checkpoint

- Working branch: `release/readiness-20261001`, isolated worktree; not yet merged/frozen.
- Web/Public Site coupled Next/eslint-config-next 16.3.8 official September security release; npm audits show zero known vulnerabilities.
- Sentry 8.58.0 retains existing PII defaults/scrubbing. setup-gradle 6.4.0 uses verified immutable tag commit.
- Node 26 typings, Gradle 9.8 wrapper, SQLAlchemy 2.1 autoflush and unused experimental Uvicorn 0.54 are deliberate RC holds, documented with Dependabot coupling/ignore policy.
- Native RU/EN Web account/recovery/navigation/admin; Public all routes; Companion/Overlay presentation. Canonical runtime/state/authority IDs remain unchanged.
- Storage-blocking regression reproduced by unit test; appearance fallback corrected. Local browser launch unavailable because Playwright CDN archive is truncated; exact-branch CI browser acceptance remains required. This is not a browser acceptance claim.
- Repository verifier: 445 PASS / 0 FAIL; design contracts: 13 PASS; Companion unit tests: 71 PASS. Final Web coverage/build and full CI pending.
- Imported design registry remains a281479; a6fc9d4 is reviewed native-study/master artwork provenance, lab56e6c9a remains rejected; current production refinement is GPT-owned.
- Final protected-main SHA, runtime deployment IDs and artifacts will replace this checkpoint only after exact CI/runtime verification.

## Owner feedback follow-up: verification email

Starting protected main `cf40028f4eb025a5ea6e738b15b12836cfd35b0a`, tree `5da6e569fbe10bd1fcf95aa48220af108eca01c3`. #420 and #426 merged; #427/#428 Node 24 typings maintenance open. All four staging deployments previously verified LIVE at cf40028; provider and design state retained in canonical Drive handoff `1ZzECIfeaULq6Y-3-OD2RjWeMdevGffhR`.

Owner reports phone test and diagnostic upload on October 1. Screenshot proves Owner-observed plaintext English verification email with unwieldy opaque code; no code retained in evidence. Fresh diagnostics were absent from canonical Drive Logs (`1Dmm-xTwNHJZH63-sNt2CgkcAVdC6_mYn`) at follow-up reconciliation; latest present diagnostic was September 27. Report remains Owner-reported, diagnostic correlation unverified.

New authorized branch `fix/email-numeric-code` implements `EMAIL_ACTION_CODES_V1.md`: branded RU/EN HTML plus plaintext, eight-digit copy/paste, 15-minute expiry, per-account/purpose persistent budget and attempt cap, compatible Android/Web input. Independent security review found a retention predicate regression, corrected before CI; PostgreSQL concurrency/retention integration tests added. Follow-up is in progress; final SHA/checks/artifacts must be written to durable evidence after merge. Previous freeze superseded by requested source change; physical observations stay bound to the previous SHA. Imported design pin a281479677d84de21a24db62b0b13af7ae11c623 and reviewed native-study a6fc9d4c513dde9d549e5dd70159b1365a76b95c remain unchanged; unstable lab56e6c9a is not imported.
