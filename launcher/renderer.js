'use strict';

const ui = window.sentinelUi;
const $ = id => document.getElementById(id);
const accountStatus = $('account-status');
const companionStatus = $('companion-status');
const wowCheckpointStatus = $('wow-checkpoint-status');
const voiceStatus = $('voice-status');
const knowledgeStatus = $('knowledge-status');
const knowledgeRefresh = $('knowledge-refresh');
const voiceResult = $('voice-result');
const connectionStatus = $('connection-status');
const voiceHeadline = $('voice-headline');
const voiceDetail = $('voice-detail');
const voiceMicState = $('voice-mic-state');
const voiceProviderState = $('voice-provider-state');
const resilienceSteps = Array.from(document.querySelectorAll('[data-runtime-state]'));
const voiceConsent = $('voice-consent');
const voiceLocale = $('voice-locale');
const voicePtt = $('voice-ptt');
const loginButton = $('login');
const mfaPanel = $('mfa-panel');
const mfaCode = $('mfa-code');
const mfaCompleteButton = $('mfa-complete');
const logoutButton = $('logout');
const startButton = $('companion-start');
const stopButton = $('companion-stop');
let signedIn = false;
let mfaRequired = false;
let companionState = 'STOPPED';
let grantedFeatures = [];
let currentVoice = {
  state: 'SIGNED_OUT', consentGranted: false, sttAvailable: false, ttsAvailable: false,
  maxAudioBytes: 512000, maxCaptureMs: 6000, captureContentType: 'audio/webm;codecs=opus', actionCapable: false,
};
let voiceRecorder = null;
let voiceStream = null;
let voiceChunks = [];
let voiceCaptureTimer = null;
let voiceCaptureDiscarded = false;
let voiceBusy = false;
let suppressNextVoiceClick = false;
let voiceHoldActive = false;

function refreshButtons() {
  loginButton.disabled = signedIn || mfaRequired;
  mfaPanel.hidden = !mfaRequired;
  mfaCompleteButton.disabled = !mfaRequired || String(mfaCode.value || '').trim().length < 6;
  logoutButton.disabled = !signedIn && !mfaRequired;
  startButton.disabled = !signedIn || companionState !== 'STOPPED' || !grantedFeatures.includes('companion');
  stopButton.disabled = companionState === 'STOPPED';

  const companionReady = ['ACTIVE', 'DEGRADED'].includes(companionState);
  const voiceReady = signedIn && grantedFeatures.includes('companion') && companionReady && currentVoice.consentGranted && currentVoice.sttAvailable;
  voiceConsent.disabled = !signedIn || !grantedFeatures.includes('companion') || voiceBusy || Boolean(voiceRecorder);
  voiceLocale.disabled = voiceBusy || Boolean(voiceRecorder);
  voicePtt.disabled = voiceRecorder ? false : (!voiceReady || voiceBusy);
  ui.text(voicePtt, voiceRecorder ? 'RELEASE TO SEND' : voiceBusy ? 'PROCESSING…' : 'HOLD TO TALK');
}

function setAccount(status, features = [], mfa = null) {
  signedIn = Boolean(status?.authenticated);
  mfaRequired = !signedIn && mfa?.required === true;
  grantedFeatures = signedIn && Array.isArray(features) ? [...features] : [];
  accountStatus.className = 'status ' + (signedIn ? 'ok' : mfaRequired ? 'warn' : '');
  ui.text(accountStatus, signedIn
    ? 'ACCOUNT: AUTHENTICATED / {entitlement}'
    : mfaRequired ? 'ACCOUNT: FIRST FACTOR VERIFIED / MFA REQUIRED' : 'ACCOUNT: SIGNED OUT',
    { entitlement: () => ui.t(grantedFeatures.includes('companion') ? 'COMPANION ENTITLED' : 'COMPANION NOT ENTITLED') });
  refreshButtons();
}

