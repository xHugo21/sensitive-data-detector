(function initMessageAnalyzer(root) {
  const sg = (root.SG = root.SG || {});

  let observer = null;

  function start() {
    if (!observer) {
      observer = new MutationObserver(handleMutations);
      observer.observe(document.documentElement, {
        childList: true,
        subtree: true,
        characterData: true,
      });
    }
  }

  function handleMutations(mutations) {
    if (sg.chatSelectors.findComposer()) sg.sendInterceptor.attach();
    for (const mutation of mutations) {
      mutation.addedNodes &&
        mutation.addedNodes.forEach((node) => {
          if (sg.chatSelectors.isMessageNode(node))
            analyzeMessageNode(node, "Response");
          if (node.querySelectorAll) {
            // Try to find message nodes within the added node
            const messageNodes = Array.from(node.querySelectorAll("*")).filter(
              (el) => sg.chatSelectors.isMessageNode(el)
            );
            messageNodes.forEach((host) => analyzeMessageNode(host, "Response"));
          }
        });
    }

    if (sg.alertStore.isResponsePending()) {
      // Find the last assistant message using platform-agnostic detection
      const allNodes = document.querySelectorAll("*");
      const assistantMessages = Array.from(allNodes).filter(
        (node) => sg.chatSelectors.getMessageRole(node) === "assistant"
      );
      const lastAssistant = assistantMessages[assistantMessages.length - 1];
      if (lastAssistant) analyzeMessageNode(lastAssistant, "Response");
    }
  }

  async function analyzeMessageNode(node, originGuess = "Unknown") {
    if (!node) return;
    const store = sg.alertStore;
    const host = node.closest?.("[data-message-author-role]") || node;
    if (!host || store.hasAnalyzed(host) || store.isInFlight(host)) return;

    // Use platform-agnostic role detection
    const messageRole = sg.chatSelectors.getMessageRole(host);
    const isAssistant = messageRole === "assistant";
    const isUser = messageRole === "user";

    if (isAssistant) {
      if (!store.isResponsePending()) return;
      store.beginInFlight(host);

      await sg.detectorClient.waitForStableContent(host, 1200);
      const contentEl = sg.chatSelectors.findAssistantContentEl(host);
      if (!contentEl) {
        store.endInFlight(host);
        return;
      }

      const text = sg.chatSelectors.extractMessageText(contentEl).trim();
      if (!text || text.length < 10) {
        store.endInFlight(host);
        return;
      }

      try {
        const result = await sg.detectorClient.detectText(text);
        const hasFindings = (result?.detected_fields || []).length > 0;
        const shouldShow =
          hasFindings ||
          ["low", "medium", "high"].includes(result?.risk_level);
        if (shouldShow) {
          sg.panel.render(result, "Response", text);
          sg.highlights.applyHighlights(
            contentEl,
            result?.detected_fields || [],
            "assistant",
          );
        }
      } catch (err) {
        console.warn(
          "[SensitiveDataDetectorExtension] analyze assistant error:",
          err,
        );
      } finally {
        store.markAnalyzed(host);
        store.endInFlight(host);
        store.consumeResponsePending();
        store.setSuppressUserAlerts(false);
      }
      return;
    }

    if (isUser || originGuess === "User") {
      if (store.shouldSuppressUserAlerts()) return;
      const textUser = sg.chatSelectors.extractMessageText(host);
      if (!textUser) return;
      try {
        const result = await sg.detectorClient.detectText(textUser);
        const hasFindings = (result?.detected_fields || []).length > 0;
        const shouldShow =
          hasFindings ||
          ["low", "medium", "high"].includes(result?.risk_level);
        if (shouldShow) {
          sg.panel.render(result, "User", textUser);
        }
        store.markAnalyzed(host);
      } catch (err) {
        console.warn(
          "[SensitiveDataDetectorExtension] analyze user error:",
          err,
        );
      }
    }
  }

  function scanExistingMessages() {
    // Use platform-agnostic message detection
    const allNodes = document.querySelectorAll("*");
    const messageNodes = Array.from(allNodes).filter(
      (node) => sg.chatSelectors.isMessageNode(node)
    );
    messageNodes.forEach((n) => analyzeMessageNode(n, "Response"));
  }

  sg.messageAnalyzer = {
    start,
    scanExistingMessages,
    analyzeMessageNode,
  };
})(typeof window !== "undefined" ? window : globalThis);
