const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("klyptraDesktop", {
  isElectron: true,
  platform: process.platform,
  version: "1.0.0",
  selectFolder: () => ipcRenderer.invoke("klyptra:select-folder"),
  selectVideoFile: () => ipcRenderer.invoke("klyptra:select-video-file")
});
