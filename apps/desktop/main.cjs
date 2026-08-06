const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("node:path");
const { API_ORIGIN, ensureApiRunning, stopOwnedApi } = require("./api-process.cjs");

let mainWindow;
let apiState = { status: "starting", owned: false, origin: API_ORIGIN, process: null };
const smokeMode = process.env.VMF_ELECTRON_SMOKE === "1";

if (smokeMode) {
  setTimeout(() => {
    console.log("electron smoke timeout reached, exiting");
    app.exit(0);
  }, 8000);
}

function publicApiState() {
  return {
    status: apiState.status,
    owned: apiState.owned,
    origin: apiState.origin,
    error: apiState.error,
  };
}

function sendApiStatus(status) {
  apiState = { ...apiState, ...status };
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send("api-status", publicApiState());
  }
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1120,
    height: 760,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow = win;
  win.loadFile(path.join(__dirname, "src", "index.html"));
  win.webContents.once("did-finish-load", () => {
    sendApiStatus(apiState);
  });
}

ipcMain.handle("get-api-status", () => publicApiState());

app.whenReady().then(async () => {
  createWindow();
  try {
    sendApiStatus({ status: "starting", origin: API_ORIGIN });
    apiState = await ensureApiRunning();
    sendApiStatus(apiState);
  } catch (error) {
    sendApiStatus({ status: "failed", error: error.message, origin: API_ORIGIN });
  }
  if (smokeMode) {
    console.log(`electron smoke api status: ${apiState.status}`);
    setTimeout(() => app.exit(apiState.status === "ready" ? 0 : 1), 1200);
  }
});

app.on("before-quit", () => {
  stopOwnedApi(apiState);
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
