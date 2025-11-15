(function initChatSelectors(root) {
  const sg = root.SG = root.SG || {};

  function findComposer() {
    const editable = Array.from(
      document.querySelectorAll('[contenteditable="true"][role="textbox"], div[contenteditable="true"]')
    ).find(el => el.offsetParent !== null && el.clientHeight > 0);
    if (editable) return editable;

    const textarea = Array.from(document.querySelectorAll("textarea"))
      .find(el => el.offsetParent !== null && el.clientHeight > 0);
    return textarea || null;
  }

  function getComposerText(el) {
    if (!el) return "";
    if (el.tagName === "TEXTAREA") return el.value;
    return (el.textContent || "").replace(/\u00A0/g, " ");
  }

  function findSendButton() {
    const composer = findComposer();
    if (!composer) return null;
    return (
      composer.closest("form")?.querySelector('button[type="submit"]') ||
      document.querySelector('[data-testid="send-button"]') ||
      composer.parentElement?.querySelector("button")
    );
  }

  function extractMessageText(node) {
    if (!node) return "";
    return (node.innerText || node.textContent || "").trim();
  }

  function isMessageNode(n) {
    if (!n || n.nodeType !== 1) return false;
    const el = n;
    if (el.hasAttribute?.("data-message-author-role")) return true;
    if (el.closest?.('[data-message-author-role]')) return true;
    if (el.matches && el.matches('[data-testid="conversation-turn"]')) return true;
    return false;
  }

  function findAssistantContentEl(host) {
    const sels = [
      ".markdown",
      ".prose",
      '[data-message-author-role="assistant"] .markdown',
      '[data-message-author-role="assistant"] .prose',
      '[data-message-author-role="assistant"] [class*=\"whitespace-pre-wrap\"]',
      '[data-message-author-role="assistant"] [data-testid="assistant-response"]'
    ];
    for (const sel of sels) {
      const el = host.querySelector?.(sel);
      if (el && el.innerText?.trim()) return el;
    }
    return host;
  }

  sg.chatSelectors = {
    findComposer,
    getComposerText,
    findSendButton,
    extractMessageText,
    isMessageNode,
    findAssistantContentEl
  };
})(typeof window !== "undefined" ? window : globalThis);
