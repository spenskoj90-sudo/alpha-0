export const tr=(pair,lang)=>Array.isArray(pair)?pair[lang==='ru'?0:1]:pair;
const page=(path,icon,title,lead,layout,sections)=>({path,icon,title,lead,layout,sections});
export const publicPages=[
page('/','intelligence',['В игре важен следующий шаг.','Your next move matters.'],['SENTINEL соединяет наблюдение, контекст и рекомендации. Решение остаётся за вами.','SENTINEL connects observation, context and recommendations. You remain in control.'],'home',[
 ['observe',['Сначала — факты','Start with facts'],['У каждого сигнала есть источник, версия игры и время. Недостающие данные остаются неизвестными.','Every signal has a source, game version and timestamp. Missing data stays unknown.']],
 ['recommendation',['Затем — понимание','Then understand'],['Рекомендация объясняет причину и ограничения. Вы видите, что наблюдалось и что было выведено.','Recommendations explain reasons and limitations. See what was observed and what was inferred.']],
 ['stop',['Всегда — ваш контроль','Always your control'],['Наблюдение можно остановить. Автоматическое выполнение игровых действий отключено.','Observation can be stopped. Automatic gameplay execution is disabled.']]]),
page('/features','builds',['Меньше догадок. Больше контекста.','Less guessing. More context.'],['От наблюдения до обоснованной рекомендации — без скрытых действий.','From observation to reasoned recommendations, without hidden actions.'],'features',[
 ['capture',['Наблюдение Android','Android observation'],['Диагностический OCR-пилот требует системного согласия на захват экрана. Он не доказывает универсальное распознавание игр.','The diagnostic OCR pilot requires system screen-capture consent. It does not establish universal game recognition.']],
 ['character',['Контекст персонажа','Character context'],['Билды, таланты и игровые рекомендации — направления развития. Проверяйте доступность для точной версии.','Builds, talents and game advice are development areas. Check availability for the exact version.']],
 ['overlay',['Companion и Overlay','Companion and Overlay'],['Отдельные поверхности для источников, состояния среды и компактных сообщений. Overlay остаётся информационным.','Dedicated surfaces for sources, host state and compact messages. Overlay remains presentation-only.']],
 ['security',['Прозрачность','Transparency'],['Согласие, свежесть, разрешения и Stop видимы рядом с действием.','Consent, freshness, permissions and Stop stay beside the action.']]]),
page('/games','games',['Каждая игра — точная среда.','Every game is an exact environment.'],['Название игры недостаточно: важны версия, источник и разрешения среды.','A game title is not enough: version, source and environment permissions matter.'],'catalog',[
 ['character',['World of Warcraft','World of Warcraft'],['Среда 3.3.5a — UNVERIFIED. Поддержка конкретного сервера и живого источника не подтверждена.','3.3.5a environment — UNVERIFIED. Specific server and live-source support is not verified.']],
 ['games',['Другие игры','Other games'],['Каталог расширяется только после проверки источников и совместимости. Общих обещаний поддержки нет.','The catalog grows only after source and compatibility checks. No blanket support promises.']]]),
page('/games/world-of-warcraft','character',['Ваш персонаж. Полный контекст.','Your character. In context.'],['Концепция игровых модулей WoW с явной границей между данными и планами.','A WoW module concept with an explicit boundary between evidence and plans.'],'wow',[
 ['builds',['Билды и таланты','Builds and talents'],['Планируется сравнение вариантов по роли и точной версии. Рабочие рекомендации для живой среды пока не подтверждены.','Role- and version-specific comparisons are planned. Live-environment recommendations are not yet verified.']],
 ['battle',['PvE / PvP','PvE / PvP'],['Раздельные сценарии, источники и ограничения. Никакого автоматического ввода в игру.','Separate scenarios, sources and limitations. No automatic game input.']],
 ['auction',['Профессии и экономика','Professions and economy'],['Аукцион, ресурсы и торговля — будущие модули. Демо не содержит реальных цен сервера.','Auction, resources and trade are future modules. The demo contains no real server prices.']]]),
page('/platforms/android','devices',['Помощник в вашем ритме.','Assistance at your pace.'],['Мобильный сценарий с системным согласием, видимым наблюдением и остановкой в один шаг.','A mobile journey with system consent, visible observation and a one-step stop.'],'android',[
 ['capture',['Только с разрешения','Only with permission'],['Android MediaProjection запрашивает доступ через системный диалог. Отказ и отзыв — полноценные состояния интерфейса.','Android MediaProjection requests access through a system dialog. Denial and revocation are first-class states.']],
 ['observe',['Диагностический пилот','Diagnostic pilot'],['OCR-сигнал не равен пониманию всей игры. Источник, время и неизвестные поля показываются явно.','An OCR signal is not complete game understanding. Source, time and unknown fields remain explicit.']],
 ['stop',['Остановить сейчас','Stop now'],['При остановке или отзыве разрешения наблюдение прекращается. Возобновление требует осознанного действия.','Stopping or revoking permission ends observation. Resuming requires an explicit action.']]]),
page('/platforms/windows','overlay',['Контекст рядом с игрой.','Context beside your game.'],['Launcher, Companion и Overlay спроектированы как разные рабочие поверхности.','Launcher, Companion and Overlay are designed as distinct working surfaces.'],'windows',[
 ['download',['Launcher','Launcher'],['Проверка пакета, прогресс, ошибка и восстановление. Публичная сборка ещё не объявлена доступной.','Package verification, progress, failure and recovery. A public build is not yet advertised as available.']],
 ['server',['Companion','Companion'],['Состояние хоста, версии коннектора, диагностика источника и ограничения видны в одной структуре.','Host state, connector versions, source diagnostics and limitations share one structure.']],
 ['overlay',['Overlay','Overlay'],['Три плотности: Minimal, Standard, Expanded. Компактные сообщения не скрывают Stop и устаревание источника.','Three densities: Minimal, Standard, Expanded. Compact messages retain Stop and source freshness.']]]),
page('/how-it-works','rotation',['От сигнала к решению.','From signal to decision.'],['Четыре понятных шага и проверяемые границы каждого.','Four clear steps, each with verifiable boundaries.'],'steps',[
 ['games',['01 / Выберите среду','01 / Choose the environment'],['Уточните игру, сборку и источник. Непроверенная среда не получает статус доступной.','Specify the game, build and source. An unverified environment never becomes available by assumption.']],
 ['confirmation',['02 / Разрешите наблюдение','02 / Allow observation'],['Разрешение ограничено сценарием и отзывается пользователем.','Permission is scoped to the journey and can be revoked.']],
 ['intelligence',['03 / Изучите контекст','03 / Review context'],['Факт, вывод и рекомендация отображаются раздельно.','Facts, inferences and recommendations are distinguished.']],
 ['stop',['04 / Решите или остановите','04 / Decide or stop'],['Игровое действие не выполняется автоматически. Stop всегда доступен.','Gameplay is not executed automatically. Stop stays available.']]]),
page('/security','security',['Контроль встроен в сценарий.','Control is part of the journey.'],['Разрешение не прячется в настройках. Оно объясняется в момент действия.','Permission is not buried in settings. It is explained at the point of action.'],'security',[
 ['capture',['Согласие','Consent'],['Захват экрана и микрофон требуют отдельных разрешений. Наблюдение и голос не равнозначны.','Screen capture and microphone use require separate consent. Observation and voice are distinct.']],
 ['unknown',['Неизвестное остаётся неизвестным','Unknown stays unknown'],['Устаревший источник не окрашивается как исправный. Нет данных — нет выдуманных показателей.','Stale sources are never presented as healthy. Missing data is never replaced by invented metrics.']],
 ['emergency-stop',['Остановка и отзыв','Stop and revoke'],['Потеря разрешений блокирует продолжение. Автоматическое исполнение остаётся отключено.','Permission loss prevents continuation. Automatic execution remains disabled.']]]),
page('/pricing','subscription',['Сначала ясность. Затем подписка.','Clarity before subscription.'],['Тарифы и коммерческие условия ещё не опубликованы. Этот раздел не принимает платежи.','Plans and commercial terms are not yet published. This page does not accept payments.'],'pricing',[
 ['account',['Индивидуальный сценарий','Individual use'],['Планируемый доступ к личным устройствам и рекомендациям. Состав и цена не утверждены.','Planned access to personal devices and recommendations. Scope and pricing are unapproved.']],
 ['devices',['Несколько устройств','Multiple devices'],['Планируется единый контекст Android и Windows. Лимиты и условия будут опубликованы отдельно.','Shared Android and Windows context is planned. Limits and terms will be published separately.']]]),
page('/faq','support',['Вопросы до первого запуска.','Questions before your first session.'],['Короткие ответы о доступности, данных и контроле.','Clear answers about availability, data and control.'],'faq',[
 ['games',['Все игры уже поддерживаются?','Are all games supported?'],['Нет. Доступность определяется для конкретной версии и среды; WoW 3.3.5a пока не подтверждён.','No. Availability is specific to version and environment; WoW 3.3.5a is not yet verified.']],
 ['automation',['Помощник играет за меня?','Does the assistant play for me?'],['Нет. Автоматическое выполнение отключено. Будущая активная помощь потребует отдельного разрешённого сценария.','No. Automatic execution is disabled. Future active assistance requires a separately permitted scenario.']],
 ['download',['Где скачать?','Where can I download it?'],['Публичные загрузки ещё не подтверждены. Раздел загрузок объясняет статус без фиктивных файлов.','Public downloads are not yet verified. The downloads page explains status without fake files.']],
 ['stop',['Как остановить наблюдение?','How do I stop observation?'],['Кнопкой Stop в активном сценарии либо отзывом системного разрешения.','Use Stop in the active journey or revoke system permission.']]]),
page('/support','support',['Поможем разобраться в состоянии.','Understand what happened.'],['Начните с диагностики: платформа, версия, источник и безопасный код ошибки.','Start with diagnostics: platform, version, source and a safe error code.'],'support',[
 ['diagnostics',['Что приложить','What to include'],['Версию приложения и ОС, последовательность шагов и обезличенный код ошибки. Не отправляйте токены или пароли.','App and OS versions, reproduction steps and a redacted error code. Never send tokens or passwords.']],
 ['offline',['Потеря соединения','Connection lost'],['Проверьте сеть, затем повторите подключение. Возобновление наблюдения требует вашего действия.','Check your network, then retry the connection. Resuming observation requires your action.']],
 ['security',['Разрешение отозвано','Permission revoked'],['Снова откройте сценарий захвата и прочитайте системный запрос. Это не ошибка подписки.','Reopen capture and review the system prompt. This is not a subscription error.']]]),
page('/about','intelligence',['Технология на стороне игрока.','Technology on the player’s side.'],['Мы проектируем помощника, которому не нужно передавать контроль вслепую.','We are designing assistance that does not require giving up control blindly.'],'about',[
 ['observe',['Наблюдать честно','Observe honestly'],['Показывать источник и ограничения важнее, чем создавать впечатление всезнания.','Showing sources and limitations matters more than appearing all-knowing.']],
 ['recommendation',['Объяснять решения','Explain decisions'],['Каждая рекомендация должна отвечать на вопрос «почему» и сохранять право отказаться.','Every recommendation should explain why and preserve the right to decline.']],
 ['confirmation',['Развиваться проверяемо','Develop with evidence'],['Концепция, сборка, работа на устройстве и принятие владельцем — разные стадии.','A concept, a build, device runtime and owner acceptance are distinct stages.']]]),
page('/download','download',['Проверенная сборка — прежде ссылки.','A verified build before a link.'],['Публичные Android APK и Windows installer пока не опубликованы как доступные.','Public Android APK and Windows installers are not yet published as available.'],'download',[
 ['devices',['Android','Android'],['Недоступно для публичной загрузки. Подписание, совместимость и проверка на целевых устройствах — отдельные этапы.','Unavailable for public download. Signing, compatibility and target-device checks are separate stages.']],
 ['server',['Windows','Windows'],['Недоступно для публичной загрузки. Требуются проверенный пакет, путь обновления и проверка на хосте.','Unavailable for public download. A verified package, update path and host acceptance are required.']]]),
page('/legal','quests',['Правила должны быть понятны.','Terms should be understandable.'],['Юридические документы требуют отдельного утверждения перед публикацией продукта.','Legal documents require separate approval before product publication.'],'legal',[
 ['security',['Конфиденциальность','Privacy'],['Предварительная структура: виды данных, цель обработки, сроки, удаление и права пользователя. Это не принятая юридическая политика.','Draft structure: data types, processing purpose, retention, deletion and user rights. This is not an adopted legal policy.']],
 ['confirmation',['Условия использования','Terms of use'],['Предварительная структура: разрешённая среда, ограничения, ответственность и прекращение доступа.','Draft structure: permitted environments, limitations, responsibility and termination.']],
 ['games',['Правила игры и оператора','Game and operator rules'],['Разрешение пользователя не заменяет правила конкретной игры, сервера и оператора.','User consent does not replace game, server and operator rules.']]])
];
const r=(path,icon,title,lead,kind)=>({path,icon,title,lead,kind});
export const productPages={
android:[
r('/splash','intelligence',['SENTINEL','SENTINEL'],['Наблюдать. Понимать. Решать.','Observe. Understand. Decide.'],'splash'),
r('/welcome','intelligence',['Играйте с пониманием.','Play with context.'],['Помощник объясняет. Вы решаете.','Your assistant explains. You decide.'],'welcome'),
r('/onboarding','observe',['Ваш контроль — с первого шага','Control from the first step'],['Наблюдение, рекомендации и действия имеют разные разрешения.','Observation, recommendations and actions have distinct permissions.'],'onboarding'),
r('/sign-in','account',['Вход в SENTINEL','Sign in to SENTINEL'],['Демо формы. Не вводите настоящий пароль.','Form demonstration. Do not enter a real password.'],'auth'),
r('/home','home',['Хороший момент для ясности.','A good moment for clarity.'],['Ваши источники, игры и следующий шаг.','Your sources, games and next step.'],'overview'),
r('/games','games',['Игры','Games'],['Доступность определяется точной версией.','Availability depends on the exact version.'],'games'),
r('/games/wow','character',['World of Warcraft','World of Warcraft'],['3.3.5a · среда не подтверждена','3.3.5a · environment unverified'],'game'),
r('/capture','capture',['Разрешение на наблюдение','Observation permission'],['Сначала объяснение. Затем системный запрос Android.','An explanation first. Then the Android system prompt.'],'capture'),
r('/games/wow/observation','observe',['Наблюдение','Observation'],['Диагностический OCR-пилот. Данные ниже — демо.','Diagnostic OCR pilot. Data below is demo content.'],'observation'),
r('/recommendations','recommendation',['Что стоит проверить','What to review next'],['Причина, источник и границы рекомендации.','Reason, source and recommendation limits.'],'recommendation'),
r('/games/wow/assistant','assistant',['Помощник под вашим контролем','Assistance under your control'],['Автоматическое выполнение отключено.','Automatic execution is disabled.'],'assistant'),
r('/battle','battle',['Состояние боя','Battle status'],['Живой источник не подтверждён.','Live source not verified.'],'battle'),
r('/games/wow/builds','builds',['Варианты билда','Build alternatives'],['Планируемый модуль, не готовые игровые советы.','Planned module, not live gameplay advice.'],'builds'),
r('/activity','activity',['История с объяснением','An explainable history'],['В демо нет серверного журнала.','The demo has no server activity log.'],'activity'),
r('/security','security',['Разрешения и контроль','Permissions and control'],['Наблюдение и микрофон разрешаются отдельно.','Observation and microphone use are consented separately.'],'security'),
r('/devices','devices',['Ваши устройства','Your devices'],['Нет подключённых реальных устройств.','No real devices connected.'],'devices'),
r('/subscription','subscription',['Доступ и подписка','Access and subscription'],['Права и тарифы не загружены.','Entitlements and plans are not loaded.'],'subscription'),
r('/settings','settings',['Настройки','Settings'],['Язык, движение и плотность интерфейса.','Language, motion and interface density.'],'settings'),
r('/diagnostics','diagnostics',['Диагностика','Diagnostics'],['Локальная демонстрация. Без секретов и сетевых запросов.','Local demonstration. No secrets or network requests.'],'diagnostics'),
r('/recovery','offline',['Вернём ясность','Restore clarity'],['Сначала восстановите источник, затем решите, продолжать ли.','Restore the source first, then decide whether to resume.'],'recovery')],
windows:[
r('/launcher','download',['Готовность к запуску','Ready to launch'],['Проверка среды прежде игрового сеанса.','Check the environment before a game session.'],'launcher'),
r('/overview','home',['Рабочее пространство игрока','Your player workspace'],['Источники, состояние хоста и игровой контекст.','Sources, host status and game context.'],'overview'),
r('/account','account',['Аккаунт','Account'],['Локальная демонстрация профиля.','Local profile demonstration.'],'account'),
r('/runtime','server',['Runtime','Runtime'],['Процесс, версия и состояние соединения.','Process, version and connection state.'],'runtime'),
r('/host','devices',['Хост','Host'],['Истинное состояние целевого Windows-хоста не проверено.','Actual target Windows-host state is unverified.'],'host'),
r('/games','games',['Игры','Games'],['Раздельная проверка каждой среды.','Each environment is verified separately.'],'games'),
r('/connectors','connection',['Игровые коннекторы','Game connectors'],['Совместимость не выводится из названия игры.','Compatibility is not inferred from a game title.'],'connectors'),
r('/wow/character','character',['Персонаж WoW','WoW character'],['Нет подтверждённого живого источника.','No verified live source.'],'character'),
r('/wow/builds','builds',['Билды','Builds'],['Сравнение вариантов планируется.','Alternative comparison is planned.'],'builds'),
r('/wow/talents','talents',['Таланты','Talents'],['Точная версия и специализация обязательны.','Exact version and specialization are required.'],'talents'),
r('/wow/pve','pve',['PvE','PvE'],['Контекст столкновения прежде рекомендации.','Encounter context before recommendations.'],'pve'),
r('/wow/pvp','pvp',['PvP','PvP'],['Режим, состав и правила среды.','Mode, composition and environment rules.'],'pvp'),
r('/wow/rotations','rotation',['Ротации','Rotations'],['Информационный сценарий. Автоввод отключён.','Advisory scenario. Automatic input disabled.'],'rotations'),
r('/wow/auction','auction',['Аукцион','Auction'],['Цены сервера не загружены.','Server prices are not loaded.'],'auction'),
r('/wow/professions','professions',['Профессии','Professions'],['Планируемый справочник ресурсов и рецептов.','Planned resource and recipe reference.'],'professions'),
r('/wow/quests','quests',['Квесты','Quests'],['Прогресс персонажа неизвестен.','Character progress is unknown.'],'quests'),
r('/wow/economy','resources',['Экономика','Economy'],['Нет истории операций или реальных цен.','No transaction history or real prices.'],'economy'),
r('/overlay','overlay',['Overlay','Overlay'],['Один сигнал за раз. Stop всегда рядом.','One signal at a time. Stop stays close.'],'overlay'),
r('/voice','voice',['Голос','Voice'],['Только push-to-talk, с отдельным согласием.','Push-to-talk only, with separate consent.'],'voice'),
r('/updates','updates',['Обновления','Updates'],['Сценарий загрузки, ошибки и отката.','Download, failure and rollback journey.'],'updates'),
r('/diagnostics','diagnostics',['Диагностика','Diagnostics'],['Состояние процесса не равно состоянию игры.','Process status is distinct from game status.'],'diagnostics')],
control:[
r('/sign-in','account',['Вход в Control','Sign in to Control'],['Изолированная демонстрация интерфейса авторизации.','Isolated authentication interface demonstration.'],'auth'),
r('/overview','home',['Обзор','Overview'],['Источники и доступ без скрытых допущений.','Sources and access without hidden assumptions.'],'overview'),
r('/intelligence','intelligence',['Интеллект','Intelligence'],['Факты, выводы и рекомендации.','Facts, inferences and recommendations.'],'intelligence'),
r('/games','games',['Игры','Games'],['Проверенные границы доступности.','Verified availability boundaries.'],'games'),
r('/activity','activity',['Активность','Activity'],['Локальная демонстрация журнала, не серверные события.','Local activity demonstration, not server events.'],'activity'),
r('/security','security',['Безопасность','Security'],['MFA, сеансы и отзыв разрешений.','MFA, sessions and permission revocation.'],'security'),
r('/devices','devices',['Устройства','Devices'],['Подключение и отзыв доступа требуют серверной проверки.','Pairing and revocation require server verification.'],'devices'),
r('/account','account',['Аккаунт','Account'],['Данные настоящего профиля не загружены.','Actual profile data not loaded.'],'account'),
r('/subscription','subscription',['Подписка','Subscription'],['Серверные права не определены.','Server entitlements unknown.'],'subscription'),
r('/billing','billing',['Платежи','Billing'],['Без checkout и реальных финансовых операций.','No checkout or real financial operations.'],'billing'),
r('/settings','settings',['Настройки','Settings'],['Предпочтения этого демонстрационного интерфейса.','Preferences for this demonstration interface.'],'settings'),
r('/support','support',['Поддержка','Support'],['Локальная подготовка обращения без отправки.','Prepare a support request locally without sending.'],'support'),
r('/diagnostics','diagnostics',['Диагностика','Diagnostics'],['Core не подключён. Не изображаем исправный сервер.','Core is disconnected. No simulated healthy server.'],'diagnostics'),
r('/admin','security',['Администрирование','Administration'],['Доступ закрыт: роль не подтверждена сервером.','Access denied: role not verified by the server.'],'admin')]
};
