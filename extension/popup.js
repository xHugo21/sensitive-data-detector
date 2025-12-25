/* global chrome */
(function initPopup(root) {
  const sg = (root.SG = root.SG || {});

  const toggle = document.getElementById("toggle-detection");
  const detectionState = document.getElementById("detection-state");
  const siteStatus = document.getElementById("site-status");
  if (!toggle || !detectionState || !siteStatus) {
    return;
  }

  function setDetectionUI(enabled) {
    toggle.checked = !!enabled;
    detectionState.textContent = enabled ? "Enabled" : "Disabled";
    detectionState.dataset.state = enabled ? "on" : "off";
  }

  function setSiteStatus(text, supportState) {
    siteStatus.textContent = text;
    if (supportState) {
      siteStatus.dataset.supported = supportState;
    } else {
      delete siteStatus.dataset.supported;
    }
  }

  function updatePlatformStatus() {
    if (!root.chrome?.tabs?.query) {
      setSiteStatus("Site status unavailable", "unknown");
      return;
    }

    root.chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (root.chrome.runtime?.lastError) {
        setSiteStatus("Site status unavailable", "unknown");
        return;
      }

      const tab = tabs && tabs[0];
      const url = tab?.url || "";
      if (!url || url.startsWith("chrome://") || url.startsWith("edge://")) {
        setSiteStatus("Site status unavailable", "unknown");
        return;
      }

      const platform = sg.platformRegistry?.detectPlatform?.(url);
      if (platform) {
        setSiteStatus(`Supported platform: ${platform.displayName}`, "yes");
        return;
      }

      setSiteStatus("This site is not supported", "no");
    });
  }

  const initialState = sg.settings?.getState?.();
  if (initialState) {
    setDetectionUI(initialState.detectionEnabled);
  } else {
    setDetectionUI(true);
  }

  sg.settings?.subscribe?.((state) => {
    setDetectionUI(state.detectionEnabled);
  });

  toggle.addEventListener("change", () => {
    if (!sg.settings?.setDetectionEnabled) return;
    sg.settings.setDetectionEnabled(toggle.checked);
  });

  updatePlatformStatus();
})(typeof window !== "undefined" ? window : globalThis);
