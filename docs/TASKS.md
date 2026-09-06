# Sentinel — Task Board

Формат: `[ ]` открыта, `[~]` в работе, `[x]` закрыта. Для `[x]` указываются SHA/PR/Run ID подтверждения.

## Governance rule

**ACTIVE:** инженерный контур SENTINEL использует только GPT/ChatGPT как AI-исполнителя. Human Owner остаётся финальным решающим лицом и единственным владельцем защищённых действий. Другие AI-системы не участвуют в инженерии, анализе, кодировании, тестировании, security, CI/CD, архитектуре или интеграции.

GPT может автономно вести обычную задачу через `DISCOVER → BASELINE → PLAN → IMPLEMENT → TEST → DIAGNOSE/FIX → REVIEW → COMMIT → PR → CI → ANALYZE → READY → INTEGRATE → POST-MERGE VERIFY`. Рутинные CI-сбои не являются остановкой.

## Закрыто / подтверждено на main

- [x] #167 / #168 — GPT-only autonomous engineering operating system — merged at `5a6668a46d92254e25bafbe6fe6d089a37733743`; PR HEAD `92e0eef1145541ff7cb55268fe7bb8117f4491c3`.
- [x] #165 / #171 — dedicated sync identity for CURRENT_STATE automation — merged after exact-SHA CI validation; superseded draft PR #166 closed.
- [x] #172 — CURRENT_STATE sync for `16d2d16542fa7f0d269af2083ac9282cedd35cc0` — merged as `ff67abcaa2544543fdcd218f56ff81e979801d06`; PR HEAD `613c7085a7131ad09acb0e6dce7933f964382c19`; required workflow Run IDs `34040984036`, `34040984012`, `34040983993`, `34040984006` all successful.
- [x] PR #170 — obsolete GITHUB_TOKEN-based CURRENT_STATE sync PR — closed as superseded.
- [x] PR #160/#162/#164 — stale pre-SYNC_PAT CURRENT_STATE sync PRs — closed as obsolete.
- [x] #12 / #109 — Supabase production database hosting boundary — merged.
- [x] #7 / #105 — Sentry Android runtime observability — merged; physical-device runtime path verified 2026-09-06.
- [x] #97 / #104 — bounded/evicted process-local rate-limit state — merged.
- [x] #100 — CI state-sync governance gate — merged.
- [x] #101 — repository hygiene / CURRENT_STATE synchronization — merged.
- [x] #103 — ReactiveCircus Android emulator runner pin — merged.
- [x] #108 — API documentation/runtime alignment — merged.
- [x] #107 — characters/game-state domain — Phase 1 + Phase 2 complete on main.
- [x] #22 — repository governance / branch cleanup / required checks — complete.
- [x] #63 — P1 preventive hardening — complete.
- [x] #8 — baseline consistency audit — complete.
- [x] #120 — deploy workflow trigger fix — merged.

## Текущая инженерная очередь

- [~] #173 — architecture foundation + Game Adapter Contract v1 + Unified Game State v1. Current HEAD: `e5701a1765706a2b71ff752bcb1febf7880ae54e`.
- [ ] #13 — define minimal PostHog/telemetry contract: event taxonomy, properties, privacy/retention and measurable engineering/product signals. No dashboard rollout until contract exists.
- [ ] #10 — establish measured performance baseline from reproducible CI/device evidence; current document is only a measurement contract and must not be marked complete until actual measurements are recorded.
- [ ] #11 — synchronize Figma design system with implementation; requires explicit design-to-code mapping and reusable tokens/components.
- [ ] #59 — Firebase Test Lab service-account GCS `storage.objects.create` permission. External/operator blocker; routine CI uses GitHub-hosted emulator instead.
- [ ] Release `SENTINEL_API_BASE_URL` — configure only when a reachable Core environment exists; production/live endpoint and release publication remain Owner-gated.

## Архитектурный / продуктовый хвост после #173

- [ ] Implement Adapter Registry + Capability Registry.
- [ ] Implement first conservative WoW adapter vertical slice against the new contracts.
- [ ] Implement deterministic replay fixture format and first replay test.
- [ ] Implement Unified Game State validation/expiry/idempotency in Core.
- [ ] Define Companion protocol and latency classes; then measure end-to-end latency.
- [ ] Define Policy Engine / Action Gateway boundary before any action-capable feature.
- [ ] Add adapter/companion observability after telemetry contract.
- [ ] Add simulation harness before expanding recommendation logic.
- [ ] Validate exact WoW 3.3.5a/private-server environment; keep unverified capabilities unverified until L3 evidence.

## Дальше

- [ ] User admin panel — after MVP vertical slice.
- [ ] PC/WoW launcher/companion — implement as the architecture reaches the Companion stage, not as an isolated parallel subsystem.
- [ ] Production infrastructure — only when external users/production traffic justify it.
- [ ] Feedback intake — GitHub Issues remains the canonical project feedback channel.

## Правила

- Не отмечать `[x]` без прямого evidence: SHA + PR + CI Run ID/device evidence where applicable.
- Не превращать proposed thresholds или UNVERIFIED capability into achieved facts.
- Не ослаблять security gates ради CI.
- FTL usage must be quota-aware; prefer GitHub-hosted emulator for routine CI.
- `docs/SENTINEL_CURRENT_STATE.md` is a state snapshot; Git `main` remains authoritative.
