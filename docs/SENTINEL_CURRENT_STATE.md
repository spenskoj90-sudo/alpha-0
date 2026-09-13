# SENTINEL — Repository State Guide

> **Authoritative state:** Git `main` at an exact commit SHA. This document is an orientation guide, not a live mirror of commit SHAs, workflow runs, or file inventories.
>
> When a repository fact matters, inspect the current `main` tree and code. When an acceptance claim matters, require the exact SHA plus the relevant test/CI/runtime evidence. Unknown facts remain **UNVERIFIED**.

## 1. Product surfaces

- Android client exists under `app/`.
- FastAPI Core exists under `server/`.
- Next.js control plane exists under `web/`.
- Electron launcher exists under `launcher/` and now exposes account/Companion runtime state in addition to local game launching.
- WoW addon sources exist under `wow-addon/`.

Existence of a source tree does not by itself establish that the surface is packaged, integrated or accepted in a real target environment.

## 2. Security and persistence baseline

- Android device identity is Keystore-backed P-256 with SHA-256 fingerprinting.
- Sessions use opaque tokens with one-time refresh rotation.
- Authorization is server-authoritative and default-deny.
- PostgreSQL is the production persistence architecture when `DATABASE_URL` is configured; migration `004_p1_rls_force.sql` applies FORCE RLS.
- Release signing controls and production/live deployment remain Owner-gated.

The Web account-control boundary stores Core access/refresh tokens only in HttpOnly, SameSite=Strict cookies, applies same-origin checks to state-changing account/billing requests, rotates an expired access session through the existing one-time Core refresh endpoint, and does not expose opaque tokens to client-side JavaScript.

The Electron launcher follows a separate desktop boundary: Core access/refresh tokens remain in main-process memory and are not persisted in launcher configuration or returned through renderer status APIs. The isolated renderer can request sign-in/start/stop operations only through the preload bridge. The dedicated Companion worker receives the current access token over local process IPC; it does not receive the refresh token.

These statements are orientation-level invariants. They do not replace inspection of the current implementation and tests.

## 3. Game integration architecture

- Game Adapter Contract v1 is implemented as the canonical adapter boundary.
- Unified Game State v1 is implemented with bounded Pydantic state validation, timezone-aware timestamp ordering, per-session duplicate/out-of-order rejection, capability observability guards, explicit stale-state degradation, and deterministic canonical replay.
- Adapter Registry / Capability Registry v1 is implemented with typed identity, capability evidence/status discipline, L3 enforcement for `AVAILABLE`, downgrade tracking, bounded normalized events, Core-side usable-capability guards, and contract/boundary tests.
- The conservative WoW adapter boundary is passive observation normalization only: explicit patch/server profiles, bounded latency and metadata, addon/launcher/entitlement observations, and UNVERIFIED-by-default capabilities. It has no action API and does not authorize or execute game actions.
- Transactional event-to-outbox persistence and the recoverable event runtime are implemented: lease ownership, `FOR UPDATE SKIP LOCKED` claims, bounded retry/backoff, durable terminal failure, explicit replay and monotonic character projection are covered by unit/PostgreSQL tests.
- Companion protocol v1 is implemented with five-way compatibility negotiation, bounded envelopes and FIFO backpressure, explicit latency classes, and fail-closed mismatch handling.
- Server-side Companion runtime composition provides bounded lifecycle state, heartbeat freshness/watchdog degradation, deterministic reconnect/backoff, kill switch, queue/backpressure, peer-authentication and authorization ordering, TLS 1.2+ verification, optional certificate pinning, WebSocket/TCP transport seams and transport binding.
- The Core WebSocket entrypoint requires loopback locality before account evaluation, a valid Core session and an ACTIVE subscription-derived `companion` feature. Browser-compatible launcher authentication may carry the opaque session token in a non-selected `sentinel.auth.<base64url>` WebSocket subprotocol so the token is not placed in the URL; Core selects only public `sentinel.v1`. ACTIVE feature state is revalidated on live Companion traffic so a transition such as `PAST_DUE` revokes an already-open session on the next heartbeat/envelope.
- The Electron launcher composes a dedicated Companion worker process: main-process account/session ownership, worker handshake/heartbeat, bounded reconnect/backoff, one-time refresh handoff, explicit stop/kill switch and player-visible `CONNECTING`/`ACTIVE`/`DEGRADED`/`STOPPED` state. Dedicated Node tests run in the routine Build & Test workflow. This is repository/runtime composition evidence, not signed desktop packaging or real-host acceptance.
- Classic and Retail addon variants now persist a bounded coarse `SentinelDB.snapshot` containing schema/sequence/time, patch/server profile, realm, bounded latency, addon-loaded state and coarse combat state. The launcher discovers the addon's SavedVariables file only beneath the configured WoW root (or a trusted process-level absolute override), parses a restricted Lua data subset without evaluation, normalizes it to a low-quality passive observation and places it in a bounded disk-backed FIFO. Companion delivers one observation at a time as `WOW_OBSERVATION`; Core validates it through `ConservativeWowAdapter`, overrides launcher/account association from server-authoritative state and returns `WOW_OBSERVATION_ACK` before the launcher removes the durable queue item. This path does not grant `game:write` and is not an action/event-execution path.
- WoW SavedVariables are checkpoint persistence rather than realtime addon IPC: disk updates depend on WoW's normal SavedVariables lifecycle such as logout/ReloadUI. Repository tests therefore prove parser/queue/protocol/addon-contract behavior, not live in-game streaming or exact-host compatibility.
- Policy Engine / Action Gateway v1 is implemented as a fail-closed authorization boundary. Capability evidence can gate prerequisites but cannot grant authorization; automatic execution is disabled and user-confirmed intent is distinct from recommendation. Paid feature requirements are resolved server-side and fail closed when the resolver is missing, fails, or does not grant the required feature.
- The deterministic intelligence path is implemented from bounded UGS context through knowledge derivation, provider-neutral routing and confidence/provenance. The Web includes a bounded recommendation presentation component, but the current default card is a presentation baseline; a live end-to-end Web recommendation retrieval path must not be inferred from that component alone.
- Android implements device binding/proof to obtain a `game:write` device session and retry-safe, sequence-protected, idempotent `/v1/events:batch` delivery. `OfflineEventQueue` provides bounded, atomically persisted local buffering with malformed-file isolation; exact WoW/private-server L3 validation remains **UNVERIFIED**.
- Exact Retail and WotLK 3.3.5a/private-server validation remains **UNVERIFIED** until exact-environment L3 evidence exists.

