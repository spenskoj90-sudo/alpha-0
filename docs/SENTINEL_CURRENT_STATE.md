# SENTINEL — Repository State Guide

> **Authoritative state:** Git `main` at an exact commit SHA. This document is an orientation guide, not a live mirror of commit SHAs, workflow runs, or file inventories.
>
> When a repository fact matters, inspect the current `main` tree and code. When an acceptance claim matters, require the exact SHA plus the relevant test/CI/runtime evidence. Unknown facts remain **UNVERIFIED**.

## 1. Product surfaces

- Android client exists under `app/`.
- FastAPI Core exists under `server/`.
- Next.js control plane exists under `web/`.
- Electron launcher exists under `launcher/` and exposes account/Companion runtime state, local game launching, passive WoW checkpoint state, a read-only Companion overlay renderer and an explicit-consent push-to-talk voice surface.
- The Electron launcher also has an unsigned source-bound Windows x64 packaging path with pinned Electron provenance, reproducibility comparison and packaged-executable smoke evidence. This is packaged CI evidence, not signed-release or physical-host acceptance.
- WoW addon sources exist under `wow-addon/`.

Existence of a source tree does not by itself establish that the surface is packaged, integrated or accepted in a real target environment.

## 2. Security and persistence baseline

- Android device identity is Keystore-backed P-256 with SHA-256 fingerprinting.
- Sessions use opaque tokens with one-time refresh rotation.
- Authorization is server-authoritative and default-deny.
- PostgreSQL is the production persistence architecture when `DATABASE_URL` is configured; migration `004_p1_rls_force.sql` applies FORCE RLS.
- Release signing controls and production/live deployment remain Owner-gated.

The Web account-control boundary stores Core access/refresh tokens only in HttpOnly, SameSite=Strict cookies, applies same-origin checks to state-changing account/billing requests, rotates an expired access session through the existing one-time Core refresh endpoint, and does not expose opaque tokens to client-side JavaScript.

The Electron launcher follows a separate desktop boundary: Core access/refresh tokens remain in main-process memory and are not persisted in launcher configuration or returned through renderer status APIs. The isolated main renderer can request sign-in/start/stop and bounded voice operations only through the preload bridge. Voice IPC is sender-bound to the current main renderer. Microphone access requires both main-owned explicit consent and a short-lived main-process capture lease; display capture is denied. The dedicated Companion worker receives the current access token over local process IPC; it does not receive the refresh token. The overlay has a separate, narrower preload exposing only a one-way snapshot subscription and no renderer-originated action IPC.

These statements are orientation-level invariants. They do not replace inspection of the current implementation and tests.

## 3. Game integration architecture

