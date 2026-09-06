# SENTINEL — Canonical Current State

**State record:** 2026-09-06  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Observed `main` baseline before Issue #167:** `33934d4d3d9c4655372fa159820f79ba90ed490d`

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

## 2. Active governance — Issue #167 / PR #168

**Status: ACTIVE — Human Owner approved the GPT-only autonomous engineering model on 2026-09-06.**

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

- `server/`: security, RLS, refresh-concurrency, character/game-state and projection coverage exists.
- `app/`: Sentry runtime path verified; refresh/session test lineage exists.
- `web/`: admin entitlements route test exists.
- `launcher/` / `wow-addon/`: dedicated test/coverage evidence **UNVERIFIED**.

## 7. External/open work

- **#167 / #168** — GPT-only autonomous engineering operating system; governance documentation migration is implemented on the task branch and awaiting exact-SHA CI validation/merge.
- **#59** — Firebase Test Lab IAM blocker; optional while emulator CI remains available.
- **#13** — PostHog telemetry contract.
- **#11** — Figma design-system synchronization.
- **#10** — measurable build/runtime performance baseline.
- Release `SENTINEL_API_BASE_URL` configuration remains blocked until a reachable Core environment is available.
- PR #133 remains an Owner-review architecture draft.

## 8. Branch protection and release

`main` has required CI/status gates and up-to-date-before-merge protection. Deploy is intentionally not a required merge check. Release publication and live deployment remain Owner-gated.

## 9. Canonical governance documents

- `docs/GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md` — canonical GPT-only operating system.
- `docs/AI_ROLES.md` — roles and non-delegation rule.
- `docs/AUTONOMOUS_ENGINEERING_CONTRACT.md` — autonomous state machine.
- `docs/AUTONOMOUS_PERMISSIONS.md` — permission/tool matrix.
- `docs/WORKFLOW_CONTRACT.md` — machine-operable workflow rules.
- `docs/OPERATING_PLAYBOOK.md` — operational procedure.
- `docs/SENTINEL_EVIDENCE_PROTOCOL.md` — evidence semantics.
- `docs/RELEASE_GATES.md` — release/CI acceptance gates.

This record describes current repository facts as of the stated state record; after PR #168 merges, the main SHA must be refreshed by the normal state-sync mechanism.
