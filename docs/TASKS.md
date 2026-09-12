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
- [x] PASS 5 — Companion transport/session/TLS hardening, peer authorization ordering, kill switch and bounded observability seams.
- [x] PASS 6 — Android Keystore device proof and retry-safe device-session event ingestion.

## Active completion program

Before each block, inspect current `main` and keep external/runtime claims evidence-scoped.

- [ ] **Block A — repository/CI/supply-chain/governance truth:** remove release signing from routine PR CI; make web tests and lockfile deterministic gates; pin Actions by immutable SHA; strengthen repository verification; reconcile active/historical documentation, release terminology/version metadata and remote-branch cleanup classification.
- [ ] **Block B — monetization/entitlement/account control:** canonical plan/product model, persistent lifecycle, provider/webhook/reconciliation boundaries, replay/idempotency/audit, API/web/account surfaces and security/PostgreSQL tests. Production payment credentials remain Owner-only.
- [ ] **Block C — Companion/WoW/player experience/voice:** packaged Companion composition, durable bounded local queue/cache, recovery/backpressure, strongest legitimate WoW bridge, presentation/overlay and safe provider-neutral STT/TTS boundaries. No recommendation or voice path bypasses the Action Gateway.
- [ ] **Block D — observability/performance/resilience/RC readiness:** cross-component correlation and privacy scrubbing, measurable budgets, failure/recovery matrix, final security review, documentation agreement and all automatable acceptance evidence.

## External / Owner-gated evidence

- [ ] Exact WoW 3.3.5a/private-server L3 validation; capabilities remain `UNVERIFIED` until exercised in that environment.
- [ ] Production payment/provider credentials, production database/ingress configuration and signing-key custody.
- [ ] Signed release-candidate execution, release tag/publication and live production deployment.
- [ ] Physical-device and real Companion-host acceptance where not already tied to the selected release commit.
- [ ] Firebase Test Lab remains optional/non-blocking while GitHub Emulator instrumentation is the routine Android gate.

## Rules

- Do not mark `[x]` without direct evidence appropriate to the claim: exact SHA + PR/commit + CI Run ID and/or device/runtime evidence.
- Do not treat a stale document, old branch, old audit, or AI report as proof of current implementation.
- Do not convert proposed thresholds or UNVERIFIED capabilities into achieved facts.
- Do not weaken security gates to obtain green CI.
- Prefer one coherent, independently testable change set per PR; split only when a block cannot remain safe and independently verifiable.
- Keep branches short-lived and return completed work to `main` promptly after exact-SHA validation.
- Documentation changes belong in the same logical PR when product/architecture meaning changes. Do not create generated HEAD-sync documentation changes for ordinary code commits.
- FTL usage must be quota-aware; prefer GitHub-hosted emulator for routine CI while the external FTL permission gate remains unresolved.

## Program order

`Completed passes 1–6 → Block A → Block B → Block C → Block D → Owner/external release gates`

### Definition of Done for every substantive block

A block is complete only when all applicable dimensions are addressed: implementation/contract, UX/design/visualization, security/privacy/failure, performance/resource, automated tests, runtime/device/integration evidence, and semantic documentation as applicable. Large blocks may be split into short-lived PRs, but each increment must remain independently testable, reviewable and integrable.

### Scope discipline

Do not expand into autonomous combat, pretend broad game/version support, or perform release/live deployment merely to make the roadmap look complete. Exact-environment capabilities remain `UNVERIFIED` until exact L3 evidence exists. Continue independent engineering when one external stream is blocked.
