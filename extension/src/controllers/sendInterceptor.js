(function initSendInterceptor(root) {
  const sg = (root.SG = root.SG || {});

  let attached = false;
  let lastSendIntent = null;
  let overrideTimer = null;

  function attach() {
    if (attached) return;
    const composer = sg.chatSelectors.findComposer();
    if (!composer) return;
    attached = true;

    sg.panel.ensure();
    sg.highlights.ensureHighlightCSS();
    sg.panel.onSendAnyway(handleSendAnywayOverride);

    composer.addEventListener("keydown", handleComposerKeydown, true);
    document.addEventListener("click", handleSendButtonClick, true);
  }

  function handleComposerKeydown(event) {
    if (event.key !== "Enter" || event.shiftKey) return;
    const composer = sg.chatSelectors.findComposer();
    if (!composer) return;
    const text = sg.chatSelectors.getComposerText(composer);
    if (!text) return;

    event.preventDefault();
    event.stopPropagation();
    analyzeBeforeSend({ composer, text });
  }

  function handleSendButtonClick(event) {
    const btn = event.target.closest(
      'button[type="submit"], [data-testid="send-button"]',
    );
    if (!btn) return;
    if (btn.dataset.sgBypass === "true") return;

    const composer = sg.chatSelectors.findComposer();
    if (!composer) return;
    const text = sg.chatSelectors.getComposerText(composer);
    if (!text) return;

    event.preventDefault();
    event.stopImmediatePropagation();
    analyzeBeforeSend({ composer, button: btn, text });
  }

  async function analyzeBeforeSend({ composer, button = null, text }) {
    const loadingTarget = button || sg.chatSelectors.findSendButton();
    sg.loadingState.show(loadingTarget);
    try {
      const result = await sg.detectorClient.detectText(text);
      sg.highlights.applyHighlights(
        composer,
        result?.detected_fields || [],
        "user",
      );

      if (sg.riskUtils.shouldBlock(result?.risk_level)) {
        lastSendIntent = { composer, button };
        sg.panel.render(result, "User", text);
        return;
      }

      allowSend(composer, button);
    } catch (err) {
      console.error(
        "[SensitiveDataDetector] Backend error, allowing send:",
        err,
      );
      allowSend(composer, button);
    } finally {
      sg.loadingState.hide(loadingTarget);
    }
  }

  function allowSend(composer, button) {
    sg.alertStore.setResponsePending(true);
    sg.alertStore.setSuppressUserAlerts(true);
    setTimeout(() => sg.highlights.clearHighlights("user"), 50);
    dispatchSend(composer, button);
    lastSendIntent = null;
  }

  function dispatchSend(composer, button) {
    const targetButton = button || sg.chatSelectors.findSendButton();
    if (targetButton) {
      targetButton.dataset.sgBypass = "true";
      setTimeout(() => {
        targetButton.click();
        delete targetButton.dataset.sgBypass;
      }, 10);
      return;
    }

    const enterEvent = new KeyboardEvent("keydown", {
      key: "Enter",
      code: "Enter",
      keyCode: 13,
      which: 13,
      bubbles: true,
      cancelable: true,
    });
    composer.dispatchEvent(enterEvent);
  }

  function handleSendAnywayOverride() {
    if (!lastSendIntent) {
      sg.panel.hide();
      return;
    }

    sg.alertStore.setResponsePending(true);
    sg.alertStore.setSuppressUserAlerts(true);
    sg.alertStore.setOverrideActive(true);
    sg.panel.hide();
    dispatchSend(lastSendIntent.composer, lastSendIntent.button);
    setTimeout(() => sg.alertStore.setOverrideActive(false), 1500);
    lastSendIntent = null;
  }

  sg.sendInterceptor = { attach };
})(typeof window !== "undefined" ? window : globalThis);
