# Release-readiness continuation — 2026-10-07

Owner authorized autonomous engineering completion. Reconciliation starts from
protected main `38ca21bf8c55fb40d9ac788b7d3369825c2560b5`, the current #451 queue,
the 06 October audit and knowledge-distribution handoff, and the active #452 PR.
Read live refs/checks for each integration; this checkpoint is not a frozen candidate.

## Execution queue

1. Finish #452 durable Web session generations, including legacy logout revocation,
   overlapping registration and committed password-reset outcomes; require exact-HEAD
   PostgreSQL/RLS/concurrency checks and post-merge runtime.
2. F09: preserve six entitlement-domain IDs while exposing their catalog-foundation,
   unverified-environment and no-execution status. Present the separate 26-profile
   research inventory through an authenticated read-only BFF route. Research profiles
   grant no entitlement; WoW foundation and Shattered observer remain environment/
   calibration pending. No strategy or input/ARM capability is activated.
3. F12: integrate existing dependency PRs only with current locks/version contracts,
   unchanged security thresholds and exact-HEAD checks; preserve Electron runtime hashes.
4. F06: preserve Companion consumer WIP and complete trusted exact-profile lifecycle;
   then Android local consumer. Epoch cancellation, digest/revision/rollback protection,
   monotonic lease expiry and Stop/logout/revocation remain required. Unit fixtures cannot
   promote a real target out of WAITING_FOR_VERIFIED_PROFILE.
5. F10: Web email verification, MFA enrollment/disable/recovery rotation, explicit
   provider linking and device suspend/revoke with current auth/CSRF boundaries and
   complete recoverable states/browser evidence.
6. Continue only concrete provider/configuration, design-state, packaging and release
   evidence defects. #379 write adapters and #381 benchmarks require measurable benefit;
   no artificial work or extra paid services to consume quota.

## F09 implementation

`/v1/games` and game detail retain existing identifiers and add conservative evidence
metadata. Launcher flags describe configuration, not target-game support. The Web Games
surface displays catalog foundations separately from research/adapter/observer profiles.
Unknown, duplicate, malformed or authority-promoting inventory fails closed. UI allowlists
exclude knowledge rules and action claims; Russian and English states remain available.

Verification is recorded after execution. A build or browser fixture does not establish
physical game calibration, Owner acceptance or release acceptance.

Local evidence: Web 124 tests PASS, coverage 98.62% lines / 92.30% branches,
lint/build PASS; catalog Core regressions RED→GREEN; repository verifier 83 PASS.
Three existing TCP/TLS tests assumed the host OpenSSL minimum default was TLS 1.2.
This host reports MINIMUM_SUPPORTED, so tests rejected the context before reaching
their intended certificate/hostname checks. Set each fixture's intended TLS minimum
explicitly; production TLS enforcement remains unchanged. Complete Core and exact-HEAD
CI results must be read after this correction.

## Remaining external evidence

Batch the unavoidable checks against one final exact candidate: compatible Android
signer custody/update and Infinix physical/visual acceptance (#314/#375/#317), Companion
target-host and microphone/provider acceptance (#314/#315), verified game environment
and source calibration (#277/#430), provider-console login/identity/credentials (#371),
and final production activation/signing/publication (#316/#317). Keep unavailable
features visibly unavailable until evidence exists. No uninstall workaround, fabricated
acceptance, production secret exposure, protection bypass or automatic game authority.
