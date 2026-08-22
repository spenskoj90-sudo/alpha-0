# SENTINEL API Contract v1

Base URL: `/v1`.

All authenticated endpoints require `Authorization: Bearer <session-token>` and a server-derived actor context. JSON requests must carry `X-Request-Id`; mutating client event endpoints additionally require `Idempotency-Key`.

## Session challenge

`POST /sessions/challenge`

Request:
```json
{"device_id":"uuid"}
```

Response:
```json
{"session_id":"uuid","challenge":"base64url","expires_at":"2026-08-11T12:00:00Z"}
```

## Session verification

`POST /sessions/verify`

Request:
```json
{
  "session_id":"uuid",
  "device_id":"uuid",
  "signature":"base64url",
  "request_hash":"base64url"
}
```

Response:
```json
{"access_token":"opaque-or-jwt","token_type":"Bearer","expires_in":900,"session_id":"uuid"}
```

The signature covers a domain-separated canonical message:
`SENTINEL_SESSION_V1 || session_id || device_id || nonce || request_hash`.

## Device registration

`POST /devices`

Request:
```json
{
  "public_key_spki":"base64",
  "fingerprint_sha256":"hex",
  "platform":"android",
  "attestation_chain":["base64", "base64"]
}
```

Response:
```json
{"device_id":"uuid","status":"ACTIVE","key_version":1}
```

## Device lifecycle

- `POST /devices/{device_id}/rotate`
- `POST /devices/{device_id}/revoke`
- `GET /devices`

## Authorization decision

Internal contract:
```json
{
  "actor_id":"uuid",
  "device_id":"uuid|null",
  "action":"character.read",
  "resource":"character:uuid",
  "scope":"user:uuid"
}
```

Decision:
```json
{"allow":true,"reason":"role_scope_policy","policy_version":1}
```

Default deny is mandatory when any decision input is missing or unknown.

## Client event ingestion

`POST /events`

```json
{
  "event_id":"uuid",
  "event_type":"game.character.updated",
  "aggregate_id":"uuid",
  "aggregate_version":12,
  "occurred_at":"2026-08-11T12:00:00Z",
  "payload":{}
}
```

The server validates event type, actor, device, aggregate ownership/scope, monotonic version where required, payload schema, size, timestamp skew and idempotency.

## Knowledge

`GET /knowledge?character_id=<uuid>`

Response entries always carry:
- `kind`: `FACT | INFERENCE | RECOMMENDATION`
- `confidence`: `[0,1]`
- `provenance`: source identifiers
- `created_at`
- `expires_at` where applicable

AI-generated recommendations are informational. They cannot mutate game state or grant entitlements.

## Errors

```json
{"error":{"code":"AUTHZ_DENIED","message":"Access denied","request_id":"uuid"}}
```

Stable error codes include `AUTH_REQUIRED`, `AUTHZ_DENIED`, `DEVICE_REVOKED`, `NONCE_EXPIRED`, `NONCE_REPLAY`, `IDEMPOTENCY_CONFLICT`, `VALIDATION_ERROR`, `NOT_FOUND`, `RATE_LIMITED`.
