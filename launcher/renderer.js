'use strict';

const $ = id => document.getElementById(id);
const accountStatus = $('account-status');
const companionStatus = $('companion-status');
const wowCheckpointStatus = $('wow-checkpoint-status');
const voiceStatus = $('voice-status');
const voiceResult = $('voice-result');
const voiceConsent = $('voice-consent');
const voiceLocale = $('voice-locale');
const voicePtt = $('voice-ptt');
const loginButton = $('login');
const logoutButton = $('logout');
const startButton = $('companion-start');
const stopButton = $('companion-stop');
let signedIn = false;
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

function refreshButtons() {
  loginButton.disabled = signedIn;
  logoutButton.disabled = !signedIn;
  startButton.disabled = !signedIn || companionState !== 'STOPPED' || !grantedFeatures.includes('companion');
  stopButton.disabled = companionState === 'STOPPED';

  const companionReady = ['ACTIVE', 'DEGRADED'].includes(companionState);
  const voiceReady = signedIn && grantedFeatures.includes('companion') && companionReady && currentVoice.consentGranted && currentVoice.sttAvailable;
  voiceConsent.disabled = !signedIn || !grantedFeatures.includes('companion') || voiceBusy || Boolean(voiceRecorder);
  voiceLocale.disabled = voiceBusy || Boolean(voiceRecorder);
  voicePtt.disabled = voiceRecorder ? false : (!voiceReady || voiceBusy);
  voicePtt.textContent = voiceRecorder ? 'STOP & SEND' : voiceBusy ? 'PROCESSING…' : 'START PUSH-TO-TALK';
}

function setAccount(status, features = []) {
  signedIn = Boolean(status?.authenticated);
  grantedFeatures = signedIn && Array.isArray(features) ? [...features] : [];
  accountStatus.className = `status ${signedIn ? 'ok' : ''}`;
  accountStatus.textContent = signedIn
    ? `ACCOUNT: AUTHENTICATED / ${grantedFeatures.includes('companion') ? 'COMPANION ENTITLED' : 'COMPANION NOT ENTITLED'}`
    : 'ACCOUNT: SIGNED OUT';
  refreshButtons();
}

function setCompanion(status) {
  companionState = status?.state || 'STOPPED';
  const reason = status?.reason ? ` / ${status.reason}` : '';
  companionStatus.className = `status ${companionState === 'ACTIVE' ? 'ok' : companionState === 'DEGRADED' ? 'warn' : ''}`;
  companionStatus.textContent = `COMPANION: ${companionState}${reason}`;
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
  refreshButtons();
  try {
    if (discarded) throw new Error('VOICE_CAPTURE_DISCARDED');
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
  try {
    voiceStream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      video: false,
    });
    voiceChunks = [];
    voiceCaptureDiscarded = false;
    const recorder = new MediaRecorder(voiceStream, { mimeType, audioBitsPerSecond: 64000 });
    voiceRecorder = recorder;
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
  voiceBusy = false;
  refreshButtons();
}

loginButton.onclick = async () => {
  loginButton.disabled = true;
  try {
    const result = await window.sentinel.login($('core-url').value, $('email').value, $('password').value);
    $('password').value = '';
    setAccount(result.session, result.features || []);
    await refreshVoiceStatus();
  } catch (error) {
    loginButton.disabled = false;
    showError(accountStatus, error);
  }
};

logoutButton.onclick = async () => {
  cancelVoiceCapture();
  await window.sentinel.logout();
  setCompanion({ state: 'STOPPED', reason: 'ACCOUNT_LOGOUT' });
  setWowCheckpoint({ state: 'STOPPED', queueDepth: 0 });
  setAccount(null, []);
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

voicePtt.onclick = async () => {
  if (voiceRecorder) {
    stopVoiceCapture();
    return;
  }
  try { await startVoiceCapture(); }
  catch (error) { showError(voiceResult, error); refreshButtons(); }
};

window.sentinel.onCompanionStatus(setCompanion);
window.sentinel.onAccountStatus(snapshot => setAccount(snapshot?.session, snapshot?.features || []));
window.sentinel.onWowCheckpointStatus(setWowCheckpoint);
window.sentinel.onVoiceStatus(setVoice);

Promise.all([window.sentinel.accountStatus(), window.sentinel.companionStatus(), window.sentinel.voiceStatus(), renderGames()])
  .then(([snapshot, companion, voice]) => {
    setAccount(snapshot?.session, snapshot?.features || []);
    setCompanion(companion);
    setVoice(voice);
    setWowCheckpoint({ state: 'STOPPED' });
  })
  .catch(error => showError(companionStatus, error));