- Game Adapter Contract v1 is implemented as the canonical adapter boundary.
- Unified Game State v1 is implemented with bounded Pydantic state validation, timezone-aware timestamp ordering, per-session duplicate/out-of-order rejection, capability observability guards, explicit stale-state degradation, and deterministic canonical replay.
- Adapter Registry / Capability Registry v1 is implemented with typed identity, capability evidence/status discipline, downgrade tracking, bounded normalized events and Core-side usable-capability guards. `AVAILABLE` is no longer accepted from a raw caller merely because it labels evidence `L3`; promotion requires a validated exact-environment admission bound to the registered adapter environment.
- The conservative WoW adapter boundary is passive observation normalization only: explicit patch/server profiles, bounded latency and metadata, addon/launcher/entitlement observations, and UNVERIFIED-by-default capabilities. It has no action API and does not authorize or execute game actions.
- Transactional event-to-outbox persistence and the recoverable event runtime are implemented: lease ownership, `FOR UPDATE SKIP LOCKED` claims, bounded retry/backoff, durable terminal failure, explicit replay and monotonic character projection are covered by unit/PostgreSQL tests.
- Companion protocol v1 is implemented with compatibility negotiation, bounded envelopes and FIFO backpressure, explicit latency classes, and fail-closed mismatch handling.
- Server-side Companion runtime composition provides bounded lifecycle state, heartbeat freshness/watchdog degradation, deterministic reconnect/backoff, kill switch, queue/backpressure, peer-authentication and authorization ordering, TLS 1.2+ verification, optional certificate pinning, WebSocket/TCP transport seams and transport binding.
- The Core WebSocket entrypoint requires loopback locality before account evaluation, a valid Core session and an ACTIVE subscription-derived `companion` feature. Browser-compatible launcher authentication may carry the opaque session token in a non-selected `sentinel.auth.<base64url>` WebSocket subprotocol so the token is not placed in the URL; Core selects only public `sentinel.v1`. ACTIVE feature state is revalidated on live Companion traffic so a transition such as `PAST_DUE` revokes an already-open session on the next heartbeat/envelope.
- The Electron launcher composes a dedicated Companion worker process: main-process account/session ownership, worker handshake/heartbeat, bounded reconnect/backoff, one-time refresh handoff, explicit stop/kill switch and player-visible `CONNECTING`/`ACTIVE`/`DEGRADED`/`STOPPED` state. Dedicated Node tests run in the routine Build & Test workflow. The Windows packaging path embeds exact build provenance in `resources/app`, verifies a pinned official Electron runtime, compares two independently staged package manifests and executes the staged `SENTINEL Companion.exe` in CI. Signing and physical target-PC acceptance remain separate gates.
- Classic and Retail addon variants persist a bounded coarse `SentinelDB.snapshot` containing schema/sequence/time, patch/server profile, realm, bounded latency, addon-loaded state and coarse combat state. The launcher discovers the addon's SavedVariables file only beneath the configured WoW root (or a trusted process-level absolute override), parses a restricted Lua data subset without evaluation, normalizes it to a low-quality passive observation and places it in a bounded disk-backed FIFO. Companion delivers one observation at a time as `WOW_OBSERVATION`; Core validates it through `ConservativeWowAdapter`, overrides launcher/account association from server-authoritative state and returns `WOW_OBSERVATION_ACK` before the launcher removes the durable queue item. This path does not grant `game:write` and is not an action/event-execution path.
- Exact-environment evidence capture/admission is implemented as a separate fail-closed boundary. Opt-in packaged capture requires a source-bound Windows package, explicit stable environment ID, normal configured-WoW SavedVariables discovery rather than the override path, an accepted exact-version Companion handshake, authenticated ACTIVE runtime health and at least two distinct Core-ACKed SavedVariables checkpoints. Core independently validates the bounded bundle, rejects replay/synthetic execution, source/environment/handshake/connection/checkpoint drift and unsupported capability claims, and computes canonical evidence SHA-256 before issuing an internal L3 admission. The Classic addon defaults `server_profile` to `unknown`; an operator may explicitly label `official|private|unknown`, but that label does not by itself establish L3.
- Accepted passive WoW checkpoints can also produce a bounded Core-authored `OVERLAY` `STATUS` presentation. The worker accepts presentations only from the dedicated `PRESENTATION` envelope type and allowlist-normalizes presentation id/channel/kind/text/confidence/provenance. Electron main sanitizes the presentation again, stores only a small TTL-bounded set and forwards a snapshot to a dedicated sandboxed, context-isolated, non-Node, non-focusable, click-through overlay window. The overlay preload exposes no command IPC and renderer text is assigned with DOM `textContent`. This is an implemented read-only player presentation path, not an action surface.
- The player-facing voice runtime is internally productized as a presentation-only extension of that same authority model. Electron main owns consent, provider status and the current presentation target; the renderer must explicitly arm a short-lived capture lease immediately before audio-only `getUserMedia`, then disarms it after the request. Capture is fixed to bounded WebM/Opus and system stop/error/logout paths discard partial audio rather than submitting it. Core `/v1/companion/voice/status`, `/transcribe` and `/synthesize` repeat opaque-session, `game:read`, ACTIVE `companion` feature and explicit-consent checks. STT transcript is not returned to the renderer or written to audit metadata. Server-side classification emits only `OBSERVE`, `ACKNOWLEDGE` or `DISMISS`; action-like speech fails closed as `ACTION_GATEWAY_REQUIRED`. Accepted intents affect only bounded local overlay state. Optional TTS uses main-owned fixed feedback phrases and bounded WAV output; the renderer has no arbitrary synthesis-text IPC.
- Voice provider integration is vendor-neutral. A configured JSON-over-HTTP adapter uses bounded STT/TTS contracts, requires HTTPS for non-loopback endpoints, rejects unsafe credentials/configuration and maps provider failure to bounded voice reason codes. With no provider configured, voice reports `VOICE_PROVIDER_UNAVAILABLE`; no hidden browser/cloud speech fallback is used. Selected production provider/network/credentials and physical microphone/acoustic acceptance remain environment/Owner gates rather than repository claims.
- WoW SavedVariables are checkpoint persistence rather than realtime addon IPC: disk updates depend on WoW's normal SavedVariables lifecycle such as logout/ReloadUI. Repository tests therefore prove parser/queue/protocol/addon-contract and L3 capture/validator behavior, not that a live target-environment run occurred.
- Policy Engine / Action Gateway v1 is implemented as a fail-closed authorization boundary. Capability evidence can gate prerequisites but cannot grant authorization; automatic execution is disabled and user-confirmed intent is distinct from recommendation. Paid feature requirements are resolved server-side and fail closed when the resolver is missing, fails, or does not grant the required feature.
- The deterministic intelligence path is implemented from bounded UGS context through knowledge derivation, provider-neutral routing and confidence/provenance. The Web Command Center has an authenticated same-origin live retrieval path through the existing HttpOnly Core-session proxy. Browser code cannot select the recommendation provider or inject browser-authored context as trusted game evidence; Core remains authoritative for `knowledge:recommend`, provider/model identity, confidence and provenance. Failed or unauthenticated retrieval does not fall back to a static recommendation presented as live evidence.
- Android implements device binding/proof to obtain a `game:write` device session and retry-safe, sequence-protected, idempotent `/v1/events:batch` delivery. `OfflineEventQueue` provides bounded, atomically persisted local buffering with malformed-file isolation. Auth, Device, Event Sync and Dashboard use one injectable `HttpTransport` boundary backed by the platform `HttpURLConnection`: common 10s/15s timeouts, platform HTTPS verification, HTTP(S)-only URLs, disabled implicit redirects, bounded response bodies, header-injection rejection and deterministic cleanup are centralized without adding automatic retries or changing server-authoritative scopes/device proof/idempotency rules.
- Exact Retail and WotLK 3.3.5a/private-server validation remains **UNVERIFIED** until a real exact-environment L3 bundle is captured and accepted. Implemented capture/admission machinery is not itself live-environment evidence.

