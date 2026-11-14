'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.join(__dirname, '..');
const main = fs.readFileSync(path.join(root, 'main.js'), 'utf8');
const preload = fs.readFileSync(path.join(root, 'preload.js'), 'utf8');
const renderer = fs.readFileSync(path.join(root, 'renderer.js'), 'utf8');

function functionBody(source, name, nextMarker) {
  const start = source.indexOf(`function ${name}`);
  const end = source.indexOf(nextMarker, start);
  assert.ok(start >= 0 && end > start, `${name} boundary not found`);
  return source.slice(start, end);
}

test('microphone permission requires short-lived main-process capture lease', () => {
  const permissions = functionBody(main, 'configureVoicePermissions()', "ipcMain.handle('catalog'");
  assert.match(main, /VOICE_CAPTURE_PERMISSION_LEASE_MS\s*=\s*5000/);
  assert.match(main, /function voiceCapturePermissionArmed\(\)/);
  assert.match(main, /voiceCapturePermissionExpiresAt\s*>\s*performance\.now\(\)/);
  assert.match(main, /voiceCapturePermissionExpiresAt\s*=\s*performance\.now\(\) \+ VOICE_CAPTURE_PERMISSION_LEASE_MS/);
  assert.doesNotMatch(main, /voiceCapturePermissionExpiresAt\s*>\s*Date\.now\(\)/);
  assert.match(permissions, /consentGranted:\s*voiceCapturePermissionArmed\(\)/);
  assert.doesNotMatch(permissions, /consentGranted:\s*voiceConsentGranted[,\n]/);
  assert.match(permissions, /setDisplayMediaRequestHandler\(\(_request, callback\) => callback\(null\)\)/);
});

test('voice IPC is sender-bound and capture lease is explicitly arm/disarm scoped', () => {
  assert.match(main, /function requireMainRenderer\(event\)/);
  assert.match(main, /event\?\.sender !== mainWindow\.webContents/);
  assert.match(main, /ipcMain\.handle\('voice:capture:arm',[\s\S]*?requireMainRenderer\(event\)/);
  assert.match(main, /ipcMain\.handle\('voice:capture:disarm',[\s\S]*?clearVoiceCapturePermission\(\)/);
  assert.match(main, /ipcMain\.handle\('voice:submit',[\s\S]*?requireMainRenderer\(event\);[\s\S]*?clearVoiceCapturePermission\(\)/);
  assert.match(preload, /armVoiceCapture:\s*\(\) => ipcRenderer\.invoke\('voice:capture:arm'\)/);
  assert.match(preload, /disarmVoiceCapture:\s*\(\) => ipcRenderer\.invoke\('voice:capture:disarm'\)/);
});

test('renderer arms only for explicit getUserMedia and immediately disarms afterward', () => {
  const armIndex = renderer.indexOf('await window.sentinel.armVoiceCapture()');
  const mediaIndex = renderer.indexOf('navigator.mediaDevices.getUserMedia');
  const disarmIndex = renderer.indexOf('await window.sentinel.disarmVoiceCapture()');
  assert.ok(armIndex >= 0 && mediaIndex > armIndex && disarmIndex > mediaIndex);
  assert.match(renderer, /video:\s*false/);
});

test('voice readiness requires active Companion transport, not just cached STT availability', () => {
  const body = functionBody(main, 'voiceSnapshot()', 'function publishVoiceSnapshot()');
  assert.match(body, /companion\.status\.state !== 'ACTIVE'/);
  assert.match(body, /state = 'COMPANION_UNAVAILABLE'/);
  assert.match(body, /state === 'COMPANION_UNAVAILABLE' \? 'COMPANION_NOT_ACTIVE'/);
  assert.ok(body.indexOf("companion.status.state !== 'ACTIVE'") < body.indexOf("voiceProviderStatus?.sttAvailable) state = 'READY'"));
});

test('voice UI and IPC never arm or retain microphone capture during degraded transport', () => {
  const arm = main.slice(main.indexOf("ipcMain.handle('voice:capture:arm'"), main.indexOf("ipcMain.handle('voice:capture:disarm'"));
  const submit = main.slice(main.indexOf("ipcMain.handle('voice:submit'"), main.indexOf("\n\napp.whenReady()"));
  for (const handler of [arm, submit]) {
    assert.match(handler, /companion\.status\.state !== 'ACTIVE'/);
    assert.doesNotMatch(handler, /\['ACTIVE', 'DEGRADED'\]\.includes\(companion\.status\.state\)/);
  }
  assert.match(renderer, /const companionReady = companionState === 'ACTIVE'/);
  assert.match(renderer, /const voiceReady = [^\n]*currentVoice\.state === 'READY'/);
  assert.match(renderer, /COMPANION_UNAVAILABLE: \['Companion connection required'/);
  assert.match(renderer, /if \(companionState !== 'ACTIVE' &&[\s\S]*?cancelVoiceCapture\(\)/);
  assert.match(renderer, /function voiceCaptureStillAuthorized[\s\S]*?companionState === 'ACTIVE'/);
});
