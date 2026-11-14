'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const renderer = fs.readFileSync(path.join(__dirname, '..', 'renderer.js'), 'utf8');

test('capture error marks audio discarded before MediaRecorder stop', () => {
  assert.match(renderer, /recorder\.onerror\s*=\s*\(\)\s*=>\s*\{[\s\S]*?voiceCaptureDiscarded\s*=\s*true;[\s\S]*?recorder\.stop\(\)/);
  assert.match(renderer, /const discarded = voiceCaptureDiscarded;/);
  assert.match(renderer, /if \(discarded\) return;/);
  assert.match(renderer, /VOICE RESULT: CANCELED/);
});

test('logout and Companion kill switch cancel rather than submit active capture', () => {
  assert.match(renderer, /function cancelVoiceCapture\(\)[\s\S]*?voiceCaptureDiscarded\s*=\s*true;[\s\S]*?voiceChunks\s*=\s*\[\];/);
  assert.match(renderer, /logoutButton\.onclick\s*=\s*async \(\)\s*=>\s*\{\s*cancelVoiceCapture\(\);/);
  assert.match(renderer, /stopButton\.onclick\s*=\s*async \(\)\s*=>\s*\{[\s\S]*?window\.confirm\([\s\S]*?if \(!confirmed\) return;[\s\S]*?cancelVoiceCapture\(\);/);
});

test('capture authorization is bound to session, consent, connection and exact epoch', () => {
  const vm = require('node:vm');
  const source = fs.readFileSync(path.join(__dirname, '..', 'renderer.js'), 'utf8');
  const start = source.indexOf('function voiceCaptureStillAuthorized(');
  const end = source.indexOf('\nfunction setVoice(', start);
  assert.ok(start >= 0 && end > start);
  const context = vm.createContext({
    voiceCaptureEpoch: 7,
    signedIn: true,
    voiceHoldActive: true,
    companionState: 'ACTIVE',
    currentVoice: { state: 'READY', consentGranted: true, sttAvailable: true },
  });
  vm.runInContext(source.slice(start, end), context);
  const allowed = () => vm.runInContext('voiceCaptureStillAuthorized(7, true)', context);
  assert.equal(allowed(), true);
  context.voiceHoldActive = false;
  assert.equal(allowed(), false);
  context.voiceHoldActive = true;
  context.companionState = 'STOPPED';
  assert.equal(allowed(), false);
  context.companionState = 'ACTIVE';
  context.currentVoice.consentGranted = false;
  assert.equal(allowed(), false);
  context.currentVoice.consentGranted = true;
  context.signedIn = false;
  assert.equal(allowed(), false);
  context.signedIn = true;
  context.voiceCaptureEpoch = 8;
  assert.equal(allowed(), false);
});

test('revocation during pending getUserMedia closes only the late stream without starting MediaRecorder', async () => {
  const vm = require('node:vm');
  const source = fs.readFileSync(path.join(__dirname, '..', 'renderer.js'), 'utf8');
  const extract = (startMarker, endMarker) => {
    const start = source.indexOf(startMarker);
    const end = source.indexOf(endMarker, start);
    assert.ok(start >= 0 && end > start);
    return source.slice(start, end);
  };
  const gate = extract('function voiceCaptureStillAuthorized(', '\nfunction setVoice(');
  const capture = extract('async function startVoiceCapture()', '\nfunction stopVoiceCapture()');
  const cancel = extract('function cancelVoiceCapture()', '\nloginButton.onclick');
  let resolveMedia;
  const waitingMedia = new Promise(resolve => { resolveMedia = resolve; });
  let recorderStarts = 0;
  let stoppedTracks = 0;
  let mediaRequests = 0;
  class Recorder {
    static isTypeSupported() { return true; }
    constructor() { recorderStarts += 1; }
  }
  const context = vm.createContext({
    voiceCaptureEpoch: 0,
    signedIn: true,
    voiceHoldActive: true,
    companionState: 'ACTIVE',
    currentVoice: { state: 'READY', consentGranted: true, sttAvailable: true, maxCaptureMs: 6000 },
    voiceRecorder: null, voiceStream: null, voiceBusy: false, voiceChunks: [],
    voiceCaptureDiscarded: false, voiceCaptureTimer: null,
    voiceMicState: null, voiceHeadline: null, voiceDetail: null,
    voiceResult: { className: '' },
    ui: { text: () => {} },
    navigator: { mediaDevices: { getUserMedia: () => { mediaRequests += 1; return waitingMedia; } } },
    MediaRecorder: Recorder,
    window: { sentinel: {
      armVoiceCapture: async () => ({ armed: true, actionCapable: false }),
      disarmVoiceCapture: async () => true,
    } },
    refreshButtons: () => {},
    stopVoiceFeedback: () => {},
    clearVoiceTimer: () => {},
    stopVoiceTracks: () => { if (context.voiceStream) {
      for (const track of context.voiceStream.getTracks()) track.stop();
      context.voiceStream = null;
    } },
    setTimeout: () => 1,
  });
  vm.runInContext(gate + capture + cancel, context);
  const pending = vm.runInContext('startVoiceCapture()', context);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(mediaRequests, 1);
  vm.runInContext('cancelVoiceCapture()', context);
  assert.equal(context.voiceCaptureEpoch, 1);
  resolveMedia({ getTracks: () => [{ stop: () => { stoppedTracks += 1; } }] });
  await assert.rejects(pending, /VOICE_CAPTURE_REVOKED/);
  assert.equal(stoppedTracks, 1);
  assert.equal(recorderStarts, 0);
  assert.equal(context.voiceStream, null);
  assert.equal(context.voiceBusy, false);
});

test('renderer refuses late transcription and stale async UI after voice revocation', () => {
  const source = fs.readFileSync(path.join(__dirname, '..', 'renderer.js'), 'utf8');
  const sub = source.slice(source.indexOf('async function submitVoiceBlob('), source.indexOf('\nasync function finalizeVoiceCapture('));
  const start = source.slice(source.indexOf('async function startVoiceCapture('), source.indexOf('\nfunction stopVoiceCapture('));
  const voice = source.slice(source.indexOf('function setVoice('), source.indexOf('\nfunction showError('));
  const account = source.slice(source.indexOf('function setAccount('), source.indexOf('\nfunction setCompanion('));
  const companion = source.slice(source.indexOf('function setCompanion('), source.indexOf('\nfunction setWowCheckpoint('));
  assert.match(sub, /await blobToBase64\(blob\);\s*if \(!voiceCaptureStillAuthorized\(epoch\)\) return/);
  assert.match(sub, /await window\.sentinel\.submitVoice\([\s\S]*?if \(!voiceCaptureStillAuthorized\(epoch\)\) return/);
  assert.match(start, /acquiredStream = await navigator\.mediaDevices\.getUserMedia/);
  assert.match(start, /if \(!voiceCaptureStillAuthorized\(epoch, true\)\) throw new Error\('VOICE_CAPTURE_REVOKED'\)/);
  assert.match(voice, /cancelVoiceCapture\(\)/);
  assert.match(account, /cancelVoiceCapture\(\)/);
  assert.match(companion, /cancelVoiceCapture\(\)/);
});
