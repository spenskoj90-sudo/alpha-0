'use strict';

const { app, BrowserWindow, ipcMain, screen } = require('electron');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { CoreSessionManager, normalizeCoreUrl } = require('./core-session');
const { CompanionProcessManager } = require('./companion-process');
const { OverlayPresentationStore } = require('./overlay-state');
const {
  WowCheckpointBridge,
  WowObservationQueue,
  discoverSentinelSavedVariables,
} = require('./wow-savedvariables');

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

const companion = new CompanionProcessManager({
  onStatus: status => {
    wowBridge?.onCompanionStatus(status);
    mainWindow?.webContents.send('companion:status', status);
    publishOverlaySnapshot();
    if (['COMPANION_ENTITLEMENT_REQUIRED', 'COMPANION_ENTITLEMENT_REVOKED'].includes(status.reason)) publishAccountSnapshot();
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
ipcMain.handle('account:login', async (_, coreUrl, email, password) => { await session.login({ coreUrl, email, password }); return accountSnapshot(); });
ipcMain.handle('account:logout', () => {
  wowBridge?.stop(); companion.stop('ACCOUNT_LOGOUT'); session.clear(); overlayStore.clear(); wowCheckpointStatus = null; companionRuntimeHealth = null; publishOverlaySnapshot(); return true;
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
  wowBridge?.start(); wowBridge?.onCompanionStatus(status); publishOverlaySnapshot(); return status;
});
ipcMain.handle('companion:stop', () => {
  wowBridge?.stop(); const status = companion.stop('STOPPED_BY_USER'); overlayStore.clear(); companionRuntimeHealth = null; publishOverlaySnapshot(); return status;
});

app.whenReady().then(() => {
  wowBridge = createWowBridge(); createOverlayWindow(); createWindow();
  app.on('activate', () => {
    if (!mainWindow || mainWindow.isDestroyed()) {
      if (!overlayWindow || overlayWindow.isDestroyed()) createOverlayWindow();
      createWindow();
    }
  });
});
app.on('before-quit', () => { if (overlayExpiryTimer) clearTimeout(overlayExpiryTimer); wowBridge?.stop(); companion.stop('APPLICATION_EXIT'); });
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
