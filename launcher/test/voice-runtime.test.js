'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { CoreSessionManager } = require('../core-session');
const { OverlayPresentationStore } = require('../overlay-state');
const {
  feedbackTextForVoiceResult,
  mediaPermissionAllowed,
  sanitizeSynthesizedAudio,
  sanitizeVoiceResult,
  sanitizeVoiceStatus,
  validateCapturePayload,
} = require('../voice-runtime');

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

test('voice status/result/audio sanitizers expose only bounded public DTOs', () => {
  const status = sanitizeVoiceStatus({
    stt_available: true,
    tts_available: true,
    capture_content_type: 'audio/webm;codecs=opus',
    synthesis_content_type: 'audio/wav',
    max_audio_bytes: 512000,
    max_text_chars: 2000,
    max_synthesized_bytes: 2000000,
    action_capable: false,
    request_id: 'voice-status-1',
    provider_token: 'must-not-pass',
  });
  assert.deepEqual(status, {
    sttAvailable: true,
    ttsAvailable: true,
    captureContentType: 'audio/webm;codecs=opus',
    synthesisContentType: 'audio/wav',
    maxAudioBytes: 512000,
    maxTextChars: 2000,
    maxSynthesizedBytes: 2000000,
    actionCapable: false,
    requestId: 'voice-status-1',
  });
  assert.equal(JSON.stringify(status).includes('provider_token'), false);

  const result = sanitizeVoiceResult({
    accepted: true,
    reason_code: 'VOICE_ACCEPTED',
    intent: { surface: 'VOICE', mode: 'ACKNOWLEDGE', recommendation_id: 'rec-1', locale: 'en' },
    action_capable: false,
    request_id: 'voice-result-1',
    transcript: 'private transcript must not pass',
  });
  assert.deepEqual(result, {
    accepted: true,
    reasonCode: 'VOICE_ACCEPTED',
    intent: { surface: 'VOICE', mode: 'ACKNOWLEDGE', recommendationId: 'rec-1', locale: 'en' },
    actionCapable: false,
    requestId: 'voice-result-1',
  });
  assert.equal(JSON.stringify(result).includes('private transcript'), false);
  assert.equal(sanitizeVoiceResult({ ...result, action_capable: true }), null);

  const wav = Buffer.from('RIFF-safe-audio');
  const audio = sanitizeSynthesizedAudio({
    audio_b64: wav.toString('base64'), content_type: 'audio/wav', bytes: wav.length,
    action_capable: false, request_id: 'voice-audio-1', arbitrary: 'drop-me',
  });
  assert.equal(Buffer.from(audio.audioBase64, 'base64').toString(), 'RIFF-safe-audio');
  assert.equal(audio.contentType, 'audio/wav');
  assert.equal('arbitrary' in audio, false);
});

test('capture validation requires canonical base64, locale and bounded bytes', () => {
  const encoded = Buffer.from('audio').toString('base64');
  assert.deepEqual(validateCapturePayload({ audioBase64: encoded, locale: 'en' }, 100), {
    audioBase64: encoded,
    locale: 'en',
    bytes: 5,
  });
  assert.throws(() => validateCapturePayload({ audioBase64: '***', locale: 'en' }), /VOICE_CAPTURE_INVALID/);
  assert.throws(() => validateCapturePayload({ audioBase64: encoded, locale: '../../' }), /VOICE_LOCALE_INVALID/);
  assert.throws(() => validateCapturePayload({ audioBase64: encoded, locale: 'en' }, 4), /VOICE_AUDIO_TOO_LARGE/);
});

test('media permission is default-deny and consent-scoped to launcher main webContents', () => {
  const mainWebContents = { getURL: () => 'file:///launcher/index.html' };
  const otherWebContents = { getURL: () => 'file:///launcher/overlay.html' };
  const base = {
    webContents: mainWebContents,
    mainWebContents,
    permission: 'media',
    requestingOrigin: 'file://',
    details: { mediaTypes: ['audio'] },
    consentGranted: true,
  };
  assert.equal(mediaPermissionAllowed(base), true);
  assert.equal(mediaPermissionAllowed({ ...base, consentGranted: false }), false);
  assert.equal(mediaPermissionAllowed({ ...base, permission: 'notifications' }), false);
  assert.equal(mediaPermissionAllowed({ ...base, webContents: otherWebContents }), false);
  assert.equal(mediaPermissionAllowed({ ...base, requestingOrigin: 'https://evil.example', details: {} }), false);
  assert.equal(mediaPermissionAllowed({ ...base, details: { mediaTypes: ['video'] } }), false);
});

