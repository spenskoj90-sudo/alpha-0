# PASS 6 — Android ↔ Core Complete Loop

## Scope

This vertical closes the application-side event path from a game adapter fact to the authenticated Core event-batch API:

`GameAdapter.pollFacts()` → `OfflineEventQueue` → `EventSyncCoordinator` → `POST /v1/events:batch`.

## Contract

- Android emits bounded `GameEvent` records with device identity, schema version, occurrence time, and monotonic sequence.
- Core ingestion is authenticated with the Android session token.
- Every batch is bounded to the Core contract maximum of 100 events.
- Requests carry generated request and idempotency identifiers.
- A successful Core response must account for the entire submitted batch as `accepted + duplicates`; only then are queued event IDs acknowledged.
- Network or protocol failure leaves the queue intact for retry.
- Duplicate acceptance is treated as successful delivery without re-executing the event locally.
- The sync layer is transport/integration infrastructure and cannot authorize or execute game actions.

## Evidence boundary

Automated tests verify the Android queue/sync seam and the game-fact-to-sync flow. Existing Core CI verifies `/v1/events:batch` authentication, device binding, sequence, idempotency, and projection behavior. This pass does not claim real-device network execution or production deployment; those remain separate acceptance evidence.
