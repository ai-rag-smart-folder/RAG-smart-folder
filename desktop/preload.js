const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
    selectFolder: () => ipcRenderer.invoke('select-folder'),
    getImageDataUrl: (filePath) => ipcRenderer.invoke('get-image-data-url', filePath),
    checkImageExists: (filePath) => ipcRenderer.invoke('check-image-exists', filePath)
});