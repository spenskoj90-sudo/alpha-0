# SENTINEL Release Gates

A release candidate is accepted only when evidence exists for the exact commit being released.

1. Core syntax/compile check passes.
2. Unit and API security tests pass.
3. Database migrations apply cleanly from an empty PostgreSQL database and from the immediately previous schema.
4. Docker image builds without secrets embedded in image layers.
5. Device registration is bound to a user-specific enrollment secret.
6. Device proof requires a fresh timestamp, unique request ID, and P-256 signature.
7. Access tokens are opaque and stored only as hashes server-side.
8. Refresh tokens rotate on every successful refresh and replay of an old token is rejected.
9. Authorization is default-deny and explicit deny policies win.
10. Game event batches are validated before mutation, sequence-checked, idempotent, and device-bound.
11. Security/audit logs do not contain credentials, tokens, signatures, or stack traces.
12. Production configuration fails closed when `DATABASE_URL` or enrollment configuration is absent.
13. No `TODO`, `FIXME`, or `IMPLEMENT LATER` markers remain in release code.

An unchecked or unverified gate is **NOT ACCEPTED** and must never be represented as a passing result.
