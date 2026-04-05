const path = require("node:path");
const { app, BrowserWindow } = require("electron");

const { createBackendManager } = require("./backend");
const { registerIpcHandlers } = require("./ipc");

const repoRoot = path.resolve(__dirname, "..", "..");
let mainWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 1100,
    minHeight: 760,
    backgroundColor: "#10161f",
    title: "Tinkler Desktop",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.loadFile(path.join(__dirname, "..", "renderer", "index.html"));
  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  return mainWindow;
}

const backendManager = createBackendManager({
  repoRoot,
  onStateChange(state) {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("backend:state", state);
    }
  }
});

registerIpcHandlers({
  backendManager,
  getMainWindow() {
    return mainWindow;
  }
});

app.whenReady().then(async () => {
  createWindow();
  await backendManager.ensureRunning();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", async () => {
  if (process.platform !== "darwin") {
    await backendManager.stop();
    app.quit();
  }
});

app.on("before-quit", async () => {
  await backendManager.stop();
});
