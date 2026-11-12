'use strict';

const { app, BrowserWindow, dialog, ipcMain, screen, session: electronSession } = require('electron');
const fs = require('node:fs');
const path = require('node:path');
const { performance } = require('node:perf_hooks');
const { documentUrl, assertMainFrameRequest, restrictAppWindowNavigation } = require('./renderer-boundary');
const { isSelectableExecutable, gameLaunchState } = require('./game-executable-policy');
const { launchGameExecutable } = require('./game-process-launch');
const TRUSTED_MAIN_DOCUMENT = documentUrl(__dirname, 'index.html');
const TRUSTED_OVERLAY_DOCUMENT = documentUrl(__dirname, 'overlay.html');
const { CoreSessionManager, normalizeCoreUrl } = require('./core-session');
const { accountSnapshot, createAccountSnapshotPublisher } = require('./account-snapshot');
const { CompanionProcessManager } = require('./companion-process');
const { revokeAccountBoundRuntime } = require('./account-lifecycle');
const { bindVoiceRequest, voiceRequestStillCurrent, sameSessionContext } = require('./voice-authorization');
const { CompanionStartFence } = require('./companion-start-fence');
const { OverlayPresentationStore, clearOverlayOnInactiveCompanion } = require('./overlay-state');
const { KnowledgePresentation } = require('./knowledge-presentation');
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
const companionStartFence = new CompanionStartFence();
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
let voiceConsentGeneration = 0;
let voiceStatusRequestGeneration = 0;
let knowledge = null;

const accountPublisher = createAccountSnapshotPublisher(session, snapshot => {
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send('account:status', snapshot);
});

function publishAccountSnapshot() {
  void accountPublisher.publish();
}

