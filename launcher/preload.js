const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('sentinel', {
  catalog: () => ipcRenderer.invoke('catalog'),
  getConfig: () => ipcRenderer.invoke('config:get'),
  setExecutable: (id, executable) => ipcRenderer.invoke('config:set', id, executable),
  launch: (id) => ipcRenderer.invoke('game:launch', id),
});
