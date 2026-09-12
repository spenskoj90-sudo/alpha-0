# PASS 6 — Android ↔ Core Complete Loop

## Scope

This vertical closes the application-side event path from a game adapter fact to the authenticated Core event-batch API:

`GameAdapter.pollFacts()` → `OfflineEventQueue` → `EventSyncCoordinator` → `POST /v1/events:batch`.

## Contract

- Android emits bounded `GameEvent` records with device identity, schema version, occurrence time, and monotonic sequence relative to the currently retained queue.
- Sequence recovery inspects the entire retained queue, not only the first 100-item transmission batch.
- Core ingestion is authenticated with the Android session token.
- Every batch is bounded to the Core contract maximum of 100 events.
- Every HTTP attempt carries a fresh request identifier.
- The idempotency key is deterministically derived from the ordered event IDs in the batch, so a retry of the same retained batch uses the same key while a changed batch produces a different key.
- A successful Core response must account for the entire submitted batch as `accepted + duplicates`; only then are queued event IDs acknowledged.
- Network or protocol failure leaves the queue intact for retry.
- Duplicate acceptance is treated as successful delivery without re-executing the event locally.
- The sync layer is transport/integration infrastructure and cannot authorize or execute game actions.

## Evidence boundary

Automated tests verify the Android queue/sync seam, game-fact-to-sync flow, queue-wide sequence recovery, and stable retry idempotency keys. Existing Core CI verifies `/v1/events:batch` authentication, device binding, sequence, idempotency, and projection behavior.

`OfflineEventQueue` is currently an in-memory retained queue. This pass therefore does not claim persistence across Android process death/device reboot. It also does not claim real-device network execution or production deployment. Durable process-restart storage and real-environment acceptance require separate implementation/evidence before RC1 production acceptance.