function setCompanion(status) {
  companionState = status?.state || 'STOPPED';
  const reason = status?.reason ? ` / ${status.reason}` : '';
  const warning = ['DEGRADED', 'LOCAL-ONLY', 'CONNECTING'].includes(companionState);
  const failed = companionState === 'OFFLINE';
  companionStatus.className = `status ${companionState === 'ACTIVE' ? 'ok' : warning ? 'warn' : failed ? 'err' : ''}`;
  ui.text(companionStatus, 'COMPANION: {state}{reason}', { state: () => ui.state(companionState), reason });

  const connectionLabel = companionState === 'ACTIVE' ? 'FULL' : companionState;
  if (connectionStatus) {
    connectionStatus.className = `status ${companionState === 'ACTIVE' ? 'ok' : warning ? 'warn' : failed ? 'err' : ''}`;
    ui.text(connectionStatus, 'CONNECTION: {state}{reason}', { state: () => ui.state(connectionLabel), reason });
  }
  for (const step of resilienceSteps) {
    step.dataset.current = String(step.dataset.runtimeState === companionState);
  }
  refreshButtons();
}

function setWowCheckpoint(status) {
  const state = status?.state || 'STOPPED';
  const depth = () => Number.isInteger(status?.queueDepth) ? ui.t(' / QUEUE {depth}', { depth: status.queueDepth }) : '';
  const reason = status?.reason ? ` / ${status.reason}` : '';
  const healthy = ['READY', 'DELIVERED'].includes(state);
  const warning = ['WAITING_FOR_SAVEDVARIABLES', 'DEFERRED', 'DELIVERING'].includes(state);
  wowCheckpointStatus.className = `status ${healthy ? 'ok' : warning ? 'warn' : state === 'STOPPED' ? '' : 'err'}`;
  ui.text(wowCheckpointStatus, 'WOW CHECKPOINT: {state}{depth}{reason}', { state: () => ui.state(state), depth, reason });
}

function setKnowledge(status) {
  const labels = {
    SIGNED_OUT: 'Knowledge: signed out', STOPPED: 'Knowledge: stopped',
    WAITING_FOR_VERIFIED_PROFILE: 'Knowledge: waiting for a verified game profile',
    READY: 'Knowledge: verified presentation lease', DEGRADED: 'Knowledge: network degraded; existing lease only',
    DENIED: 'Knowledge: access denied', UNAVAILABLE: 'Knowledge: unavailable',
  };
  const state = status?.state || 'UNAVAILABLE';
  ui.text(knowledgeStatus, Object.hasOwn(labels, state) ? labels[state] : labels.UNAVAILABLE);
  knowledgeStatus.className = `status ${state === 'READY' ? 'ok' : 'warn'}`;
  knowledgeRefresh.disabled = !['READY', 'DEGRADED', 'UNAVAILABLE'].includes(state);
}

knowledgeRefresh.addEventListener('click', async () => {
  knowledgeRefresh.disabled = true;
  try { setKnowledge(await window.sentinel.refreshKnowledge()); }
  catch { setKnowledge({ state: 'UNAVAILABLE' }); }
});

