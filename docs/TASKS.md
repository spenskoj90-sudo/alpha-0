# Sentinel — Task Board

Формат: `[ ]` открыта, `[~]` в работе (укажи кто и с какого момента), `[x]` закрыта (укажи SHA/PR подтверждения).
Любой ИИ перед началом работы читает этот файл и берёт в работу только то, что здесь открыто.
После завершения — сам обновляет статус здесь же, в том же коммите/PR, где сделана работа.

## Сейчас в фокусе

- [x] Слияние canonical-ветки sentinel-ftl-2026-08-13 в main без потери данных — закрыто, main на e37d557, 16/17 checks (FTL блокер — известное исключение)
- [ ] Исправить P0-баг: Android-клиент обрывает TCP-соединение при получении ответа от локального тестового сервера (BrokenPipeError). Гипотеза: OkHttp ожидает HTTPS/TLS и обрывает соединение на plaintext-ответе — не подтверждено, требует проверки в коде клиента.
- [x] Repository hygiene (16 целевых веток): **Grok**, 2026-08-22. Перепроверка против актуального main `b27040b056136ba1e92ad5b4a5e4b33f18218078`. Все 16 имён уже отсутствовали в `list_branches` (ранее удалены вручную/ранее): `agent/sentinel-complete-platform`, `backup/canonical-before-merge-2026-08-19`, `backup/main-before-merge-2026-08-19`, `ci-validation-main-2026-08-19`, `docs/ai-roles-tasks-2026-08-19`, `docs/grok-audit-tasks-2026-08-19-v2`…`v6`, `docs/grok-audit-tasks-v2-2026-08-19`, `p1-close-2026-08-13`, `sentinel/android-http-hardening-main-2026-08-17`, `sentinel/evidence-protocol-v2`, `sentinel-ftl-repair-2026-08-14`, `sentinel-user-auth`. Удалять через API было нечего. Evidence: PR этой задачи + branch list на main `b27040b0`. Примечание: connector по-прежнему не предоставляет `delete_branch`; для уже отсутствующих refs это не блокер.
- [x] p1-evidence.yml push-триггер обновлён с `sentinel-1.0.0-rc1-final` на `main` — применено в commit `3188aebeb0b717e06a18cf8c42fb50c4fad82f59` в PR #38.
- [x] Проверить дублирующуюся нумерацию миграций: server/migrations/002_p1_rls.sql и server/migrations/002_user_auth.sql оба имеют префикс 002 — подтвердить реальный порядок применения, переименовать при необходимости (например 002/003) — выполнено: `002_user_auth.sql` переименован в `003_user_auth.sql`, содержимое сохранено без изменений; PR будет содержать этот rename.
- [x] Обновить docs/SENTINEL_CURRENT_STATE.md и README.md: документы синхронизированы с текущим main `4a0fd8255e4b7beb065e73a254ebb72d3b8b4d11`; Login/Register и полный Android MVP nav graph подтверждены в дереве main; exact-head CI status API вернул пустой набор, поэтому старые CI runs не выданы за evidence для текущего SHA.
- [~] Разобраться с аномалией deploy.yml: текущий `.github/workflows/deploy.yml` содержит только `release.published`; точную историческую причину старых push-associated runs по текущему файлу установить не удалось, поэтому задача остаётся открытой до проверки истории Actions/workflow revisions.
- [~] Repository hygiene (расширено по итогам аудита Grok): 25→~26 веток на 2026-08-22; "призрачные" workflow-записи в Actions без файлов в дереве main (ci.yml, codeql.yml, server-ci.yml и др.); дублирующиеся PROJECT_STATE.md — свести к одному. **16-branch cleanup closed** (см. пункт выше). Остаток: ghost workflows / PROJECT_STATE consolidation — не закрыт.
- [~] Device Details revoke/rotate: предыдущая запись PR #38 ошибочно утверждала, что backend endpoints уже существовали. В PR #40 реализованы реальные `/v1/devices/{device_id}/rotate` и `/v1/devices/{device_id}/revoke`, session-device linkage при `/v1/devices/bind`, ownership checks, fingerprint validation, session invalidation/replacement и Android persistence нового device/session. Security regression добавлен в `server/tests/test_device_session_lifecycle.py`; в ходе ревью обнаружен второй дублирующий route в `server/app/core/wow_api.py`: из-за `app.include_router(wow_router)` до routes `main.py` старый handler перехватывал `/v1/devices/{device_id}/rotate` и `/revoke`. Дублирующие routes и их старую rotate/revoke-логику удалены из `wow_api.py`; канонические handlers остаются в `main.py`. Диагностические `ACTUAL PAYLOAD` assert-сообщения удалены из теста. Закрыть после CI evidence PR #40.

## Дальше по плану (не начинать без явного решения пользователя)

- [x] Достроить Android-навигацию: Login/Register (готово) → Device Setup (PR #36) → Dashboard → Device Details → Game Details — реализовано в PR #37, head `530e476421e0bcc4d42b5908ce63483234edd83f`; Security #126 PASS, P1 Evidence #37 PASS, ALPHA-0 Android CI #893 PASS, Build & Test #206 PASS по всем code/build jobs; известный FTL/GCP job остаётся инфраструктурным blocker.
- [~] UI/визуальный дизайн — реализация визуальной системы «Пункт наблюдения» в PR #45, текущий head `8c65da63ce6cbb5c47d2497a8159f53e5705035b`; предыдущий Android CI #977 был сломан только диагностическими compile errors, исправления запушены; текущие Security #157, P1 Evidence #67, Android CI #987, Build & Test #237 запущены, evidence pending.
- [ ] Админ-панель для пользователя (статистика, нагрузка, capacity) — после MVP, не параллельно
- [ ] PC/WoW-клиент и лаунчер — не начинать, пока Android MVP не протестирован вручную пользователем
- [ ] Инфраструктура/сервер — оставаться на бесплатном/локальном варианте, пока нет реальных внешних пользователей
- [ ] Система приёма фидбека/багов от тестеров — предложен вариант: GitHub Issues в этом же репозитории

## Правила ведения файла
- Не отмечать `[x]` без прямой ссылки на SHA/PR/CI run — устные "готово" не считаются (см. Evidence Integrity Protocol).
- Не добавлять сюда задачи из "Дальше по плану" в работу без явного решения пользователя — история проекта показывает, что параллельный захват лишних задач и есть причина затора.
