'use strict';

const { app, BrowserWindow, ipcMain, screen, session: electronSession } = require('electron');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { CoreSessionManager, normalizeCoreUrl } = require('./core-session');
const { CompanionProcessManager } = require('./companion-process');
const { OverlayPresentationStore } = require('./overlay-state');
const {
  CAPTURE_CONTENT_TYPE,
  MAX_AUDIO_BYTES,
  MAX_CAPTURE_MS,
  feedbackTextForVoiceResult,
  mediaPermissionAllowed,
  sanitizeSynthesizedAudio,
  sanitizeVoiceResult,
  sanitizeVoiceStatus,
  validateCapturePayload,
} = require('./voice-runtime');
const {
  WowCheckpointBridge,
  WowObservationQueue,
  discoverSentinelSavedVariables,
} = require('./wow-savedvariables');

const VOICE_CAPTURE_PERMISSION_LEASE_MS = 5000;
const catalog = [
  { id: 'world-of-warcraft', name: 'World of Warcraft', platform: 'windows' },
  { id: 'diablo-1-pc', name: 'Diablo', platform: 'windows' },
  { id: 'diablo-2-pc', name: 'Diablo II', platform: 'windows' },
  { id: 'diablo-2-resurrected-pc', name: 'Diablo II: Resurrected', platform: 'windows' },
  { id: 'diablo-3-pc', name: 'Diablo III', platform: 'windows' },
  { id: 'diablo-4-pc', name: 'Diablo IV', platform: 'windows' },
  { id: 'diablo-immortal-android', name: 'Diablo Immortal', platform: 'android' },
];

const session = new CoreSessionManager();
const overlayStore = new OverlayPresentationStore({ maxItems: 4, ttlMs: 15000 });
let mainWindow = null;
let overlayWindow = null;
let wowBridge = null;
let wowCheckpointStatus = null;
let companionRuntimeHealth = null;
let overlayExpiryTimer = null;
let voiceConsentGranted = false;
let voiceProviderStatus = null;
let voiceStateReason = 'VOICE_CONSENT_REQUIRED';
let voiceCapturePermissionExpiresAt = 0;

async function accountSnapshot() {
  if (!session.status) return { session: null, features: [] };
  try {
    const payload = await session.featureStatus();
    return { session: session.status, features: Array.isArray(payload.features) ? payload.features : [] };
  } catch {
    return { session: session.status, features: [] };
  }
}

function publishAccountSnapshot() {
  void accountSnapshot().then(snapshot => mainWindow?.webContents.send('account:status', snapshot));
}

function voiceSnapshot() {
  let state = 'SIGNED_OUT';
  if (session.status) {
    if (!voiceConsentGranted) state = 'CONSENT_REQUIRED';
    else if (['COMPANION_ENTITLEMENT_REQUIRED', 'COMPANION_ENTITLEMENT_REVOKED'].includes(voiceStateReason)) state = 'ENTITLEMENT_REQUIRED';
    else if (voiceProviderStatus?.sttAvailable) state = 'READY';
    else state = 'PROVIDER_UNAVAILABLE';
  }
  return Object.freeze({
    state,
    reason: voiceStateReason,
    consentGranted: voiceConsentGranted,
    sttAvailable: Boolean(voiceProviderStatus?.sttAvailable),
    ttsAvailable: Boolean(voiceProviderStatus?.ttsAvailable),
    maxAudioBytes: voiceProviderStatus?.maxAudioBytes || MAX_AUDIO_BYTES,
    maxCaptureMs: MAX_CAPTURE_MS,
    captureContentType: CAPTURE_CONTENT_TYPE,
    actionCapable: false,
  });
}

function publishVoiceSnapshot() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.webContents.send('voice:status', voiceSnapshot());
}

function clearVoiceCapturePermission() {
  voiceCapturePermissionExpiresAt = 0;
}

function voiceCapturePermissionArmed() {
  return voiceConsentGranted && voiceCapturePermissionExpiresAt > Date.now();
}

function requireMainRenderer(event) {
  if (!mainWindow || mainWindow.isDestroyed() || event?.sender !== mainWindow.webContents) {
    throw new Error('UNTRUSTED_RENDERER');
  }
}

function resetVoiceState(reason = 'VOICE_CONSENT_REQUIRED') {
  clearVoiceCapturePermission();
  voiceConsentGranted = false;
  voiceProviderStatus = null;
  voiceStateReason = reason;
  publishVoiceSnapshot();
}

