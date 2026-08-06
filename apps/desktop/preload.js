const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("vmf", {
  getApiStatus: () => ipcRenderer.invoke("get-api-status"),
  onApiStatus: (callback) => {
    ipcRenderer.on("api-status", (_event, status) => callback(status));
  },
});
