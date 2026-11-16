'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { CompanionStartFence } = require('../companion-start-fence');

const initial = Object.freeze({ origin: 'http://127.0.0.1:8080', sessionId: '41' });

test('Companion launch lease is valid only for original session and latest generation', () => {
  const fence = new CompanionStartFence();
  const lease = fence.begin(initial);
  assert.equal(fence.isCurrent(lease, { ...initial }), true);
  assert.equal(fence.isCurrent(lease, { ...initial, sessionId: '42' }), false);
  assert.equal(fence.isCurrent(lease, { ...initial, origin: 'http://localhost:8080' }), false);
  fence.revoke();
  assert.equal(fence.isCurrent(lease, initial), false);
  const second = fence.begin(initial);
  assert.equal(fence.isCurrent(second, initial), true);
  assert.equal(fence.isCurrent(lease, initial), false);
  const third = fence.begin(initial);
  assert.equal(fence.isCurrent(second, initial), false);
  assert.equal(fence.isCurrent(third, initial), true);
});

test('Companion launch lease never authorizes absent or invalid session contexts', () => {
  const fence = new CompanionStartFence();
  assert.equal(fence.begin(null), null);
  assert.equal(fence.begin({ origin: '', sessionId: '41' }), null);
  assert.equal(fence.begin({ origin: initial.origin, sessionId: '' }), null);
  const lease = fence.begin(initial);
  assert.equal(fence.isCurrent(null, initial), false);
  assert.equal(fence.isCurrent(lease, null), false);
  assert.equal(fence.isCurrent(lease, { origin: initial.origin, sessionId: '' }), false);
});

test('revoke while entitlement lookup is pending denies late launch and new epoch can launch', async () => {
  const fence = new CompanionStartFence();
  let completeLookup;
  const pending = new Promise(resolve => { completeLookup = resolve; });
  let startCount = 0;
  const launch = async () => {
    const lease = fence.begin(initial);
    await pending;
    if (!fence.isCurrent(lease, initial)) throw new Error('COMPANION_START_REVOKED');
    startCount++;
  };
  const attempt = launch();
  fence.revoke(); // user pressed Stop during network entitlement lookup
  completeLookup();
  await assert.rejects(attempt, /COMPANION_START_REVOKED/);
  assert.equal(startCount, 0);
  const newLease = fence.begin(initial);
  assert.equal(fence.isCurrent(newLease, initial), true);
});

test('main runtime gates pending start after entitlement await and revokes on Stop/account switch', () => {
  const code = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  const start = code.slice(code.indexOf("ipcMain.handle('companion:start'"), code.indexOf("ipcMain.handle('companion:stop'"));
  const stop = code.slice(code.indexOf("ipcMain.handle('companion:stop'"), code.indexOf("ipcMain.handle('voice:status'"));
  const account = code.slice(code.indexOf('function clearAccountBoundary(reason)'), code.indexOf('\nfunction configPath()'));
  assert.ok(start.includes('const startLease = companionStartFence.begin(session.knowledgeContext);'));
  assert.ok(start.indexOf('if (!companionStartFence.isCurrent(startLease, session.knowledgeContext))') > start.indexOf('await session.featureStatus()'));
  assert.ok(start.indexOf('if (!companionStartFence.isCurrent(startLease, session.knowledgeContext))') < start.indexOf('companion.start('));
  assert.ok(stop.indexOf('companionStartFence.revoke()') < stop.indexOf('companion.stop('));
  assert.ok(account.indexOf('companionStartFence.revoke()') < account.indexOf('revokeAccountBoundRuntime('));
});
