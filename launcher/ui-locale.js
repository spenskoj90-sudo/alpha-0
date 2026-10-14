'use strict';

// Presentation-only locale. Runtime codes, provider/game payloads and evidence remain opaque.
(() => {
  const storageKey = 'sentinel.ui.locale';
  const ru = {
    'Refresh knowledge': 'Обновить знания',
    'Knowledge: signed out': 'Знания: вход не выполнен',
    'Knowledge: stopped': 'Знания: остановлены',
    'Knowledge: waiting for a verified game profile': 'Знания: ожидание подтверждённого игрового профиля',
    'Knowledge: verified presentation lease': 'Знания: подтверждённое разрешение на отображение',
    'Knowledge: network degraded; existing lease only': 'Знания: сеть ограничена; действует только прежнее разрешение',
    'Knowledge: access denied': 'Знания: доступ отклонён',
    'Knowledge: unavailable': 'Знания: недоступны',
    'FACT': 'ФАКТ', 'INFERENCE': 'ВЫВОД',
    'Confidence unknown · no calibrated estimate': 'Уверенность неизвестна · калиброванной оценки нет',
    'Skip to main content': 'Перейти к основному содержимому',
    'Companion navigation': 'Навигация Companion',
    'Overview': 'Обзор', 'Account': 'Аккаунт', 'Runtime': 'Среда выполнения',
    'Resilience': 'Устойчивость', 'Host configuration': 'Настройки компьютера',
    'Games': 'Игры', 'Adapters': 'Адаптеры', 'Voice': 'Голос', 'Overlay': 'Оверлей',
    'Diagnostics': 'Диагностика', 'Updates': 'Обновления',
    'Runtime control with explicit authority boundaries.': 'Управление средой с явными границами полномочий.',
    'Runtime summary': 'Сводка состояния среды', 'Authentication': 'Аутентификация',
    'WoW checkpoint': 'Контрольная точка WoW', 'Observation': 'Наблюдение', 'Connection': 'Соединение',
    'Email': 'Электронная почта', 'Password': 'Пароль', 'Sign in': 'Войти', 'Sign out': 'Выйти',
    'Authenticator or recovery code': 'Код аутентификатора или восстановления', 'Verify MFA': 'Проверить MFA',
    'Runtime lifecycle': 'Жизненный цикл среды',
    'Start and stop the authenticated Companion lifecycle. Runtime authority remains bounded by Core.': 'Запуск и остановка Companion после входа. Полномочия среды ограничены Core.',
    'Start Companion': 'Запустить Companion',
    'Observational presentation only · no autonomous game action': 'Только отображение наблюдений · без самостоятельных действий в игре',
    'Stop runtime': 'Остановить среду', 'Immediate local lifecycle control.': 'Немедленная локальная остановка.',
    'STOP / KILL SWITCH': 'СТОП / АВАРИЙНАЯ ОСТАНОВКА',
    'Stops Companion runtime; does not change account or device authority.': 'Останавливает Companion; не изменяет полномочия аккаунта или устройства.',
    'Connection state is explicit. Degraded or offline runtime never masquerades as healthy, and presentation can continue only inside the authority the runtime actually has.': 'Состояние соединения показано явно. Ограниченная или автономная среда не отображается как исправная. Отображение продолжается только в пределах действующих полномочий.',
    'Runtime resilience states': 'Состояния устойчивости среды',
    'Core connected and authoritative runtime active.': 'Core подключён, среда с подтверждёнными полномочиями активна.',
    'Core is reachable with reduced capability or delayed evidence.': 'Core доступен; возможности ограничены или данные задерживаются.',
    'Local observation may continue; remote authority is unavailable.': 'Локальное наблюдение может продолжаться; удалённые полномочия недоступны.',
    'No network authority. No server state is invented.': 'Нет сетевых полномочий. Состояние сервера не предполагается.',
    'Core URL': 'Адрес Core',
    'Connection settings are operational configuration, separate from account credentials.': 'Настройки соединения отделены от учётных данных аккаунта.',
    'Runtime adapter availability is authoritative from the signed-in Companion/Core session. Missing capability is shown as UNVERIFIED rather than healthy.': 'Доступность адаптеров подтверждается сессией Companion/Core. Неподтверждённая возможность отображается как UNVERIFIED.',
    'ADAPTER CAPABILITY: UNVERIFIED UNTIL RUNTIME REPORTS': 'ВОЗМОЖНОСТИ АДАПТЕРА: UNVERIFIED ДО ПОЛУЧЕНИЯ ДАННЫХ СРЕДЫ',
    'PRODUCT SURFACE / VOICE': 'ГОЛОСОВОЙ ИНТЕРФЕЙС', 'Voice is unavailable': 'Голос недоступен',
    'Sign in and start Companion to evaluate voice capability.': 'Войдите и запустите Companion для проверки голосовых возможностей.',
    'HOLD TO TALK': 'УДЕРЖИВАЙТЕ ДЛЯ РЕЧИ', 'RELEASE TO SEND': 'ОТПУСТИТЕ ДЛЯ ОТПРАВКИ', 'PROCESSING…': 'ОБРАБОТКА…',
    'Press and hold to capture. Release to send. Move away to cancel. Keyboard: hold Space or Enter.': 'Удерживайте для записи. Отпустите для отправки. Уведите указатель для отмены. Клавиатура: удерживайте пробел или Enter.',
    'Voice authority facts': 'Факты о голосовых полномочиях', 'MICROPHONE': 'МИКРОФОН', 'PROVIDER': 'ПРОВАЙДЕР',
    'ACTION AUTHORITY': 'ПОЛНОМОЧИЯ НА ДЕЙСТВИЯ', 'NONE · PRESENTATION ONLY': 'НЕТ · ТОЛЬКО ОТОБРАЖЕНИЕ',
    'CLOSED': 'ЗАКРЫТ (CLOSED)', 'UNAVAILABLE': 'НЕДОСТУПНО (UNAVAILABLE)', 'OPEN · HOLDING': 'ОТКРЫТ · УДЕРЖАНИЕ',
    'Consent copy': 'Я явно разрешаю запись микрофона только при активном push-to-talk. Микрофон не слушает постоянно. Согласие действует только в этой сессии и сбрасывается при выходе из аккаунта или закрытии окна.',
    'Voice locale': 'Язык распознавания речи',
    'VOICE: SIGNED OUT': 'ГОЛОС: SIGNED OUT', 'VOICE RESULT: IDLE': 'РЕЗУЛЬТАТ ГОЛОСА: IDLE',
    'Presentation only · no autonomous game action. Core may classify OBSERVE, ACKNOWLEDGE or DISMISS. Action-like language is rejected. Capture is bounded to 6 seconds and the configured byte limit.': 'Только отображение · без самостоятельных действий в игре. Core распознаёт OBSERVE, ACKNOWLEDGE или DISMISS. Команды действий отклоняются. Запись ограничена 6 секундами и настроенным размером данных.',
    'Presentation-only surface. Minimal, Standard and Expanded density preserve one meaningful message at a time; overlay never gains command authority.': 'Интерфейс только для отображения. Режимы Minimal, Standard и Expanded показывают одно значимое сообщение; оверлей не получает полномочий на команды.',
    'AUTHORITY: PRESENTATION ONLY': 'ПОЛНОМОЧИЯ: ТОЛЬКО ОТОБРАЖЕНИЕ',
    'Use connection and runtime state above as bounded diagnostics. Check diagnostics before changing host configuration when the runtime is degraded.': 'Используйте состояния соединения и среды выше для диагностики. При ограниченной работе проверьте диагностику перед изменением настроек компьютера.',
    'Update channel and package trust remain authoritative from the packaged runtime. No release state is inferred when updater evidence is absent.': 'Канал обновлений и доверие к пакету подтверждаются упакованной средой. Без данных обновления состояние релиза не предполагается.',
    'UPDATE STATE: UNVERIFIED IN THIS SESSION': 'СОСТОЯНИЕ ОБНОВЛЕНИЯ: UNVERIFIED В ЭТОЙ СЕССИИ',
    'Interface language': 'Язык интерфейса',
    'ACCOUNT: AUTHENTICATED / {entitlement}': 'АККАУНТ: AUTHENTICATED / {entitlement}',
    'COMPANION ENTITLED': 'COMPANION ДОСТУПЕН', 'COMPANION NOT ENTITLED': 'НЕТ ПРАВА НА COMPANION',
    'ACCOUNT: FIRST FACTOR VERIFIED / MFA REQUIRED': 'АККАУНТ: ПЕРВЫЙ ФАКТОР ПОДТВЕРЖДЁН / ТРЕБУЕТСЯ MFA',
    'ACCOUNT: SIGNED OUT': 'АККАУНТ: SIGNED OUT',
    'COMPANION: STOPPED': 'COMPANION: ОСТАНОВЛЕНО (STOPPED)',
    'WOW CHECKPOINT: STOPPED': 'КОНТРОЛЬНАЯ ТОЧКА WOW: ОСТАНОВЛЕНО (STOPPED)',
    'CONNECTION: STOPPED': 'СОЕДИНЕНИЕ: ОСТАНОВЛЕНО (STOPPED)',
    'COMPANION: {state}{reason}': 'COMPANION: {state}{reason}',
    'CONNECTION: {state}{reason}': 'СОЕДИНЕНИЕ: {state}{reason}',
    ' / QUEUE {depth}': ' / ОЧЕРЕДЬ {depth}',
    'WOW CHECKPOINT: {state}{depth}{reason}': 'КОНТРОЛЬНАЯ ТОЧКА WOW: {state}{depth}{reason}',
    ' / STT READY{tts}': ' / STT ГОТОВ{tts}', ' / TTS READY': ' / TTS ГОТОВ', ' / TTS UNAVAILABLE': ' / TTS НЕДОСТУПЕН',
    'STT READY · {tts}': 'STT ГОТОВ · {tts}', 'TTS READY': 'TTS ГОТОВ', 'TTS UNAVAILABLE': 'TTS НЕДОСТУПЕН',
    'VOICE: {state}{provider}{reason}': 'ГОЛОС: {state}{provider}{reason}',
    'Hold to talk': 'Удерживайте для речи',
    'The microphone opens only while you hold the control. Release to send.': 'Микрофон открывается только при удержании кнопки. Отпустите для отправки.',
    'Microphone consent required': 'Требуется согласие на микрофон',
    'Voice remains closed until you explicitly allow capture for this launcher session.': 'Микрофон закрыт, пока вы явно не разрешите запись для этой сессии.',
    'Voice provider unavailable': 'Голосовой провайдер недоступен',
    'Text and non-voice Companion functions remain available.': 'Текстовые и остальные функции Companion остаются доступны.',
    'Voice is not entitled': 'Нет права на голосовую функцию',
    'The current account does not have the required Companion voice capability.': 'У текущего аккаунта нет требуемого права на голосовую функцию Companion.',
    'Voice is signed out': 'Голос: вход не выполнен',
    'The current runtime cannot establish a voice provider boundary.': 'Текущая среда не может подтвердить доступность голосового провайдера.',
    'Voice is off': 'Голос выключен', 'The microphone is closed and no capture is active.': 'Микрофон закрыт; запись не ведётся.',
    'Voice · {state}': 'Голос · {state}', 'Runtime voice state is authoritative from Core.': 'Голосовое состояние подтверждается Core.',
    'USE ANDROID CLIENT': 'ИСПОЛЬЗУЙТЕ ANDROID-КЛИЕНТ', 'LAUNCH': 'ЗАПУСТИТЬ',
    'EXECUTABLE CONFIGURED': 'ИСПОЛНЯЕМЫЙ ФАЙЛ НАСТРОЕН', 'EXECUTABLE NOT CONFIGURED': 'ИСПОЛНЯЕМЫЙ ФАЙЛ НЕ НАСТРОЕН',
    'VOICE RESULT: {code}{mode}{feedback}': 'РЕЗУЛЬТАТ ГОЛОСА: {code}{mode}{feedback}',
    'Voice request understood': 'Голосовой запрос распознан', 'Voice request not accepted': 'Голосовой запрос не принят',
    'Core accepted the presentation intent. No autonomous game action was performed.': 'Core принял запрос отображения. Самостоятельных действий в игре не выполнялось.',
    'Core kept the request fail-closed: {code}.': 'Core отклонил запрос по принципу fail-closed: {code}.',
    'Capture canceled': 'Запись отменена', 'Nothing was sent. Hold the control again when you are ready.': 'Ничего не отправлено. Когда будете готовы, снова удерживайте кнопку.',
    'VOICE RESULT: CANCELED': 'РЕЗУЛЬТАТ ГОЛОСА: CANCELED',
    'Understanding request': 'Распознавание запроса', 'Capture ended. SENTINEL is evaluating the bounded voice request.': 'Запись завершена. SENTINEL обрабатывает ограниченный голосовой запрос.',
    'Listening…': 'Запись…', 'Release to send. Move away from the control to cancel without submitting.': 'Отпустите для отправки. Уведите указатель с кнопки для отмены без отправки.',
    'VOICE RESULT: CAPTURING / MAX {seconds}s': 'РЕЗУЛЬТАТ ГОЛОСА: CAPTURING / МАКС. {seconds} с',
    'Stop SENTINEL Companion runtime? Active local runtime and presentation state will stop.': 'Остановить SENTINEL Companion? Локальная среда и отображение будут остановлены.',
    'Voice capture unavailable': 'Голосовая запись недоступна',
    'Presentation only': 'Только отображение',
    'No authoritative overlay presentation · {state}': 'Нет подтверждённого сообщения оверлея · {state}',
    'Companion degraded · waiting for authoritative presentation.': 'Companion ограничен · ожидание подтверждённого сообщения.',
    'Waiting for Companion presentation.': 'Ожидание сообщения Companion.',
    'Confidence {percent}%': 'Уверенность {percent}%', 'source unavailable': 'источник недоступен',
    'Source: {source} · Source time: unavailable': 'Источник: {source} · Время источника: недоступно',
    'FACT': 'ФАКТ (FACT)', 'INFERENCE': 'ВЫВОД (INFERENCE)', 'RECOMMENDATION': 'РЕКОМЕНДАЦИЯ (RECOMMENDATION)',
    'STATUS': 'СОСТОЯНИЕ (STATUS)', 'ALERT': 'ПРЕДУПРЕЖДЕНИЕ (ALERT)',
  };
  const en = { 'Consent copy': 'I explicitly consent to microphone capture while push-to-talk is active. MICROPHONE IS NOT CONTINUOUSLY LISTENING. Consent is kept only for this launcher session and is cleared on sign-out/window close.' };
  const stateLabels = {
    VERIFIED: 'ПОДТВЕРЖДЕНО', ACTIVE: 'АКТИВНО', PENDING: 'ОЖИДАНИЕ', WARNING: 'ПРЕДУПРЕЖДЕНИЕ',
    DENIED: 'ОТКАЗАНО', REVOKED: 'ОТОЗВАНО', FAILED: 'ОШИБКА', UNKNOWN: 'НЕИЗВЕСТНО',
    UNAVAILABLE: 'НЕДОСТУПНО', STOPPED: 'ОСТАНОВЛЕНО', FULL: 'ПОЛНОЕ СОЕДИНЕНИЕ',
    DEGRADED: 'ОГРАНИЧЕННО', 'LOCAL-ONLY': 'ТОЛЬКО ЛОКАЛЬНО', OFFLINE: 'БЕЗ СЕТИ', CONNECTING: 'ПОДКЛЮЧЕНИЕ',
    READY: 'ГОТОВО', DELIVERED: 'ДОСТАВЛЕНО', WAITING_FOR_SAVEDVARIABLES: 'ОЖИДАНИЕ SAVEDVARIABLES',
    DEFERRED: 'ОТЛОЖЕНО', DELIVERING: 'ДОСТАВКА', SIGNED_OUT: 'ВХОД НЕ ВЫПОЛНЕН',
    CONSENT_REQUIRED: 'ТРЕБУЕТСЯ СОГЛАСИЕ', PROVIDER_UNAVAILABLE: 'ПРОВАЙДЕР НЕДОСТУПЕН',
    ENTITLEMENT_REQUIRED: 'ТРЕБУЕТСЯ ПРАВО ДОСТУПА', DISABLED: 'ВЫКЛЮЧЕНО',
  };
  function state(code) {
    return current === 'ru' && Object.hasOwn(stateLabels, code) ? `${stateLabels[code]} (${code})` : code;
  }
  const bindings = new Map();
  const listeners = new Set();
  const valid = value => value === 'ru' || value === 'en';
  let current = /^ru(?:-|$)/i.test(navigator.language || '') ? 'ru' : 'en';
  try { const saved = window.localStorage.getItem(storageKey); if (valid(saved)) current = saved; } catch { /* Storage may be unavailable in a sandboxed host. */ }
  function t(key, values = {}) {
    const english = Object.hasOwn(en, key) ? en[key] : key;
    const copy = current === 'ru' && Object.hasOwn(ru, key) ? ru[key] : english;
    return copy.replace(/\{([a-z]+)\}/gi, (token, name) => Object.hasOwn(values, name) ? String(typeof values[name] === 'function' ? values[name]() : values[name]) : token);
  }
  function text(node, key, values = {}) {
    if (!node) return;
    bindings.set(node, { key, values });
    node.textContent = t(key, values);
  }
  function apply() {
    document.documentElement.lang = current;
    for (const node of document.querySelectorAll('[data-i18n]')) node.textContent = t(node.getAttribute('data-i18n'));
    for (const node of document.querySelectorAll('[data-i18n-aria-label]')) node.setAttribute('aria-label', t(node.getAttribute('data-i18n-aria-label')));
    for (const [node, binding] of bindings) node.textContent = t(binding.key, binding.values);
    const selector = document.getElementById('ui-locale');
    if (selector) selector.value = current;
  }
  function setLocale(value, persist = true) {
    if (!valid(value)) return;
    current = value;
    if (persist) { try { window.localStorage.setItem(storageKey, current); } catch { /* Language still changes for this window. */ } }
    apply();
    for (const listener of listeners) listener();
  }
  window.sentinelUi = Object.freeze({ t, text, state, setLocale, locale: () => current, onChange: listener => listeners.add(listener) });
  document.getElementById('ui-locale')?.addEventListener('change', event => setLocale(event.target.value));
  window.addEventListener('storage', event => {
    if (event.key === storageKey && valid(event.newValue)) setLocale(event.newValue, false);
  });
  apply();
})();