async function refreshVoiceProviderStatus() {
  if (!session.status) {
    resetVoiceState('AUTHENTICATION_REQUIRED');
    return voiceSnapshot();
  }
  try {
    const sanitized = sanitizeVoiceStatus(await session.voiceStatus());
    if (!sanitized) throw new Error('VOICE_STATUS_INVALID');
    voiceProviderStatus = sanitized;
    voiceStateReason = sanitized.sttAvailable ? null : 'VOICE_PROVIDER_UNAVAILABLE';
  } catch (error) {
    voiceProviderStatus = null;
    voiceStateReason = String(error?.message || 'VOICE_STATUS_FAILED').slice(0, 128);
  }
  publishVoiceSnapshot();
  return voiceSnapshot();
}

function overlaySnapshot() {
  return {
    companion: companion.status,
    runtime: companionRuntimeHealth,
    wow: wowCheckpointStatus ? {
      state: wowCheckpointStatus.state,
      queueDepth: Number.isInteger(wowCheckpointStatus.queueDepth) ? wowCheckpointStatus.queueDepth : 0,
      dropped: Number.isInteger(wowCheckpointStatus.dropped) ? wowCheckpointStatus.dropped : 0,
    } : null,
    presentations: overlayStore.snapshot(),
  };
}

function publishOverlaySnapshot() {
  if (!overlayWindow || overlayWindow.isDestroyed()) return;
  overlayWindow.webContents.send('overlay:snapshot', overlaySnapshot());
  if (['ACTIVE', 'DEGRADED'].includes(companion.status.state)) overlayWindow.showInactive();
  else overlayWindow.hide();
}

function scheduleOverlayExpiry() {
  if (overlayExpiryTimer) clearTimeout(overlayExpiryTimer);
  overlayExpiryTimer = setTimeout(() => {
    overlayExpiryTimer = null;
    publishOverlaySnapshot();
  }, 15100);
  overlayExpiryTimer.unref?.();
}

function applyVoiceIntent(intent) {
  if (!intent || intent.surface !== 'VOICE') return;
  if (intent.mode === 'ACKNOWLEDGE' || intent.mode === 'DISMISS') {
    overlayStore.remove(intent.recommendationId);
  }
  publishOverlaySnapshot();
  if (intent.mode === 'OBSERVE' && overlayWindow && !overlayWindow.isDestroyed() && ['ACTIVE', 'DEGRADED'].includes(companion.status.state)) {
    overlayWindow.showInactive();
  }
}

const companion = new CompanionProcessManager({
  onStatus: status => {
    wowBridge?.onCompanionStatus(status);
    mainWindow?.webContents.send('companion:status', status);
    publishOverlaySnapshot();
    publishVoiceSnapshot();
    if (['COMPANION_ENTITLEMENT_REQUIRED', 'COMPANION_ENTITLEMENT_REVOKED'].includes(status.reason)) {
      resetVoiceState(status.reason);
      publishAccountSnapshot();
    }
  },
  onRefreshNeeded: async () => {
    await session.refresh();
    publishAccountSnapshot();
    return session.accessToken;
  },
  onObservationAck: ({ eventId, accepted, reason }) => wowBridge?.acknowledge(eventId, accepted, reason),
  onObservationDeferred: eventId => wowBridge?.defer(eventId),
  onPresentation: presentation => {
    if (!overlayStore.push(presentation)) return;
    publishOverlaySnapshot();
    scheduleOverlayExpiry();
  },
  onRuntimeHealth: health => {
    companionRuntimeHealth = health;
    publishOverlaySnapshot();
  },
});

function configPath() { return path.join(app.getPath('userData'), 'games.json'); }
function loadConfig() {
  try { return JSON.parse(fs.readFileSync(configPath(), 'utf8')); } catch { return {}; }
}
function saveConfig(value) { fs.writeFileSync(configPath(), JSON.stringify(value, null, 2), { mode: 0o600 }); }

