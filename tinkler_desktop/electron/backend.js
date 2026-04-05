const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const DEFAULT_BACKEND_URL = process.env.TINKLER_BACKEND_URL || "http://127.0.0.1:8000";
const HEALTHCHECK_PATH = "/health";
const STARTUP_RETRIES = 24;
const STARTUP_DELAY_MS = 500;
const LOG_LIMIT = 200;

function delay(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function createBackendManager({ repoRoot, onStateChange }) {
  let backendProcess = null;
  let startupPromise = null;
  let stopping = false;
  const logs = [];
  const backendUrl = DEFAULT_BACKEND_URL;
  let state = {
    status: "idle",
    url: backendUrl,
    message: "Backend not started yet.",
    logs: [],
    pid: null,
    startedByApp: false
  };

  function pushLog(source, chunk) {
    const lines = String(chunk)
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);

    for (const line of lines) {
      logs.push(`[${source}] ${line}`);
      if (logs.length > LOG_LIMIT) {
        logs.shift();
      }
    }

    emit({});
  }

  function emit(partial) {
    state = {
      ...state,
      ...partial,
      logs: [...logs]
    };
    if (typeof onStateChange === "function") {
      onStateChange(state);
    }
  }

  function getState() {
    return {
      ...state,
      logs: [...logs]
    };
  }

  async function isHealthy() {
    try {
      const response = await fetch(`${backendUrl}${HEALTHCHECK_PATH}`);
      return response.ok;
    } catch (_error) {
      return false;
    }
  }

  function resolvePythonCommand() {
    const venvPython = path.join(repoRoot, ".venv", "bin", "python");
    if (fs.existsSync(venvPython)) {
      return venvPython;
    }
    return "python3";
  }

  function resolveBackendEnvironment() {
    const url = new URL(backendUrl);
    return {
      ...process.env,
      TINKLER_BACKEND_HOST: url.hostname,
      TINKLER_BACKEND_PORT: url.port || "8000"
    };
  }

  async function ensureRunning() {
    if (await isHealthy()) {
      emit({
        status: "ready",
        message: "Connected to running backend.",
        pid: null,
        startedByApp: false
      });
      return getState();
    }

    if (startupPromise) {
      return startupPromise;
    }

    startupPromise = (async () => {
      emit({
        status: "starting",
        message: "Starting local backend..."
      });

      const pythonCommand = resolvePythonCommand();
      backendProcess = spawn(pythonCommand, ["-m", "tinkler_backend"], {
        cwd: repoRoot,
        env: resolveBackendEnvironment(),
        stdio: ["ignore", "pipe", "pipe"]
      });
      stopping = false;

      backendProcess.stdout.on("data", (chunk) => {
        pushLog("backend", chunk);
      });
      backendProcess.stderr.on("data", (chunk) => {
        pushLog("backend", chunk);
      });
      backendProcess.on("exit", (code, signal) => {
        const expected = stopping;
        backendProcess = null;
        emit({
          status: expected ? "stopped" : "error",
          message: expected
            ? "Backend stopped."
            : `Backend exited unexpectedly (${code ?? signal ?? "unknown"}).`,
          pid: null,
          startedByApp: false
        });
      });

      emit({
        status: "starting",
        message: "Waiting for backend health check...",
        pid: backendProcess.pid,
        startedByApp: true
      });

      for (let attempt = 0; attempt < STARTUP_RETRIES; attempt += 1) {
        if (await isHealthy()) {
          emit({
            status: "ready",
            message: "Backend is ready.",
            pid: backendProcess ? backendProcess.pid : null,
            startedByApp: true
          });
          return getState();
        }
        await delay(STARTUP_DELAY_MS);
      }

      emit({
        status: "error",
        message: "Backend did not become healthy in time.",
        pid: backendProcess ? backendProcess.pid : null,
        startedByApp: true
      });
      return getState();
    })().finally(() => {
      startupPromise = null;
    });

    return startupPromise;
  }

  async function stop() {
    if (!backendProcess) {
      emit({
        status: "stopped",
        message: "Backend is not running.",
        pid: null,
        startedByApp: false
      });
      return getState();
    }

    stopping = true;
    const processRef = backendProcess;
    processRef.kill("SIGTERM");
    await delay(250);

    if (backendProcess && backendProcess.pid === processRef.pid) {
      processRef.kill("SIGKILL");
    }

    backendProcess = null;
    emit({
      status: "stopped",
      message: "Backend stopped.",
      pid: null,
      startedByApp: false
    });
    return getState();
  }

  return {
    ensureRunning,
    stop,
    getState
  };
}

module.exports = {
  createBackendManager
};
