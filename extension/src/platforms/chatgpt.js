/**
 * ChatGPT Platform Adapter
 */
(function initChatGPTPlatform(root) {
  const sg = (root.SG = root.SG || {});

  class ChatGPTPlatform extends sg.BasePlatform {
    get name() {
      return "chatgpt";
    }

    get displayName() {
      return "ChatGPT";
    }

    get urlPatterns() {
      return ["chatgpt.com"];
    }

    findComposer() {
      // Try to find contenteditable elements first
      const editable = Array.from(
        document.querySelectorAll(
          '[contenteditable="true"][role="textbox"], div[contenteditable="true"]',
        ),
      ).find((el) => el.offsetParent !== null && el.clientHeight > 0);
      if (editable) return editable;

      // Fallback to textarea
      const textarea = Array.from(document.querySelectorAll("textarea")).find(
        (el) => el.offsetParent !== null && el.clientHeight > 0,
      );
      return textarea || null;
    }

    findSendButton() {
      const composer = this.findComposer();
      if (!composer) return null;

      const formButton = composer
        .closest("form")
        ?.querySelector('button[type="submit"]');
      if (formButton) return formButton;

      const testIdButton = document.querySelector(
        '[data-testid="send-button"]',
      );
      if (testIdButton) return testIdButton;

      // Fallback: find any button near the composer
      return composer.parentElement?.querySelector("button") || null;
    }

    isMessageNode(n) {
      if (!n || n.nodeType !== 1) return false;
      const el = n;

      // Check for ChatGPT's message author role attribute
      if (el.hasAttribute?.("data-message-author-role")) return true;
      if (el.closest?.("[data-message-author-role]")) return true;

      // Check for conversation turn test ID
      if (el.matches && el.matches('[data-testid="conversation-turn"]')) {
        return true;
      }

      return false;
    }

    findAssistantContentEl(host) {
      // List of selectors to try for finding assistant message content
      const selectors = [
        ".markdown",
        ".prose",
        '[data-message-author-role="assistant"] .markdown',
        '[data-message-author-role="assistant"] .prose',
        '[data-message-author-role="assistant"] [class*="whitespace-pre-wrap"]',
        '[data-message-author-role="assistant"] [data-testid="assistant-response"]',
      ];

      for (const sel of selectors) {
        const el = host.querySelector?.(sel);
        if (el && el.innerText?.trim()) return el;
      }

      // Fallback to the host element itself
      return host;
    }

    getMessageRole(node) {
      if (!node) return null;

      // Try to get role from data attribute
      const host = node.closest?.("[data-message-author-role]") || node;
      const roleAttr = host.getAttribute?.("data-message-author-role");

      if (roleAttr === "assistant") return "assistant";
      if (roleAttr === "user") return "user";

      return null;
    }

    initialize() {
      console.log(
        "[SensitiveDataDetector] ChatGPT platform adapter initialized",
      );
    }
  }

  sg.ChatGPTPlatform = ChatGPTPlatform;

  // Self-register when script loads
  if (sg.platformRegistry) {
    sg.platformRegistry.register(ChatGPTPlatform);
  }
})(typeof window !== "undefined" ? window : globalThis);
