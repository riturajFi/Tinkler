(function attachBackendClient(globalScope) {
  function normaliseDataLines(lines) {
    return lines.join("\n").trim();
  }

  function parseEventBlock(block) {
    const lines = block
      .split(/\r?\n/)
      .map((line) => line.trimEnd())
      .filter(Boolean);

    if (!lines.length) {
      return null;
    }

    let eventType = "message";
    const dataLines = [];

    for (const line of lines) {
      if (line.startsWith("event:")) {
        eventType = line.slice(6).trim();
        continue;
      }
      if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }

    if (!dataLines.length) {
      return null;
    }

    const rawData = normaliseDataLines(dataLines);
    return {
      type: eventType,
      payload: JSON.parse(rawData)
    };
  }

  async function streamRun({ backendUrl, payload, onEvent }) {
    const response = await fetch(`${backendUrl}/api/v1/agent/runs/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Backend request failed with ${response.status}`);
    }

    if (!response.body) {
      throw new Error("Streaming response body was not available.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split(/\n\n/);
      buffer = parts.pop() || "";

      for (const part of parts) {
        const parsed = parseEventBlock(part);
        if (parsed && typeof onEvent === "function") {
          onEvent(parsed);
        }
      }
    }

    const tail = buffer.trim();
    if (tail) {
      const parsed = parseEventBlock(tail);
      if (parsed && typeof onEvent === "function") {
        onEvent(parsed);
      }
    }
  }

  globalScope.TinklerBackendClient = {
    parseEventBlock,
    streamRun
  };
})(typeof window !== "undefined" ? window : globalThis);
