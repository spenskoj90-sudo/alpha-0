# SENTINEL Security — Release Candidate

## Controls

- Server-side authentication and authorization.
- Default-deny policy evaluation.
- Least-privilege scopes.
- User-bound device enrollment.
- P-256 challenge-response device proof.
- Fresh timestamp and one-time request/challenge replay protection.
- Opaque access tokens with hashed persistence.
- One-time refresh-token rotation and replay rejection.
- Email verification and password recovery use high-entropy single-use credentials; only SHA-256 token digests are persisted.
- Verification/reset requests are deliberately non-enumerating for unknown email addresses.
- Password reset revokes all existing sessions for the affected identity before a new login can be trusted.
- Account TOTP MFA is server-authoritative across password and federated first factors: a successful first factor yields only a five-minute hashed one-time challenge, never a session, until MFA succeeds.
- Account TOTP seeds are encrypted at rest with the deployment-managed `SENTINEL_ACCOUNT_MFA_KEY`; the raw key is never committed. Missing/invalid encryption configuration fails enrollment and MFA verification closed.
- TOTP counters are replay-protected. Recovery codes are high-entropy, stored only as SHA-256 digests, consumed once, and are shown only when initially generated or explicitly rotated.
- Enabling or disabling account MFA revokes existing sessions so a previously issued refresh token cannot bypass the changed security policy.
- The Web control plane keeps raw MFA challenges in a short-lived HttpOnly, SameSite=Strict cookie; browser JavaScript receives only the fact that MFA is required and submits only the user-entered second factor.
- Federated identities are keyed by provider subject, never by email equality. Existing-email collisions require explicit authenticated linking, and adding a persistent provider identity requires a device-bound SENTINEL session obtained after device proof; a pre-device account session is insufficient.
- Google ID tokens are checked server-side for signature, issuer, audience, time bounds and one-time nonce.
- Telegram OIDC and VK ID browser flows use PKCE plus one-time hashed state. Redirect URIs are exact server allowlists; arbitrary client redirects are rejected.
- Android persists browser PKCE state only as AES-GCM ciphertext protected by Android Keystore and consumes it on callback.
- Provider client secrets and provider access tokens are never embedded in the Android APK.
- Device-bound event ingestion with sequence constraints.
- Idempotency-key conflict detection.
- Input validation and bounded payloads.
- Rate limiting and security-failure audit records.
- Append-oriented audit events.
- Secure response headers: CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy and production HSTS.
- Production startup fails closed without PostgreSQL or enrollment configuration.

## Threat boundaries

TLS termination must occur at a trusted reverse proxy/WAF in production. PostgreSQL is never exposed publicly. Secrets belong in deployment secret stores or GitHub Actions Secrets, never Git.

## Secrets

`.env.example` contains placeholders only. Secret scanning is part of CI. The repository must also be reviewed with GitHub Secret Scanning and push protection before a public production deployment.

## Known operational boundary

The reference rate limiter is process-local. A multi-replica production deployment must place distributed rate limiting at the WAF/API gateway or replace the in-process limiter with a shared store before scaling horizontally.

## Security testing

CI runs Python security tests, API regression tests, CodeQL, Trivy and dependency audits. Runtime penetration testing (OWASP ZAP/Burp) remains an environment-level release gate rather than a claim of completion from source inspection alone.


## Integrity access policy

Device integrity tiers are evaluated server-side. Client-supplied Play Integrity verdicts are never trusted.

| Tier | Access |
| --- | --- |
| `MEETS_STRONG_INTEGRITY` | Full access to security-critical operations |
| `MEETS_DEVICE_INTEGRITY` | Normal authenticated access; rotate/revoke, event write, admin grant and recommendations are denied |
| `MEETS_BASIC_INTEGRITY` | Read-only basic access (`character:read`, `game:read`, `audit:read`) |
| `FAILED` / `UNKNOWN` | Protected operations denied |

Server-issued attestation nonces are one-time and TTL-bound. Google Play Integrity token verification is fail-closed until `SENTINEL_PLAY_INTEGRITY_AUDIENCE` and a verified token path are configured. Absent that configuration the attested tier remains `UNKNOWN` and does not upgrade authorization.

## Admin control plane

Admin endpoints require both the high-entropy `SENTINEL_ADMIN_TOKEN` and a current RFC 6238-compatible six-digit TOTP derived from the server-side `SENTINEL_ADMIN_TOTP_SECRET`. The TOTP secret must contain at least 128 bits of Base32 key material and is compatible with Google Authenticator and equivalent authenticator apps. The server accepts only the current 30-second counter plus the adjacent counter on either side for clock skew. Missing server-side MFA configuration fails the admin plane closed with 503; invalid factors share the generic `ADMIN_ACCESS_DENIED` response, are rate-limited, record failed attempts, and participate in the existing source lockout. The Web admin surface forwards only the currently entered code and does not persist either factor. Owner/admin authority is server-authoritative and is never inferred from an Android APK variant.
