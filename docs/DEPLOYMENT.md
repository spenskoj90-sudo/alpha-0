# SENTINEL Deployment Guide — 1.0.0-RC1

## Runtime

- Android client: API 29+, target SDK 35.
- Core: Python 3.12+, FastAPI/Uvicorn.
- Database: PostgreSQL 17 in the reference Compose stack.
- Web: Next.js App Router.

## Reference deployment

`docker compose up --build` starts PostgreSQL, Core and Web. Core runs checksum-verified migrations before Uvicorn starts.

Required environment is documented in `.env.example`.

## Production topology

Put Core and Web behind a TLS-terminating WAF/load balancer. Keep PostgreSQL private. Store secrets in a secret manager or deployment secret store. Do not commit `.env` files, private keys, database passwords or enrollment secrets.

## Required production configuration

```text
SENTINEL_ENV=production
DATABASE_URL=postgresql+psycopg://...
SENTINEL_ENROLLMENT_TOKEN=<user-id>:<high-entropy-secret>
SENTINEL_REQUIRE_ENROLLMENT=true
SESSION_TTL_SECONDS=3600
REFRESH_TTL_SECONDS=2592000
MAX_REQUEST_SKEW_SECONDS=120
RATE_LIMIT_PER_MINUTE=120
CORS_ORIGINS=https://your-web-origin.example
```

Production startup intentionally fails closed if `DATABASE_URL` or enrollment configuration is missing.

## Database rollout

1. Provision PostgreSQL 17.
2. Run `python server/migrate.py` or start the Core container.
3. Verify `/healthz`.
4. Run API/security smoke tests against a disposable database.
5. Put the service behind TLS/WAF.
6. Enable traffic only after all release gates pass.

The migration runner records SHA-256 checksums and refuses to run if an applied migration was modified.

## Rollback

Keep application/schema changes backward-compatible. Never remove security or audit columns during rollback. Restore the previous application image and investigate the failed gate before re-enabling traffic.

## Observability

Monitor request rate, latency, 4xx/5xx rate, authorization denials, device-proof failures, replay/idempotency conflicts, migration failures and database saturation.

## Scaling boundary

The in-process rate limiter is suitable for the single-process reference deployment. Before horizontal Core scaling, enforce distributed rate limiting at the WAF/API gateway or migrate the limiter to shared infrastructure.