function createWowBridge() {
  const queue = new WowObservationQueue({ filePath: path.join(app.getPath('userData'), 'wow-observations.json'), maxItems: 128 });
  return new WowCheckpointBridge({
    queue,
    resolvePath: () => discoverSentinelSavedVariables(loadConfig()['world-of-warcraft'], process.env.SENTINEL_WOW_SAVEDVARIABLES_PATH || null),
    sendObservation: observation => companion.sendObservation(observation),
    onStatus: status => {
      wowCheckpointStatus = status;
      mainWindow?.webContents.send('wow:checkpoint-status', status);
      publishOverlaySnapshot();
    },
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1180, height: 800, minWidth: 900, minHeight: 640, backgroundColor: '#070a0d',
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  mainWindow = win;
  win.on('closed', () => {
    if (mainWindow === win) mainWindow = null;
    resetVoiceState('VOICE_CONSENT_REQUIRED');
    if (overlayWindow && !overlayWindow.isDestroyed()) overlayWindow.close();
  });
  win.loadFile(path.join(__dirname, 'index.html'));
}

function createOverlayWindow() {
  const width = 420;
  const height = 190;
  const workArea = screen.getPrimaryDisplay().workArea;
  const win = new BrowserWindow({
    width, height,
    x: Math.max(workArea.x, workArea.x + workArea.width - width - 18),
    y: workArea.y + 18,
    transparent: true, frame: false, show: false, focusable: false, alwaysOnTop: true, skipTaskbar: true,
    resizable: false, fullscreenable: false,
    webPreferences: { preload: path.join(__dirname, 'overlay-preload.js'), contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  overlayWindow = win;
  win.setIgnoreMouseEvents(true, { forward: true });
  win.setMenuBarVisibility(false);
  win.webContents.on('did-finish-load', publishOverlaySnapshot);
  win.on('closed', () => { if (overlayWindow === win) overlayWindow = null; });
  win.loadFile(path.join(__dirname, 'overlay.html'));
}

function configureVoicePermissions() {
  const runtimeSession = electronSession.defaultSession;
  runtimeSession.setPermissionCheckHandler((webContents, permission, requestingOrigin, details) => mediaPermissionAllowed({
    webContents,
    mainWebContents: mainWindow?.webContents || null,
    permission,
    requestingOrigin,
    details,
    consentGranted: voiceCapturePermissionArmed(),
  }));
  runtimeSession.setPermissionRequestHandler((webContents, permission, callback, details) => {
    callback(mediaPermissionAllowed({
      webContents,
      mainWebContents: mainWindow?.webContents || null,
      permission,
      requestingOrigin: details?.requestingUrl || details?.securityOrigin || webContents?.getURL?.() || '',
      details,
      consentGranted: voiceCapturePermissionArmed(),
    }));
  });
  runtimeSession.setDisplayMediaRequestHandler((_request, callback) => callback(null));
}

ipcMain.handle('catalog', () => catalog);
ipcMain.handle('config:get', () => loadConfig());
ipcMain.handle('config:set', (_, id, executable) => {
  const game = catalog.find(item => item.id === id);
  if (!game || game.platform !== 'windows') throw new Error('UNSUPPORTED_GAME');
  if (typeof executable !== 'string' || !path.isAbsolute(executable)) throw new Error('INVALID_EXECUTABLE_PATH');
  const config = loadConfig(); config[id] = executable; saveConfig(config); return true;
});
ipcMain.handle('game:launch', (_, id) => {
  const game = catalog.find(item => item.id === id);
  if (!game || game.platform !== 'windows') throw new Error('ANDROID_GAME_REQUIRES_ANDROID_CLIENT');
  const executable = loadConfig()[id];
  if (!executable || !fs.existsSync(executable)) throw new Error('GAME_EXECUTABLE_NOT_CONFIGURED');
  spawn(executable, [], { detached: true, stdio: 'ignore', windowsHide: false }).unref(); return true;
});
ipcMain.handle('account:login', async (_, coreUrl, email, password) => {
  await session.login({ coreUrl, email, password });
  resetVoiceState('VOICE_CONSENT_REQUIRED');
  return accountSnapshot();
});
ipcMain.handle('account:logout', () => {
  wowBridge?.stop(); companion.stop('ACCOUNT_LOGOUT'); session.clear(); overlayStore.clear(); wowCheckpointStatus = null; companionRuntimeHealth = null; resetVoiceState('AUTHENTICATION_REQUIRED'); publishOverlaySnapshot(); return true;
});
ipcMain.handle('account:status', () => accountSnapshot());
ipcMain.handle('companion:status', () => companion.status);
ipcMain.handle('companion:start', async (_, coreUrl) => {
  if (!session.accessToken) throw new Error('AUTHENTICATION_REQUIRED');
  const requestedCore = normalizeCoreUrl(coreUrl);
  if (requestedCore !== session.coreUrl) throw new Error('CORE_SESSION_ORIGIN_MISMATCH');
  const features = await session.featureStatus();
  if (!Array.isArray(features.features) || !features.features.includes('companion')) throw new Error('COMPANION_ENTITLEMENT_REQUIRED');
  companionRuntimeHealth = null;
  const status = companion.start({ coreUrl: session.coreUrl, sessionToken: session.accessToken });
  wowBridge?.start(); wowBridge?.onCompanionStatus(status); publishOverlaySnapshot(); publishVoiceSnapshot(); return status;
});
ipcMain.handle('companion:stop', () => {
  clearVoiceCapturePermission();
  wowBridge?.stop(); const status = companion.stop('STOPPED_BY_USER'); overlayStore.clear(); companionRuntimeHealth = null; publishOverlaySnapshot(); publishVoiceSnapshot(); return status;
});
ipcMain.handle('voice:status', async event => {
  requireMainRenderer(event);
  if (!session.status) return voiceSnapshot();
  return refreshVoiceProviderStatus();
});
ipcMain.handle('voice:consent:set', async (event, granted) => {
  requireMainRenderer(event);
  if (typeof granted !== 'boolean') throw new Error('VOICE_CONSENT_INVALID');
  if (!granted) {
    resetVoiceState('VOICE_CONSENT_REQUIRED');
    return voiceSnapshot();
  }
  if (!session.status) throw new Error('AUTHENTICATION_REQUIRED');
  const features = await session.featureStatus();
  if (!Array.isArray(features.features) || !features.features.includes('companion')) {
    resetVoiceState('COMPANION_ENTITLEMENT_REQUIRED');
    throw new Error('COMPANION_ENTITLEMENT_REQUIRED');
  }
  voiceConsentGranted = true;
  voiceStateReason = null;
  return refreshVoiceProviderStatus();
});
ipcMain.handle('voice:capture:arm', async event => {
  requireMainRenderer(event);
  if (!session.status) throw new Error('AUTHENTICATION_REQUIRED');
  if (!voiceConsentGranted) throw new Error('VOICE_CONSENT_REQUIRED');
  if (!['ACTIVE', 'DEGRADED'].includes(companion.status.state)) throw new Error('COMPANION_NOT_ACTIVE');
  if (!voiceProviderStatus) await refreshVoiceProviderStatus();
  if (!voiceProviderStatus?.sttAvailable) throw new Error(voiceStateReason || 'VOICE_PROVIDER_UNAVAILABLE');
  voiceCapturePermissionExpiresAt = Date.now() + VOICE_CAPTURE_PERMISSION_LEASE_MS;
  return { armed: true, expiresInMs: VOICE_CAPTURE_PERMISSION_LEASE_MS, actionCapable: false };
});
ipcMain.handle('voice:capture:disarm', event => {
  requireMainRenderer(event);
  clearVoiceCapturePermission();
  return true;
});
ipcMain.handle('voice:submit', async (event, payload) => {
  requireMainRenderer(event);
  clearVoiceCapturePermission();
  if (!session.status) throw new Error('AUTHENTICATION_REQUIRED');
  if (!voiceConsentGranted) throw new Error('VOICE_CONSENT_REQUIRED');
  if (!['ACTIVE', 'DEGRADED'].includes(companion.status.state)) throw new Error('COMPANION_NOT_ACTIVE');
  if (!voiceProviderStatus) await refreshVoiceProviderStatus();
  if (!voiceProviderStatus?.sttAvailable) throw new Error(voiceStateReason || 'VOICE_PROVIDER_UNAVAILABLE');
  const capture = validateCapturePayload(payload, voiceProviderStatus.maxAudioBytes);
  const rawResult = await session.transcribeVoice({
    audioBase64: capture.audioBase64,
    locale: capture.locale,
    recommendationId: overlayStore.latestRecommendationId(),
    consentGranted: true,
  });
  const result = sanitizeVoiceResult(rawResult);
  if (!result) throw new Error('VOICE_RESPONSE_INVALID');
  if (result.intent) applyVoiceIntent(result.intent);

  let feedbackAudio = null;
  let feedbackReason = null;
  const feedbackText = feedbackTextForVoiceResult(result);
  if (feedbackText && voiceProviderStatus.ttsAvailable) {
    try {
      feedbackAudio = sanitizeSynthesizedAudio(await session.synthesizeVoice({
        text: feedbackText,
        locale: capture.locale,
        consentGranted: true,
      }));
      if (!feedbackAudio) feedbackReason = 'VOICE_TTS_RESPONSE_INVALID';
    } catch {
      feedbackReason = 'VOICE_TTS_DEGRADED';
    }
  } else if (feedbackText) {
    feedbackReason = 'VOICE_TTS_UNAVAILABLE';
  }
  return { result, feedbackAudio, feedbackReason };
});

app.whenReady().then(() => {
  configureVoicePermissions();
  wowBridge = createWowBridge(); createOverlayWindow(); createWindow();
  app.on('activate', () => {
    if (!mainWindow || mainWindow.isDestroyed()) {
      if (!overlayWindow || overlayWindow.isDestroyed()) createOverlayWindow();
      createWindow();
    }
  });
});
app.on('before-quit', () => { if (overlayExpiryTimer) clearTimeout(overlayExpiryTimer); resetVoiceState('APPLICATION_EXIT'); wowBridge?.stop(); companion.stop('APPLICATION_EXIT'); });
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
