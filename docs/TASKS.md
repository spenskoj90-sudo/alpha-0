# Sentinel — Task Board

Формат: `[ ]` открыта, `[~]` в работе (укажи кто и с какого момента), `[x]` закрыта (укажи SHA/PR подтверждения).
Любой ИИ перед началом работы читает этот файл и берёт в работу только то, что здесь открыто.
После завершения — сам обновляет статус здесь же, в том же коммите/PR, где сделана работа.

## Сейчас в фокусе

- [x] Слияние canonical-ветки sentinel-ftl-2026-08-13 в main без потери данных — закрыто, main на e37d557, 16/17 checks (FTL блокер — известное исключение)
- [x] P0-баг с обрывом TCP-соединения — закрыт. Причина НЕ в коде: клиент использует HttpURLConnection (не OkHttp), h2c/HTTP2-гипотеза опровергнута. Реальная причина — агрессивное ограничение батареи/фоновой сети на прошивке устройства пользователя (MIUI-подобная), из-за которого первый сетевой запрос приложения подвисал вплоть до readTimeout (15 сек) и завершался SocketTimeoutException, что на стороне сервера выглядело как BrokenPipeError при попытке записать ответ в уже недоступный сокет. Подтверждено эмпirически: отключение battery optimization для приложения в настройках Android → первый же запрос прошёл мгновенно, получен полный ответ, экран перешёл на 'Account authenticated — device flow next'. Диагностика проведена через временный stdlib-only auth-сервер и модифицированный AuthApi.kt (PR #34, смержен), раскрывающий реальный класс+текст исключения вместо общего NETWORK_ERROR.
- [~] Repository hygiene: 20+ веток в репозитории, часть устарела (agent/*, датированные sentinel/* branches, diagnostic branches). Составить список кандидатов на удаление, подтвердить с пользователем перед удалением любой ветки. 16 целевых веток проверены `ahead_by=0` относительно main e41d235; удаление не выполнено, поскольку доступный GitHub connector не предоставляет branch-delete operation.
- [x] p1-evidence.yml push-триггер обновлён с `sentinel-1.0.0-rc1-final` на `main` — применено в commit `3188aebeb0b717e06a18cf8c42fb50c4fad82f59` в PR #38.
- [x] Проверить дублирующуюся нумерацию миграций: server/migrations/002_p1_rls.sql и server/migrations/002_user_auth.sql оба имеют префикс 002 — подтвердить реальный порядок применения, переименовать при необходимости (например 002/003) — выполнено: `002_user_auth.sql` переименован в `003_user_auth.sql`, содержимое сохранено без изменений; PR будет содержать этот rename.
- [x] Обновить docs/SENTINEL_CURRENT_STATE.md и README.md: документы синхронизированы с текущим main `4a0fd8255e4b7beb065e73a254ebb72d3b8b4d11`; Login/Register и полный Android MVP nav graph подтверждены в дереве main; exact-head CI status API вернул пустой набор, поэтому старые CI runs не выданы за evidence для текущего SHA.
- [~] Разобраться с аномалией deploy.yml: текущий `.github/workflows/deploy.yml` содержит только `release.published`; точную историческую причину старых push-associated runs по текущему файлу установить не удалось, поэтому задача остаётся открытой до проверки истории Actions/workflow revisions.
- [~] Repository hygiene (расширено по итогам аудита Grok): 25 веток; "призрачные" workflow-записи в Actions без файлов в дереве main (ci.yml, codeql.yml, server-ci.yml и др.); дублирующиеся PROJECT_STATE.md — свести к одному. Дубликаты PROJECT_STATE.md консолидируются в этом PR; 16 целевых веток проверены fully merged, но их удаление заблокировано отсутствием branch-delete operation.
- [~] Device Details revoke/rotate: предыдущая запись PR #38 ошибочно утверждала, что backend endpoints уже существовали. В PR #40 реализованы реальные `/v1/devices/{device_id}/rotate` и `/v1/devices/{device_id}/revoke`, session-device linkage при `/v1/devices/bind`, ownership checks, fingerprint validation, session invalidation/replacement и Android persistence нового device/session. Security regression добавлен в `server/tests/test_device_session_lifecycle.py`; в ходе ревью обнаружен второй дублирующий route в `server/app/core/wow_api.py`: из-за `app.include_router(wow_router)` до routes `main.py` старый handler перехватывал `/v1/devices/{device_id}/rotate` и `/revoke`. Дублирующие routes и их старую rotate/revoke-логику удалены из `wow_api.py`; канонические handlers остаются в `main.py`. Диагностические `ACTUAL PAYLOAD` assert-сообщения удалены из теста. Закрыть после CI evidence PR #40.

## Дальше по плану (не начинать без явного решения пользователя)

- [x] Достроить Android-навигацию: Login/Register (готово) → Device Setup (PR #36) → Dashboard → Device Details → Game Details — реализовано в PR #37, head `530e476421e0bcc4d42b5908ce63483234edd83f`; Security #126 PASS, P1 Evidence #37 PASS, ALPHA-0 Android CI #893 PASS, Build & Test #206 PASS по всем code/build jobs; известный FTL/GCP job остаётся инфраструктурным blocker.
- [ ] UI/визуальный дизайн — намеренно отложен до стабилизации основных экранов
- [ ] Админ-панель для пользователя (статистика, нагрузка, capacity) — после MVP, не параллельно
- [ ] PC/WoW-клиент и лаунчер — не начинать, пока Android MVP не протестирован вручную пользователем
- [ ] Инфраструктура/сервер — оставаться на бесплатном/локальном варианте, пока нет реальных внешних пользователей
- [ ] Система приёма фидбека/багов от тестеров — предложен вариант: GitHub Issues в этом же репозитории
- [ ] Добавить в онбординг приложения мягкий запрос на исключение из battery optimization (аналог 'Ignore battery optimizations' через ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS или как минимум подсказку с инструкцией). Обнаружено при диагностике P0 TCP-бага: агрессивные прошивки (MIUI и подобные) придерживают сетевую активность приложения по умолчанию, что выглядит как случайные сетевые сбои для пользователя. Не блокирует MVP, но важно для качества первого впечатления при реальном тестировании.

## Правила ведения файла
- Не отмечать `[x]` без прямой ссылки на SHA/PR/CI run — устные "готово" не считаются (см. Evidence Integrity Protocol).
- Не добавлять сюда задачи из "Дальше по плану" в работу без явного решения пользователя — история проекта показывает, что параллельный захват лишних задач и есть причина затора.
