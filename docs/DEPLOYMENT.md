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

## Production database hosting

Supabase (managed PostgreSQL, free tier) is used **exclusively** as Postgres hosting via the standard `DATABASE_URL` connection string.

The following Supabase-managed features are **not used** and must not be enabled or relied upon:

- Supabase Auth
- Supabase RLS policies-as-a-service
- any other managed Supabase product surface (Realtime, Storage, Edge Functions, etc.)

All authentication and authorization remain on the existing SENTINEL system:

- opaque session tokens with hashed persistence and one-time refresh rotation
- Android Keystore / EC P-256 device identity
- server-authoritative default-deny authorization
- `service_role` (and FORCE RLS) defined and enforced by SENTINEL migrations (see `004_p1_rls_force.sql` and related)

Production Core connects to the hosted Postgres instance solely through `DATABASE_URL`. No Supabase client SDKs or platform-specific auth flows are part of the SENTINEL runtime boundary.

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

1. Provision PostgreSQL 17 (or compatible managed instance such as Supabase free-tier Postgres).
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
