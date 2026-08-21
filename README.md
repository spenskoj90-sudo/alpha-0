# SENTINEL — Security & Authorization Platform

SENTINEL is a security-first modular monolith for device identity, server-authoritative authorization, game entitlements, auditability and a personal control plane.

## Canonical repository state

- Canonical branch: `main`.
- Current canonical HEAD: `4a0fd8255e4b7beb065e73a254ebb72d3b8b4d11`.
- Branch/PR work is not accepted as product state until merged into `main` and revalidated at the resulting main SHA.
- Architecture documents describe the target/contract and must not be treated as proof of runtime implementation.
- The authoritative current-state record is `docs/SENTINEL_CURRENT_STATE.md`.
- Evidence/acceptance rules are `docs/SENTINEL_EVIDENCE_PROTOCOL.md`.
- Engineering decisions are recorded in `docs/SENTINEL_DECISION_LOG.md`.

## MVP scope currently implemented on main

- Android client with Android Keystore-backed P-256 identity and AES-GCM session storage.
- Login/Register.
- Device Setup with authenticated device binding.
- Dashboard with authenticated device/security and entitlement data.
- Device Details with fingerprint, algorithm, state, binding/last-seen data, plus existing backend rotate/revoke actions.
- Game Details backed by authenticated entitlement APIs and the existing game catalog.
- Complete Android MVP navigation: `Login/Register → Device Setup → Dashboard → Device Details → Game Details`.
- FastAPI SENTINEL CORE with PostgreSQL production architecture and schema; runtime persistence still requires exact-main runtime validation.
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

The current GitHub API status query for exact main HEAD `4a0fd8255e4b7beb065e73a254ebb72d3b8b4d11` returned no status records. Exact-head workflow PASS/FAIL and run URLs therefore must not be inferred from older PR runs.

The known release APK fingerprint previously verified in CI is:

`2A:CD:1C:FF:F4:F3:4D:B1:25:0D:3F:6C:81:F0:88:74:93:C4:60:2D:3C:FA:65:31:09:93:C0:58:08:9D:B8:8E`

That fingerprint evidence came from an earlier CI run and is not claimed as exact-main-HEAD evidence until `apksigner verify` is run for the current SHA.

The PostgreSQL schema exists, but the current runtime persistence path must still be validated independently before PostgreSQL is described as the authoritative runtime system of record.

The P1 Evidence workflow currently has a push trigger for the historical branch `sentinel-1.0.0-rc1-final` and a pull-request trigger for `main`; this CI configuration remains an open task and has not been changed here.

The current deploy workflow file declares only `release.published` as its trigger. The historical observation of push-associated Deploy runs remains under investigation and is not treated as evidence that the current file triggers on push.

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
