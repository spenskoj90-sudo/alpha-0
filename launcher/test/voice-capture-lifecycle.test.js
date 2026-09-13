'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const renderer = fs.readFileSync(path.join(__dirname, '..', 'renderer.js'), 'utf8');

test('capture error marks audio discarded before MediaRecorder stop', () => {
  assert.match(renderer, /recorder\.onerror\s*=\s*\(\)\s*=>\s*\{[\s\S]*?voiceCaptureDiscarded\s*=\s*true;[\s\S]*?recorder\.stop\(\)/);
  assert.match(renderer, /const discarded = voiceCaptureDiscarded;/);
  assert.match(renderer, /if \(discarded\) throw new Error\('VOICE_CAPTURE_DISCARDED'\);/);
});

test('logout and Companion kill switch cancel rather than submit active capture', () => {
  assert.match(renderer, /function cancelVoiceCapture\(\)[\s\S]*?voiceCaptureDiscarded\s*=\s*true;[\s\S]*?voiceChunks\s*=\s*\[\];/);
  assert.match(renderer, /logoutButton\.onclick\s*=\s*async \(\)\s*=>\s*\{\s*cancelVoiceCapture\(\);/);
  assert.match(renderer, /stopButton\.onclick\s*=\s*async \(\)\s*=>\s*\{\s*cancelVoiceCapture\(\);/);
});
