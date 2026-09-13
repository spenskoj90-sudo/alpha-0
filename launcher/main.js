'use strict';

const { app, BrowserWindow, ipcMain, screen } = require('electron');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { CoreSessionManager, normalizeCoreUrl } = require('./core-session');
const { CompanionProcessManager } = require('./companion-process');
const { PresentationStore } = require('./presentation-runtime');
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
let mainWindow = null;
let overlayWindow = null;
let wowBridge = null;

function publishOverlaySnapshot(snapshot = presentationStore.snapshot()) {
  const safeSnapshot = Array.isArray(snapshot) ? snapshot : [];
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.webContents.send('overlay:snapshot', safeSnapshot);
    if (safeSnapshot.length > 0) overlayWindow.showInactive();
    else overlayWindow.hide();
  }
  mainWindow?.webContents.send('overlay:status', {
    visible: safeSnapshot.length > 0,
    count: safeSnapshot.length,
  });
}

const presentationStore = new PresentationStore({
  maxItems: 8,
  onChange: publishOverlaySnapshot,
});

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

const companion = new CompanionProcessManager({
  onStatus: status => {
    wowBridge?.onCompanionStatus(status);
    mainWindow?.webContents.send('companion:status', status);
    if (status.state === 'STOPPED') presentationStore.clear();
    if (['COMPANION_ENTITLEMENT_REQUIRED', 'COMPANION_ENTITLEMENT_REVOKED'].includes(status.reason)) {
      publishAccountSnapshot();
    }
  },
  onRefreshNeeded: async () => {
    await session.refresh();
    publishAccountSnapshot();
    return session.accessToken;
  },
  onObservationAck: ({ eventId, accepted, reason }) => {
    wowBridge?.acknowledge(eventId, accepted, reason);
  },
  onObservationDeferred: eventId => wowBridge?.defer(eventId),
  onPresentation: presentation => presentationStore.add(presentation),
});

function configPath() { return path.join(app.getPath('userData'), 'games.json'); }
function loadConfig() {
  try { return JSON.parse(fs.readFileSync(configPath(), 'utf8')); } catch { return {}; }
}
function saveConfig(value) { fs.writeFileSync(configPath(), JSON.stringify(value, null, 2), { mode: 0o600 }); }

function createWowBridge() {
  const queue = new WowObservationQueue({
    filePath: path.join(app.getPath('userData'), 'wow-observations.json'),
    maxItems: 128,
  });
  return new WowCheckpointBridge({
    queue,
    resolvePath: () => discoverSentinelSavedVariables(
      loadConfig()['world-of-warcraft'],
      process.env.SENTINEL_WOW_SAVEDVARIABLES_PATH || null,
    ),
    sendObservation: observation => companion.sendObservation(observation),
    onStatus: status => mainWindow?.webContents.send('wow:checkpoint-status', status),
  });
}

function createOverlayWindow() {
  const workArea = screen.getPrimaryDisplay().workArea;
  const width = Math.min(440, workArea.width);
  const height = Math.min(320, workArea.height);
  const margin = 18;
  const win = new BrowserWindow({
    width,
    height,
    x: Math.max(workArea.x, workArea.x + workArea.width - width - margin),
    y: Math.max(workArea.y, workArea.y + margin),
    show: false,
    frame: false,
    transparent: true,
    resizable: false,
    movable: false,
    focusable: false,
    fullscreenable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, 'overlay-preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  overlayWindow = win;
  win.setIgnoreMouseEvents(true, { forward: true });
  win.setAlwaysOnTop(true, 'floating');
  win.on('closed', () => { if (overlayWindow === win) overlayWindow = null; });
  win.webContents.on('did-finish-load', () => publishOverlaySnapshot());
  win.loadFile(path.join(__dirname, 'overlay.html'));
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1180,
    height: 800,
    minWidth: 900,
    minHeight: 640,
    backgroundColor: '#070a0d',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  mainWindow = win;
  win.on('closed', () => {
    if (mainWindow === win) mainWindow = null;
    if (overlayWindow && !overlayWindow.isDestroyed()) overlayWindow.close();
  });
  win.webContents.on('did-finish-load', () => publishOverlaySnapshot());
  win.loadFile(path.join(__dirname, 'index.html'));
}

ipcMain.handle('catalog', () => catalog);
ipcMain.handle('config:get', () => loadConfig());
ipcMain.handle('config:set', (_, id, executable) => {
  const game = catalog.find(item => item.id === id);
  if (!game || game.platform !== 'windows') throw new Error('UNSUPPORTED_GAME');
  if (typeof executable !== 'string' || !path.isAbsolute(executable)) throw new Error('INVALID_EXECUTABLE_PATH');
  const config = loadConfig();
  config[id] = executable;
  saveConfig(config);
  return true;
});
ipcMain.handle('game:launch', (_, id) => {
  const game = catalog.find(item => item.id === id);
  if (!game || game.platform !== 'windows') throw new Error('ANDROID_GAME_REQUIRES_ANDROID_CLIENT');
  const executable = loadConfig()[id];
  if (!executable || !fs.existsSync(executable)) throw new Error('GAME_EXECUTABLE_NOT_CONFIGURED');
  spawn(executable, [], { detached: true, stdio: 'ignore', windowsHide: false }).unref();
  return true;
});

ipcMain.handle('account:login', async (_, coreUrl, email, password) => {
  await session.login({ coreUrl, email, password });
  return accountSnapshot();
});
ipcMain.handle('account:logout', () => {
  presentationStore.clear();
  wowBridge?.stop();
  companion.stop('ACCOUNT_LOGOUT');
  session.clear();
  return true;
});
ipcMain.handle('account:status', () => accountSnapshot());
ipcMain.handle('companion:status', () => companion.status);
ipcMain.handle('companion:start', async (_, coreUrl) => {
  if (!session.accessToken) throw new Error('AUTHENTICATION_REQUIRED');
  const requestedCore = normalizeCoreUrl(coreUrl);
  if (requestedCore !== session.coreUrl) throw new Error('CORE_SESSION_ORIGIN_MISMATCH');
  const features = await session.featureStatus();
  if (!Array.isArray(features.features) || !features.features.includes('companion')) {
    throw new Error('COMPANION_ENTITLEMENT_REQUIRED');
  }
  const status = companion.start({ coreUrl: session.coreUrl, sessionToken: session.accessToken });
  wowBridge?.start();
  wowBridge?.onCompanionStatus(status);
  return status;
});
ipcMain.handle('companion:stop', () => {
  presentationStore.clear();
  wowBridge?.stop();
  return companion.stop('STOPPED_BY_USER');
});

app.whenReady().then(() => {
  wowBridge = createWowBridge();
  createOverlayWindow();
  createWindow();
  app.on('activate', () => {
    if (!overlayWindow || overlayWindow.isDestroyed()) createOverlayWindow();
    if (!mainWindow || mainWindow.isDestroyed()) createWindow();
  });
});
app.on('before-quit', () => {
  presentationStore.clear();
  wowBridge?.stop();
  companion.stop('APPLICATION_EXIT');
});
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
