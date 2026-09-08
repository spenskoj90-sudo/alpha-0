# SENTINEL — Companion Local Kill Switch v1

**Status:** ACTIVE FOUNDATION  
**Version:** 1.0

## Purpose

The Companion kill switch is a local, process-resident fail-closed shutdown latch. It does not depend on cloud availability and does not make authorization or game-action decisions.

## Semantics

- `activate_kill_switch()` immediately transitions the Companion runtime to terminal `STOPPED`.
- Activation clears the bounded outbound queue through the session boundary.
- Queue admission and successful-send acknowledgement are blocked while the switch is active.
- Reconnect attempts are rejected while the switch is active; no reconnect backoff is scheduled.
- Watchdog/degradation paths preserve `STOPPED` while the switch is active.
- `reset_kill_switch()` is an explicit local operation. Reset leaves the runtime `STOPPED`; a fresh `connect()` is required before the runtime becomes `ACTIVE`.
- Queue reset is explicit and clears stale messages before reuse.

## Security boundary

The switch is deliberately independent of network/cloud state. It does not authorize commands, grant capabilities, execute game actions, manipulate a game process, or bypass the Policy Engine / Action Gateway. A kill-switch activation is a shutdown signal, not an authorization mechanism.

## Verification

Automated transport-session tests cover activation, terminal shutdown, queue clearing, blocked reconnect, blocked send acknowledgement, explicit reset, and the required fresh-connect transition back to `ACTIVE`.

Real device, launcher, WoW-addon and production operator-control evidence are not implied by this module and remain separate acceptance concerns.