## 4. Billing, entitlement and account control

- Core defines a provider-neutral plan catalog and persistent subscription lifecycle with `PENDING`, `ACTIVE`, `PAST_DUE`, `CANCELED` and `EXPIRED` states.
- Caller-scoped `/v1/billing/plans`, `/v1/billing/subscriptions` and `/v1/billing/features` APIs are protected by the existing server-authoritative policy engine; browser code does not receive additional scopes.
- External provider events have a separate cryptographically verified ingress at `/v1/billing/provider-webhooks/{provider}`. The implemented generic adapter verifies `HMAC-SHA256 v1` over the exact raw body with bounded timestamp skew and constant-time comparison. It is a concrete signed-provider contract, not a claim of Stripe or another vendor-specific wire protocol.
- The legacy `/v1/billing/webhooks/{provider}` shared-token path is restricted by `BillingService` to the internal `manual`/`test` providers and cannot activate an arbitrary external-provider subscription.
- Provider snapshot reconciliation is deterministic: provider + subscription + provider revision + state derive an idempotent reconciliation event ID, and lifecycle transitions still pass through the same billing state machine.
- Feature grants are derived only from `ACTIVE` subscriptions. `PENDING`, `PAST_DUE`, `CANCELED` and `EXPIRED` states grant no paid feature. `core-plus` currently grants `core` + `companion`; Companion connection startup and live traffic enforce the `companion` grant.
- `/v1/entitlements/me` remains the caller-scoped game-entitlement readback; subscription-derived product features are separate from manually/admin-granted game entitlements.
- The Web control plane presents live plan, subscription and game-entitlement state through the secure cookie-session proxy and exposes subscription-intent creation without pretending that payment occurred. The browser provider value is constrained to the provider-neutral manual boundary; activation remains provider-confirmed.
- Production provider selection, vendor-specific protocol/network integration and payment credentials remain Owner/external activation work. No production provider credential is embedded in repository code.

## 5. Telemetry and performance

