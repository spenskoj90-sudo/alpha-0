# Sentinel — Task Board

`TASKS.md` is a human-readable work queue. It is **not** a mirror of the repository and is never used as proof that an implementation exists. The repository, tests and exact CI/runtime evidence remain authoritative.

## Governance rule

**ACTIVE:** SENTINEL uses only GPT/ChatGPT as its AI engineering participant. The Human Owner remains the final decision-maker and sole owner of protected actions. GPT may autonomously execute ordinary engineering work through the canonical lifecycle and may merge after the exact-SHA gate passes.

## Completed foundation on main

- [x] GPT-only governance, exact-SHA merge gate and repository-first evidence model.
- [x] Identity/session/default-deny authorization, PostgreSQL/RLS, migrations, audit and device proof foundations.
- [x] Adapter/capability contract, UGS validation, deterministic replay/simulation and character projection.
- [x] PASS 1 — transactional event/outbox consistency and monotonic UGS projection.
- [x] PASS 2 — recoverable event runtime with lease ownership, bounded retry/dead-letter and explicit replay.
- [x] PASS 3 — conservative authenticated WoW observation → UGS → projection → recommendation-context vertical.
- [x] PASS 4 — bounded Knowledge Engine, provider-neutral intelligence routing and confidence/provenance.
- [x] PASS 5 — server-side Companion transport/session/TLS hardening, peer authorization ordering, kill switch and bounded observability seams.
- [x] PASS 6 — Android Keystore device proof and retry-safe device-session event ingestion.
- [x] **Block A foundation — repository/CI/supply-chain/governance truth:** release signing is removed from routine PR CI; web tests and lockfile gates are deterministic; Actions are pinned by immutable SHA; repository verification and release/version documentation are reconciled.

## Active internal completion program

The 2026-09-13 code-first rebaseline distinguished implemented foundations from product/runtime completion. Do not restore broad completion claims without code, automated evidence and exact-environment evidence appropriate to the claim.

- [x] **Block B — monetization/entitlement/account control productization.** Core plan/subscription persistence and lifecycle state, replay-safe events, secure Web account control and caller-scoped billing APIs are joined by a cryptographically verified signed-provider ingress (`HMAC-SHA256 v1` generic adapter contract), deterministic provider snapshot reconciliation, ACTIVE-subscription-derived feature grants, fail-closed Action Gateway entitlement resolution, and real `companion` feature enforcement before `/v1/companion/ws` runtime activation. The legacy shared-token webhook is restricted to `manual`/`test` providers and cannot activate an external-provider subscription. This does **not** claim Stripe or another vendor-specific protocol: selecting/configuring a production payment provider and supplying its credentials remain Owner/external activation work.
- [ ] **Block C — Companion/WoW/player experience/voice productization.** The launcher has a real account/Companion runtime, passive WoW checkpoint ingestion and a read-only player overlay runtime. Core tokens remain in Electron main-process memory; a dedicated worker owns the Companion socket lifecycle; reconnect/backoff and heartbeats are bounded; browser-compatible socket auth avoids bearer-in-URL; paid access is checked before start and revalidated on live traffic; terminal entitlement revocation stops the worker. Classic/Retail addons persist bounded `SentinelDB` checkpoints; launcher ingestion uses a strict non-evaluating Lua-subset parser, disk-backed bounded FIFO and explicit `WOW_OBSERVATION_ACK`; Core normalizes accepted checkpoints through the conservative WoW adapter without granting `game:write`. Accepted checkpoints can now produce bounded server-authored `OVERLAY` presentations that are independently sanitized in worker and parent and rendered in a dedicated sandboxed, click-through, non-action Electron overlay. SavedVariables remain checkpoint evidence only, not realtime addon IPC. Remaining Block C work is actual voice-provider/device runtime integration, signed/packaged host acceptance and exact WoW target evidence.
- [ ] **Block D — observability/performance/resilience productization.** Privacy scrubbing, budget contracts and deterministic recovery matrices exist. End-to-end correlation propagation, deployed metrics/tracing composition, benchmark/failure-injection measurements and launcher/addon operational telemetry remain separate implementation/evidence targets where absent. Deterministic tests are not measured production performance.
- [ ] **Android client platform consolidation.** Multiple Android API surfaces still retain independent `HttpURLConnection` implementations. Consolidate only where the shared transport demonstrably improves coroutine I/O, timeout/header/request-ID/error/TLS/test-injection/retry discipline without changing server-authoritative security semantics.
- [x] **WoW-addon deterministic repository evidence.** Routine launcher CI now covers the strict SavedVariables parser, bounded durable queue, Companion envelope generation and static Classic/Retail passive snapshot contract. This is repository evidence only; exact WoW 3.3.5a/private-server L3 behavior remains environment-unverified.

## External / Owner-gated evidence

- [ ] Exact WoW 3.3.5a/private-server L3 validation; capabilities remain `UNVERIFIED` until exercised in that environment.
- [ ] Production payment/provider credentials and selected vendor-specific protocol/network integration, production database/ingress configuration and signing-key custody.
- [ ] Signed release-candidate execution, release tag/publication and live production deployment.
- [ ] Physical-device and real packaged Companion-host acceptance where not already tied to the selected release commit.
- [ ] Firebase Test Lab remains optional/non-blocking while GitHub Emulator instrumentation is the routine Android gate.

## Rules

- Do not mark `[x]` without direct evidence appropriate to the claim: exact SHA + PR/commit + CI Run ID and/or device/runtime evidence.
- Do not treat a stale document, old branch, old audit, or AI report as proof of current implementation.
- Distinguish **IMPLEMENTED**, **INTEGRATION-TESTED**, **SIMULATED**, **PRODUCTIZED**, **ENVIRONMENT-UNVERIFIED**, **MISSING** and **TECHNICAL-DEBT** when a broad feature spans more than one evidence level.
- Do not convert proposed thresholds or UNVERIFIED capabilities into achieved facts.
- Do not weaken security gates to obtain green CI.
- Prefer one coherent, independently testable large vertical per PR; split only when a block cannot remain safe and independently verifiable.
- Keep branches short-lived and return completed work to `main` promptly after exact-SHA validation.
- Documentation changes belong in the same logical PR when product/architecture meaning changes. Do not create generated HEAD-sync documentation changes for ordinary code commits.
- FTL usage must be quota-aware; prefer GitHub-hosted emulator for routine CI while the external FTL permission gate remains unresolved.

## Program order

`Verified foundation → Block B productization → Companion/launcher/WoW runtime → player/voice UX → observability/performance runtime → Android transport debt → Owner/external release gates`

### Definition of Done for every substantive block

A block is complete only when all applicable dimensions are addressed: implementation/contract, UX/design/visualization, security/privacy/failure, performance/resource, automated tests, runtime/device/integration evidence, and semantic documentation as applicable. Large blocks may be split into short-lived PRs, but each increment must remain independently testable, reviewable and integrable.

### Scope discipline

Do not expand into autonomous combat, pretend broad game/version support, or perform release/live deployment merely to make the roadmap look complete. Exact-environment capabilities remain `UNVERIFIED` until L3 evidence exists. Continue independent engineering when one external stream is blocked.