function setVoice(status) {
  currentVoice = status && typeof status === 'object' ? status : {
    state: 'UNAVAILABLE', consentGranted: false, sttAvailable: false, ttsAvailable: false,
    maxAudioBytes: 512000, maxCaptureMs: 6000, captureContentType: 'audio/webm;codecs=opus', actionCapable: false,
  };
  voiceConsent.checked = currentVoice.consentGranted === true;
  const state = String(currentVoice.state || 'UNAVAILABLE');
  const reason = currentVoice.reason ? ` / ${currentVoice.reason}` : '';
  const sttAvailable = currentVoice.sttAvailable;
  const ttsAvailable = currentVoice.ttsAvailable;
  const provider = () => sttAvailable ? ui.t(' / STT READY{tts}', { tts: ui.t(ttsAvailable ? ' / TTS READY' : ' / TTS UNAVAILABLE') }) : '';
  const healthy = state === 'READY';
  const warning = ['CONSENT_REQUIRED', 'PROVIDER_UNAVAILABLE', 'ENTITLEMENT_REQUIRED'].includes(state);
  voiceStatus.className = `status ${healthy ? 'ok' : warning ? 'warn' : state === 'SIGNED_OUT' ? '' : 'err'}`;
  ui.text(voiceStatus, 'VOICE: {state}{provider}{reason}', { state: () => ui.state(state), provider, reason });

  if (voiceProviderState) {
    ui.text(voiceProviderState, sttAvailable ? 'STT READY · {tts}' : 'UNAVAILABLE', { tts: () => ui.t(ttsAvailable ? 'TTS READY' : 'TTS UNAVAILABLE') });
  }
  if (voiceMicState && !voiceRecorder) ui.text(voiceMicState, 'CLOSED');
  if (voiceHeadline && voiceDetail && !voiceRecorder && !voiceBusy) {
    const copyByState = {
      READY: ['Hold to talk', 'The microphone opens only while you hold the control. Release to send.'],
      CONSENT_REQUIRED: ['Microphone consent required', 'Voice remains closed until you explicitly allow capture for this launcher session.'],
      PROVIDER_UNAVAILABLE: ['Voice provider unavailable', 'Text and non-voice Companion functions remain available.'],
      ENTITLEMENT_REQUIRED: ['Voice is not entitled', 'The current account does not have the required Companion voice capability.'],
      SIGNED_OUT: ['Voice is signed out', 'Sign in and start Companion to evaluate voice capability.'],
      UNAVAILABLE: ['Voice is unavailable', 'The current runtime cannot establish a voice provider boundary.'],
      DISABLED: ['Voice is off', 'The microphone is closed and no capture is active.'],
    };
    const copy = Object.hasOwn(copyByState, state) ? copyByState[state] : null;
    ui.text(voiceHeadline, copy ? copy[0] : 'Voice · {state}', { state });
    if (copy) ui.text(voiceDetail, copy[1]);
    else ui.text(voiceDetail, reason ? '{reason}' : 'Runtime voice state is authoritative from Core.', { reason: reason.slice(3) });
  }
  refreshButtons();
}

function showError(target, error) {
  target.className = 'status err';
  ui.text(target, '{error}', { error: String(error?.message || error || 'UNKNOWN_ERROR') });
}

async function refreshVoiceStatus() {
  try { setVoice(await window.sentinel.voiceStatus()); }
  catch (error) { showError(voiceStatus, error); }
}

async function renderGames() {
  const [catalog, config] = await Promise.all([window.sentinel.catalog(), window.sentinel.getConfig()]);
  const grid = $('grid');
  grid.replaceChildren();
  for (const game of catalog) {
    const card = document.createElement('section');
    card.className = 'card';
    const title = document.createElement('strong');
    title.textContent = game.name;
    const platform = document.createElement('div');
    platform.className = 'sub';
    platform.textContent = String(game.platform || '').toUpperCase();
    card.append(title, platform);

    const button = document.createElement('button');
    button.className = 'btn';
    ui.text(button, game.platform === 'android' ? 'USE ANDROID CLIENT' : 'LAUNCH');
    button.disabled = game.platform === 'android';
    button.onclick = async () => {
      try { await window.sentinel.launch(game.id); } catch (error) { window.alert(String(error?.message || error)); }
    };
    card.appendChild(button);

    if (game.platform === 'windows') {
      const configured = document.createElement('div');
      configured.className = 'sub';
      configured.style.marginTop = '12px';
      ui.text(configured, config[game.id] ? 'EXECUTABLE CONFIGURED' : 'EXECUTABLE NOT CONFIGURED');
      card.appendChild(configured);
    }
    grid.appendChild(card);
  }
}

function stopVoiceTracks() {
  if (voiceStream) {
    for (const track of voiceStream.getTracks()) track.stop();
  }
  voiceStream = null;
}

function clearVoiceTimer() {
  if (voiceCaptureTimer) clearTimeout(voiceCaptureTimer);
  voiceCaptureTimer = null;
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('VOICE_CAPTURE_READ_FAILED'));
    reader.onload = () => {
      const result = String(reader.result || '');
      const comma = result.indexOf(',');
      if (comma < 0) reject(new Error('VOICE_CAPTURE_READ_FAILED'));
      else resolve(result.slice(comma + 1));
    };
    reader.readAsDataURL(blob);
  });
}

