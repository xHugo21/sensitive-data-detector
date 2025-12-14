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

    // Allow send if override is active
    if (sg.alertStore.isOverrideActive()) return;

    const composer = sg.chatSelectors.findComposer();
    if (!composer) return;
    const text = sg.chatSelectors.getComposerText(composer);
    if (!text) return;

    event.preventDefault();
    event.stopPropagation();
    analyzeBeforeSend({ composer, text });
  }

  function handleSendButtonClick(event) {
    // Check if clicked element or its closest button ancestor is the send button
    const clickedButton =
      event.target.tagName === "BUTTON"
        ? event.target
        : event.target.closest("button");

    if (!clickedButton) return;

    // Use platform-specific button detection
    const platform = sg.platformRegistry?.getActive();
    if (!platform || !platform.isSendButton(clickedButton)) return;

    // Allow send if override is active or bypass flag is set
    if (clickedButton.dataset.sgBypass === "true") return;
    if (sg.alertStore.isOverrideActive()) return;

    const composer = sg.chatSelectors.findComposer();
    if (!composer) return;
    const text = sg.chatSelectors.getComposerText(composer);
    if (!text) return;

    event.preventDefault();
    event.stopImmediatePropagation();
    analyzeBeforeSend({ composer, button: clickedButton, text });
  }

  async function analyzeBeforeSend({ composer, button = null, text }) {
    const startedAt = (root.performance || {}).now
      ? performance.now()
      : Date.now();
    const loadingTarget = {
      composer,
      button: button || sg.chatSelectors.findSendButton(),
      message: "Analyzing message...",
    };
    sg.loadingState.show(loadingTarget);
    try {
      const result = await sg.detectorClient.detectText(text);
      sg.highlights.applyHighlights(
        composer,
        result?.detected_fields || [],
        "user",
      );

      if (sg.riskUtils.shouldBlock(result)) {
        const durationMs = ((root.performance || {}).now
          ? performance.now()
          : Date.now()) - startedAt;
        lastSendIntent = { composer, button };
        sg.panel.render(result, text, { durationMs });
        return;
      }

      allowSend(composer, button);
    } catch (err) {
      console.error(
        "[SensitiveDataDetectorExtension] Backend error, allowing send:",
        err,
      );
      allowSend(composer, button);
    } finally {
      sg.loadingState.hide();
    }
  }

  function allowSend(composer, button) {
    setTimeout(() => sg.highlights.clearHighlights("user"), 50);
    dispatchSend(composer, button);
    lastSendIntent = null;
  }

  function dispatchSend(composer, button) {
    sg.alertStore.setOverrideActive(true);
    try {
      sg.chatSelectors.triggerSend(composer, button);
    } finally {
      setTimeout(() => sg.alertStore.setOverrideActive(false), 150);
    }
  }

  function handleSendAnywayOverride() {
    if (!lastSendIntent) {
      sg.panel.hide();
      return;
    }

    sg.alertStore.setOverrideActive(true);
    sg.panel.hide();
    dispatchSend(lastSendIntent.composer, lastSendIntent.button);
    setTimeout(() => sg.alertStore.setOverrideActive(false), 1500);
    lastSendIntent = null;
  }

  sg.sendInterceptor = { attach };
})(typeof window !== "undefined" ? window : globalThis);
