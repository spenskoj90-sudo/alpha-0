# SENTINEL — Security & Authorization Platform

SENTINEL is a security-first modular monolith for device identity, server-authoritative authorization, game entitlements, auditability and a personal control plane.

## Canonical repository state

Актуальное состояние: см. `docs/SENTINEL_CURRENT_STATE.md`.

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

## Engineering workflow

GPT / ChatGPT is the **primary SENTINEL executor and final integrator**. GPT independently inspects the current GitHub repository state, issues, PRs, commits, diffs and available CI evidence through the authorized GitHub connector, then performs the normal engineering lifecycle within the declared issue scope.

Grok is a **secondary executor for exceptional, genuinely large-scale work only** — for example major multi-stage architectural transformations or exceptionally large multi-file implementation programs. Grok is not the default implementation path.

The Human Owner remains the final authority for merge into `main`, deployment, credentials/secrets and signing material, releases, branch protection, destructive operations and final product acceptance.

Repository inspection by GPT does not provide access to credentials or secrets. Engineering evidence remains tied to the exact commit SHA and workflow Run ID; a textual claim that tests passed is not sufficient. Before merge, the Human Owner independently verifies the PR with `gh pr checks <PR> -R spenskoj90-sudo/alpha-0`.

See `docs/WORKFLOW_CONTRACT.md` and `docs/OPERATING_PLAYBOOK.md` for the authoritative process.

## Runtime findings

The earlier local plaintext-server BrokenPipeError was confirmed as an environmental battery/background-network restriction on the test device, not an Android HTTP/TLS/h2c implementation defect. The client uses `HttpURLConnection`; after battery optimization was disabled, the request completed immediately. PR #34 provided the temporary diagnostic exception reporting used to establish the cause.

The Android device identity remains Keystore-backed: P-256 / `secp256r1` with SHA-256 fingerprinting, with private key material retained in Android Keystore.

## Current-state limitations / open work

- PostgreSQL runtime persistence still requires exact-main runtime evidence before PostgreSQL is declared the authoritative runtime system of record.
- Repository hygiene: historical branch cleanup (Owner-only deletes).
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

See `docs/CONTRIBUTING.md` and `docs/WORKFLOW_CONTRACT.md`. Every security-sensitive behavior change requires a regression test and passing CI. PRs that change code or process must update `README.md` and `docs/SENTINEL_CURRENT_STATE.md` with the current HEAD. The operational workflow is documented in `docs/OPERATING_PLAYBOOK.md`.

## License

MIT. See `LICENSE`.
