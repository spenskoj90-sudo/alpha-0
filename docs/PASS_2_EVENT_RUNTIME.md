# PASS 2 — Event Processing Runtime

PASS 2 turns the PASS 1 durable event→outbox boundary into a recoverable processing contract.

## Durable contract

`outbox_events` and `worker_jobs` use `PENDING → PROCESSING → DONE/FAILED`. A processing claim carries a lease expiry and an opaque `locked_by` token. Claims use PostgreSQL `FOR UPDATE SKIP LOCKED`, so concurrent workers do not serialize on the same pending row.

An expired processing lease is claimable again. Completion and failure require the exact lease token, preventing a worker from acknowledging another worker's claim.

## Retry and DLQ

Retries are bounded by `max_attempts`. Retry availability uses exponential backoff. Once the attempt budget is exhausted the row becomes `FAILED`, which is the durable dead-letter state. `replay_failed_outbox()` explicitly resets a failed outbox item to `PENDING` with a fresh attempt budget.

Worker jobs persist `last_error` on failure. Error text is bounded before persistence to prevent unbounded diagnostic payloads.

## Runtime boundary

`PostgresEventRuntime` is the durable runtime primitive. It does not invent a deployment process, queue broker, or external provider. A future deployed worker may repeatedly call `run_outbox_once()` and/or claim worker jobs while preserving this database contract.

## Security invariants

- No bypass of PostgreSQL RLS.
- Lease ownership is explicit and opaque.
- Stale leases are recoverable.
- Completion is fail-closed when ownership is wrong or the row is no longer processing.
- Retry is bounded; terminal failure is durable.
- Replay is explicit rather than implicit.

## Evidence target

The CI PostgreSQL integration suite validates lease ownership, retry-to-DLQ, replay, worker-job failure persistence, and wrong-owner completion rejection.
