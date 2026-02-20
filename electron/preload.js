const { contextBridge, ipcRenderer } = require('electron');

// API segura disponível para o renderer.
contextBridge.exposeInMainWorld('merlinAPI', {
  ask: (question) => ipcRenderer.invoke('ask-merlin', question),
  getDocuments: () => ipcRenderer.invoke('get-documents'),
  onUpdateAvailable: (callback) => ipcRenderer.on('update-available', callback),
});
