'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function openLocale({ language = 'ru-RU', saved = null, denied = false } = {}) {
  const filename = path.join(__dirname, '..', 'ui-locale.js');
  assert.equal(fs.existsSync(filename), true, 'local UI locale module must exist');
  const events = {};
  const selector = { value: '', addEventListener(name, handler) { events[name] = handler; } };
  const document = { documentElement: { lang: 'en' }, getElementById: () => selector, querySelectorAll: () => [] };
  const storage = { getItem() { if (denied) throw Error('denied'); return saved; }, setItem(key, value) { if (denied) throw Error('denied'); saved = value; } };
  const window = { localStorage: storage, addEventListener(name, handler) { events[name] = handler; } };
  vm.runInNewContext(fs.readFileSync(filename, 'utf8'), { window, document, navigator: { language } });
  return { ui: window.sentinelUi, document, selector, events, stored: () => saved };
}

test('UI locale follows saved choice, otherwise browser language, and tolerates denied storage', () => {
  assert.equal(openLocale().ui.locale(), 'ru');
  assert.equal(openLocale({ saved: 'en' }).ui.locale(), 'en');
  assert.equal(openLocale({ language: 'fr-FR', saved: 'invalid' }).ui.locale(), 'en');
  const denied = openLocale({ denied: true });
  denied.ui.setLocale('en');
  assert.equal(denied.document.documentElement.lang, 'en');
});

test('locale switch updates bound runtime copy, persists and keeps raw evidence opaque', () => {
  const { ui, document, stored } = openLocale();
  const node = { textContent: '' };
  ui.text(node, 'COMPANION: {state}{reason}', { state: 'DEGRADED', reason: ' / NETWORK_TIMEOUT' });
  assert.equal(node.textContent, 'COMPANION: DEGRADED / NETWORK_TIMEOUT');
  ui.setLocale('en');
  assert.equal(node.textContent, 'COMPANION: DEGRADED / NETWORK_TIMEOUT');
  assert.equal(document.documentElement.lang, 'en');
  assert.equal(stored(), 'en');
  assert.equal(ui.t('Unknown provider payload'), 'Unknown provider payload');
  assert.equal(ui.t('Source: {source} · Source time: unavailable', { source: '<Core>' }), 'Source: <Core> · Source time: unavailable');
});

test('Russian voice consent, intelligence grammar and controls preserve meaning and codes', () => {
  const { ui } = openLocale();
  assert.equal(ui.t('HOLD TO TALK'), 'УДЕРЖИВАЙТЕ ДЛЯ РЕЧИ');
  assert.equal(ui.t('FACT'), 'ФАКТ (FACT)');
  assert.equal(ui.t('INFERENCE'), 'ВЫВОД (INFERENCE)');
  assert.equal(ui.t('RECOMMENDATION'), 'РЕКОМЕНДАЦИЯ (RECOMMENDATION)');
  assert.match(ui.t('Consent copy'), /не слушает постоянно/i);
  assert.equal(ui.t('Core kept the request fail-closed: {code}.', { code: 'ACTION_GATEWAY_REQUIRED' }), 'Core отклонил запрос по принципу fail-closed: ACTION_GATEWAY_REQUIRED.');
});

function openSurface(rendererName) {
  const nodes = new Map();
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, { id, textContent: '', value: '', className: '', dataset: {}, children: [], disabled: false, checked: false,
      setAttribute(name, value) { this[name] = value; }, getAttribute(name) { return this[name]; },
      addEventListener() {}, append(...items) { this.children.push(...items); }, appendChild(item) { this.children.push(item); },
      replaceChildren() { this.children = []; }, removeChild() { this.children.shift(); }, get firstChild() { return this.children[0]; }, style: {} });
    return nodes.get(id);
  }
  let snapshotHandler;
  let voiceHandler;
  let knowledgeHandler;
  let consentCalls = 0;
  const document = { documentElement: { lang: 'en' }, getElementById: node, querySelectorAll: () => [], querySelector: () => node('panel'), createElement: tag => node(Symbol(tag)) };
  const window = { localStorage: { getItem: () => null, setItem() {} }, addEventListener() {},
    sentinelOverlay: { onSnapshot(handler) { snapshotHandler = handler; } },
    sentinel: { onCompanionStatus() {}, onAccountStatus() {}, onWowCheckpointStatus() {}, onVoiceStatus(handler) { voiceHandler = handler; },
      onKnowledgeStatus(handler) { knowledgeHandler = handler; }, knowledgeStatus: async () => ({ state: 'SIGNED_OUT', actionAuthority: false }),
      accountStatus: async () => ({ session: null }), companionStatus: async () => ({ state: 'STOPPED' }), voiceStatus: async () => ({ state: 'SIGNED_OUT' }), catalog: async () => [], getConfig: async () => ({}),
      setVoiceConsent: async () => { consentCalls += 1; } } };
  const context = vm.createContext({ window, document, navigator: { language: 'ru-RU' }, console });
  for (const file of ['ui-locale.js', rendererName]) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', file), 'utf8'), context);
  return { window, document, node, render: snapshot => snapshotHandler(snapshot), voice: snapshot => voiceHandler(snapshot),
    knowledge: snapshot => knowledgeHandler(snapshot), consentCalls: () => consentCalls };
}

