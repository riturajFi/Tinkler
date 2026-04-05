(function bootstrapDesktopApp() {
  const elements = {
    backendStatusPill: document.getElementById("backend-status-pill"),
    backendStartButton: document.getElementById("backend-start-button"),
    backendUrl: document.getElementById("backend-url"),
    backendMessage: document.getElementById("backend-message"),
    backendLog: document.getElementById("backend-log"),
    selectedFolder: document.getElementById("selected-folder"),
    pickFolderButton: document.getElementById("pick-folder-button"),
    requestInput: document.getElementById("request-input"),
    modelInput: document.getElementById("model-input"),
    maxTurnsInput: document.getElementById("max-turns-input"),
    allowWritesInput: document.getElementById("allow-writes-input"),
    runButton: document.getElementById("run-button"),
    runStatus: document.getElementById("run-status"),
    loopProgress: document.getElementById("loop-progress"),
    finalResponse: document.getElementById("final-response"),
    timeline: document.getElementById("timeline"),
    eventCount: document.getElementById("event-count"),
    changedFiles: document.getElementById("changed-files")
  };

  const state = {
    backend: null,
    eventCount: 0,
    running: false
  };

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  function renderEmptyTimeline() {
    elements.timeline.innerHTML = '<div class="timeline-empty">No loop events yet.</div>';
  }

  function appendTimelineEvent({ title, subtitle, content, tone = "neutral" }) {
    if (state.eventCount === 0) {
      elements.timeline.innerHTML = "";
    }

    const item = document.createElement("article");
    item.className = `timeline-item tone-${tone}`;
    item.innerHTML = [
      '<div class="timeline-head">',
      `  <div class="timeline-title">${escapeHtml(title)}</div>`,
      `  <div class="timeline-subtitle">${escapeHtml(subtitle)}</div>`,
      "</div>",
      `<div class="timeline-content">${escapeHtml(content)}</div>`
    ].join("\n");
    elements.timeline.prepend(item);

    state.eventCount += 1;
    elements.eventCount.textContent = `${state.eventCount} event${state.eventCount === 1 ? "" : "s"}`;
  }

  function setRunStatus(status, label) {
    elements.runStatus.className = `run-status ${status}`;
    elements.runStatus.textContent = label;
  }

  function renderChangedFiles(files) {
    elements.changedFiles.innerHTML = "";
    if (!files || !files.length) {
      return;
    }

    for (const file of files) {
      const chip = document.createElement("span");
      chip.className = "changed-file";
      chip.textContent = file;
      elements.changedFiles.appendChild(chip);
    }
  }

  function formatPayload(event) {
    return JSON.stringify(event.payload, null, 2);
  }

  function formatStatusLabel(status) {
    return String(status || "idle").replaceAll("_", " ");
  }

  function toneForEventType(type) {
    if (type === "model.action") {
      return "model";
    }
    if (type === "tool.result") {
      return "tool";
    }
    if (type === "run.completed") {
      return "success";
    }
    if (type === "run.failed") {
      return "error";
    }
    if (type === "loop.progress") {
      return "progress";
    }
    return "neutral";
  }

  function updateLoopProgress(turnCount, maxTurns) {
    elements.loopProgress.textContent = `${turnCount} / ${maxTurns}`;
  }

  function applyBackendState(backendState) {
    state.backend = backendState;
    elements.backendUrl.textContent = backendState.url;
    elements.backendMessage.textContent = backendState.message;
    elements.backendStatusPill.textContent = formatStatusLabel(backendState.status);
    elements.backendStatusPill.className = `status-pill status-${backendState.status}`;
    elements.backendLog.textContent = backendState.logs.length
      ? backendState.logs.join("\n")
      : "No logs yet.";
  }

  async function initialiseBackendState() {
    const backendState = await window.tinklerDesktop.backend.getState();
    applyBackendState(backendState);
  }

  async function ensureBackendReady() {
    const backendState = await window.tinklerDesktop.backend.start();
    applyBackendState(backendState);
    if (backendState.status !== "ready") {
      throw new Error(backendState.message || "Backend was not ready.");
    }
    return backendState;
  }

  function buildRequestPayload() {
    return {
      cwd: elements.selectedFolder.value.trim(),
      request: elements.requestInput.value.trim(),
      max_turns: Number(elements.maxTurnsInput.value || 30),
      model: elements.modelInput.value.trim() || null,
      allow_writes: elements.allowWritesInput.checked
    };
  }

  function validateForm(payload) {
    if (!payload.cwd) {
      throw new Error("Choose a repository folder first.");
    }
    if (!payload.request) {
      throw new Error("Enter a request for the agent.");
    }
  }

  function resetRunOutput() {
    state.eventCount = 0;
    elements.eventCount.textContent = "0 events";
    elements.finalResponse.textContent = "Waiting for agent output...";
    renderChangedFiles([]);
    renderEmptyTimeline();
    updateLoopProgress(0, 0);
  }

  async function runAgent() {
    const payload = buildRequestPayload();
    validateForm(payload);
    const backendState = await ensureBackendReady();
    resetRunOutput();
    state.running = true;
    setRunStatus("running", "Running");
    elements.runButton.disabled = true;

    appendTimelineEvent({
      title: "Run queued",
      subtitle: payload.cwd,
      content: payload.request,
      tone: "progress"
    });

    try {
      await window.TinklerBackendClient.streamRun({
        backendUrl: backendState.url,
        payload,
        onEvent(event) {
          const turnCount = event.payload.turn_count || 0;
          const maxTurns = event.payload.max_turns || payload.max_turns || 0;
          updateLoopProgress(turnCount, maxTurns);

          if (event.type === "run.completed") {
            elements.finalResponse.textContent = event.payload.payload.response || "Run completed.";
            renderChangedFiles(event.payload.payload.changed_files || []);
            setRunStatus("done", "Completed");
          } else if (event.type === "run.failed") {
            elements.finalResponse.textContent = event.payload.payload.error || "Run failed.";
            setRunStatus("error", "Failed");
          }

          if (event.type === "model.action") {
            appendTimelineEvent({
              title: "Model action",
              subtitle: `Turn ${event.payload.turn_count}`,
              content: formatPayload(event),
              tone: "model"
            });
            return;
          }

          if (event.type === "tool.result") {
            appendTimelineEvent({
              title: "Tool result",
              subtitle: event.payload.payload.tool_name || event.payload.node || "tool",
              content: formatPayload(event),
              tone: "tool"
            });
            return;
          }

          appendTimelineEvent({
            title: event.type,
            subtitle: event.payload.node || `Turn ${event.payload.turn_count}`,
            content: formatPayload(event),
            tone: toneForEventType(event.type)
          });
        }
      });

      if (elements.runStatus.textContent === "Running") {
        setRunStatus("done", "Completed");
      }
    } catch (error) {
      elements.finalResponse.textContent = error.message;
      setRunStatus("error", "Failed");
      appendTimelineEvent({
        title: "Run error",
        subtitle: "Renderer",
        content: error.message,
        tone: "error"
      });
    } finally {
      state.running = false;
      elements.runButton.disabled = false;
    }
  }

  async function handleFolderPick() {
    const selectedFolder = await window.tinklerDesktop.pickFolder();
    if (selectedFolder) {
      elements.selectedFolder.value = selectedFolder;
    }
  }

  function bindEvents() {
    elements.pickFolderButton.addEventListener("click", handleFolderPick);
    elements.backendStartButton.addEventListener("click", async () => {
      const backendState = await window.tinklerDesktop.backend.start();
      applyBackendState(backendState);
    });
    elements.runButton.addEventListener("click", () => {
      if (!state.running) {
        runAgent().catch((error) => {
          elements.finalResponse.textContent = error.message;
          setRunStatus("error", "Failed");
        });
      }
    });
    window.tinklerDesktop.backend.onStateChange(applyBackendState);
  }

  async function start() {
    bindEvents();
    renderEmptyTimeline();
    setRunStatus("idle", "Not running");
    await initialiseBackendState();
  }

  start().catch((error) => {
    elements.finalResponse.textContent = error.message;
    setRunStatus("error", "Failed");
  });
})();
