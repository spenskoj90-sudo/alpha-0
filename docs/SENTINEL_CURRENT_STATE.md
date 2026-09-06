# SENTINEL — Canonical Current State

**State record:** 2026-09-06  
**Repository:** `spenskoj90-sudo/alpha-0`  
**Canonical branch:** `main`  
**Observed `main` baseline before Issue #167:** `33934d4d3d9c4655372fa159820f79ba90ed490d`

> Git/main is authoritative for product state. Unmerged branch evidence is not current product state.
> Exact CI/release claims require exact SHA + workflow Run ID. Unknown facts remain **UNVERIFIED**.

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
- Sentry Android runtime path is **VERIFIED** on a physical device on 2026-09-06; temporary smoke UI was removed after confirmation.
- Deploy workflow is release/manual triggered and optional remote rollout is separately gated.
- CURRENT_STATE auto-sync is implemented through the dedicated CI path.

## 2. Governance migration — Issue #167

**Status: PROPOSED — pending Human Owner approval.**

The legacy multi-AI engineering model is superseded by the proposed GPT-only model:

| Responsibility | GPT / ChatGPT | Human Owner | Other AI |
|---|---|---|---|
| Engineering analysis | **Sole AI role** | Final authority | **No role** |
| Architecture | **Sole AI role** | Product authority | **No role** |
| Implementation | **Sole AI role** | Scope/acceptance authority | **No role** |
| Testing/security/CI analysis | **Sole AI role** | Final acceptance | **No role** |
| PR preparation/review | **Sole AI role** | Merge authority | **No role** |
| Merge to `main` | Prepare/verify | **Owner gate** | **No role** |
| Production/live actions | Prepare/verify | **Owner gate** | **No role** |

No other AI system participates in engineering, coding, testing, review, security, CI diagnosis, architecture or integration.

Autonomous routine loop:

`DISCOVER → BASELINE → PLAN → IMPLEMENT → TEST → DIAGNOSE/FIX → REVIEW → COMMIT → PR → CI → ANALYZE → FIX/CI → READY`

Routine CI failures are not a conversational stop condition. GPT continues diagnosis and remediation until completion, a protected action, an unresolved product decision, or a genuine permission blocker.

## 3. Security invariants

Do not silently weaken the documented server-authoritative/default-deny model, device identity protections, opaque session/refresh protections, database/RLS boundaries, migration integrity or release signing controls.

## 4. Verification state

- `server/`: security, RLS, refresh-concurrency, character/game-state and projection coverage exists.
- `app/`: Sentry runtime path verified; refresh/session test lineage exists.
- `web/`: admin entitlements route test exists.
- `launcher/` / `wow-addon/`: dedicated test/coverage evidence **UNVERIFIED**.

## 5. External/open work

- **#167** — GPT-only autonomous engineering operating system; documentation migration pending Owner approval.
- **#59** — Firebase Test Lab IAM blocker; optional while emulator CI remains available.
- **#13** — PostHog telemetry contract.
- **#11** — Figma design-system synchronization.
- **#10** — measurable build/runtime performance baseline.
- Release `SENTINEL_API_BASE_URL` configuration remains blocked until a reachable Core environment is available.
- PR #133 remains an Owner-review architecture draft.

## 6. Branch protection and release

`main` has required CI/status gates and up-to-date-before-merge protection. Deploy is intentionally not a required merge check. Release publication and live deployment remain Owner-gated under the proposed operating model.

## 7. Canonical governance documents

- `docs/AI_ROLES.md` — roles and non-delegation rule.
- `docs/AUTONOMOUS_ENGINEERING_CONTRACT.md` — autonomous state machine.
- `docs/AUTONOMOUS_PERMISSIONS.md` — permission/tool matrix.
- `docs/WORKFLOW_CONTRACT.md` — machine-operable workflow rules.
- `docs/OPERATING_PLAYBOOK.md` — operational procedure.
- `docs/SENTINEL_EVIDENCE_PROTOCOL.md` — evidence semantics.
- `docs/RELEASE_GATES.md` — release/CI acceptance gates.

After Issue #167 approval, these documents must be reconciled to the final approved policy and the current `main` SHA must be refreshed by the normal state-sync mechanism.
