'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {
  documentUrl, isLocalDocument, assertMainFrameRequest, restrictAppWindowNavigation,
} = require('../renderer-boundary');

const fixtureDir = path.resolve('SENTINEL Companion');
const trusted = documentUrl(fixtureDir, 'index.html');
const overlay = documentUrl(fixtureDir, 'overlay.html');

function fixture(url = trusted) {
  const mainFrame = { url };
  const webContents = { mainFrame, getURL: () => url };
  return { win: { webContents, isDestroyed: () => false },
    event: { sender: webContents, senderFrame: mainFrame } };
}

test('packaged file URI permits only the exact local document and optional fragment', () => {
  assert.match(trusted, /\/SENTINEL%20Companion\/index\.html$/);
  assert.equal(documentUrl(fixtureDir, 'index.html'), trusted);
  for (const url of [trusted, trusted + '#games', trusted + '#main-content']) {
    assert.equal(isLocalDocument(url, trusted), true, url);
  }
  for (const url of [
    'https://lasthavens.com/play', overlay, trusted + '.bak',
    trusted + '?debug=true', 'javascript:alert(1)', 'data:text/html,evil',
    'file:///opt/other/index.html', '', null, 22,
    'file:///opt/SENTINEL%20Companion/../index.html',
  ]) {
    assert.equal(isLocalDocument(url, trusted), false, String(url));
  }
});

test('IPC permits only current live top-level local frame and rejects overlay, remote or stale frames', () => {
  const { win, event } = fixture();
  assert.doesNotThrow(() => assertMainFrameRequest(event, win, trusted));
  win.webContents.getURL = () => trusted + '#account';
  event.senderFrame.url = trusted + '#games';
  assert.doesNotThrow(() => assertMainFrameRequest(event, win, trusted));
  const untrustedEvents = [
    { ...event, sender: {} },
    { ...event, senderFrame: { url: trusted } },
    { ...event, senderFrame: null },
    null,
  ];
  for (const attempt of untrustedEvents) {
    assert.throws(() => assertMainFrameRequest(attempt, win, trusted), /UNTRUSTED_RENDERER/);
  }
  event.senderFrame.url = 'https://malicious.invalid/';
  assert.throws(() => assertMainFrameRequest(event, win, trusted), /UNTRUSTED_RENDERER/);
  event.senderFrame.url = trusted;
  win.webContents.getURL = () => overlay;
  assert.throws(() => assertMainFrameRequest(event, win, trusted), /UNTRUSTED_RENDERER/);
  win.webContents.getURL = () => trusted;
  win.isDestroyed = () => true;
  assert.throws(() => assertMainFrameRequest(event, win, trusted), /UNTRUSTED_RENDERER/);
});

test('navigation handler denies popups and all untrusted document/subframe attempts', () => {
  const handlers = new Map();
  let popupPolicy;
  const contents = {
    on: (name, callback) => handlers.set(name, callback),
    setWindowOpenHandler: callback => { popupPolicy = callback; },
  };
  restrictAppWindowNavigation(contents, overlay);
  assert.deepEqual(popupPolicy({ url: 'https://evil.invalid/' }), { action: 'deny' });
  const event = { count: 0, preventDefault() { this.count++; } };
  handlers.get('will-navigate')(event, { url: overlay + '#main' });
  assert.equal(event.count, 0);
  handlers.get('will-navigate')(event, { url: trusted });
  assert.equal(event.count, 1);
  handlers.get('will-navigate')({ url: 'https://evil.invalid', preventDefault() { event.count++; } });
  assert.equal(event.count, 2);
  const frame = { count: 0, preventDefault() { this.count++; } };
  handlers.get('will-frame-navigate')(frame, { isMainFrame: true, url: overlay });
  assert.equal(frame.count, 0);
  handlers.get('will-frame-navigate')(frame, { isMainFrame: false, url: overlay });
  assert.equal(frame.count, 1);
  handlers.get('will-frame-navigate')(frame, { isMainFrame: true, url: trusted });
  assert.equal(frame.count, 2);
});

test('all sensitive Electron IPC handlers invoke main-frame authorization as their first action', () => {
  const main = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  const tokens = [...main.matchAll(/ipcMain\.handle\('([^']+)'/g)];
  const expected = [
    'catalog', 'game:choose-executable', 'game:launch', 'account:login',
    'account:mfa-complete', 'account:logout', 'account:status', 'companion:status',
    'knowledge:status', 'knowledge:refresh', 'companion:start', 'companion:stop',
    'voice:status', 'voice:consent:set', 'voice:capture:arm', 'voice:capture:disarm', 'voice:submit',
  ];
  assert.deepEqual(tokens.map(x => x[1]), expected);
  // Native file selection is the only renderer-accessible writer. Previously
  // exposed config:get/set allowed the renderer to leak paths or bypass .exe selection.
  const preload = fs.readFileSync(path.join(__dirname, '..', 'preload.js'), 'utf8');
  assert.doesNotMatch(main, /ipcMain\\.handle\\('config:(?:get|set)'/);
  assert.doesNotMatch(preload, /(?:getConfig|setExecutable)\\s*:/);
  assert.doesNotMatch(preload, /ipcRenderer\\.invoke\\('config:(?:get|set)'/);
  assert.match(preload, /chooseExecutable: id => ipcRenderer\\.invoke\\('game:choose-executable', id\\)/);
  for (let i = 0; i < tokens.length; i++) {
    const body = main.slice(tokens[i].index, tokens[i + 1]?.index ?? main.indexOf('\n\napp.whenReady()', tokens[i].index));
    assert.match(body.slice(0, 220), /requireMainRenderer\(event\)/, expected[i]);
  }
  assert.match(main, /restrictAppWindowNavigation\(win\.webContents, TRUSTED_MAIN_DOCUMENT\)/);
  assert.match(main, /restrictAppWindowNavigation\(win\.webContents, TRUSTED_OVERLAY_DOCUMENT\)/);
  assert.match(main, /assertMainFrameRequest\(event, mainWindow, TRUSTED_MAIN_DOCUMENT\)/);
});