test('voice feedback text is fixed by sanitized intent and never accepts renderer text', () => {
  assert.equal(feedbackTextForVoiceResult({ accepted: true, intent: { mode: 'ACKNOWLEDGE' } }), 'Acknowledged.');
  assert.equal(feedbackTextForVoiceResult({ accepted: true, intent: { mode: 'DISMISS' } }), 'Dismissed.');
  assert.equal(feedbackTextForVoiceResult({ accepted: true, intent: { mode: 'OBSERVE' } }), 'Status requested.');
  assert.equal(feedbackTextForVoiceResult({ accepted: false, reasonCode: 'ACTION_GATEWAY_REQUIRED' }), 'Voice cannot execute game actions.');
  assert.equal(feedbackTextForVoiceResult({ accepted: false, reasonCode: 'VOICE_COMMAND_UNSUPPORTED' }), 'Voice command not recognized.');
});

test('voice presentation intents can only remove bounded overlay presentation state', () => {
  const store = new OverlayPresentationStore({ maxItems: 4, ttlMs: 15000, now: () => 1000 });
  store.push({ presentationId: 'rec-1', channel: 'OVERLAY', kind: 'RECOMMENDATION', text: 'Tip', confidence: 0.8, provenance: ['core'] });
  store.push({ presentationId: 'status-1', channel: 'OVERLAY', kind: 'STATUS', text: 'Healthy', confidence: null, provenance: ['core'] });
  assert.equal(store.latestRecommendationId(), 'rec-1');
  assert.equal(store.remove('rec-1'), true);
  assert.equal(store.latestRecommendationId(), 'companion-status');
  assert.deepEqual(store.snapshot().map(item => item.presentationId), ['status-1']);
});

test('CoreSessionManager voice requests keep token in main boundary and refresh once on 401', async () => {
  const calls = [];
  let voiceAttempts = 0;
  const manager = new CoreSessionManager({
    fetchImpl: async (url, init = {}) => {
      calls.push({ url, init });
      if (url.endsWith('/v1/auth/login')) {
        return response(200, { session_token: 'voice-access-old', refresh_token: 'voice-refresh-old', scopes: ['game:read'] });
      }
      if (url.endsWith('/v1/sessions/refresh')) {
        return response(200, { session_token: 'voice-access-new', refresh_token: 'voice-refresh-new', scopes: ['game:read'] });
      }
      if (url.endsWith('/v1/companion/voice/status')) {
        voiceAttempts += 1;
        if (voiceAttempts === 1) return response(401, { code: 'INVALID_SESSION' });
        return response(200, {
          stt_available: true, tts_available: false,
          capture_content_type: 'audio/webm;codecs=opus', synthesis_content_type: 'audio/wav',
          max_audio_bytes: 512000, max_text_chars: 2000, max_synthesized_bytes: 2000000,
          action_capable: false, request_id: 'status-after-refresh',
        });
      }
      throw new Error(`unexpected ${url}`);
    },
  });
  await manager.login({ coreUrl: 'http://127.0.0.1:8080', email: 'voice@example.com', password: 'secret' });
  const status = await manager.voiceStatus();
  assert.equal(status.stt_available, true);
  assert.equal(voiceAttempts, 2);
  const voiceCalls = calls.filter(call => call.url.endsWith('/v1/companion/voice/status'));
  assert.equal(voiceCalls[0].init.headers.Authorization, 'Bearer voice-access-old');
  assert.equal(voiceCalls[1].init.headers.Authorization, 'Bearer voice-access-new');
  assert.equal(JSON.stringify(status).includes('voice-access'), false);
});

test('launcher static voice composition has no arbitrary synthesis IPC and requests audio-only media', () => {
  const root = path.join(__dirname, '..');
  const main = fs.readFileSync(path.join(root, 'main.js'), 'utf8');
  const preload = fs.readFileSync(path.join(root, 'preload.js'), 'utf8');
  const renderer = fs.readFileSync(path.join(root, 'renderer.js'), 'utf8');
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');

  assert.match(main, /setPermissionCheckHandler/);
  assert.match(main, /setPermissionRequestHandler/);
  assert.match(main, /setDisplayMediaRequestHandler/);
  assert.match(main, /voiceConsentGranted/);
  assert.match(main, /overlayStore\.latestRecommendationId\(\)/);
  assert.doesNotMatch(main, /ipcMain\.handle\(['"]voice:synthesize/);
  assert.doesNotMatch(preload, /synthesizeVoice/);
  assert.match(preload, /submitVoice/);
  assert.match(renderer, /getUserMedia/);
  assert.match(renderer, /audio:\s*\{/);
  assert.match(renderer, /video:\s*false/);
  assert.match(renderer, /MediaRecorder/);
  assert.match(html, /I explicitly consent to microphone capture/);
  assert.match(html, /media-src 'self' blob:/);
});
