# SENTINEL API v1

Base path: `/api/v1`

## Error envelope

```json
{
  "error": {
    "code": "AUTHORIZATION_DENIED",
    "message": "Access denied",
    "request_id": "uuid"
  }
}
```

Clients must not infer security state from HTTP text. `403` means the policy decision was DENY; `401` means the authentication context is missing or invalid.

## Device identity

### POST `/devices/register`

Registers a device public key. Requires authenticated account context.

Request:

```json
{
  "device_id": "uuid",
  "public_key_der_b64": "base64",
  "algorithm": "EC-P256-SHA256"
}
```

Response `201`:

```json
{
  "device_id": "uuid",
  "fingerprint_sha256": "hex",
  "key_state": "ACTIVE"
}
```

### POST `/devices/{device_id}/challenge`

Creates a single-use challenge. Response contains opaque random challenge and expiry. Challenge values must not be logged.

### POST `/devices/{device_id}/verify`

Request:

```json
{
  "challenge_id": "uuid",
  "signature_b64": "base64"
}
```

Successful response:

```json
{
  "session_id": "uuid",
  "expires_at": "RFC3339"
}
```

## Authorization

### POST `/authz/check`

```json
{
  "action": "character.read",
  "resource": {"type": "character", "id": "uuid"},
  "scope": "account"
}
```

Response:

```json
{"decision":"ALLOW","reason":"policy_match"}
```

The API never accepts a client-provided `ALLOW` or role claim as authoritative.

## Entitlements

### GET `/me/entitlements`

Returns active grants calculated by the server.

## Game state

### GET `/characters/{character_id}`

Returns the authorized character projection.

### POST `/characters/{character_id}/events`

Accepts normalized adapter events with an idempotency key. The server validates game, adapter, scope, ownership, schema, and sequence before applying state transitions.

## Knowledge

### POST `/knowledge/query`

Request:

```json
{
  "context": {"game":"example","character_id":"uuid"},
  "question": "..."
}
```

Response separates:

- `facts`: sourced claims
- `inferences`: derived claims with confidence
- `recommendations`: optional suggestions, never commands

## Billing

### GET `/billing/subscription`
### POST `/billing/portal`

Provider-specific identifiers remain server-side. Client never submits an amount or entitlement grant.

## Audit

### GET `/audit/events`

Requires audit-read scope. Supports bounded pagination. Security-sensitive audit data is redacted by server policy.
