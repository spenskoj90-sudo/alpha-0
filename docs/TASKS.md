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
- [x] **#22 repository governance COMPLETE** — branch cleanup (groups 1–3) + required status checks on `main` (Owner 2026-09-01). Checks: Secret and image scan; Core tests and coverage; Android build and tests; Dependency audit; Web build; CodeQL; Build Android APK; P1 evidence artifacts; PostgreSQL integration and recovery; Repository verification.

## Текущие открытые items

- [ ] #107 — Backend: implement characters/game-state domain (per ARCHITECTURE_V4). OPEN / planning. Requires issue-level approval and intake before implementation.
- [~] #63 — P1 preventive hardening: **reconciled 2026-09-01**. Items 3–4 and most of 1/6 done on main; item 7 → #107; item 5 blocked on #59. Residual optional: deeper Postgres IDOR, Android process-death/revoke tests. Owner may close #63 if residual out of scope.
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
