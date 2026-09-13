'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('sentinelOverlay', {
  onSnapshot: callback => {
    if (typeof callback !== 'function') return () => {};
    const handler = (_event, snapshot) => callback(Array.isArray(snapshot) ? snapshot : []);
    ipcRenderer.on('overlay:snapshot', handler);
    return () => ipcRenderer.removeListener('overlay:snapshot', handler);
  },
});
