# 23 October 2026: PR and Issue disposition

## Truth and authority

The Human Owner requested a decision and administrative closure for the open GitHub
PR/Issue inventory on 2026-10-23. This register archives the dispositions. **Closing
a GitHub Issue is not acceptance, completion or cancellation of its underlying safety
and product requirements.** Live main/CI/runtime evidence outranks this historical
snapshot. Current technical priorities remain in `docs/TASKS.md`, the active product
roadmap in `docs/PLAYER_INTELLIGENCE_ROADMAP_V1.md`, and binding release/physical
gates in `docs/RELEASE_GATES.md`, `docs/FINAL_RELEASE_ACCEPTANCE_V1.md`,
`docs/USER_VISIBLE_ACCEPTANCE_CONTRACT.md` and
`docs/ANDROID_PHYSICAL_TEST_UPDATE_CHANNEL.md`.

Source prior to reconciliation: `41125e160c6cd0a34bf570e5bddc473ad6883a4c`.
No production deploy, release tag, signing keys, billing or privileged action was
authorized or performed by administrative tracker closure.

## Open Dependabot PRs resolved

Selected for coordinated exact-main integration, conditional on current-head CI:
- #487 OSV Scanner Action 2.7.0
- #482 FastAPI 0.143.3
- #480 Pydantic 2.14.1
- #478 setup-java 6.1.0
- #474 setup-node 7.1.0
- #473 upload-artifact 7.0.2
- #469 CodeQL Action 4.39.0

The previous independent bot runs were green but used earlier base commits.
The integration PR must be verified independently. Close old bot PRs as superseded
**only after** confirmed integrated source and successful exact-HEAD checks.

Declined as currently unverified/failing; do not claim they were integrated:
- #491 web React 19.3.1 — Repository verification failed
- #490 web Playwright 1.64.1 — Repository verification failed
- #488 web React DOM 19.3.1 — dependency audit, Web build, browser, evidence and verification failed
- #486 site React DOM 19.3.1 — dependency audit, Web build, browser and verification failed
- #485 Android Sentry 8.61.0 — Repository verification failed
- #484 site React 19.3.1 — Repository verification failed
- #483 Vitest tooling 5.0.5 — Repository verification failed
- #481 Electron 44.9.0 — repository, SBOM and packaged-host evidence failed
- #479 SQLAlchemy 2.0.55 — Repository verification failed
- #472 Kotlin Gradle plugin 2.4.21 — Android API 34 and verification failed
- #470 download-artifact 8.0.2 — supply-chain, release evidence and verification failed
- #466 Compose compiler plugin 2.4.21 — Repository verification failed

These are not blanket rejections of upstream versions. Fresh, mutually compatible
dependency updates can be proposed later against then-current main with full CI,
rather than accepting stale/red Dependabot heads.

## GitHub Issue disposition: close tracker; retain underlying gate

| Issue | Disposition | Durable authority / acceptance status |
|---|---|---|
| #455 | Archive requirements-tracker as documented | `docs/PLAYER_INTELLIGENCE_ROADMAP_V1.md` is ACTIVE; GI roadmap, subscriptions and gameplay remain not implemented/accepted unless source and runtime prove them |
| #451 | Archive obsolete omnibus audit-remediation tracker, **incomplete work remains** | `docs/TASKS.md`, audit contract, new scoped engineering PRs; do not treat backlog items as completed |
| #430 | Archive design/research tracker | game automation remains disabled and real source/calibration/action acceptance is pending; see active roadmap and `docs/ANDROID_STOCK_GAME_OBSERVER_V1.md` |
| #381 | Decline optional cross-family benchmarking without proven bottleneck | GPT-led review remains the default; no provider or credential expansion |
| #379 | Archive broad orchestration harness proposal | root `AGENTS.md`, current Control Bridge source, CI and TASKS remain authoritative; missing write adapters do not become accepted |
| #375 | Archive tracker, NOT Owner visual acceptance | `docs/USER_VISIBLE_ACCEPTANCE_CONTRACT.md` and final release gate remain binding |
| #371 | Archive provider-activation tracker, NOT activation | free email staging evidence does not enable Google/Telegram/VK; provider console, credentials, exact callbacks and physical login unverified |
| #317 | Archive publication tracker, NOT release approval | exact candidate signing/publication/production deployment still Owner-gated and blocked by final acceptance |
| #316 | Archive production activation tracker, NOT production activation | live provider/payment/database/ingress setup requires Owner-approved credentials and deployment |
| #315 | Archive voice tracker, NOT microphone/provider acceptance | physical host, selected STT/TTS network/acoustic and Owner keys remain unverified |
| #314 | Archive physical-acceptance tracker, NOT physical acceptance | selected Android/Companion artifacts, signer compatibility, real device/host and visual acceptance pending |
| #277 | Archive exact-WoW-environment tracker, NOT L3 acceptance | WotLK 3.3.5a realm/host and real PASSIVE_CHECKPOINT_ACCEPTED evidence remain pending |

**Never convert a closed Issue into release-accepted evidence.** For final release,
the binding validator reads exact-candidate evidence, not labels or issue counts.
Physical devices, signing custody, selected providers, voice hardware, WoW target
environment, Owner visual acceptance, publication and production activation are
still external/Owner-gated conditions.

## Reopen criteria

Reopen or file a narrowly scoped implementation issue only for a reproducible
defect/owner-approved bounded task that cannot be resolved in the current coherent
engineering pass. No automatic game input, source guessing, secret handling, release
publication or production operation is authorized by this tracker cleanup.
