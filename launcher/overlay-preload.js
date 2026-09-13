'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('sentinelOverlay', Object.freeze({
  onSnapshot(callback) {
    if (typeof callback !== 'function') return () => {};
    const listener = (_event, snapshot) => callback(snapshot);
    ipcRenderer.on('overlay:snapshot', listener);
    return () => ipcRenderer.removeListener('overlay:snapshot', listener);
  },
}));
