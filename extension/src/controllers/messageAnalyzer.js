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
            node
              .querySelectorAll("[data-message-author-role]")
              .forEach((host) => analyzeMessageNode(host, "Response"));
          }
        });
    }

    if (sg.alertStore.isResponsePending()) {
      const lastAssistant = [
        ...document.querySelectorAll('[data-message-author-role="assistant"]'),
      ].pop();
      if (lastAssistant) analyzeMessageNode(lastAssistant, "Response");
    }
  }

  async function analyzeMessageNode(node, originGuess = "Unknown") {
    if (!node) return;
    const store = sg.alertStore;
    const host = node.closest?.("[data-message-author-role]") || node;
    if (!host || store.hasAnalyzed(host) || store.isInFlight(host)) return;

    const roleAttr = host.getAttribute?.("data-message-author-role");
    const isAssistant = roleAttr === "assistant";
    const isUser = roleAttr === "user";

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
    const nodes = document.querySelectorAll(
      '[data-message-author-role], [data-testid="conversation-turn"], .markdown',
    );
    nodes.forEach((n) => analyzeMessageNode(n, "Response"));
  }

  sg.messageAnalyzer = {
    start,
    scanExistingMessages,
    analyzeMessageNode,
  };
})(typeof window !== "undefined" ? window : globalThis);
