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
      const composer = document.getElementById("prompt-textarea");
      if (
        composer &&
        composer.classList.contains("ProseMirror") &&
        composer.offsetParent !== null
      ) {
        return composer;
      }
      return null;
    }

    findSendButton() {
      const composer = this.findComposer();
      if (!composer) return null;

      return (
        document.getElementById("composer-submit-button") ||
        document.querySelector('button[data-testid="send-button"]')
      );
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
