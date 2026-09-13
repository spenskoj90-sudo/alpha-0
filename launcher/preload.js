'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('sentinel', {
  catalog: () => ipcRenderer.invoke('catalog'),
  getConfig: () => ipcRenderer.invoke('config:get'),
  setExecutable: (id, executable) => ipcRenderer.invoke('config:set', id, executable),
  launch: id => ipcRenderer.invoke('game:launch', id),
  login: (coreUrl, email, password) => ipcRenderer.invoke('account:login', coreUrl, email, password),
  logout: () => ipcRenderer.invoke('account:logout'),
  accountStatus: () => ipcRenderer.invoke('account:status'),
  companionStatus: () => ipcRenderer.invoke('companion:status'),
  startCompanion: coreUrl => ipcRenderer.invoke('companion:start', coreUrl),
  stopCompanion: () => ipcRenderer.invoke('companion:stop'),
  onCompanionStatus: callback => {
    if (typeof callback !== 'function') return () => {};
    const handler = (_event, status) => callback(status);
    ipcRenderer.on('companion:status', handler);
    return () => ipcRenderer.removeListener('companion:status', handler);
  },
  onAccountStatus: callback => {
    if (typeof callback !== 'function') return () => {};
    const handler = (_event, status) => callback(status);
    ipcRenderer.on('account:status', handler);
    return () => ipcRenderer.removeListener('account:status', handler);
  },
  onWowCheckpointStatus: callback => {
    if (typeof callback !== 'function') return () => {};
    const handler = (_event, status) => callback(status);
    ipcRenderer.on('wow:checkpoint-status', handler);
    return () => ipcRenderer.removeListener('wow:checkpoint-status', handler);
  },
  onOverlayStatus: callback => {
    if (typeof callback !== 'function') return () => {};
    const handler = (_event, status) => callback(status);
    ipcRenderer.on('overlay:status', handler);
    return () => ipcRenderer.removeListener('overlay:status', handler);
  },
});
