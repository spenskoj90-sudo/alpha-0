const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const catalog = [
  { id: 'diablo-1-pc', name: 'Diablo', platform: 'windows' },
  { id: 'diablo-2-pc', name: 'Diablo II', platform: 'windows' },
  { id: 'diablo-2-resurrected-pc', name: 'Diablo II: Resurrected', platform: 'windows' },
  { id: 'diablo-3-pc', name: 'Diablo III', platform: 'windows' },
  { id: 'diablo-4-pc', name: 'Diablo IV', platform: 'windows' },
  { id: 'diablo-immortal-android', name: 'Diablo Immortal', platform: 'android' },
];

function configPath() { return path.join(app.getPath('userData'), 'games.json'); }
function loadConfig() {
  try { return JSON.parse(fs.readFileSync(configPath(), 'utf8')); } catch { return {}; }
}
function saveConfig(value) { fs.writeFileSync(configPath(), JSON.stringify(value, null, 2), { mode: 0o600 }); }

function createWindow() {
  const win = new BrowserWindow({
    width: 1180,
    height: 760,
    minWidth: 900,
    minHeight: 600,
    backgroundColor: '#070a0d',
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  win.loadFile(path.join(__dirname, 'index.html'));
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
  spawn(executable, [], { detached: true, stdio: 'ignore', windowsHide: false }).unref();
  return true;
});

app.whenReady().then(() => { createWindow(); app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); }); });
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
