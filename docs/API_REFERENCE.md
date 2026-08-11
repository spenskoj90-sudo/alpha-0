# SENTINEL API Reference v1

Base URL: `/v1`

## Error envelope

```json
{"code":"INVALID_SESSION","message":"Session is invalid","request_id":"uuid"}
```

## POST /devices/register

Registers an Android device public key. The server verifies that `SHA-256(DER(public_key)) == fingerprint_sha256`.

Request:

```json
{"user_id":"uuid","platform":"android","public_key_der_b64":"...","fingerprint_sha256":"..."}
```

Response:

```json
{"device_id":"uuid","state":"ACTIVE","challenge":"base64url-nonce"}
```

## POST /devices/{device_id}/prove

Signs canonical `{challenge,timestamp,request_id}` with the device's P-256 private key. The challenge is single-use and expires after 120 seconds.

Response:

```json
{"session_token":"opaque-token","expires_at":"2026-08-11T20:00:00Z","scopes":["character:read","game:write","audit:read"]}
```

## POST /authorize

Server-side policy decision.

```json
{"action":"character:read","resource":"character:123"}
```

Response:

```json
{"decision":"ALLOW","reason_code":"POLICY_ALLOW"}
```

No matching policy is always `DENY`.

## POST /events:batch

Accepts up to 100 game events. The server checks session scope, device binding, event idempotency and monotonic device sequence.

## GET /audit

Returns security/business audit events for the authenticated user when the `audit:read` scope is present.

## POST /recommendations

Returns fact/inference/recommendation objects with confidence and provenance. This endpoint is intentionally non-authoritative.

## Authorization header

`Authorization: Bearer <opaque-session-token>`

Mutating production requests should additionally carry a client-generated `X-Request-Id` and idempotency key where specified by the final deployment contract.
