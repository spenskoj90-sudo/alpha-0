'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '..', 'renderer.js'), 'utf8');
function fragment(a, b) {
  const i = source.indexOf(a), j = source.indexOf(b, i);
  assert.ok(i >= 0 && j > i, 'RENDERER_SECTION_MISSING');
  return source.slice(i, j);
}
const audio = fragment('function stopVoiceFeedback()', '\nasync function submitVoiceBlob(');

test('explicit Stop pauses voice feedback and revokes its Blob URL exactly once', async () => {
  let paused = 0, revoked = 0, player;
  class FakeAudio {
    constructor() { this.handlers = {}; player = this; }
    addEventListener(name, callback) { this.handlers[name] = callback; }
    async play() {}
    pause() { paused++; }
  }
  const ctx = vm.createContext({
    voiceFeedbackPlayback: null, voiceCaptureEpoch: 3, authorized: true,
    voiceCaptureStillAuthorized: epoch => ctx.authorized && ctx.voiceCaptureEpoch === epoch,
    atob, Uint8Array, Blob, Audio: FakeAudio,
    URL: { createObjectURL: () => 'blob:sample', revokeObjectURL: () => { revoked++; } },
  });
  vm.runInContext(audio, ctx);
  await vm.runInContext("playFeedbackAudio({ audioBase64:'AAE=', contentType:'audio/wav' }, 3)", ctx);
  assert.ok(ctx.voiceFeedbackPlayback);
  vm.runInContext('stopVoiceFeedback()', ctx);
  assert.equal(paused, 1);
  assert.equal(revoked, 1);
  assert.equal(ctx.voiceFeedbackPlayback, null);
  player.handlers.ended();
  assert.equal(revoked, 1);
});

test('Stop during unresolved playback prevents stale sound and releases URL', async () => {
  let paused = 0, revoked = 0, finish;
  const pending = new Promise(resolve => { finish = resolve; });
  class FakeAudio {
    addEventListener() {}
    play() { return pending; }
    pause() { paused++; }
  }
  const ctx = vm.createContext({
    voiceFeedbackPlayback: null, voiceCaptureEpoch: 9, authorized: true,
    voiceCaptureStillAuthorized: epoch => ctx.authorized && ctx.voiceCaptureEpoch === epoch,
    atob, Uint8Array, Blob, Audio: FakeAudio,
    URL: { createObjectURL: () => 'blob:sample', revokeObjectURL: () => { revoked++; } },
  });
  vm.runInContext(audio, ctx);
  const started = vm.runInContext("playFeedbackAudio({ audioBase64:'AAE=', contentType:'audio/wav' }, 9)", ctx);
  ctx.authorized = false; ctx.voiceCaptureEpoch++;
  vm.runInContext('stopVoiceFeedback()', ctx);
  finish();
  await started;
  assert.equal(paused, 1);
  assert.equal(revoked, 1);
  assert.equal(ctx.voiceFeedbackPlayback, null);
});

test('Stop, account switch, transport revocation and new capture revoke audio', () => {
  const cancel = fragment('function cancelVoiceCapture()', '\nloginButton.onclick');
  const account = fragment('function setAccount(', '\nfunction setCompanion(');
  const transport = fragment('function setCompanion(', '\nfunction setWowCheckpoint(');
  const voice = fragment('function setVoice(', '\nfunction showError(');
  const start = fragment('async function startVoiceCapture()', '\nfunction stopVoiceCapture(');
  const submit = fragment('async function submitVoiceBlob(', '\nasync function finalizeVoiceCapture(');
  assert.match(cancel, /stopVoiceFeedback\(\)/);
  assert.match(account, /voiceFeedbackPlayback/);
  assert.match(transport, /voiceFeedbackPlayback/);
  assert.match(voice, /voiceFeedbackPlayback/);
  assert.match(start, /stopVoiceFeedback\(\)/);
  assert.match(submit, /playFeedbackAudio\(response\.feedbackAudio, epoch\)/);
});
