# Deterministic UGS Simulation Harness v1

## Purpose

`server/app/core/ugs_simulation.py` provides a deterministic, side-effect-free harness for exercising Core Unified Game State validation semantics without a live game, network transport, AI provider, or action executor.

The harness is intentionally narrower than a game emulator. It supplies controlled timestamps to the existing `UGSIngestor` and records observable validation outcomes for regression and future intelligence work.

## Contract

Each `UGSSimulationStep` contains:

- a validated `UGSState` input;
- an explicit timezone-aware `now` timestamp.

`DeterministicUGSSimulation.run()` records, per step:

- session and sequence identity;
- whether the state was accepted by the ordering/idempotency gate;
- freshness at the supplied clock value;
- whether the last known state is marked stale;
- capabilities that remain usable while the state is fresh.

The result exposes canonical JSON bytes and a SHA-256 digest. Equivalent inputs produce equivalent observations and digests independent of wall-clock time or host environment.

## Safety boundary

The harness does not:

- execute game actions;
- authorize commands;
- perform network I/O;
- call AI providers;
- start or manipulate game processes;
- mutate persistent state.

Stale observations never expose a capability as usable. Capability availability remains governed by the existing UGS capability semantics.

## Scope

This is a foundation for deterministic scenario/regression testing. It does not claim exact World of Warcraft 3.3.5a/private-server validation, real Companion transport behavior, device latency, or production observability. Those remain separate evidence gates on the task board.
