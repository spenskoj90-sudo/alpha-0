# Sentinel — Task Board

Формат: `[ ]` открыта, `[~]` в работе (укажи кто и с какого момента), `[x]` закрыта (укажи SHA/PR подтверждения).
Любой ИИ перед началом работы читает этот файл и берёт в работу только то, что здесь открыто.
После завершения — сам обновляет статус здесь же, в том же коммите/PR, где сделана работа.

## Сейчас в фокусе

- [x] **Grok**, 2026-08-27. Release-hardening pass on `sentinel/release-hardening-2026-08-27` HEAD `5439e715175eb8444c12aa85b81cbb0e9385b2b3` (PR #68). Admin lockout, RLS negatives (non-owner probe), concurrent refresh (Memory + Postgres), integrity policy/nonce, StrongBox TEE fallback, emulator CI. **Exact-head CI:** Build & Test run `33069908061` SUCCESS (all product jobs including emulator + signed release APK). Security, P1 Evidence, ALPHA-0 Android CI PASS. **Not product state until merge + Owner/Final Integrator accept.**

- [x] Слияние canonical-ветки sentinel-ftl-2026-08-13 в main без потери данных — исторически закрыто; последующие main commits являются каноническим состоянием.
- [x] P0 TCP-баг с обрывом TCP-соединения — закрыто PR #34 + real-device evidence.
- [x] Repository hygiene (16 целевых веток) — 2026-08-22.
- [x] p1-evidence.yml push-триггер — `3188aebeb0b717e06a18cf8c42fb50c4fad82f59`.
- [x] Дублирующаяся нумерация миграций — `003_user_auth.sql`.
- [x] Device Details revoke/rotate — PR #40 lineage.
- [x] UI / финальная Sentinel design system — PR #46.
- [~] Аномалия deploy.yml: файл содержит только `release.published`. Push-associated FAIL runs are non-product ghost records; origin of historical registration remains open but does not block product release.
- [~] Repository hygiene — delete-candidates with `ahead_by=0` documented; deletion deferred (no branch-delete without Owner).
- [~] PostgreSQL runtime persistence: CI path covered; **live/deployment SoR evidence remains open.**
- [x] Security authorization: `POST /v1/recommendations` — main lineage + negative regression.
- [ ] **CI governance: required status-check contexts for protected `main`.** Live metadata shows protection but empty named required checks. Owner/settings action; agents must not change governance without approval.
- [x] Stale PR cleanup batches #1 and #2 — 2026-08-23.
- [x] Battery optimization onboarding — PR #51; real-device UX still manual.
- [x] Postgres/deployment evidence hardening — PR #57.
- [~] **Firebase Test Lab / Tool Results API:** still blocked on GCP API enablement. Emulator path is the active CI instrumentation gate (PR #68).

## Дальше по плану

- [x] Android-навигация — PR #37 lineage.
- [x] UI/визуальный дизайн — PR #46.
- [x] Battery optimization onboarding — PR #51.
- [ ] Админ-панель для пользователя — после MVP.
- [ ] PC/WoW-клиент и лаунчер — после стабильного Android MVP.
- [ ] Инфраструктура/сервер — локальный/бесплатный пока нет внешних пользователей.
- [ ] Система приёма фидбека — GitHub Issues.

## Правила ведения файла
- Не отмечать `[x]` без прямой ссылки на SHA/PR/CI run.
- Не добавлять задачи из "Дальше по плану" без явного решения Owner.
- Governance/security acceptance gates не заменяются предположением.
- FTL usage must be quota-aware; prefer emulator for routine CI.
