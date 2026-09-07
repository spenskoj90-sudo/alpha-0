# SENTINEL — Repository State Guide

> **Authoritative state:** Git `main` at an exact commit SHA. This document is an orientation guide, not a live mirror of commit SHAs, workflow runs, or file inventories.
>
> When a repository fact matters, inspect the current `main` tree and code. When an acceptance claim matters, require the exact SHA plus the relevant test/CI/runtime evidence. Unknown facts remain **UNVERIFIED**.

## 1. Product surfaces

- Android client exists under `app/`.
- FastAPI Core exists under `server/`.
- Next.js control plane exists under `web/`.
- Electron launcher exists under `launcher/`.
- WoW addon sources exist under `wow-addon/`.

## 2. Security and persistence baseline

- Android device identity is Keystore-backed P-256 with SHA-256 fingerprinting.
- Sessions use opaque tokens with one-time refresh rotation.
- Authorization is server-authoritative and default-deny.
- PostgreSQL is the production persistence architecture when `DATABASE_URL` is configured; migration `004_p1_rls_force.sql` applies FORCE RLS.
- Release signing controls and production/live deployment remain Owner-gated.

These statements are orientation-level invariants. They do not replace inspection of the current implementation and tests.

## 3. Game integration architecture

- Game Adapter Contract v1 is implemented as the canonical adapter boundary.
- Unified Game State v1 is implemented with bounded Pydantic state validation, timezone-aware timestamp ordering, per-session duplicate/out-of-order rejection, capability observability guards, explicit stale-state degradation, and deterministic canonical replay.
- Adapter Registry / Capability Registry v1 is implemented on `main` with typed identity, capability evidence/status discipline, L3 enforcement for `AVAILABLE`, downgrade tracking, bounded normalized events, Core-side usable-capability guards, and contract/boundary tests.
- The conservative WoW adapter boundary is implemented as passive observation normalization only: explicit patch/server profiles, bounded latency and metadata, addon/launcher/entitlement observations, and UNVERIFIED-by-default capabilities. It has no action API and does not authorize or execute game actions.
- Policy Engine / Action Gateway v1 is implemented as a fail-closed authorization boundary. Capability evidence can gate prerequisites but cannot grant authorization; automatic execution is disabled and user-confirmed intent is distinct from recommendation.
- Exact Retail and WotLK 3.3.5a/private-server validation remains **UNVERIFIED** until exact-environment L3 evidence exists.

## 4. Telemetry and performance

- PostHog telemetry contract v1 is defined and provider-neutral.
- Runtime PostHog instrumentation is not yet established as a complete implementation; contract and runtime instrumentation are separate stages.
- Performance baseline methodology exists; measured results are acceptance evidence only when tied to the relevant exact SHA/Run ID and current main state.
- Launcher/WoW-addon dedicated test and coverage evidence remains **UNVERIFIED** unless current repository evidence proves otherwise.

## 5. Architecture work remaining

The repository should be compared against `docs/SENTINEL_MASTER_ARCHITECTURE_v0.3.md` before each substantive implementation block. Known architectural gaps include, but are not limited to:

- Companion protocol and measurable latency classes;
- adapter/Companion observability implementation;
- simulation harness before expanding recommendation logic;
- exact-environment WoW validation with L3 evidence;
- AI provider abstraction/routing, confidence/provenance implementation, compatibility/version negotiation, overlay/voice interaction contracts and related MVP architecture items where implementation evidence is absent;
- Android `AuthApi` transport architecture remains technical debt because it still uses synchronous `HttpURLConnection`.

The Policy Engine / Action Gateway boundary is no longer an open architectural gap; its execution surface remains intentionally conservative and does not authorize autonomous game actions.

This list is a planning aid, not a claim that the gaps have not changed. The next baseline must inspect the repository and tests before selecting work.

## 6. Governance

The canonical operating model is `docs/GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md`: GPT/ChatGPT is the sole AI engineering participant, the Human Owner is final authority, routine CI failures are diagnosed/fixed autonomously, and merges require exact-SHA successful required checks without bypassing security or repository protection.

## 7. Source-of-truth model

Use each source for the kind of truth it actually owns:

| Source | Authority |
|---|---|
| Git `main` + exact SHA | Actual repository/product implementation state |
| Code + tests | Implemented behavior and regression evidence |
| GitHub Actions | Build/test/security workflow evidence and Run IDs |
| Issues / PRs | Active work, acceptance scope and historical implementation evidence |
| Architecture contracts / ADRs | Normative target, constraints and accepted design decisions |
| TASKS.md | Human-readable work queue and open architectural gaps |
| This document | Orientation only; never a substitute for repository inspection |
| Historical audits / handovers | Historical context only unless independently revalidated |

## 8. Documentation rule

Ordinary code changes do **not** require a generated current-state commit or a documentation-only PR. Update this guide only when its semantic orientation materially changes. Never embed a mutable `main` HEAD or workflow-run mirror here.

A document can describe an intended architecture or a historical observation, but it cannot prove that an implementation exists on current `main`. For implementation claims, inspect the repository and require evidence.

## 9. Vertical-block completion rule

A substantive SENTINEL block is complete only when its applicable concerns are completed as one coherent vertical slice:

1. implementation and stable contract boundaries;
2. UX/design/visualization for user-facing behavior;
3. security/privacy and failure/degradation behavior;
4. performance/resource behavior appropriate to the block;
5. automated tests and regression evidence;
6. runtime/device/integration evidence where applicable;
7. semantic documentation/decision records when the block changes product or architectural meaning.

A large architectural block may be delivered through several short-lived, independently verifiable PRs. What is prohibited is intentionally leaving a known required dimension of the active block for an unspecified later pass.

The completion gate is evidence-based: an item remains **UNVERIFIED** when the required repository, CI, runtime, device or exact-environment evidence does not exist.

## 10. First complete SENTINEL vertical slice

The approved implementation sequence is:

`UGS runtime validation → deterministic replay → conservative WoW adapter → Companion protocol/runtime → Policy Engine / Action Gateway → context/recommendation/confidence/provenance → Command Center/overlay UX → observability/performance → real-device/integration acceptance`

This sequence is the primary implementation program for the first complete SENTINEL path. The slice remains conservative: no autonomous combat, no premature broad game/version expansion, no production/live deployment, and no release publication. Exact-environment capabilities remain UNVERIFIED until L3 evidence exists.

Each completed block becomes the verified foundation for the next block; do not create parallel long-lived unfinished implementations when the next stage depends on the current one.