async function playFeedbackAudio(feedback) {
  if (!feedback?.audioBase64 || feedback.contentType !== 'audio/wav') return;
  const binary = atob(feedback.audioBase64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  const url = URL.createObjectURL(new Blob([bytes], { type: feedback.contentType }));
  const player = new Audio(url);
  const cleanup = () => URL.revokeObjectURL(url);
  player.addEventListener('ended', cleanup, { once: true });
  player.addEventListener('error', cleanup, { once: true });
  try { await player.play(); } catch { cleanup(); }
}

async function submitVoiceBlob(blob) {
  if (!blob.size) throw new Error('VOICE_CAPTURE_EMPTY');
  if (blob.size > Number(currentVoice.maxAudioBytes || 512000)) throw new Error('VOICE_AUDIO_TOO_LARGE');
  const response = await window.sentinel.submitVoice({
    audioBase64: await blobToBase64(blob),
    locale: voiceLocale.value,
  });
  const result = response?.result;
  if (!result || typeof result.reasonCode !== 'string') throw new Error('VOICE_RESPONSE_INVALID');
  const mode = result.intent?.mode ? ` / ${result.intent.mode}` : '';
  const feedback = response.feedbackReason ? ` / ${response.feedbackReason}` : '';
  voiceResult.className = `status ${result.accepted ? 'ok' : result.reasonCode === 'ACTION_GATEWAY_REQUIRED' ? 'warn' : ''}`;
  ui.text(voiceResult, 'VOICE RESULT: {code}{mode}{feedback}', { code: result.reasonCode, mode, feedback });
  if (voiceHeadline && voiceDetail) {
    ui.text(voiceHeadline, result.accepted ? 'Voice request understood' : 'Voice request not accepted');
    ui.text(voiceDetail, result.accepted
      ? 'Core accepted the presentation intent. No autonomous game action was performed.'
      : 'Core kept the request fail-closed: {code}.', { code: result.reasonCode });
  }
  if (response.feedbackAudio) await playFeedbackAudio(response.feedbackAudio);
}

async function finalizeVoiceCapture() {
  clearVoiceTimer();
  const chunks = voiceChunks;
  const discarded = voiceCaptureDiscarded;
  voiceChunks = [];
  voiceCaptureDiscarded = false;
  voiceRecorder = null;
  stopVoiceTracks();
  voiceBusy = true;
  if (voiceMicState) ui.text(voiceMicState, 'CLOSED');
  if (discarded) {
    if (voiceHeadline) ui.text(voiceHeadline, 'Capture canceled');
    if (voiceDetail) ui.text(voiceDetail, 'Nothing was sent. Hold the control again when you are ready.');
    voiceResult.className = 'status';
    ui.text(voiceResult, 'VOICE RESULT: CANCELED');
  } else {
    if (voiceHeadline) ui.text(voiceHeadline, 'Understanding request');
    if (voiceDetail) ui.text(voiceDetail, 'Capture ended. SENTINEL is evaluating the bounded voice request.');
  }
  refreshButtons();
  try {
    if (discarded) return;
    const blob = new Blob(chunks, { type: currentVoice.captureContentType || 'audio/webm;codecs=opus' });
    await submitVoiceBlob(blob);
  } catch (error) {
    showError(voiceResult, error);
  } finally {
    voiceBusy = false;
    refreshButtons();
  }
}

async function startVoiceCapture() {
  if (voiceRecorder || voiceBusy) return;
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') throw new Error('VOICE_CAPTURE_UNAVAILABLE');
  const mimeType = currentVoice.captureContentType || 'audio/webm;codecs=opus';
  if (typeof MediaRecorder.isTypeSupported === 'function' && !MediaRecorder.isTypeSupported(mimeType)) throw new Error('VOICE_CAPTURE_FORMAT_UNSUPPORTED');

  voiceBusy = true;
  refreshButtons();
  let armed = false;
  try {
    const lease = await window.sentinel.armVoiceCapture();
    if (!lease?.armed || lease.actionCapable !== false) throw new Error('VOICE_CAPTURE_PERMISSION_DENIED');
    armed = true;
    try {
      voiceStream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        video: false,
      });
    } finally {
      if (armed) {
        armed = false;
        try { await window.sentinel.disarmVoiceCapture(); } catch { /* lease expires fail-closed */ }
      }
    }
    voiceChunks = [];
    voiceCaptureDiscarded = false;
    const recorder = new MediaRecorder(voiceStream, { mimeType, audioBitsPerSecond: 64000 });
    voiceRecorder = recorder;
    if (voiceMicState) ui.text(voiceMicState, 'OPEN · HOLDING');
    if (voiceHeadline) ui.text(voiceHeadline, 'Listening…');
    if (voiceDetail) ui.text(voiceDetail, 'Release to send. Move away from the control to cancel without submitting.');
    recorder.ondataavailable = event => { if (event.data?.size) voiceChunks.push(event.data); };
    recorder.onerror = () => {
      voiceCaptureDiscarded = true;
      showError(voiceResult, new Error('VOICE_CAPTURE_FAILED'));
      if (recorder.state !== 'inactive') recorder.stop();
    };
    recorder.onstop = () => { void finalizeVoiceCapture(); };
    recorder.start(250);
    const maxMs = Math.min(Math.max(Number(currentVoice.maxCaptureMs || 6000), 1000), 6000);
    voiceCaptureTimer = setTimeout(() => { if (recorder.state !== 'inactive') recorder.stop(); }, maxMs);
    voiceResult.className = 'status warn';
    ui.text(voiceResult, 'VOICE RESULT: CAPTURING / MAX {seconds}s', { seconds: Math.round(maxMs / 1000) });
  } catch (error) {
    if (armed) {
      try { await window.sentinel.disarmVoiceCapture(); } catch { /* lease expires fail-closed */ }
    }
    stopVoiceTracks();
    voiceRecorder = null;
    voiceCaptureDiscarded = false;
    throw error;
  } finally {
    voiceBusy = false;
    refreshButtons();
  }
}

