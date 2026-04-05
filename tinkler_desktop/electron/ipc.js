const { dialog, ipcMain } = require("electron");

function registerIpcHandlers({ backendManager, getMainWindow }) {
  ipcMain.handle("backend:get-state", async () => {
    return backendManager.getState();
  });

  ipcMain.handle("backend:start", async () => {
    return backendManager.ensureRunning();
  });

  ipcMain.handle("backend:stop", async () => {
    return backendManager.stop();
  });

  ipcMain.handle("dialog:pick-folder", async () => {
    const window = getMainWindow();
    const result = await dialog.showOpenDialog(window, {
      properties: ["openDirectory", "createDirectory"]
    });

    if (result.canceled || !result.filePaths.length) {
      return null;
    }
    return result.filePaths[0];
  });
}

module.exports = {
  registerIpcHandlers
};