test('knowledge waiting/unknown states remain truthful and locale changes grant no authority', async () => {
  const surface = openSurface('renderer.js');
  await new Promise(resolve => setImmediate(resolve));
  surface.knowledge({ state: 'WAITING_FOR_VERIFIED_PROFILE', actionAuthority: false });
  assert.match(surface.node('knowledge-status').textContent, /ожидание подтверждённого/);
  assert.equal(surface.node('knowledge-refresh').disabled, true);
  surface.window.sentinelUi.setLocale('en');
  assert.equal(surface.node('knowledge-status').textContent, 'Knowledge: waiting for a verified game profile');
  assert.equal(surface.node('knowledge-refresh').disabled, true);
  surface.knowledge({ state: 'constructor' });
  assert.equal(surface.node('knowledge-status').textContent, 'Knowledge: unavailable');
  assert.equal(surface.node('knowledge-refresh').disabled, true);
});

test('Companion locale switch preserves signed-out and disabled voice authority without making IPC calls', async () => {
  const surface = openSurface('renderer.js');
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(surface.node('account-status').textContent, 'АККАУНТ: SIGNED OUT');
  assert.equal(surface.node('voice-ptt').textContent, 'УДЕРЖИВАЙТЕ ДЛЯ РЕЧИ');
  assert.equal(surface.node('voice-ptt').disabled, true);
  assert.equal(surface.node('voice-consent').checked, false);
  surface.window.sentinelUi.setLocale('en');
  assert.equal(surface.node('account-status').textContent, 'ACCOUNT: SIGNED OUT');
  assert.equal(surface.node('voice-ptt').textContent, 'HOLD TO TALK');
  assert.equal(surface.node('voice-ptt').disabled, true);
  assert.equal(surface.consentCalls(), 0);
});

test('Overlay localizes its labels and missing evidence while keeping provider presentation and provenance unchanged', () => {
  const surface = openSurface('overlay-renderer.js');
  surface.render({ companion: { state: 'DEGRADED' } });
  assert.equal(surface.node('presentations').children[0].textContent, 'Companion ограничен · ожидание подтверждённого сообщения.');
  surface.render({ companion: { state: 'ACTIVE' }, overlayDensity: 'Expanded', presentations: [{ channel: 'OVERLAY', kind: 'RECOMMENDATION', text: '<opaque game text>', confidence: 0.75, provenance: ['sentinel-core', 'evidence-id'] }] });
  const children = surface.node('presentations').children[0].children;
  assert.equal(children[0].textContent, 'РЕКОМЕНДАЦИЯ (RECOMMENDATION)');
  assert.equal(children[1].textContent, '<opaque game text>');
  assert.equal(children[2].textContent, 'Уверенность 75%');
  assert.equal(children[3].textContent, 'Источник: sentinel-core · evidence-id · Время источника: недоступно');
  surface.window.sentinelUi.setLocale('en');
  const translated = surface.node('presentations').children[0].children;
  assert.equal(translated[0].textContent, 'RECOMMENDATION');
  assert.equal(translated[1].textContent, '<opaque game text>');
  assert.equal(translated[2].textContent, 'Confidence 75%');
});


test('state labels are readable in Russian while canonical codes remain present and unknown states remain opaque', () => {
  const { ui } = openLocale();
  assert.equal(ui.state('DEGRADED'), 'ОГРАНИЧЕННО (DEGRADED)');
  assert.equal(ui.state('UNKNOWN'), 'НЕИЗВЕСТНО (UNKNOWN)');
  assert.equal(ui.state('NEW_PROVIDER_STATE'), 'NEW_PROVIDER_STATE');
  ui.setLocale('en');
  assert.equal(ui.state('DEGRADED'), 'DEGRADED');
});

test('unknown translation keys use safe literal fallback, including inherited property names', () => {
  const { ui } = openLocale();
  for (const key of ['constructor', '__proto__', 'toString']) assert.equal(ui.t(key), key);
});

test('Overlay follows a saved language change without a control or IPC mutation', () => {
  const { ui, events, document, stored } = openLocale({ saved: 'en' });
  events.storage({ key: 'sentinel.ui.locale', newValue: 'ru' });
  assert.equal(ui.locale(), 'ru');
  assert.equal(document.documentElement.lang, 'ru');
  assert.equal(stored(), 'en');
  events.storage({ key: 'unrelated', newValue: 'en' });
  assert.equal(ui.locale(), 'ru');
});


test('unknown voice runtime reasons stay opaque even when they match UI keys', async () => {
  const surface = openSurface('renderer.js');
  await new Promise(resolve => setImmediate(resolve));
  surface.voice({ state: 'constructor', reason: 'Sign in' });
  assert.equal(surface.node('voice-headline').textContent, 'Голос · constructor');
  assert.equal(surface.node('voice-detail').textContent, 'Sign in');
});
