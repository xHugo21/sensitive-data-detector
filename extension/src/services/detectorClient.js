(function initDetectorClient(root) {
  const sg = (root.SG = root.SG || {});

  async function detectText(text, mode = sg.config.MODE) {
    const payload = { text };
    if (mode) payload.mode = mode;
    const resp = await fetch(`${sg.config.API_BASE}/detect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(`Detector HTTP ${resp.status}`);
    return resp.json();
  }

  async function detectFile(formData) {
    const resp = await fetch(`${sg.config.API_BASE}/detect_file`, {
      method: "POST",
      body: formData,
    });
    if (!resp.ok) throw new Error(`Detector HTTP ${resp.status}`);
    return resp.json();
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
    detectFile,
    waitForStableContent,
  };
})(typeof window !== "undefined" ? window : globalThis);
