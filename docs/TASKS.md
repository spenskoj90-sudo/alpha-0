# Sentinel — Task Board

Формат: `[ ]` открыта, `[~]` в работе, `[x]` закрыта (указывай SHA/PR подтверждения).
Любой ИИ перед началом работы читает этот файл и берёт в работу только то, что здесь открыто. После завершения статус обновляется в том же PR.

## Закрыто на текущем main

- [x] Issue #12 / PR #109 — Supabase production database hosting boundary — merged at `7f795596df6d7d0362fa2113aafe74daa167cd81`.
- [x] Issue #7 / PR #105 — Sentry Android runtime observability — merged at `38184d3cb8b81c1ff2470327de104e1cc57e50a9`.
- [x] Issue #97 / PR #104 — bounded/evicted process-local rate-limit state — merged.
- [x] PR #100 — CI state-sync governance gate — merged as `1df91de661c8bb0946d68f1671cbabf5f9714455`.
- [x] PR #101 — repository hygiene / CURRENT_STATE synchronization — merged.
- [x] PR #103 — ReactiveCircus Android emulator runner pin to `v2.37.0` — merged.
- [x] PR #108 — docs(api): align API index with runtime — merged at `8af71e183f802fd156384268d128bef952100e07`.
- [x] PR #110 — docs sync CURRENT_STATE/TASKS after #109 — merged at `cd87d409935c8b59f7d760beab7588c1fbf8cd67`.
- [x] PR #111 — docs: record #22 branch cleanup decision — merged at `23ee6d2dbe0765159ce2dad9687dbd555c984cb5`.
- [x] PR #112 — docs: historical branch hygiene complete — merged at `516c53862ee3fbf715f5891495f74d9127b13026`.
- [x] PR #113 — docs: #22 branch protection complete; #63 backlog reconciled — merged at `4a2a987873e3c7248d1b18bd6711619c0eb80e80`.
- [x] PR #114 — docs: close #63 as completed; mark #107 next priority — merged at `657ceb80afc1ddfe7a38e2a3e2e72799ae7c22b8`.
- [x] **PR #115 / #107 Phase 1** — characters/game-state read domain — merged at `a261389f589c0d281c3f45a772fa6ee17abade42`. Store + GET characters/games/access + IDOR/auth + tests. Product CI green on exact HEAD (Build & Test `33599398555`, Security `33599398765`, Android `33599398549`, P1 Evidence `33599398550`).
- [x] **PR #116** — docs sync CURRENT_STATE/TASKS after Phase 1 — merged at `01a8539cb122f9a71f798b6ece3a26173bd2a469`.
- [x] **#22 repository governance COMPLETE** — branch cleanup (groups 1–3) + required status checks on `main` (Owner 2026-09-01).
- [x] **#63 P1 preventive hardening COMPLETE** — closed 2026-09-01 by Owner after D-019 reconciliation.

## Текущие открытые items

- [~] **#107 Phase 2** — event → character projection (ARCHITECTURE_V4 §5–6). **PR #117** implements projection from `/v1/events:batch` into `characters` via `apply_character_projections` + natural-key upsert. Types: `character.snapshot` / `character.upsert` / `character.state`. No public mutable character write API. After CI green + Owner merge + post-merge evidence sync, close #107.
- [ ] #59 — P0 Firebase Test Lab service-account GCS `storage.objects.create` permission. **External/operator blocker** (optional given emulator CI / D-013).
- [ ] #13 — define PostHog telemetry contract.
- [ ] #11 — synchronize Figma design system with implementation.
- [ ] #10 — establish measurable build/runtime performance baseline.
- [ ] #8 — SENTINEL baseline consistency audit.

## Дальше по плану

- [ ] Админ-панель для пользователя — после MVP.
- [ ] PC/WoW-клиент и лаунчер — после стабильного Android MVP.
- [ ] Инфраструктура/сервер — локальный/бесплатный пока нет внешних пользователей.
- [ ] Система приёма фидбека — GitHub Issues.

## Правила ведения файла

- Не отмечать `[x]` без прямой ссылки на SHA/PR/CI run.
- Не добавлять новые задачи без явного решения Owner.
- Governance/security acceptance gates не заменяются предположением.
- FTL usage must be quota-aware; prefer the GitHub-hosted emulator for routine CI.
- Current repository state is governed by `docs/SENTINEL_CURRENT_STATE.md`; historical documents are not current HEAD evidence.