function stopVoiceCapture() {
  clearVoiceTimer();
  if (voiceRecorder && voiceRecorder.state !== 'inactive') {
    voiceBusy = true;
    refreshButtons();
    voiceRecorder.stop();
  }
}

function cancelVoiceCapture() {
  clearVoiceTimer();
  voiceCaptureDiscarded = true;
  voiceChunks = [];
  if (voiceRecorder && voiceRecorder.state !== 'inactive') {
    voiceBusy = true;
    refreshButtons();
    voiceRecorder.stop();
    return;
  }
  voiceRecorder = null;
  stopVoiceTracks();
  if (voiceMicState) ui.text(voiceMicState, 'CLOSED');
  if (voiceHeadline) ui.text(voiceHeadline, 'Capture canceled');
  if (voiceDetail) ui.text(voiceDetail, 'Nothing was sent. Hold the control again when you are ready.');
  voiceBusy = false;
  refreshButtons();
}

loginButton.onclick = async () => {
  loginButton.disabled = true;
  try {
    const result = await window.sentinel.login($('core-url').value, $('email').value, $('password').value);
    $('password').value = '';
    setAccount(result.session, result.features || [], result.mfa);
    if (result.mfa?.required) {
      mfaCode.focus();
    } else {
      await refreshVoiceStatus();
    }
  } catch (error) {
    loginButton.disabled = false;
    showError(accountStatus, error);
  }
};

mfaCode.oninput = refreshButtons;

mfaCompleteButton.onclick = async () => {
  mfaCompleteButton.disabled = true;
  try {
    const result = await window.sentinel.completeMfa(mfaCode.value);
    mfaCode.value = '';
    setAccount(result.session, result.features || [], result.mfa);
    await refreshVoiceStatus();
  } catch (error) {
    showError(accountStatus, error);
    refreshButtons();
  }
};

logoutButton.onclick = async () => {
  cancelVoiceCapture();
  await window.sentinel.logout();
  setCompanion({ state: 'STOPPED', reason: 'ACCOUNT_LOGOUT' });
  setWowCheckpoint({ state: 'STOPPED', queueDepth: 0 });
  mfaCode.value = '';
  setAccount(null, [], null);
  setVoice({ state: 'SIGNED_OUT', consentGranted: false, sttAvailable: false, ttsAvailable: false, maxAudioBytes: 512000, maxCaptureMs: 6000, captureContentType: 'audio/webm;codecs=opus', actionCapable: false });
};

