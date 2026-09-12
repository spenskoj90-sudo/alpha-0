# PASS 6 — Android ↔ Core Authenticated Event Ingestion

## Scope

This vertical closes the **Android application-side authenticated ingestion seam** from a normalized game fact to the Core event-batch boundary:

`GameAdapter.pollFacts()` → `OfflineEventQueue` → `EventSyncCoordinator` → proven device-bound session → `POST /v1/events:batch`.

It also closes a security prerequisite found during the full repository re-baseline: normal Android login/register sessions are intentionally least-privilege read sessions and therefore cannot write game events. Android now completes the existing hardware-backed P-256 device proof flow and persists the resulting device-bound session before entering device-scoped application operation.

## Authentication and authorization contract

- Login/register sessions remain restricted to `character:read`, `game:read`, and `audit:read`.
- Android binds its Keystore-backed P-256 public identity to the authenticated user.
- Device binding returns a one-time challenge.
- Android signs Core's canonical proof payload `{challenge, request_id, timestamp}` with `SHA256withECDSA` using the non-exportable device key.
- Core validates freshness, consumes the challenge, verifies the signature, rejects replayed proof request IDs, and issues a device-bound session.
- Android fails closed if the proven session does not contain `game:write`; an incomplete proof response is never persisted as the event-ingestion session.
- If a proof attempt must be retried, Android requests a fresh authenticated challenge for the same caller-owned active device instead of creating a duplicate device binding.
- A foreign user cannot request a proof challenge for another user's device.
- Core remains the only authority for session scopes and `event:write` authorization.

## Event delivery contract

- Android emits bounded `GameEvent` records with device identity, schema version, occurrence time, and monotonic sequence relative to the currently retained queue.
- Sequence recovery inspects the entire retained queue, not only the first 100-item transmission batch.
- Core ingestion uses the proven device-bound Android session token.
- Every batch is bounded to the Core contract maximum of 100 events.
- Every HTTP attempt carries a fresh request identifier.
- The idempotency key is deterministically derived from the ordered event IDs in the batch, so a retry of the same retained batch uses the same key while a changed batch produces a different key.
- A successful Core response must account for the entire submitted batch as `accepted + duplicates`; only then are queued event IDs acknowledged.
- Network or protocol failure leaves the queue intact for retry.
- Duplicate acceptance is treated as successful delivery without re-executing the event locally.
- The sync layer cannot authorize or execute game actions.

## Evidence boundary

Automated Android/JVM tests cover the queue/sync seam, game-fact-to-sync flow, queue-wide sequence recovery, stable retry idempotency keys, and canonical device-proof payload construction. Core regression tests cover the key authorization transition: a bound read-only session is denied event ingestion; successful device proof issues a session containing `game:write`; the same event path is then accepted. Tests also cover authenticated challenge refresh and foreign-device denial.

This pass does **not** claim that Android is the production WoW game-data bridge. The repository's target architecture assigns live game/client bridging and durable local queue/cache responsibilities primarily to the local Companion. No concrete live WoW Android adapter lifecycle is asserted here.

`OfflineEventQueue` remains an in-memory application queue, so this pass does not claim Android process-death/device-reboot persistence. It also does not claim real-device network execution, exact WoW environment execution, production deployment, or release acceptance. Those require separate runtime evidence before RC1 acceptance.