## 4. Billing, entitlement and account control

- Core defines a provider-neutral plan catalog and persistent subscription lifecycle with `PENDING`, `ACTIVE`, `PAST_DUE`, `CANCELED` and `EXPIRED` states.
- Caller-scoped `/v1/billing/plans`, `/v1/billing/subscriptions` and `/v1/billing/features` APIs are protected by the existing server-authoritative policy engine; browser code does not receive additional scopes.
- External provider events have a separate cryptographically verified ingress at `/v1/billing/provider-webhooks/{provider}`. The implemented generic adapter verifies `HMAC-SHA256 v1` over the exact raw body with bounded timestamp skew and constant-time comparison. It is a concrete signed-provider contract, not a claim of Stripe or another vendor-specific wire protocol.
- The legacy `/v1/billing/webhooks/{provider}` shared-token path is restricted by `BillingService` to the internal `manual`/`test` providers and cannot activate an arbitrary external-provider subscription.
- Provider snapshot reconciliation is deterministic: provider + subscription + provider revision + state derive an idempotent reconciliation event ID, and lifecycle transitions still pass through the same billing state machine.
- Feature grants are derived only from `ACTIVE` subscriptions. `PENDING`, `PAST_DUE`, `CANCELED` and `EXPIRED` states grant no paid feature. `core-plus` currently grants `core` + `companion`; Companion connection startup, live traffic and voice access enforce the `companion` grant.
- `/v1/entitlements/me` remains the caller-scoped game-entitlement readback; subscription-derived product features are separate from manually/admin-granted game entitlements.
- The Web control plane presents live plan, subscription and game-entitlement state through the secure cookie-session proxy and exposes subscription-intent creation without pretending that payment occurred. The browser provider value is constrained to the provider-neutral manual boundary; activation remains provider-confirmed.
- Production provider selection, vendor-specific protocol/network integration and payment credentials remain Owner/external activation work. No production provider credential is embedded in repository code.

## 5. Telemetry and performance