startButton.onclick = async () => {
  startButton.disabled = true;
  try {
    setCompanion(await window.sentinel.startCompanion($('core-url').value));
    await refreshVoiceStatus();
  } catch (error) { showError(companionStatus, error); refreshButtons(); }
};
stopButton.onclick = async () => {
  const confirmed = window.confirm(ui.t('Stop SENTINEL Companion runtime? Active local runtime and presentation state will stop.'));
  if (!confirmed) return;
  cancelVoiceCapture();
  setWowCheckpoint({ state: 'STOPPED' });
  setCompanion(await window.sentinel.stopCompanion());
};

voiceConsent.onchange = async () => {
  const requested = voiceConsent.checked;
  try { setVoice(await window.sentinel.setVoiceConsent(requested)); }
  catch (error) {
    voiceConsent.checked = false;
    showError(voiceStatus, error);
    await refreshVoiceStatus();
  }
};

async function beginVoiceHold() {
  if (voiceRecorder || voiceBusy || voicePtt.disabled) return;
  try {
    await startVoiceCapture();
    if (!voiceHoldActive && voiceRecorder) stopVoiceCapture();
  }
  catch (error) {
    showError(voiceResult, error);
    if (voiceMicState) ui.text(voiceMicState, 'CLOSED');
    if (voiceHeadline) ui.text(voiceHeadline, 'Voice capture unavailable');
    if (voiceDetail) ui.text(voiceDetail, '{error}', { error: String(error?.message || error || 'VOICE_CAPTURE_FAILED') });
    refreshButtons();
  }
}

voicePtt.addEventListener('pointerdown', event => {
  if (voicePtt.disabled) return;
  suppressNextVoiceClick = true;
  voiceHoldActive = true;
  event.preventDefault();
  void beginVoiceHold();
});
voicePtt.addEventListener('pointerup', event => {
  voiceHoldActive = false;
  event.preventDefault();
  if (voiceRecorder) stopVoiceCapture();
});
voicePtt.addEventListener('pointerleave', () => {
  voiceHoldActive = false;
  suppressNextVoiceClick = false;
  if (voiceRecorder) cancelVoiceCapture();
});
voicePtt.addEventListener('pointercancel', () => {
  voiceHoldActive = false;
  suppressNextVoiceClick = false;
  if (voiceRecorder) cancelVoiceCapture();
});
voicePtt.addEventListener('keydown', event => {
  if (![' ', 'Enter'].includes(event.key) || event.repeat || voicePtt.disabled) return;
  suppressNextVoiceClick = true;
  voiceHoldActive = true;
  event.preventDefault();
  void beginVoiceHold();
});
voicePtt.addEventListener('keyup', event => {
  if (![' ', 'Enter'].includes(event.key)) return;
  voiceHoldActive = false;
  event.preventDefault();
  if (voiceRecorder) stopVoiceCapture();
});
voicePtt.addEventListener('click', event => {
  if (suppressNextVoiceClick) {
    suppressNextVoiceClick = false;
    event.preventDefault();
    return;
  }
  // Assistive-technology fallback where no pointer/key hold events are emitted:
  // first activation starts a bounded capture, second activation sends it.
  if (voiceRecorder) {
    voiceHoldActive = false;
    stopVoiceCapture();
  } else {
    voiceHoldActive = true;
    void beginVoiceHold();
  }
});

window.sentinel.onCompanionStatus(setCompanion);
window.sentinel.onAccountStatus(snapshot => setAccount(snapshot?.session, snapshot?.features || [], snapshot?.mfa));
window.sentinel.onWowCheckpointStatus(setWowCheckpoint);
window.sentinel.onVoiceStatus(setVoice);
window.sentinel.onKnowledgeStatus(setKnowledge);

Promise.all([window.sentinel.accountStatus(), window.sentinel.companionStatus(), window.sentinel.voiceStatus(), renderGames()])
  .then(([snapshot, companion, voice]) => {
    setAccount(snapshot?.session, snapshot?.features || [], snapshot?.mfa);
    setCompanion(companion);
    setVoice(voice);
    setWowCheckpoint({ state: 'STOPPED' });
  })
  .catch(error => showError(companionStatus, error));
window.sentinel.knowledgeStatus().then(setKnowledge).catch(() => setKnowledge({ state: 'UNAVAILABLE' }));
