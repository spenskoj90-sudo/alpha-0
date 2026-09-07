# Sentinel — Task Board

`TASKS.md` is a human-readable work queue. It is **not** a mirror of the repository and is never used as proof that an implementation exists. The repository, tests and exact CI/runtime evidence remain authoritative.

## Governance rule

**ACTIVE:** SENTINEL uses only GPT/ChatGPT as its AI engineering participant. The Human Owner remains the final decision-maker and sole owner of protected actions. GPT may autonomously execute ordinary engineering work through the canonical lifecycle and may merge after the exact-SHA gate passes.

## Completed architectural foundation on main

- [x] GPT-only autonomous engineering operating system and role model — active canonical governance in `docs/GPT_ONLY_AUTONOMOUS_ENGINEERING_OS.md` and related contracts.
- [x] Architecture foundation — Master Architecture v0.3, Game Adapter Contract v1 and Unified Game State v1 are present on main.
- [x] Adapter Registry / Capability Registry foundation — typed identity, capability status/evidence discipline, L3 availability enforcement, downgrade tracking, bounded normalized events and regression coverage are present on main.
- [x] Telemetry contract v1 — provider-neutral taxonomy/privacy/retention contract is present; runtime instrumentation remains a separate implementation stage.
- [x] Workflow cleanup — obsolete CURRENT_STATE self-sync workflow and remaining state-sync execution path were removed; routine validation is now focused on repository/build/security evidence.
- [x] Characters/game-state domain — Phase 1 + Phase 2 are complete on main.

## Current architectural implementation queue

These are the next candidate blocks. Before starting a block, GPT must baseline current `main` and verify that the gap still exists in code/tests.

- [ ] UGS validator — schema compatibility, ordering, idempotency, quality propagation and bounded staleness/expiry.
- [ ] Deterministic replay fixture format and first replay/regression test.
- [ ] Conservative first WoW adapter vertical slice against the v1 contracts.
- [ ] Companion protocol and explicit latency classes; then measurable end-to-end latency evidence.
- [ ] Policy Engine / Action Gateway boundary before any action-capable feature.
- [ ] Adapter/Companion observability implementation after the telemetry runtime path is ready.
- [ ] Simulation harness before expanding recommendation logic.
- [ ] Exact WoW 3.3.5a/private-server validation; keep capabilities UNVERIFIED until exact-environment L3 evidence exists.
- [ ] AI provider abstraction/routing and confidence/provenance implementation where the current codebase still lacks the required boundaries.
- [ ] Compatibility/version negotiation and overlay/voice interaction contracts where implementation evidence is absent.

## Active external / product work

- [ ] #11 — synchronize the Figma design system with the implementation; use Figma only when the corresponding UI work is active.
- [ ] #59 — Firebase Test Lab service-account GCS `storage.objects.create` permission; external/Owner infrastructure gate, not a reason to distort routine CI.
- [ ] #181 — reconcile architecture gap register, task board and implementation state under the repository-first documentation model.
- [ ] Measured performance baseline — retain as open until reproducible measurements are tied to current-main evidence.

## Later horizons

- [ ] User admin panel — after the MVP vertical slice requires it.
- [ ] PC/WoW launcher/Companion — implement as the architecture reaches the Companion stage, not as an isolated parallel subsystem.
- [ ] Production infrastructure — only when external users/production traffic justify it; live deployment remains Owner-gated.
- [ ] Feedback intake — GitHub Issues remains the canonical project feedback channel.

## Rules

- Do not mark `[x]` without direct evidence appropriate to the claim: exact SHA + PR/commit + CI Run ID and/or device/runtime evidence.
- Do not treat a stale document, old branch, old audit, or AI report as proof of current implementation.
- Do not convert proposed thresholds or UNVERIFIED capabilities into achieved facts.
- Do not weaken security gates to obtain green CI.
- Prefer one coherent, independently testable change set per PR; split only when a block cannot remain safe and independently verifiable.
- Keep branches short-lived and return completed work to `main` promptly after exact-SHA validation.
- Documentation changes belong in the same logical PR when product/architecture meaning changes. Do not create generated HEAD-sync documentation changes for ordinary code commits.
- FTL usage must be quota-aware; prefer GitHub-hosted emulator for routine CI while the external FTL permission gate remains unresolved.
