'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.join(__dirname, '..');
const main = fs.readFileSync(path.join(root, 'main.js'), 'utf8');
const preload = fs.readFileSync(path.join(root, 'preload.js'), 'utf8');
const renderer = fs.readFileSync(path.join(root, 'renderer.js'), 'utf8');

test('microphone permission requires short-lived main-process capture lease', () => {
  assert.match(main, /VOICE_CAPTURE_PERMISSION_LEASE_MS\s*=\s*5000/);
  assert.match(main, /function voiceCapturePermissionArmed\(\)/);
  assert.match(main, /voiceCapturePermissionExpiresAt\s*>\s*Date\.now\(\)/);
  assert.match(main, /consentGranted:\s*voiceCapturePermissionArmed\(\)/);
  assert.doesNotMatch(main, /consentGranted:\s*voiceConsentGranted[,\n]/);
  assert.match(main, /setDisplayMediaRequestHandler\(\(_request, callback\) => callback\(null\)\)/);
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
