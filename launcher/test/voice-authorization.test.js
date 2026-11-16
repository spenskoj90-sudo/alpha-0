'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { sameSessionContext, bindVoiceRequest, voiceRequestStillCurrent } = require('../voice-authorization');

const base = { origin: 'http://127.0.0.1:8080', sessionId: '44' };
test('voice request remains bound during in-account refresh only', () => {
  const bound = bindVoiceRequest(base, 5);
  assert.ok(bound);
  assert.equal(voiceRequestStillCurrent(bound, { ...base }, 5, true, 'ACTIVE'), true);
  assert.equal(voiceRequestStillCurrent(bound, { ...base }, 5, true, 'DEGRADED'), false);
  assert.equal(voiceRequestStillCurrent(bound, { ...base, sessionId: '45' }, 5, true, 'ACTIVE'), false);
  assert.equal(voiceRequestStillCurrent(bound, { ...base, origin: 'http://localhost:8080' }, 5, true, 'ACTIVE'), false);
  assert.equal(voiceRequestStillCurrent(bound, base, 6, true, 'ACTIVE'), false);
  assert.equal(voiceRequestStillCurrent(bound, base, 5, false, 'ACTIVE'), false);
  assert.equal(voiceRequestStillCurrent(bound, base, 5, true, 'STOPPED'), false);
  assert.equal(voiceRequestStillCurrent(bound, base, 5, true, 'CONNECTING'), false);
});
test('voice boundary rejects missing session, invalid generation and malformed context', () => {
  assert.equal(bindVoiceRequest(null, 0), null);
  assert.equal(bindVoiceRequest(base, -1), null);
  assert.equal(bindVoiceRequest(base, Number.NaN), null);
  assert.equal(bindVoiceRequest({ origin: '', sessionId: '44' }, 1), null);
  assert.equal(sameSessionContext(base, null), null);
  assert.equal(voiceRequestStillCurrent(null, base, 0, true, 'ACTIVE'), false);
});

test('main voice IPC rechecks the original authority across every network await', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  const arm = src.slice(src.indexOf("ipcMain.handle('voice:capture:arm'"), src.indexOf("ipcMain.handle('voice:capture:disarm'"));
  const submit = src.slice(src.indexOf("ipcMain.handle('voice:submit'"), src.indexOf('\n\napp.whenReady()'));
  const consent = src.slice(src.indexOf("ipcMain.handle('voice:consent:set'"), src.indexOf("ipcMain.handle('voice:capture:arm'"));
  const refresh = src.slice(src.indexOf('async function refreshVoiceProviderStatus()'), src.indexOf('\nfunction voiceRequestBoundary()'));
  assert.ok(arm.includes('const boundary = voiceRequestBoundary();'));
  assert.ok(arm.indexOf('requireVoiceBoundary(boundary)', arm.indexOf('await refreshVoiceProviderStatus()')) > -1);
  assert.ok(submit.includes('const boundary = voiceRequestBoundary();'));
  assert.ok(submit.indexOf('requireVoiceBoundary(boundary)', submit.indexOf('await refreshVoiceProviderStatus()')) > -1);
  assert.ok(submit.indexOf('requireVoiceBoundary(boundary)', submit.indexOf('await session.transcribeVoice(')) > -1);
  assert.ok(submit.indexOf('requireVoiceBoundary(boundary)', submit.indexOf('await session.synthesizeVoice(')) > -1);
  assert.ok(submit.lastIndexOf('requireVoiceBoundary(boundary)') > submit.indexOf('feedbackReason ='));
  assert.ok(consent.includes('const generation = ++voiceConsentGeneration'));
  assert.ok(consent.includes('!sameSessionContext(sessionContext, session.knowledgeContext)'));
  assert.ok(refresh.includes('const generation = ++voiceStatusRequestGeneration'));
  assert.ok(refresh.includes('if (!stillCurrent()) return voiceSnapshot()'));
  assert.ok(src.includes("if (status.state !== 'ACTIVE') {"));
});
