'use strict';

const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { CoreSessionManager, normalizeCoreUrl } = require('./core-session');
const { CompanionProcessManager } = require('./companion-process');

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
const companion = new CompanionProcessManager({
  onStatus: status => mainWindow?.webContents.send('companion:status', status),
  onRefreshNeeded: async () => {
    await session.refresh();
    mainWindow?.webContents.send('account:status', session.status);
    return session.accessToken;
  },
});

function configPath() { return path.join(app.getPath('userData'), 'games.json'); }
function loadConfig() {
  try { return JSON.parse(fs.readFileSync(configPath(), 'utf8')); } catch { return {}; }
}
function saveConfig(value) { fs.writeFileSync(configPath(), JSON.stringify(value, null, 2), { mode: 0o600 }); }

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
  win.on('closed', () => { if (mainWindow === win) mainWindow = null; });
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
  const status = await session.login({ coreUrl, email, password });
  const features = await session.featureStatus();
  return { session: status, features: features.features || [] };
});
ipcMain.handle('account:logout', () => {
  companion.stop('ACCOUNT_LOGOUT');
  session.clear();
  return true;
});
ipcMain.handle('account:status', () => session.status);
ipcMain.handle('companion:status', () => companion.status);
ipcMain.handle('companion:start', async (_, coreUrl) => {
  if (!session.accessToken) throw new Error('AUTHENTICATION_REQUIRED');
  const requestedCore = normalizeCoreUrl(coreUrl);
  if (requestedCore !== session.coreUrl) throw new Error('CORE_SESSION_ORIGIN_MISMATCH');
  const features = await session.featureStatus();
  if (!Array.isArray(features.features) || !features.features.includes('companion')) {
    throw new Error('COMPANION_ENTITLEMENT_REQUIRED');
  }
  return companion.start({ coreUrl: session.coreUrl, sessionToken: session.accessToken });
});
ipcMain.handle('companion:stop', () => companion.stop('STOPPED_BY_USER'));

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});
app.on('before-quit', () => companion.stop('APPLICATION_EXIT'));
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
