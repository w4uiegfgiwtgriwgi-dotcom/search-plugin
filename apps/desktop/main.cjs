const { app, BrowserWindow } = require("electron");
const path = require("node:path");
function createWindow() {
  const win = new BrowserWindow({ width: 1120, height: 760, webPreferences: { preload: path.join(__dirname, "preload.js") } });
  win.loadFile(path.join(__dirname, "src", "index.html"));
}
app.whenReady().then(createWindow);
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
