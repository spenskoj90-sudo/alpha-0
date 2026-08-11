# SENTINEL Deployment Guide

## Runtime

- Android client: API 29+, target SDK 35.
- Core: Python 3.12+, FastAPI/Uvicorn.
- Database: PostgreSQL.
- Web: Next.js App Router.

## Production topology

Run the FastAPI core behind a TLS-terminating WAF/load balancer. Run workers separately from API replicas. PostgreSQL is the system of record. Store secrets outside Git. Use separate credentials for migrations, runtime API and workers.

## Environment

```text
DATABASE_URL=postgresql+psycopg://...
SENTINEL_ENV=production
SESSION_TTL_SECONDS=43200
MAX_REQUEST_SKEW_SECONDS=120
```

No environment value containing a secret should be committed.

## Database rollout

1. Provision PostgreSQL.
2. Apply migrations in order.
3. Verify indexes and RLS.
4. Run integration tests against a disposable database.
5. Deploy API.
6. Deploy workers.
7. Run smoke tests.
8. Only then enable production traffic.

## Rollback

Application deployments must be backward-compatible with the previous schema. Never drop security/audit columns as part of an emergency rollback. Disable the new release, restore the previous application image, and investigate the failed gate.

## Observability

Minimum signals: request rate, latency, 4xx/5xx rate, authorization denials, device-proof failures, replay rejections, queue depth, worker retries, dead-letter count and database saturation. Sentry/PostHog are optional sinks; they are not sources of security truth.
