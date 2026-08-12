# SENTINEL Deployment Guide — 1.0.0-RC1

## Runtime

- Android client: API 29+, target SDK 35.
- Core: Python 3.12+, FastAPI/Uvicorn.
- Database: PostgreSQL 17 in the reference compose deployment.
- Web: Next.js App Router.

## Production topology

Run SENTINEL CORE behind a TLS-terminating WAF/load balancer. PostgreSQL is the production system of record. Use separate credentials for migration and runtime access in real deployments. Do not expose PostgreSQL publicly.

The reference deployment is in `docker-compose.yml` and the Core image is `server/Dockerfile`.

## Required environment

```text
SENTINEL_ENV=production
DATABASE_URL=postgresql+psycopg://...
SENTINEL_ENROLLMENT_TOKEN=<user-id>:<high-entropy-secret>
SENTINEL_REQUIRE_ENROLLMENT=true
SESSION_TTL_SECONDS=3600
REFRESH_TTL_SECONDS=2592000
MAX_REQUEST_SKEW_SECONDS=120
RATE_LIMIT_PER_MINUTE=120
```

No secret may be committed to Git. Production startup intentionally fails closed if `DATABASE_URL` or the enrollment configuration is missing.

## Database rollout

`server/migrate.py` is the authoritative migration runner for the reference deployment. It records migration checksums in `schema_migrations` and refuses to continue when an already-applied migration has been modified.

1. Provision PostgreSQL.
2. Set production secrets outside Git.
3. Start the Core container; it runs `migrate.py` before Uvicorn.
4. Verify `/healthz`.
5. Run the release smoke/security tests against the deployed endpoint.
6. Only then enable production traffic.

## Rollback

Application deployments must remain backward-compatible with the previous schema. Never remove security or audit columns during an emergency rollback. Restore the previous application image and investigate the failed release gate.

## Observability

Minimum signals: request rate, latency, 4xx/5xx rate, authorization denials, device-proof failures, replay rejections, idempotency conflicts, database saturation and migration failures. Sentry/PostHog are optional sinks; they are not sources of security truth.

## Release acceptance

Use `docs/RELEASE_GATES.md`. An unverified gate is not a pass.
