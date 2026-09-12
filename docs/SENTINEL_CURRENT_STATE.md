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
- Transactional event-to-outbox persistence and the recoverable event runtime are implemented: lease ownership, `FOR UPDATE SKIP LOCKED` claims, bounded retry/backoff, durable terminal failure, explicit replay and monotonic character projection are covered by unit/PostgreSQL tests.
- Companion protocol v1 is implemented with five-way compatibility negotiation, bounded envelopes and FIFO backpressure, explicit latency classes, and fail-closed mismatch handling.
- Companion runtime composition provides bounded lifecycle state, heartbeat freshness/watchdog degradation, deterministic reconnect/backoff, kill switch, queue/backpressure, peer-authentication and authorization ordering, TLS 1.2+ verification, optional certificate pinning, WebSocket/TCP transport seams and transport binding. Automated loopback tests exercise the composed socket path; a packaged production Companion host and live network environment remain unverified.
- Policy Engine / Action Gateway v1 is implemented as a fail-closed authorization boundary. Capability evidence can gate prerequisites but cannot grant authorization; automatic execution is disabled and user-confirmed intent is distinct from recommendation.
- The deterministic intelligence path is implemented from bounded UGS context through knowledge derivation, provider-neutral routing, confidence/provenance, recommendation delivery and the web Command Center presentation. No external AI provider or credential is implied.
- Android implements device binding/proof to obtain a `game:write` device session and retry-safe, sequence-protected, idempotent `/v1/events:batch` delivery. `OfflineEventQueue` now provides bounded, atomically persisted local buffering with malformed-file isolation; exact WoW/private-server L3 validation remains **UNVERIFIED**.
- Exact Retail and WotLK 3.3.5a/private-server validation remains **UNVERIFIED** until exact-environment L3 evidence exists.

## 4. Telemetry and performance

- The telemetry contract is provider-neutral. Companion emits bounded privacy-safe runtime/transport events, exposes health and latency snapshots, supports fanout, and has opt-in PostgreSQL persistence/retention seams.
- External telemetry-provider delivery and a deployed operator observability stack remain optional environment integrations, not implementation claims.
- Performance budgets are represented as operation-scoped contracts with deterministic pass/fail evaluation; measured results remain acceptance evidence only when tied to the relevant exact SHA/Run ID and current main state.
- Block D adds deterministic privacy scrubbing for telemetry attributes and a canonical recovery matrix with fail-closed health outcomes; implementation evidence is covered by unit tests and the Block D contract.
- Launcher/WoW-addon dedicated test and coverage evidence remains **UNVERIFIED** unless current repository evidence proves otherwise.

## 5. Architecture work remaining

The first six implementation passes and Blocks A–D closed the repository/CI re-baseline, monetization/entitlement, Companion experience, and observability/resilience verticals. Remaining work is external or Owner-gated activation only: exact WoW target validation, production credentials and ingress/database configuration, real-device/Companion-host acceptance, signed release-candidate execution, release publication and live deployment.

Known evidence and environment gaps remain: exact WoW target validation, a real Companion host, live production ingress/database evidence, external provider credentials where selected, and signed/public release acceptance. Android `AuthApi` retains a `HttpURLConnection` implementation behind an injectable transport and coroutine I/O boundary; replacing that implementation is technical debt, not a current authorization bypass.

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

`UGS runtime validation → deterministic replay → conservative WoW adapter → Companion protocol/runtime → Policy Engine / Action Gateway → context/recommendation/confidence/provenance → Command Center/Overlay UX → observability/performance → real-device/integration acceptance`

This sequence is the primary implementation program for the first complete SENTINEL path. The slice remains conservative: no autonomous combat, no premature broad game/version expansion, no production/live deployment, and no release publication. Exact-environment capabilities remain UNVERIFIED until L3 evidence exists.

Each completed block becomes the verified foundation for the next block; do not create parallel long-lived unfinished implementations when the next stage depends on the current one.