- The telemetry contract is provider-neutral. Companion emits bounded privacy-safe runtime/transport events, exposes health and latency snapshots, supports fanout, and has opt-in PostgreSQL persistence/retention seams.
- Core now has a bounded operational observability plane: global `X-Request-ID` normalization, server-authored trace IDs, low-cardinality route-template/method/status-class HTTP counters and latency windows, a bounded recent-trace ring, overflow/drop evidence and admin-protected JSON/OpenMetrics-compatible readback. Request and trace identifiers are not metric labels.
- Operational correlation is propagated through the authenticated Web proxy, launcher refresh/retry path and shared Android HTTP transport while preserving explicit caller correlation where valid. Companion and voice runtime outcomes are instrumented without using audio, transcript, token, user, IP, realm or payload values as metric labels.
- Deterministic Block D failure injection covers unsafe correlation, series-cardinality saturation, bounded trace overflow and identifier-label isolation. CI-local performance evidence measures normalization, registry-recording and snapshot overhead against explicit budgets and publishes exact-SHA evidence in routine Build & Test.
- External telemetry-provider delivery, a deployed Prometheus/OpenTelemetry/vendor backend, production alerting/on-call integration and production SLOs remain optional environment integrations, not repository implementation claims.
- Performance budgets are operation-scoped contracts; measured results are acceptance evidence only when tied to the relevant exact SHA/Run ID and current main state. Real-load, physical-device and packaged-host performance remain environment-specific evidence.
- Deterministic privacy scrubbing and a canonical recovery matrix with fail-closed health outcomes are implemented and covered by unit tests.
- Launcher session/process/reconnect security, passive SavedVariables parser/queue/protocol behavior, overlay presentation isolation, voice consent/capture/provider/result boundaries and exact-environment evidence capture contracts have deterministic routine CI coverage. Exact WoW addon lifecycle/host behavior, physical microphone/acoustic behavior and real packaged-overlay/voice latency remain environment-unverified until exercised on the target runtime.

## 6. Internal architecture work remaining

The first six implementation passes plus Blocks A-D now cover the approved repository-internal architecture sequence through observability/performance/resilience productization. The live Web intelligence retrieval gap is also closed by the authenticated Command Center path. The unsigned Windows Companion is packageable/reproducibility-tested in CI, and the repository contains a bounded exact-environment L3 capture/validation/admission path for the conservative WoW integration.

There is no comparably large known missing repository-internal architecture block inside the approved first vertical slice. Remaining internal work is predominantly quality and evidence-driven hardening rather than another foundational subsystem. Current candidates include:

1. design-system/UI synchronization and accessibility consistency across the implemented surfaces where authoritative design evidence is available;
2. measured fixes discovered by real packaged-host, physical-device or exact-game-environment acceptance;
3. narrowly scoped operational or provider hardening justified by observed production-like evidence rather than speculative rewrites.

Android transport consolidation is implemented as a shared injectable boundary; future transport work should be driven by measured or platform-specific needs rather than reopening independent connection implementations.

The machinery needed to collect and validate exact-environment evidence is repository-internal and implemented, but the evidence itself is deliberately external: exact WoW/private-server L3 behavior, selected production voice-provider behavior, physical microphone/driver/acoustic evidence, signed desktop packaging and physical real-host acceptance remain environment/Owner gates. Release signing/publication/deployment remain Owner-gated.

## 7. External / Owner-gated evidence

Known external or protected items remain:

- real exact WoW 3.3.5a/private-server L3 capture and acceptance against the intended target environment;
- physical Android release-device acceptance;
- selected production STT/TTS provider credentials/network acceptance and physical microphone/driver/acoustic-quality evidence;
- physical target-PC acceptance for the packaged Companion where required by the release candidate;
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

`UGS runtime validation → deterministic replay → conservative WoW adapter → Companion protocol/runtime → Policy Engine / Action Gateway → context/recommendation/confidence/provenance → Command Center/Overlay/Voice UX → observability/performance/resilience → packaged-host provenance → exact-environment evidence capture/admission → real-device/integration acceptance`

The repository-internal sequence through exact-environment evidence capture/admission is implemented; the next acceptance phase is actual exact-device/host/game-environment evidence. No autonomous combat, no premature broad game/version expansion, no production/live deployment, and no release publication are implied. Exact-environment capabilities remain UNVERIFIED until a real L3 bundle exists and is accepted.
