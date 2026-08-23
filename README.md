# SENTINEL — Security & Authorization Platform

SENTINEL is a security-first modular monolith for device identity, server-authoritative authorization, game entitlements, auditability and a personal control plane.

## Canonical repository state

- Canonical branch: `main`.
- Current canonical HEAD: `ebd344f5f42adab3f4b0dea7ee26f3af90b81c79`.
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
- Device Details with fingerprint, algorithm, state, binding/last-seen data, plus backend rotate/revoke actions.
- Game Details backed by authenticated entitlement APIs and the existing game catalog.
- Complete Android MVP navigation: `Login/Register → Device Setup → Dashboard → Device Details → Game Details`.
- Final Sentinel visual system across all five Android MVP screens: centralized final palette, Outfit/Inter/JetBrains Mono typography, 4dp cards with 2dp ultraviolet left accent, status badges, rounded primary/destructive controls and one-shot 1000ms device scan-line.
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

## Current validation status

PR #46, which introduced the final Sentinel design system, was merged into `main` as `ebd344f5f42adab3f4b0dea7ee26f3af90b81c79` after exact-head CI verification.

Evidence on PR #46 head `43f94338df4da82917e615b2e1c9eb79014e9246`:

- Security #170 / run `32626297508` — PASS.
- P1 Evidence #80 / run `32626297477` — PASS.
- ALPHA-0 Android CI #1022 / run `32626297516` — PASS.
- Build & Test #250 / run `32626297494` — all product/code/build jobs PASS; Firebase Test Lab failed at Google Cloud authentication, so instrumentation did not execute. This remains the known FTL/GCP infrastructure exception.

The P1 Evidence workflow currently uses `push.branches: [main]` and `pull_request.branches: [main]`.

The deploy workflow currently declares only `release.published`. Historical observations of push-associated Deploy runs remain under investigation; the current workflow file itself does not contain a push trigger.

## Runtime findings

The earlier local plaintext-server BrokenPipeError was confirmed as an environmental battery/background-network restriction on the test device, not an Android HTTP/TLS/h2c implementation defect. The client uses `HttpURLConnection`; after battery optimization was disabled, the request completed immediately. PR #34 provided the temporary diagnostic exception reporting used to establish the cause.

The Android device identity remains Keystore-backed: P-256 / `secp256r1` with SHA-256 fingerprinting, with private key material retained in Android Keystore.

## Current-state limitations / open work

- PostgreSQL runtime persistence still requires exact-main runtime evidence before PostgreSQL is declared the authoritative runtime system of record.
- `POST /v1/recommendations` remains an authorization-review item until its `policy_engine.authorize` enforcement and regression coverage are confirmed.
- Repository hygiene still includes historical PR/branch classification, ghost workflow records and duplicate state-document cleanup.
- A soft battery-optimization onboarding prompt remains planned to reduce first-run network failures on aggressive Android/MIUI-like firmware.

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