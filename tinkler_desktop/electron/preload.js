const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("tinklerDesktop", {
  backend: {
    getState() {
      return ipcRenderer.invoke("backend:get-state");
    },
    start() {
      return ipcRenderer.invoke("backend:start");
    },
    stop() {
      return ipcRenderer.invoke("backend:stop");
    },
    onStateChange(listener) {
      const wrapped = (_event, payload) => {
        listener(payload);
      };
      ipcRenderer.on("backend:state", wrapped);
      return () => {
        ipcRenderer.removeListener("backend:state", wrapped);
      };
    }
  },
  pickFolder() {
    return ipcRenderer.invoke("dialog:pick-folder");
  }
});
