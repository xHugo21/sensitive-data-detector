(function initDetectorClient(root) {
  const sg = (root.SG = root.SG || {});

  const DEFAULT_ERROR_MESSAGE = "Analysis failed - Backend Unreachable";
  function createDetectorError(message, displayMessage) {
    const err = new Error(message);
    if (displayMessage) err.displayMessage = displayMessage;
    return err;
  }

  function ensureValidResponse(payload) {
    if (!payload || typeof payload !== "object") {
      throw createDetectorError(
        "Invalid detector response",
        "Analysis failed - invalid response.",
      );
    }
    if (payload.error) {
      throw createDetectorError(
        `Detector error: ${payload.error}`,
        "Analysis failed - backend error.",
      );
    }
    if (!("risk_level" in payload) || !Array.isArray(payload.detected_fields)) {
      throw createDetectorError(
        "Invalid detector response",
        "Analysis failed - invalid response.",
      );
    }
    return payload;
  }

  function formatNodeMessage(node, status) {
    if (!node) return null;
    const label = String(node).replace(/_/g, " ").trim();
    if (status === "completed") {
      return `${label} finished`;
    }
    return `${label} running`;
  }

  async function requestDetect(formData) {
    let resp;
    try {
      resp = await fetch(`${sg.config.API_BASE}/detect`, {
        method: "POST",
        body: formData,
      });
    } catch (err) {
      throw createDetectorError("Detector unreachable", DEFAULT_ERROR_MESSAGE);
    }
    if (!resp.ok) {
      throw createDetectorError(
        `Detector HTTP ${resp.status}`,
        "Analysis failed - backend error.",
      );
    }
    let payload;
    try {
      payload = await resp.json();
    } catch (err) {
      throw createDetectorError(
        "Invalid detector response",
        "Analysis failed - invalid response.",
      );
    }
    return ensureValidResponse(payload);
  }

  async function requestDetectStream(formData, onProgress) {
    let resp;
    try {
      resp = await fetch(`${sg.config.API_BASE}/detect/stream`, {
        method: "POST",
        body: formData,
      });
    } catch (err) {
      throw createDetectorError("Detector unreachable", DEFAULT_ERROR_MESSAGE);
    }
    if (!resp.ok) {
      let payload = null;
      try {
        payload = await resp.json();
      } catch (err) {
        payload = null;
      }
      if (payload?.error) {
        throw createDetectorError(
          `Detector error: ${payload.error}`,
          "Analysis failed - backend error.",
        );
      }
      throw createDetectorError(
        `Detector HTTP ${resp.status}`,
        "Analysis failed - backend error.",
      );
    }
    if (!resp.body) {
      let payload;
      try {
        payload = await resp.json();
      } catch (err) {
        throw createDetectorError(
          "Invalid detector response",
          "Analysis failed - invalid response.",
        );
      }
      return ensureValidResponse(payload);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalResult = null;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        let event;
        try {
          event = JSON.parse(trimmed);
        } catch (err) {
          continue;
        }
        if (event.type === "node") {
          if (typeof onProgress === "function") {
            const message = formatNodeMessage(event.node, event.status);
            if (message) onProgress(message, event);
          }
        } else if (event.type === "error") {
          throw createDetectorError(
            `Detector error: ${event.error}`,
            "Analysis failed - backend error.",
          );
        } else if (event.type === "result") {
          finalResult = event.result;
        }
      }
    }

    if (buffer.trim()) {
      try {
        const event = JSON.parse(buffer.trim());
        if (event.type === "result") {
          finalResult = event.result;
        } else if (event.type === "error") {
          throw createDetectorError(
            `Detector error: ${event.error}`,
            "Analysis failed - backend error.",
          );
        }
      } catch (err) {
        // ignore trailing parse errors
      }
    }

    if (!finalResult) {
      throw createDetectorError(
        "Invalid detector response",
        "Analysis failed - invalid response.",
      );
    }
    return ensureValidResponse(finalResult);
  }

  async function detectText(text) {
    const formData = new FormData();
    formData.append("text", text);

    return requestDetect(formData);
  }

  async function detectTextStream(text, onProgress) {
    const formData = new FormData();
    formData.append("text", text);

    return requestDetectStream(formData, onProgress);
  }

  async function detectFile(formData) {
    return requestDetect(formData);
  }

  async function detectFileStream(formData, onProgress) {
    return requestDetectStream(formData, onProgress);
  }

  function waitForStableContent(node, idleMs = 800) {
    return new Promise((resolve) => {
      let timer = setTimeout(done, idleMs);
      const obs = new MutationObserver(() => {
        clearTimeout(timer);
        timer = setTimeout(done, idleMs);
      });
      function done() {
        obs.disconnect();
        resolve();
      }
      obs.observe(node, {
        childList: true,
        subtree: true,
        characterData: true,
      });
    });
  }

  sg.detectorClient = {
    detectText,
    detectTextStream,
    detectFile,
    detectFileStream,
    waitForStableContent,
  };
})(typeof window !== "undefined" ? window : globalThis);
