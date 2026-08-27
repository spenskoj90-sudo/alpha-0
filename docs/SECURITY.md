# SENTINEL Security — RC1

## Controls

- Server-side authentication and authorization.
- Default-deny policy evaluation.
- Least-privilege scopes.
- User-bound device enrollment.
- P-256 challenge-response device proof.
- Fresh timestamp and one-time request/challenge replay protection.
- Opaque access tokens with hashed persistence.
- One-time refresh-token rotation and replay rejection.
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

Admin endpoints require `SENTINEL_ADMIN_TOKEN`, are rate-limited, record failed attempts, and lock out the source after 5 failures in 15 minutes. Error bodies do not echo the presented token.
