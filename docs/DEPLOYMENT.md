# SENTINEL Deployment Guide — Release Candidate

## Runtime

- Android client: min SDK 29, target SDK 36, compile SDK 37.
- Core: Python 3.14.7, FastAPI 0.141.1 / Uvicorn 0.53.0; native runtimes are pinned by `.python-version`.
- Database: PostgreSQL 18 in the reference Compose/integration/recovery stack.
- Web: Node.js 24.21.0 LTS with Next.js 16.3.6 / React 19.3.0; native Node resolution is pinned by `.node-version`.
- Companion packaging: Node.js 24.21.0 LTS with Electron 44.4.5 and an immutable official Win32 x64 runtime digest.

## Reference deployment

`docker compose up --build` starts PostgreSQL, Core and Web. Core runs checksum-verified migrations before Uvicorn starts.

Required environment is documented in `.env.example`.

## Production topology

Put Core and Web behind a TLS-terminating WAF/load balancer. Keep PostgreSQL private. Store secrets in a secret manager or deployment secret store. Do not commit `.env` files, private keys, database passwords or enrollment secrets.

## Managed database hosting

The current **pre-release/staging** database is hosted on Neon PostgreSQL and is consumed through the standard `DATABASE_URL` boundary. The active pre-release baseline is PostgreSQL 18; the previously retained PostgreSQL 17 environment remains rollback/evidence state and must not be deleted automatically.

Neon is infrastructure, not an identity or authorization authority. SENTINEL does **not** delegate authentication, authorization, RLS policy ownership or device/session authority to a managed-database vendor.

All authentication and authorization remain on the existing SENTINEL system:

- opaque session tokens with hashed persistence and one-time refresh rotation;
- Android Keystore / EC P-256 device identity;
- server-authoritative default-deny authorization;
- repository-owned migrations, RLS + FORCE RLS and transaction-local `service_role` activation.

Core connects to managed PostgreSQL solely through `DATABASE_URL`. Provider-specific client SDKs are not part of the Core security boundary.

For production, the current topology candidate is:

`Cloudflare edge/WAF → Render Web/Core → Neon PostgreSQL`

Production account creation, custom domain/DNS, WAF policy, production database credentials, backup/restore acceptance and live traffic remain Owner/external gates. A different managed PostgreSQL vendor may be selected only through an explicit evidence-backed infrastructure decision; active documentation must not claim an unused provider as current state.

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

1. Provision PostgreSQL 18 for a new reference deployment. Existing managed databases require an explicit, evidence-backed major-version migration; repository image changes do not migrate them.
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
