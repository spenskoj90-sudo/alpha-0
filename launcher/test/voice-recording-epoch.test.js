'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '..', 'renderer.js'), 'utf8');
function section(startMarker, endMarker) {
  const start = source.indexOf(startMarker);
  const end = source.indexOf(endMarker, start);
  assert.ok(start >= 0 && end > start, `Missing renderer section: ${startMarker}`);
  return source.slice(start, end);
}
const gate = section('function voiceCaptureStillAuthorized(', '\nfunction setVoice(');
const start = section('async function startVoiceCapture()', '\nfunction stopVoiceCapture()');
const cancel = section('function cancelVoiceCapture()', '\nloginButton.onclick');
const finalize = section('async function finalizeVoiceCapture(', '\nasync function startVoiceCapture()');

test('late recorder data and stop callback cannot poison the next microphone capture', async () => {
  const recorders = [];
  const streams = [];
  let stoppedTracks = 0;
  class Recorder {
    static isTypeSupported() { return true; }
    constructor(stream) { this.stream = stream; this.state = 'inactive'; recorders.push(this); }
    start() { this.state = 'recording'; }
    stop() { this.state = 'inactive'; }
  }
  const context = vm.createContext({
    voiceCaptureEpoch: 0, signedIn: true, voiceHoldActive: true, companionState: 'ACTIVE',
    currentVoice: { state: 'READY', consentGranted: true, sttAvailable: true, maxCaptureMs: 6000 },
    voiceRecorder: null, voiceStream: null, voiceBusy: false, voiceChunks: [],
    voiceCaptureDiscarded: false, voiceCaptureTimer: null,
    voiceMicState: null, voiceHeadline: null, voiceDetail: null,
    voiceResult: { className: '' }, ui: { text: () => {} },
    navigator: { mediaDevices: { getUserMedia: async () => {
      const stream = { getTracks: () => [{ stop: () => { stoppedTracks += 1; } }] };
      streams.push(stream); return stream;
    } } },
    MediaRecorder: Recorder,
    window: { sentinel: {
      armVoiceCapture: async () => ({ armed: true, actionCapable: false }),
      disarmVoiceCapture: async () => true,
    } },
    refreshButtons: () => {}, clearVoiceTimer: () => {},
    stopVoiceFeedback: () => {},
    stopVoiceTracks: () => { if (context.voiceStream) {
      for (const track of context.voiceStream.getTracks()) track.stop();
      context.voiceStream = null;
    } },
    setTimeout: () => 1,
  });
  vm.runInContext(gate + start + cancel, context);
  await vm.runInContext('startVoiceCapture()', context);
  assert.equal(recorders.length, 1);
  const oldRecorder = recorders[0];
  vm.runInContext('cancelVoiceCapture()', context);
  assert.equal(oldRecorder.state, 'inactive');
  assert.equal(context.voiceRecorder, null);
  assert.equal(context.voiceBusy, false);
  assert.equal(stoppedTracks, 1);

  // New explicit press-to-talk consent begins the replacement generation.
  context.voiceHoldActive = true;
  await vm.runInContext('startVoiceCapture()', context);
  assert.equal(recorders.length, 2);
  const newRecorder = recorders[1];
  assert.equal(context.voiceRecorder, newRecorder);
  oldRecorder.ondataavailable({ data: { size: 100 } });
  oldRecorder.onerror();
  oldRecorder.onstop();
  assert.equal(context.voiceRecorder, newRecorder);
  assert.equal(context.voiceStream, streams[1]);
  assert.equal(context.voiceChunks.length, 0);
  newRecorder.ondataavailable({ data: { size: 10 } });
  assert.equal(context.voiceChunks.length, 1);
  vm.runInContext('cancelVoiceCapture()', context);
  assert.equal(stoppedTracks, 2);
});

test('completed old transcription cannot clear busy state of a replacement capture', async () => {
  const oldRecorder = { state: 'inactive' };
  const newRecorder = { state: 'recording' };
  let releaseSubmit;
  const pendingSubmit = new Promise(resolve => { releaseSubmit = resolve; });
  const context = vm.createContext({
    voiceCaptureEpoch: 3, voiceRecorder: oldRecorder, voiceBusy: false,
    voiceChunks: [{ size: 4 }], voiceCaptureDiscarded: false,
    voiceMicState: null, voiceHeadline: null, voiceDetail: null,
    voiceResult: { className: '' },
    currentVoice: { captureContentType: 'audio/webm;codecs=opus' },
    ui: { text: () => {} },
    Blob, clearVoiceTimer: () => {}, stopVoiceTracks: () => {}, refreshButtons: () => {},
    submitVoiceBlob: async () => pendingSubmit,
    showError: () => { throw new Error('STALE_UI_MUTATION'); },
  });
  vm.runInContext(finalize, context);
  const finishing = vm.runInContext('finalizeVoiceCapture(3, voiceRecorder)', context);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(context.voiceRecorder, null);
  assert.equal(context.voiceBusy, true);
  context.voiceCaptureEpoch = 4;
  context.voiceRecorder = newRecorder;
  context.voiceBusy = true;
  releaseSubmit();
  await finishing;
  assert.equal(context.voiceRecorder, newRecorder);
  assert.equal(context.voiceBusy, true);
});
