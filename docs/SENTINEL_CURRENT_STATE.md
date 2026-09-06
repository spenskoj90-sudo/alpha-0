# SENTINEL — Canonical Current State

**State record:** 2026-09-06  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Observed `main` HEAD (snapshot):** `713f602d0d3b86a836e6c7dcd093f5d7d59adefe`

> Git/main is authoritative for product state. Unmerged branch evidence is not current product state.
> Exact CI/release claims require exact SHA + workflow Run ID where available. Unknown facts remain **UNVERIFIED**.

## 1. Current product state

- Android client exists under `app/`.
- FastAPI Core exists under `server/`.
- Next.js control plane exists under `web/`.
- Electron launcher exists under `launcher/`.
- WoW addon sources exist under `wow-addon/`.
- Android device identity is Keystore-backed P-256 with SHA-256 fingerprinting.
- Sessions use opaque tokens with one-time refresh rotation.
- Authorization is server-authoritative and default-deny.
- PostgreSQL is the production persistence architecture when `DATABASE_URL` is configured; migration `004_p1_rls_force.sql` applies FORCE RLS.
- Character/game-state work (#107) is complete on main.
- Sentry Android runtime path is VERIFIED on a physical device on 2026-09-06; temporary smoke UI was removed after confirmation.
- Deploy workflow is release/manual triggered and optional remote rollout is separately gated.
- CURRENT_STATE auto-sync is implemented through the dedicated CI path.
- Game Adapter Contract v1 and Unified Game State v1 are part of the architecture foundation on main.
- PostHog/runtime telemetry contract v1 is defined; runtime instrumentation, dashboards and alerts remain separate implementation work.
- A reproducible CI performance baseline is recorded; device startup/memory/network and API/event-batch latency remain UNVERIFIED.

## 2. Active governance

The canonical governance document is `docs/GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md`.

| Responsibility | GPT / ChatGPT | Human Owner | Other AI |
|---|---|---|---|
| Engineering analysis | **Sole AI role** | Final authority | **No role** |
| Architecture | **Sole AI role** | Product authority | **No role** |
| Implementation | **Sole AI role** | Scope/acceptance authority | **No role** |
| Testing/security/CI analysis | **Sole AI role** | Protected-action authority | **No role** |
| PR preparation/review | **Sole AI role** | Final product authority | **No role** |
| Merge to `main` | **May merge after exact-SHA required checks pass** | Ultimate authority / protected gates | **No role** |
| Production/live actions | Prepare/verify | **Owner gate** | **No role** |

No other AI system participates in engineering, coding, testing, review, security, research, CI diagnosis, architecture, DevOps, release engineering or integration.

Routine CI failures are not a conversational stop condition. GPT diagnoses, fixes, retests and reruns CI until required validation passes or a genuine Owner gate/blocker is reached.

## 3. Exact-SHA merge rule

GPT may merge a PR into `main` only when all required checks have successfully completed on the exact PR HEAD SHA being merged. Missing, pending, failed or stale required checks are a hard no-merge condition. Branch protection and security gates must never be bypassed or weakened.

## 4. Owner gates

Production secrets/credentials, signing material, branch-protection changes, irreversible destructive operations, production/live deployment, release publication and unresolved fundamental product-direction decisions remain Owner-gated.

## 5. Security invariants

Do not silently weaken the documented server-authoritative/default-deny model, device identity protections, opaque session/refresh protections, database/RLS boundaries, migration integrity or release signing controls.

## 6. Verification state

- `server/`: security, RLS, refresh-concurrency, character/game-state and projection coverage exists; Game Adapter registry is implemented with bounded normalized events and explicit capability evidence discipline.
- `app/`: Sentry runtime path verified; refresh/session test lineage exists.
- `web/`: admin entitlements route test exists.
- `launcher/` / `wow-addon/`: dedicated test/coverage evidence **UNVERIFIED**.
- Unified Game State validation, replay determinism, live WoW capability validation and end-to-end companion latency are **UNVERIFIED**.

## 7. External/open work

- **#59** — Firebase Test Lab IAM blocker; Owner action remains required only if dedicated FTL coverage is needed beyond the working GitHub Emulator path.
- **#11** — Figma design-system synchronization; requires the actual Figma design file/key before repository-to-design comparison can be completed.
- Release `SENTINEL_API_BASE_URL` configuration remains blocked until a reachable Core environment is available.

## 8. Architecture implementation queue

1. Deterministic replay fixture and validation harness for normalized adapter events / Unified Game State.
2. Unified Game State validator: schema, compatibility, idempotency, ordering, data-quality propagation and bounded staleness expiry.
3. Adapter Registry / Capability Registry integration into the Core runtime path without turning the registry into authorization.
4. Conservative first WoW adapter; capability status remains UNVERIFIED/LIMITED until exact target-environment evidence exists.
5. Companion protocol with interactive / near-real-time / batch / offline-replay transport classes and measurable end-to-end latency.
6. Policy Engine / Action Gateway boundary: recommendation/request → policy decision → explicit action gateway, with no adapter-side authorization.
7. Adapter/companion observability using the telemetry contract and bounded diagnostics.
8. Simulation harness for replay and recommendation evaluation.
9. Exact WoW 3.3.5a/private-server environment validation.

## 9. Engineering maintenance queue

- Modernize deprecated GitHub Actions runtimes/versions and move workflows away from Node 20 where supported.
- Replace stale task-board references to already-closed historical issues.
- Complete Figma design-system synchronization after the actual design file is available.
- Resolve Firebase Test Lab bucket IAM only when dedicated FTL coverage is required.

## 10. Canonical documents

- `docs/GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md` — canonical GPT-only operating system.
- `docs/SENTINEL_MASTER_ARCHITECTURE_v0.3.md` — system architecture foundation.
- `docs/GAME_ADAPTER_CONTRACT_V1.md` — adapter boundary and capability evidence contract.
- `docs/UNIFIED_GAME_STATE_V1.md` — normalized state contract.
- `docs/POSTHOG_TELEMETRY_CONTRACT_V1.md` — runtime telemetry contract.
- `docs/SENTINEL_PERFORMANCE_BASELINE.md` — reproducible performance measurements.
- `docs/SENTINEL_EVIDENCE_PROTOCOL.md` — evidence semantics.
- `docs/RELEASE_GATES.md` — release/CI acceptance gates.

This record describes repository facts as of the stated state record. The observed snapshot is maintained by the normal state-sync mechanism and always points to the triggering `main` SHA.
