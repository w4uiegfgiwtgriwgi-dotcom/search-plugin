const http = require("node:http");
const path = require("node:path");
const { spawn } = require("node:child_process");

const API_HOST = "127.0.0.1";
const API_PORT = 17860;
const API_ORIGIN = `http://${API_HOST}:${API_PORT}`;

function projectRoot() {
  return path.resolve(__dirname, "..", "..");
}

function pythonPath(root = projectRoot()) {
  return path.join(root, ".venv", "Scripts", "python.exe");
}

function apiScriptPath(root = projectRoot()) {
  return path.join(root, "scripts", "run-fastapi-api.py");
}

function checkApi(timeoutMs = 1200) {
  return new Promise((resolve) => {
    const request = http.get(`${API_ORIGIN}/api/platforms`, { timeout: timeoutMs }, (response) => {
      response.resume();
      resolve(response.statusCode >= 200 && response.statusCode < 500);
    });
    request.on("timeout", () => {
      request.destroy();
      resolve(false);
    });
    request.on("error", () => resolve(false));
  });
}

async function waitForApi(timeoutMs = 12000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    if (await checkApi(800)) return true;
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  return false;
}

async function ensureApiRunning(options = {}) {
  const root = options.root || projectRoot();
  if (await checkApi()) {
    return { status: "ready", owned: false, origin: API_ORIGIN, process: null };
  }

  const child = spawn(pythonPath(root), [apiScriptPath(root)], {
    cwd: root,
    windowsHide: true,
    stdio: "ignore",
  });

  const ready = await waitForApi(options.timeoutMs || 15000);
  if (!ready) {
    child.kill();
    throw new Error("本地 API 启动超时");
  }
  return { status: "ready", owned: true, origin: API_ORIGIN, process: child };
}

function stopOwnedApi(apiState) {
  if (apiState && apiState.owned && apiState.process && !apiState.process.killed) {
    apiState.process.kill();
  }
}

module.exports = {
  API_ORIGIN,
  checkApi,
  ensureApiRunning,
  stopOwnedApi,
  projectRoot,
  pythonPath,
  apiScriptPath,
};
