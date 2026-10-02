# Game action offline contract v1

Status: implemented closed offline fixture; no real game executor or activation.
Owner direction: 2026-10-02, #430. Contract: `sentinel.game-action.v1`.

## Design and execution scope

The available step is a versioned request, policy check, scheduling, dispatch and
new-observation outcome loop. `server/app/core/offline_game_actions.py` provides
this loop for `sentinel-turn-fixture`, package `sentinel.offline.fixture`, version
`1`, environment `local-offline-replay`, profile `turn-v1`. The only semantic action
is `advance_turn`, with an empty, extra-field-rejecting argument schema. The world
is an independent in-memory counter; no platform input, shell, URL, filesystem,
network, game APK/EXE, save or game memory is touched. There is no HTTP endpoint.

This is L2 replay plumbing. It does not authenticate a person, prove consent on a
phone, calibrate OCR, attest a captured app or grant a real game capability. The
synthetic replay principal and entitlement are explicitly confined to the fixture.
Production principal/session authority remains in the existing authenticated APIs.

## Boundary and budgets

- Strict, frozen request; unsupported version/action, unknown fields, executable
  arguments and bool-to-int coercion are rejected.
- Exact target, session, principal including device, sequence and state digest
  must match trusted local context at enqueue and again immediately before dispatch.
- The caller is a single-threaded local loop using monotonic elapsed milliseconds.
  A backwards clock fails closed. Network clock/lease verification is not implemented.
- A separate explicit consent lease permits `USER_CONFIRMED` (one step) or
  `BOUNDED_RULE` (at most three steps). TTL is at most 30 seconds. There is one
  pending slot, a one-second delivery interval, at most three retained outcomes,
  a three-second request expiry and a 1.5-second scheduling freshness window.
- The only armed rule is the compiled condition `turn < 3`. No model-generated
  rule/expression/program is accepted. Each next step needs a new observed state.
- Existing ActionGateway policy and trusted entitlement resolver are checked again
  before delivery. The synthetic feature is `offline-game-test`. Capability is
  `LIMITED/L2/offline_fixture`, never Android `AVAILABLE/L3`.
- Reserve step/rate before delivery. `SUCCEEDED` requires a new observation with
  the same trusted context, exactly the next sequence and exactly one turn advanced.
  Missing, wrong or exceptional observation yields `UNKNOWN` and latches Stop.
- Outcome vocabulary is `SUCCEEDED | FAILED | CANCELLED | UNKNOWN`. Pre-dispatch
  invalidation returns `CANCELLED`; malformed enqueue raises a bounded reason.
  The fixture makes no exactly-once claim for an external side effect.
- Identical idempotency keys return their prior outcome; conflicting bytes are
  rejected. UNKNOWN never triggers delivery again. A different principal cannot
  read a prior result. Rearming never erases history; use a new session after Stop.
- Stop clears scheduling. It cannot undo a previously delivered side effect.
  The ordinary fixture remains usable with SENTINEL stopped or entitlement absent.

## Migration and activation prerequisites

The old `ActionRequest` schema and global `AUTOMATIC_EXECUTION_DISABLED` remain
unchanged. Old requests are not automatically migrated. The fixture evaluates
`USER_CONFIRMED` intent inside its separate bounded local lease; it does not enable
the old AUTOMATIC mode or install a platform executor.

Before a real profile can consume v1 requests, implement a separately reviewed
platform boundary and establish all prerequisites: exact installed game/version,
publisher/environment permission, physical HUD calibration with ground truth/error,
trusted capture/context, authenticated principal, trusted entitlement, consent/arming
custody, freshness and policy evidence. First test one user-confirmed semantic action
and a new observed outcome. Only then test a deterministic armed rule and budgets.
An Android Accessibility delivery callback is not an observed game success.

Real invalidation must be wired to override, lock, capture revoke, cross-app/window,
scene/version change, unexpected dialog, death/loading, stale/low confidence,
entitlement/lease expiry/revocation and Stop. Calling `stop()` in a replay test proves
queue semantics, not Android detection/wiring of those physical events. No secure
surface bypass, online automation permission or store approval is implied.

## Verification and next evidence

`server/tests/test_offline_game_actions.py` covers schema, context, dispatch-time
revalidation, policy/entitlement, deadlines, queue/rate/step budgets, idempotency,
uncertain outcomes and independent world operation. Existing gateway tests retain
the AUTOMATIC denial. `python scripts/game_action_replay.py` runs the three-step
closed fixture and prints bounded numeric/status evidence; use the pinned Core
Python environment. No new database migration is needed: state and outcomes exist
only for the lifetime of this local fixture, never as durable offline grants.

Physical Shattered Pixel Dungeon observation/calibration remains PENDING under
`ANDROID_STOCK_GAME_OBSERVER_V1.md`. No recommendation based on its uncalibrated
health is promoted here. Windows/WoW L3 and Android input/outcome acceptance remain
separate external campaigns; replay cannot close them.
