'use strict';

const MAX_AUDIO_BYTES = 512000;
const MAX_SYNTHESIZED_BYTES = 2000000;
const MAX_CAPTURE_MS = 6000;
const CAPTURE_CONTENT_TYPE = 'audio/webm;codecs=opus';
const SYNTHESIS_CONTENT_TYPE = 'audio/wav';
const ALLOWED_MODES = new Set(['OBSERVE', 'ACKNOWLEDGE', 'DISMISS']);
const ALLOWED_REASON_CODES = new Set([
  'VOICE_ACCEPTED',
  'VOICE_COMMAND_UNSUPPORTED',
  'ACTION_GATEWAY_REQUIRED',
  'VOICE_TEXT_TOO_LARGE',
]);
const ID_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const LOCALE_PATTERN = /^[A-Za-z0-9-]{2,16}$/;

function boundedRequestId(value) {
  return typeof value === 'string' && value.length >= 1 && value.length <= 128 ? value : null;
}

function sanitizeVoiceStatus(value) {
  if (!value || typeof value !== 'object') return null;
  if (typeof value.stt_available !== 'boolean' || typeof value.tts_available !== 'boolean') return null;
  if (value.capture_content_type !== CAPTURE_CONTENT_TYPE || value.synthesis_content_type !== SYNTHESIS_CONTENT_TYPE) return null;
  if (!Number.isInteger(value.max_audio_bytes) || value.max_audio_bytes < 1 || value.max_audio_bytes > MAX_AUDIO_BYTES) return null;
  if (!Number.isInteger(value.max_text_chars) || value.max_text_chars < 1 || value.max_text_chars > 2000) return null;
  if (!Number.isInteger(value.max_synthesized_bytes) || value.max_synthesized_bytes < 1 || value.max_synthesized_bytes > MAX_SYNTHESIZED_BYTES) return null;
  if (value.action_capable !== false) return null;
  const requestId = boundedRequestId(value.request_id);
  if (!requestId) return null;
  return Object.freeze({
    sttAvailable: value.stt_available,
    ttsAvailable: value.tts_available,
    captureContentType: CAPTURE_CONTENT_TYPE,
    synthesisContentType: SYNTHESIS_CONTENT_TYPE,
    maxAudioBytes: value.max_audio_bytes,
    maxTextChars: value.max_text_chars,
    maxSynthesizedBytes: value.max_synthesized_bytes,
    actionCapable: false,
    requestId,
  });
}

function sanitizeVoiceResult(value) {
  if (!value || typeof value !== 'object' || typeof value.accepted !== 'boolean') return null;
  if (!ALLOWED_REASON_CODES.has(value.reason_code) || value.action_capable !== false) return null;
  const requestId = boundedRequestId(value.request_id);
  if (!requestId) return null;
  let intent = null;
  if (value.intent != null) {
    if (!value.intent || typeof value.intent !== 'object') return null;
    if (value.intent.surface !== 'VOICE' || !ALLOWED_MODES.has(value.intent.mode)) return null;
    if (typeof value.intent.recommendation_id !== 'string' || !ID_PATTERN.test(value.intent.recommendation_id)) return null;
    if (typeof value.intent.locale !== 'string' || !LOCALE_PATTERN.test(value.intent.locale)) return null;
    intent = Object.freeze({
      surface: 'VOICE',
      mode: value.intent.mode,
      recommendationId: value.intent.recommendation_id,
      locale: value.intent.locale,
    });
  }
  if (value.accepted !== Boolean(intent)) return null;
  return Object.freeze({
    accepted: value.accepted,
    reasonCode: value.reason_code,
    intent,
    actionCapable: false,
    requestId,
  });
}

function sanitizeSynthesizedAudio(value) {
  if (!value || typeof value !== 'object') return null;
  if (value.content_type !== SYNTHESIS_CONTENT_TYPE || value.action_capable !== false) return null;
  if (!Number.isInteger(value.bytes) || value.bytes < 1 || value.bytes > MAX_SYNTHESIZED_BYTES) return null;
  const requestId = boundedRequestId(value.request_id);
  if (!requestId || typeof value.audio_b64 !== 'string') return null;
  const audio = decodeCanonicalBase64(value.audio_b64);
  if (!audio || audio.length !== value.bytes || audio.length > MAX_SYNTHESIZED_BYTES) return null;
  return Object.freeze({
    audioBase64: value.audio_b64,
    contentType: SYNTHESIS_CONTENT_TYPE,
    bytes: value.bytes,
    actionCapable: false,
    requestId,
  });
}

function decodeCanonicalBase64(value) {
  if (typeof value !== 'string' || !value || value.length % 4 !== 0 || !/^[A-Za-z0-9+/]*={0,2}$/.test(value)) return null;
  let decoded;
  try { decoded = Buffer.from(value, 'base64'); } catch { return null; }
  return decoded.toString('base64') === value ? decoded : null;
}

function validateCapturePayload(value, maxAudioBytes = MAX_AUDIO_BYTES) {
  if (!value || typeof value !== 'object') throw new Error('VOICE_CAPTURE_INVALID');
  if (typeof value.audioBase64 !== 'string') throw new Error('VOICE_CAPTURE_INVALID');
  if (typeof value.locale !== 'string' || !LOCALE_PATTERN.test(value.locale)) throw new Error('VOICE_LOCALE_INVALID');
  if (!Number.isInteger(maxAudioBytes) || maxAudioBytes < 1 || maxAudioBytes > MAX_AUDIO_BYTES) throw new Error('VOICE_CAPTURE_LIMIT_INVALID');
  const audio = decodeCanonicalBase64(value.audioBase64);
  if (!audio) throw new Error('VOICE_CAPTURE_INVALID');
  if (audio.length > maxAudioBytes) throw new Error('VOICE_AUDIO_TOO_LARGE');
  return Object.freeze({ audioBase64: value.audioBase64, locale: value.locale, bytes: audio.length });
}

function feedbackTextForVoiceResult(result) {
  if (!result) return null;
  if (result.accepted && result.intent?.mode === 'ACKNOWLEDGE') return 'Acknowledged.';
  if (result.accepted && result.intent?.mode === 'DISMISS') return 'Dismissed.';
  if (result.accepted && result.intent?.mode === 'OBSERVE') return 'Status requested.';
  if (result.reasonCode === 'ACTION_GATEWAY_REQUIRED') return 'Voice cannot execute game actions.';
  if (result.reasonCode === 'VOICE_COMMAND_UNSUPPORTED') return 'Voice command not recognized.';
  return null;
}

function mediaPermissionAllowed({ webContents, mainWebContents, permission, requestingOrigin, details, consentGranted }) {
  if (!consentGranted || permission !== 'media' || !webContents || webContents !== mainWebContents) return false;
  const origin = String(details?.securityOrigin || requestingOrigin || webContents.getURL?.() || '');
  if (origin !== 'file://' && !origin.startsWith('file:///')) return false;
  const mediaTypes = Array.isArray(details?.mediaTypes) ? details.mediaTypes : [];
  if (mediaTypes.includes('video')) return false;
  return mediaTypes.length === 0 || mediaTypes.includes('audio');
}

module.exports = {
  CAPTURE_CONTENT_TYPE,
  MAX_AUDIO_BYTES,
  MAX_CAPTURE_MS,
  MAX_SYNTHESIZED_BYTES,
  SYNTHESIS_CONTENT_TYPE,
  feedbackTextForVoiceResult,
  mediaPermissionAllowed,
  sanitizeSynthesizedAudio,
  sanitizeVoiceResult,
  sanitizeVoiceStatus,
  validateCapturePayload,
};
