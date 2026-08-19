# SENTINEL — Security & Authorization Platform

SENTINEL is a security-first modular monolith for device identity, server-authoritative authorization, game entitlements, auditability and a personal control plane.

## Canonical repository state

- Canonical branch: `main`.
- Branch/PR work is not accepted as product state until merged into `main` and revalidated at the resulting main SHA.
- Architecture documents describe the target/contract and must not be treated as proof of runtime implementation.
- The authoritative current-state record is `docs/SENTINEL_CURRENT_STATE.md`.
- Evidence/acceptance rules are `docs/SENTINEL_EVIDENCE_PROTOCOL.md`.
- Engineering decisions are recorded in `docs/SENTINEL_DECISION_LOG.md`.

## RC1 scope

- Android client with Android Keystore-backed P-256 identity and AES-GCM session storage.
- FastAPI SENTINEL CORE with PostgreSQL production architecture and schema; runtime PostgreSQL persistence remains subject to exact-main validation.
- Default-deny authorization with roles, scopes and policies.
- User-bound device enrollment and one-time challenge proof.
- Opaque access sessions and one-time refresh rotation/session-security primitives.
- Device-bound, sequence-protected and idempotent game events and supporting structures.
- Diablo catalog, entitlement gate, admin entitlement control and WoW support.
- Next.js web control plane.
- Docker Compose reference deployment.
- GitHub Actions build, security, deployment and release workflows.

## Architecture

`Android/Web -> TLS/WAF -> SENTINEL CORE -> PostgreSQL`

Authorization is server-side:

`Identity + Role + Scope + Entitlement + Policy + Context -> ALLOW/DENY -> Audit`

Architecture decisions D-001 through D-007 are documented in `docs/ARCHITECTURE.md` and the full architecture reference `docs/ARCHITECTURE_V4.md`.

## Current-state limitations

The PostgreSQL schema exists, but the current pre-merge `main` runtime path instantiates an in-memory `MemoryStore`. PostgreSQL must not be described as the authoritative runtime persistence layer until the runtime repository integration is merged and validated on `main`.

The Android entry point on the pre-merge `main` state is the technical `CharacterDashboard` surface. Login/Register and later multi-section product navigation remain branch-only until verified on `main`.

The current Android CI evidence identifies a signing-secret infrastructure dependency. No keystore recreation is authorized without root-cause evidence and Human Owner approval.

## Repository

- `app/` — Android application.
- `server/` — FastAPI Core, security engine, persistence and migrations.
- `web/` — Next.js control plane.
- `launcher/` — isolated desktop launcher surface.
- `wow-addon/` — WoW adapter/addon surfaces.
- `docs/` — architecture, security, deployment, release, current-state and evidence contracts.
- `.github/workflows/` — CI/CD and security automation.

## Requirements

- JDK 17.
- Android SDK 35 for Android builds.
- Python 3.12 for Core.
- Node.js 20 for web.
- Docker / Docker Compose for the reference stack.
- PostgreSQL 17 for production reference deployment.

## Quick start

```bash
cp .env.example .env
# Set POSTGRES_PASSWORD and SENTINEL_ENROLLMENT_TOKEN.
docker compose up --build
```

Services:

- Core: `http://127.0.0.1:8080/healthz`
- OpenAPI: `http://127.0.0.1:8080/docs`
- Web: `http://127.0.0.1:3000`

## Development

### Core

```bash
cd server
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
pytest
```

### Android

```bash
./gradlew assembleDebug
./gradlew test
```

Release signing must be performed in a protected release environment. CI signing requirements are governed by the current workflow configuration and exact-main evidence.

### Web

```bash
cd web
npm install
npm run lint
npm run build
```

## Testing and release gates

The authoritative rule is:

`FAIL → root cause → FIX → regression → MAIN PASS → ACCEPTED`

The RC workflow scope includes Core coverage (minimum 80%), Android build/tests, web lint/build, container build, CodeQL, dependency audit and filesystem secret scanning. Actual acceptance requires those checks to pass on the exact `main` SHA being claimed.

See `docs/RELEASE_GATES.md` for the RC acceptance matrix.

## Security

Security controls include default deny, least privilege, server-side authorization, P-256 device proof, opaque token/session storage, refresh rotation, replay/idempotency controls, input bounds, audit logging and security headers.

Production secrets are never stored in Git. Production requires TLS termination and a PostgreSQL system of record. The process-local rate limiter must be fronted by a distributed WAF/API-gateway limiter before horizontally scaling Core.

See `docs/SECURITY.md` and `docs/SECURITY_WHITEPAPER.md`.

## Deployment

The reference production stack is `docker-compose.yml`. For real production, place Core and Web behind a TLS-terminating reverse proxy/WAF, keep PostgreSQL private, inject secrets from a secret manager, and use the release workflow to publish the Core image to GHCR.

See `docs/DEPLOYMENT.md`.

## API

FastAPI publishes OpenAPI at `/openapi.json` and Swagger UI at `/docs`.

See `docs/API.md` for the endpoint contract.

## Contributing

See `docs/CONTRIBUTING.md`. Every security-sensitive behavior change requires a regression test and passing CI.

## License

MIT. See `LICENSE`.
