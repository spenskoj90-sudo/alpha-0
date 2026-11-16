'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { revokeAccountBoundRuntime } = require('../account-lifecycle');

function fixture(failStop = false) {
  const calls = [];
  const record = name => { calls.push(name); if (name === 'stop' && failStop) throw new Error('secret credential'); };
  return {
    calls,
    parts: {
      session: { clear: () => record('clear-session') },
      companion: { stop: reason => { calls.push(reason); record('stop'); } },
      knowledge: { logout: () => record('knowledge-logout') },
      wowBridge: { stop: () => record('wow-stop') },
      overlayStore: { clear: () => record('overlay-clear') },
      resetEvidence: () => record('clear-evidence'),
      resetVoice: reason => { assert.equal(reason, 'AUTHENTICATION_REQUIRED'); record('clear-voice'); },
      publishOverlay: () => record('publish-overlay'),
    },
  };
}

test('account switch revokes old identity and every account-bound live surface', () => {
  const { calls, parts } = fixture();
  revokeAccountBoundRuntime(parts, 'ACCOUNT_SWITCH');
  assert.deepEqual(calls, [
    'clear-session', 'ACCOUNT_SWITCH', 'stop', 'knowledge-logout', 'wow-stop',
    'overlay-clear', 'clear-evidence', 'clear-voice', 'publish-overlay',
  ]);
});

test('a failed worker stop cannot skip session revocation or leave overlay/voice state', () => {
  const { calls, parts } = fixture(true);
  assert.throws(() => revokeAccountBoundRuntime(parts, 'ACCOUNT_SWITCH'), error =>
    error.message === 'ACCOUNT_BOUNDARY_CLEANUP_FAILED' && !error.message.includes('secret'));
  assert.deepEqual(calls.slice(-6), [
    'knowledge-logout', 'wow-stop', 'overlay-clear', 'clear-evidence', 'clear-voice', 'publish-overlay',
  ]);
  assert.equal(calls[0], 'clear-session');
});

test('launcher gates new login behind revocation and uses the same logout path', () => {
  const code = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  const login = code.slice(code.indexOf("ipcMain.handle('account:login'"), code.indexOf("ipcMain.handle('account:mfa-complete'"));
  const logout = code.slice(code.indexOf("ipcMain.handle('account:logout'"), code.indexOf("ipcMain.handle('account:status'"));
  assert.ok(login.indexOf("clearAccountBoundary('ACCOUNT_SWITCH')") !== -1);
  assert.ok(login.indexOf("clearAccountBoundary('ACCOUNT_SWITCH')") < login.indexOf('await session.login('));
  assert.ok(logout.includes("clearAccountBoundary('ACCOUNT_LOGOUT')"));
  assert.ok(code.includes('revokeAccountBoundRuntime({'));
});
