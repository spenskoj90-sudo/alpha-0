'use strict';

const $ = id => document.getElementById(id);
const accountStatus = $('account-status');
const companionStatus = $('companion-status');
const wowCheckpointStatus = $('wow-checkpoint-status');
const voiceStatus = $('voice-status');
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
  voicePtt.textContent = voiceRecorder ? 'RELEASE TO SEND' : voiceBusy ? 'PROCESSING…' : 'HOLD TO TALK';
}

function setAccount(status, features = [], mfa = null) {
  signedIn = Boolean(status?.authenticated);
  mfaRequired = !signedIn && mfa?.required === true;
  grantedFeatures = signedIn && Array.isArray(features) ? [...features] : [];
  accountStatus.className = 'status ' + (signedIn ? 'ok' : mfaRequired ? 'warn' : '');
  accountStatus.textContent = signedIn
    ? 'ACCOUNT: AUTHENTICATED / ' + (grantedFeatures.includes('companion') ? 'COMPANION ENTITLED' : 'COMPANION NOT ENTITLED')
    : mfaRequired
      ? 'ACCOUNT: FIRST FACTOR VERIFIED / MFA REQUIRED'
      : 'ACCOUNT: SIGNED OUT';
  refreshButtons();
}

function setCompanion(status) {
  companionState = status?.state || 'STOPPED';
  const reason = status?.reason ? ` / ${status.reason}` : '';
  const warning = ['DEGRADED', 'LOCAL-ONLY', 'CONNECTING'].includes(companionState);
  const failed = companionState === 'OFFLINE';
  companionStatus.className = `status ${companionState === 'ACTIVE' ? 'ok' : warning ? 'warn' : failed ? 'err' : ''}`;
  companionStatus.textContent = `COMPANION: ${companionState}${reason}`;

  const connectionLabel = companionState === 'ACTIVE' ? 'FULL' : companionState;
  if (connectionStatus) {
    connectionStatus.className = `status ${companionState === 'ACTIVE' ? 'ok' : warning ? 'warn' : failed ? 'err' : ''}`;
    connectionStatus.textContent = `CONNECTION: ${connectionLabel}${reason}`;
  }
  for (const step of resilienceSteps) {
    step.dataset.current = String(step.dataset.runtimeState === companionState);
  }
  refreshButtons();
}

function setWowCheckpoint(status) {
  const state = status?.state || 'STOPPED';
  const depth = Number.isInteger(status?.queueDepth) ? ` / QUEUE ${status.queueDepth}` : '';
  const reason = status?.reason ? ` / ${status.reason}` : '';
  const healthy = ['READY', 'DELIVERED'].includes(state);
  const warning = ['WAITING_FOR_SAVEDVARIABLES', 'DEFERRED', 'DELIVERING'].includes(state);
  wowCheckpointStatus.className = `status ${healthy ? 'ok' : warning ? 'warn' : state === 'STOPPED' ? '' : 'err'}`;
  wowCheckpointStatus.textContent = `WOW CHECKPOINT: ${state}${depth}${reason}`;
}

function setVoice(status) {
  currentVoice = status && typeof status === 'object' ? status : {
    state: 'UNAVAILABLE', consentGranted: false, sttAvailable: false, ttsAvailable: false,
    maxAudioBytes: 512000, maxCaptureMs: 6000, captureContentType: 'audio/webm;codecs=opus', actionCapable: false,
  };
  voiceConsent.checked = currentVoice.consentGranted === true;
  const state = String(currentVoice.state || 'UNAVAILABLE');
  const reason = currentVoice.reason ? ` / ${currentVoice.reason}` : '';
  const provider = currentVoice.sttAvailable ? ` / STT READY${currentVoice.ttsAvailable ? ' / TTS READY' : ' / TTS UNAVAILABLE'}` : '';
  const healthy = state === 'READY';
  const warning = ['CONSENT_REQUIRED', 'PROVIDER_UNAVAILABLE', 'ENTITLEMENT_REQUIRED'].includes(state);
  voiceStatus.className = `status ${healthy ? 'ok' : warning ? 'warn' : state === 'SIGNED_OUT' ? '' : 'err'}`;
  voiceStatus.textContent = `VOICE: ${state}${provider}${reason}`;

  if (voiceProviderState) {
    voiceProviderState.textContent = currentVoice.sttAvailable
      ? `STT READY · ${currentVoice.ttsAvailable ? 'TTS READY' : 'TTS UNAVAILABLE'}`
      : 'UNAVAILABLE';
  }
  if (voiceMicState && !voiceRecorder) voiceMicState.textContent = 'CLOSED';
  if (voiceHeadline && voiceDetail && !voiceRecorder && !voiceBusy) {
    const copy = {
      READY: ['Hold to talk', 'The microphone opens only while you hold the control. Release to send.'],
      CONSENT_REQUIRED: ['Microphone consent required', 'Voice remains closed until you explicitly allow capture for this launcher session.'],
      PROVIDER_UNAVAILABLE: ['Voice provider unavailable', 'Text and non-voice Companion functions remain available.'],
      ENTITLEMENT_REQUIRED: ['Voice is not entitled', 'The current account does not have the required Companion voice capability.'],
      SIGNED_OUT: ['Voice is signed out', 'Sign in and start Companion to evaluate voice capability.'],
      UNAVAILABLE: ['Voice is unavailable', 'The current runtime cannot establish a voice provider boundary.'],
      DISABLED: ['Voice is off', 'The microphone is closed and no capture is active.'],
    }[state] || [`Voice · ${state}`, reason ? reason.slice(3) : 'Runtime voice state is authoritative from Core.'];
    voiceHeadline.textContent = copy[0];
    voiceDetail.textContent = copy[1];
  }
  refreshButtons();
}