function voiceSnapshot() {
  let state = 'SIGNED_OUT';
  if (session.status) {
    if (!voiceConsentGranted) state = 'CONSENT_REQUIRED';
    else if (['COMPANION_ENTITLEMENT_REQUIRED', 'COMPANION_ENTITLEMENT_REVOKED'].includes(voiceStateReason)) state = 'ENTITLEMENT_REQUIRED';
    else if (companion.status.state !== 'ACTIVE') state = 'COMPANION_UNAVAILABLE';
    else if (voiceProviderStatus?.sttAvailable) state = 'READY';
    else state = 'PROVIDER_UNAVAILABLE';
  }
  return Object.freeze({
    state,
    reason: state === 'COMPANION_UNAVAILABLE' ? 'COMPANION_NOT_ACTIVE' : voiceStateReason,
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
  return voiceConsentGranted && voiceCapturePermissionExpiresAt > performance.now();
}

function requireMainRenderer(event) {
  if (!mainWindow || mainWindow.isDestroyed() || event?.sender !== mainWindow.webContents) {
    throw new Error('UNTRUSTED_RENDERER');
  }
  assertMainFrameRequest(event, mainWindow, TRUSTED_MAIN_DOCUMENT);
}

function resetVoiceState(reason = 'VOICE_CONSENT_REQUIRED') {
  voiceConsentGeneration += 1;
  voiceStatusRequestGeneration += 1;
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
  // Latest request wins. A delayed former-session provider response cannot
  // turn a new principal's voice UI READY or overwrite its error state.
  const generation = ++voiceStatusRequestGeneration;
  const boundSession = session.knowledgeContext;
  const stillCurrent = () => generation === voiceStatusRequestGeneration &&
    sameSessionContext(boundSession, session.knowledgeContext);
  try {
    const sanitized = sanitizeVoiceStatus(await session.voiceStatus());
    if (!stillCurrent()) return voiceSnapshot();
    if (!sanitized) throw new Error('VOICE_STATUS_INVALID');
    voiceProviderStatus = sanitized;
    voiceStateReason = sanitized.sttAvailable ? null : 'VOICE_PROVIDER_UNAVAILABLE';
  } catch (error) {
    if (!stillCurrent()) return voiceSnapshot();
    voiceProviderStatus = null;
    voiceStateReason = String(error?.message || 'VOICE_STATUS_FAILED').slice(0, 128);
  }
  publishVoiceSnapshot();
  return voiceSnapshot();
}

function voiceRequestBoundary() {
  return bindVoiceRequest(session.knowledgeContext, voiceConsentGeneration);
}

function requireVoiceBoundary(expected) {
  if (!voiceRequestStillCurrent(
    expected, session.knowledgeContext, voiceConsentGeneration,
    voiceConsentGranted, companion.status.state,
  )) throw new Error('VOICE_CAPTURE_REVOKED');
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
    if (clearOverlayOnInactiveCompanion(status, overlayStore)) companionRuntimeHealth = null;
    if (status.state !== 'ACTIVE') {
      // A lost/replaced transport cannot keep an in-flight capture/voice result alive.
      voiceConsentGeneration += 1;
      clearVoiceCapturePermission();
    }
    if (status.state === 'STOPPED') knowledge?.stop();
    wowBridge?.onCompanionStatus(status);
    mainWindow?.webContents.send('companion:status', status);
    publishOverlaySnapshot();
    publishVoiceSnapshot();
    if (['COMPANION_ENTITLEMENT_REQUIRED', 'COMPANION_ENTITLEMENT_REVOKED'].includes(status.reason)) {
      knowledge?.deny();
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
    // A delayed Core message must not resurrect advice after disconnect/Stop.
    if (companion.status.state !== 'ACTIVE' || !overlayStore.push(presentation)) return;
    publishOverlaySnapshot();
    scheduleOverlayExpiry();
  },
  onRuntimeHealth: health => {
    if (companion.status.state !== 'ACTIVE') return;
    companionRuntimeHealth = health;
    publishOverlaySnapshot();
  },
});

// New account identity must not inherit an old worker, game observer, cached
// overlay recommendation, voice consent or asynchronous Core response.
function clearAccountBoundary(reason) {
  // Revoke in-flight account feature publications before changing principal.
  accountPublisher.revoke();
  // Cancel a pending entitlement/start request before tearing down the worker.
  companionStartFence.revoke();
  revokeAccountBoundRuntime({
    session,
    companion,
    knowledge,
    wowBridge,
    overlayStore,
    resetEvidence: () => {
      wowCheckpointStatus = null;
      companionRuntimeHealth = null;
    },
    resetVoice: resetVoiceState,
    publishOverlay: publishOverlaySnapshot,
  }, reason);
}

function configPath() { return path.join(app.getPath('userData'), 'games.json'); }
function loadConfig() {
  try {
    const value = JSON.parse(fs.readFileSync(configPath(), 'utf8'));
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  } catch { return {}; }
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
  restrictAppWindowNavigation(win.webContents, TRUSTED_MAIN_DOCUMENT);
  win.on('closed', () => {
    knowledge?.stop();
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
  restrictAppWindowNavigation(win.webContents, TRUSTED_OVERLAY_DOCUMENT);
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

ipcMain.handle('catalog', event => {
  requireMainRenderer(event);
  const config = loadConfig();
  return catalog.map(game => ({
    ...game,
    // Never expose a saved absolute path in the game card. A missing EXE is not ready.
    launchState: gameLaunchState(game, config?.[game.id], fs.statSync),
  }));
});
// Keep existing saved paths compatible, but never expose or mutate them through
// arbitrary renderer strings. New selections must use the native main-process dialog.
ipcMain.handle('game:choose-executable', async (event, id) => {
  requireMainRenderer(event);
  const game = catalog.find(item => item.id === id);
  if (!game || game.platform !== 'windows') throw new Error('UNSUPPORTED_GAME');
  if (process.platform !== 'win32') throw new Error('WINDOWS_HOST_REQUIRED');
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Select the game executable',
    properties: ['openFile'],
    filters: [{ name: 'Windows executables', extensions: ['exe'] }],
  });
  // A modal chooser may outlive its initiating renderer or document.
  requireMainRenderer(event);
  if (result.canceled) return { configured: false };
  const executable = result.filePaths?.[0];
  if (!isSelectableExecutable(executable) ||
      gameLaunchState(game, executable, fs.statSync) !== 'READY') {
    throw new Error('GAME_EXECUTABLE_UNAVAILABLE');
  }
  const config = loadConfig();
  config[id] = executable;
  saveConfig(config);
  // Do not send private executable paths back to the renderer.
  return { configured: true };
});
ipcMain.handle('game:launch', async (event, id) => {
  requireMainRenderer(event);
  const game = catalog.find(item => item.id === id);
  if (!game || game.platform !== 'windows') throw new Error('ANDROID_GAME_REQUIRES_ANDROID_CLIENT');
  if (process.platform !== 'win32') throw new Error('WINDOWS_HOST_REQUIRED');
  const executable = loadConfig()[id];
  if (gameLaunchState(game, executable, fs.statSync) !== 'READY') {
    throw new Error('GAME_EXECUTABLE_NOT_CONFIGURED');
  }
  return launchGameExecutable(executable);
});
ipcMain.handle('account:login', async (event, coreUrl, email, password) => {
  requireMainRenderer(event);
  // Deny stale account/worker activity at the start of the new login attempt,
  // not after a response (which may be delayed, rejected or MFA-pending).
  clearAccountBoundary('ACCOUNT_SWITCH');
  await session.login({ coreUrl, email, password });
  resetVoiceState(session.status ? 'VOICE_CONSENT_REQUIRED' : 'AUTHENTICATION_REQUIRED');
  return accountSnapshot(session);
});
ipcMain.handle('account:mfa-complete', async (event, code) => {
  requireMainRenderer(event);
  await session.completeMfa(code);
  resetVoiceState('VOICE_CONSENT_REQUIRED');
  return accountSnapshot(session);
});
ipcMain.handle('account:logout', event => {
  requireMainRenderer(event);
  clearAccountBoundary('ACCOUNT_LOGOUT');
  return true;
});
ipcMain.handle('account:status', event => { requireMainRenderer(event); return accountSnapshot(session); });
ipcMain.handle('companion:status', event => { requireMainRenderer(event); return companion.status; });
ipcMain.handle('knowledge:status', event => { requireMainRenderer(event); return knowledge?.status(); });
ipcMain.handle('knowledge:refresh', event => { requireMainRenderer(event); return knowledge?.refresh(); });
ipcMain.handle('companion:start', async (event, coreUrl) => {
  requireMainRenderer(event);
  if (!session.accessToken) throw new Error('AUTHENTICATION_REQUIRED');
  const startLease = companionStartFence.begin(session.knowledgeContext);
  if (!startLease) throw new Error('AUTHENTICATION_REQUIRED');
  const requestedCore = normalizeCoreUrl(coreUrl);
  if (requestedCore !== session.coreUrl) throw new Error('CORE_SESSION_ORIGIN_MISMATCH');
  const features = await session.featureStatus();
  // A prior Stop, account replacement or newer start request must not be
  // undone when an older entitlement lookup finishes asynchronously.
  if (!companionStartFence.isCurrent(startLease, session.knowledgeContext))
    throw new Error('COMPANION_START_REVOKED');
  if (!Array.isArray(features.features) || !features.features.includes('companion')) throw new Error('COMPANION_ENTITLEMENT_REQUIRED');
  companionRuntimeHealth = null;
  const status = companion.start({ coreUrl: session.coreUrl, sessionToken: session.accessToken });
  void knowledge?.start();
  wowBridge?.start(); wowBridge?.onCompanionStatus(status); publishOverlaySnapshot(); publishVoiceSnapshot(); return status;
});
ipcMain.handle('companion:stop', event => {
  requireMainRenderer(event);
  companionStartFence.revoke();
  knowledge?.stop();
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
  const sessionContext = session.knowledgeContext;
  const generation = ++voiceConsentGeneration;
  const features = await session.featureStatus();
  if (generation !== voiceConsentGeneration ||
      !sameSessionContext(sessionContext, session.knowledgeContext)) {
    throw new Error('VOICE_CONSENT_REVOKED');
  }
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
  if (companion.status.state !== 'ACTIVE') throw new Error('COMPANION_NOT_ACTIVE');
  const boundary = voiceRequestBoundary();
  requireVoiceBoundary(boundary);
  if (!voiceProviderStatus) await refreshVoiceProviderStatus();
  requireVoiceBoundary(boundary);
  if (!voiceProviderStatus?.sttAvailable) throw new Error(voiceStateReason || 'VOICE_PROVIDER_UNAVAILABLE');
  voiceCapturePermissionExpiresAt = performance.now() + VOICE_CAPTURE_PERMISSION_LEASE_MS;
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
  if (companion.status.state !== 'ACTIVE') throw new Error('COMPANION_NOT_ACTIVE');
  const boundary = voiceRequestBoundary();
  requireVoiceBoundary(boundary);
  if (!voiceProviderStatus) await refreshVoiceProviderStatus();
  requireVoiceBoundary(boundary);
  if (!voiceProviderStatus?.sttAvailable) throw new Error(voiceStateReason || 'VOICE_PROVIDER_UNAVAILABLE');
  const capture = validateCapturePayload(payload, voiceProviderStatus.maxAudioBytes);
  const rawResult = await session.transcribeVoice({
    audioBase64: capture.audioBase64,
    locale: capture.locale,
    recommendationId: overlayStore.latestRecommendationId(),
    consentGranted: true,
  });
  requireVoiceBoundary(boundary);
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
      requireVoiceBoundary(boundary);
      if (!feedbackAudio) feedbackReason = 'VOICE_TTS_RESPONSE_INVALID';
    } catch {
      requireVoiceBoundary(boundary);
      feedbackReason = 'VOICE_TTS_DEGRADED';
    }
  } else if (feedbackText) {
    feedbackReason = 'VOICE_TTS_UNAVAILABLE';
  }
  requireVoiceBoundary(boundary);
  return { result, feedbackAudio, feedbackReason };
});

app.whenReady().then(() => {
  knowledge = new KnowledgePresentation({
    directory: path.join(app.getPath('userData'), 'knowledge'), session,
    // No renderer/game catalog/SavedVariables assertion proves calibration.
    // Replace only through a reviewed independently verified target adapter.
    getTrustedContext: () => null,
    getTrustedObservation: () => null,
    onChange: status => mainWindow?.webContents.send('knowledge:status', status),
  });
  configureVoicePermissions();
  wowBridge = createWowBridge(); createOverlayWindow(); createWindow();
  app.on('activate', () => {
    if (!mainWindow || mainWindow.isDestroyed()) {
      if (!overlayWindow || overlayWindow.isDestroyed()) createOverlayWindow();
      createWindow();
    }
  });
});
app.on('before-quit', () => { knowledge?.stop(); if (overlayExpiryTimer) clearTimeout(overlayExpiryTimer); resetVoiceState('APPLICATION_EXIT'); wowBridge?.stop(); companion.stop('APPLICATION_EXIT'); });
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
