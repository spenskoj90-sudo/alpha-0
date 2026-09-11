# SENTINEL PASS 1 — UGS Completion

## Baseline

PASS 1 starts from main commit `4be710fd68c4b5c489b91dd387b9ebb3537a755a`.
Existing UGS validation already provides schema validation, timezone-aware timestamps, per-session sequence acceptance, freshness checks, capability usability, deterministic replay, and character projection helpers.

## This pass closes

1. **Transactional event → outbox boundary** — every newly accepted `game_events` row creates a `PENDING` `outbox_events` row in the same PostgreSQL transaction through an `AFTER INSERT` trigger.
2. **Authoritative character ordering** — the database rejects silent regression of a character snapshot by retaining the existing row when an update carries a lower `version`.
3. **Projection registry** — `UGSProjectionRegistry` provides a deterministic, storage-agnostic projection boundary with stable projection ordering and strict per-session replay ordering.
4. **Regression coverage** — unit tests cover projection ordering, duplicate sequence rejection, replay ordering, and deterministic replay; PostgreSQL coverage verifies the durable outbox and monotonic character projection guard when PostgreSQL CI is available.

## Deliberate boundary

PASS 1 does **not** implement the production worker/lease/retry/DLQ runtime. Existing `OutboxManager`/`WorkerManager` state-machine primitives and the durable `outbox_events` table remain the baseline for PASS 2, where processing and recovery are completed.

## Security invariant

No action authorization is introduced by UGS projection. UGS remains a validated facts/state boundary; projections are ordered and fail closed on replay/order violations.