- The telemetry contract is provider-neutral. Companion emits bounded privacy-safe runtime/transport events, exposes health and latency snapshots, supports fanout, and has opt-in PostgreSQL persistence/retention seams.
- External telemetry-provider delivery and a deployed operator observability stack remain optional environment integrations, not implementation claims.
- Performance budgets are represented as operation-scoped contracts with deterministic pass/fail evaluation; measured results remain acceptance evidence only when tied to the relevant exact SHA/Run ID and current main state.
- Deterministic privacy scrubbing and a canonical recovery matrix with fail-closed health outcomes are implemented and covered by unit tests.
- Launcher session/process/reconnect security plus passive SavedVariables parser/queue/protocol behavior now have deterministic routine CI coverage. This remains repository evidence; exact WoW addon lifecycle/host behavior is environment-unverified until exercised on the target client/server.
- End-to-end correlation propagation, real metrics/tracing composition and benchmark/failure-injection measurements remain separate implementation/evidence concerns when repository inspection does not prove them.

## 6. Internal architecture work remaining

The first six implementation passes and Blocks A-D produced substantial foundations, but the 2026-09-13 code-first rebaseline found that several earlier completion labels conflated **foundation complete** with **product/runtime complete**.

Largest remaining internal targets include:

1. Continue launcher/Companion/WoW productization beyond the tested account/process/socket and passive checkpoint path into complete player-facing Overlay/voice runtime behavior. Signed desktop packaging and real-host acceptance remain evidence targets after repository composition exists.
2. Complete actual player-facing Overlay/voice runtime wiring. Provider-neutral STT/TTS or presentation models alone do not constitute a complete voice product.
3. Preserve exact-environment evidence classification for addon/launcher behavior; repository parser/protocol tests must not be promoted to WoW 3.3.5a/private-server L3 validation.
4. Android transport consolidation where it provides concrete engineering value. Several Android API surfaces still retain independent `HttpURLConnection` implementations; replacement is technical debt reduction, not a current authorization bypass.
5. Observability/performance runtime composition and measured evidence beyond deterministic contract tests.

These are internal engineering targets and must not be mislabeled as Owner/external blockers.

## 7. External / Owner-gated evidence

Known external or protected items remain:

- exact WoW target validation in the real 3.3.5a/private-server environment;
- physical Android release-device acceptance;
- real packaged Companion-host acceptance where exact-environment evidence is required;
- production ingress/database credentials;
- selected production payment-provider credentials and vendor-specific live integration;
- signing-key/certificate custody;
- signed release-candidate Owner execution;
- release tag/publication and live production deployment.

Firebase Test Lab issue #59 remains deferred/non-blocking while GitHub-hosted emulator instrumentation is the routine Android gate.

## 8. Governance

The canonical operating model is `docs/GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md`: GPT/ChatGPT is the sole AI engineering participant, the Human Owner is final authority, routine CI failures are diagnosed/fixed autonomously, and GPT may merge only after exact-PR-HEAD required checks are successful without bypassing security or repository protection.

Historical workflow or playbook documents that prohibit GPT merge are superseded where they conflict with that canonical operating system.

## 9. Source-of-truth model

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

## 10. Evidence classification

For broad targets use evidence-scoped labels rather than one binary completion flag:

- **IMPLEMENTED** — source implementation exists.
- **INTEGRATION-TESTED** — automated integration evidence exercises the composed path.
- **SIMULATED** — deterministic/fake/replay evidence exists but no real environment is implied.
- **PRODUCTIZED** — the intended user/operator runtime surface is coherently wired and usable.
- **ENVIRONMENT-UNVERIFIED** — implementation may exist, but the required exact external/runtime environment has not been exercised.
- **MISSING** — required implementation surface is absent.
- **TECHNICAL-DEBT** — current behavior works within accepted invariants but an internal engineering improvement remains.

## 11. Documentation rule

Ordinary code changes do **not** require a generated current-state commit or a documentation-only PR. Update this guide only when its semantic orientation materially changes. Never embed a mutable `main` HEAD or workflow-run mirror here.

A document can describe an intended architecture or a historical observation, but it cannot prove that an implementation exists on current `main`. For implementation claims, inspect the repository and require evidence.

## 12. Vertical-block completion rule

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

## 13. First complete SENTINEL vertical slice

The approved implementation sequence remains conservative:

`UGS runtime validation → deterministic replay → conservative WoW adapter → Companion protocol/runtime → Policy Engine / Action Gateway → context/recommendation/confidence/provenance → Command Center/Overlay UX → observability/performance → real-device/integration acceptance`

No autonomous combat, no premature broad game/version expansion, no production/live deployment, and no release publication are implied. Exact-environment capabilities remain UNVERIFIED until L3 evidence exists.