function showError(target, error) {
  target.className = 'status err';
  target.textContent = String(error?.message || error || 'UNKNOWN_ERROR');
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
    button.textContent = game.platform === 'android' ? 'USE ANDROID CLIENT' : 'LAUNCH';
    button.disabled = game.platform === 'android';
    button.onclick = async () => {
      try { await window.sentinel.launch(game.id); } catch (error) { window.alert(String(error?.message || error)); }
    };
    card.appendChild(button);

    if (game.platform === 'windows') {
      const configured = document.createElement('div');
      configured.className = 'sub';
      configured.style.marginTop = '12px';
      configured.textContent = config[game.id] ? 'EXECUTABLE CONFIGURED' : 'EXECUTABLE NOT CONFIGURED';
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
  voiceResult.textContent = `VOICE RESULT: ${result.reasonCode}${mode}${feedback}`;
  if (voiceHeadline && voiceDetail) {
    voiceHeadline.textContent = result.accepted ? 'Voice request understood' : 'Voice request not accepted';
    voiceDetail.textContent = result.accepted
      ? 'Core accepted the presentation intent. No autonomous game action was performed.'
      : `Core kept the request fail-closed: ${result.reasonCode}.`;
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
  if (voiceMicState) voiceMicState.textContent = 'CLOSED';
  if (discarded) {
    if (voiceHeadline) voiceHeadline.textContent = 'Capture canceled';
    if (voiceDetail) voiceDetail.textContent = 'Nothing was sent. Hold the control again when you are ready.';
    voiceResult.className = 'status';
    voiceResult.textContent = 'VOICE RESULT: CANCELED';
  } else {
    if (voiceHeadline) voiceHeadline.textContent = 'Understanding request';
    if (voiceDetail) voiceDetail.textContent = 'Capture ended. SENTINEL is evaluating the bounded voice request.';
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
    if (voiceMicState) voiceMicState.textContent = 'OPEN · HOLDING';
    if (voiceHeadline) voiceHeadline.textContent = 'Listening…';
    if (voiceDetail) voiceDetail.textContent = 'Release to send. Move away from the control to cancel without submitting.';
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
    voiceResult.textContent = `VOICE RESULT: CAPTURING / MAX ${Math.round(maxMs / 1000)}s`;
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
  if (voiceMicState) voiceMicState.textContent = 'CLOSED';
  if (voiceHeadline) voiceHeadline.textContent = 'Capture canceled';
  if (voiceDetail) voiceDetail.textContent = 'Nothing was sent. Hold the control again when you are ready.';
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
  const confirmed = window.confirm('Stop SENTINEL Companion runtime? Active local runtime and presentation state will stop.');
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
    if (voiceMicState) voiceMicState.textContent = 'CLOSED';
    if (voiceHeadline) voiceHeadline.textContent = 'Voice capture unavailable';
    if (voiceDetail) voiceDetail.textContent = String(error?.message || error || 'VOICE_CAPTURE_FAILED');
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

Promise.all([window.sentinel.accountStatus(), window.sentinel.companionStatus(), window.sentinel.voiceStatus(), renderGames()])
  .then(([snapshot, companion, voice]) => {
    setAccount(snapshot?.session, snapshot?.features || [], snapshot?.mfa);
    setCompanion(companion);
    setVoice(voice);
    setWowCheckpoint({ state: 'STOPPED' });
  })
  .catch(error => showError(companionStatus, error));
