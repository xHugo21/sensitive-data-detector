/* global chrome */
(function initPopup(root) {
  const sg = (root.SG = root.SG || {});

  const blockLevelValue = document.getElementById("block-level-value");
  const siteStatus = document.getElementById("site-status");
  if (!blockLevelValue || !siteStatus) {
    return;
  }

  function setBlockLevelUI(level) {
    const displayLevel = level ? level.charAt(0).toUpperCase() + level.slice(1) : "Unknown";
    blockLevelValue.textContent = displayLevel;
    blockLevelValue.dataset.state = "on"; // Always green-ish since it's active
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

  // Display current block level from config
  setBlockLevelUI(sg.config?.MIN_BLOCK_LEVEL);

  updatePlatformStatus();
})(typeof window !== "undefined" ? window : globalThis);
