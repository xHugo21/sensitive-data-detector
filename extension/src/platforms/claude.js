/**
 * Claude Platform Adapter
 *
 * Implements platform-specific selectors and behaviors for Claude (claude.ai).
 */
(function initClaudePlatform(root) {
  const sg = (root.SG = root.SG || {});

  class ClaudePlatform extends sg.BasePlatform {
    get name() {
      return "claude";
    }

    get displayName() {
      return "Claude";
    }

    get urlPatterns() {
      return ["claude.ai"];
    }

    findComposer() {
      // Claude typically uses a contenteditable div or textarea
      const editable = Array.from(
        document.querySelectorAll('[contenteditable="true"]'),
      ).find((el) => {
        return (
          el.offsetParent !== null &&
          el.clientHeight > 0 &&
          !el.closest('[role="dialog"]')
        );
      });
      if (editable) return editable;

      // Try textarea as fallback
      const textarea = Array.from(document.querySelectorAll("textarea")).find(
        (el) => el.offsetParent !== null && el.clientHeight > 0,
      );
      return textarea || null;
    }

    findSendButton() {
      const composer = this.findComposer();
      if (!composer) return null;

      const form = composer.closest("form");
      if (form) {
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) return submitButton;
      }

      const buttons = document.querySelectorAll("button");
      for (const btn of buttons) {
        const ariaLabel = btn.getAttribute("aria-label")?.toLowerCase() || "";
        const text = btn.textContent?.toLowerCase() || "";
        if (
          ariaLabel.includes("send") ||
          text.includes("send") ||
          ariaLabel.includes("submit") ||
          btn.getAttribute("type") === "submit"
        ) {
          if (btn.offsetParent !== null) {
            return btn;
          }
        }
      }

      // Fallback: find button near composer
      return composer.parentElement?.querySelector("button") || null;
    }

    isMessageNode(n) {
      if (!n || n.nodeType !== 1) return false;
      const el = n;

      // Check for common message container patterns
      if (
        el.hasAttribute?.("data-message") ||
        el.hasAttribute?.("data-message-id")
      ) {
        return true;
      }

      // Check for role-based attributes
      if (
        el.getAttribute?.("role") === "article" ||
        el.getAttribute?.("role") === "region"
      ) {
        return true;
      }

      // Check for class patterns common in message containers
      const className = el.className || "";
      if (
        typeof className === "string" &&
        (className.includes("message") || className.includes("chat"))
      ) {
        return true;
      }

      return false;
    }

    findAssistantContentEl(host) {
      // Try to find the main content area within the message
      const selectors = [
        '[role="article"]',
        ".message-content",
        "[data-message-content]",
        'div[class*="content"]',
        "p",
      ];

      for (const sel of selectors) {
        const el = host.querySelector?.(sel);
        if (el && el.innerText?.trim()) return el;
      }

      return host;
    }

    getMessageRole(node) {
      if (!node) return null;

      // Try to determine role from data attributes
      const role =
        node.getAttribute?.("data-role") ||
        node.getAttribute?.("data-author") ||
        node.getAttribute?.("data-message-role");

      if (role === "assistant" || role === "claude") return "assistant";
      if (role === "user" || role === "human") return "user";

      // Try to infer from context or structure
      const text = (node.textContent || "").toLowerCase();
      const className =
        typeof node.className === "string"
          ? node.className.toLowerCase()
          : node.className?.baseVal?.toLowerCase() || "";

      if (className.includes("assistant") || className.includes("claude")) {
        return "assistant";
      }
      if (className.includes("user") || className.includes("human")) {
        return "user";
      }

      return null;
    }

    findPanelInsertionPoint() {
      const composer = this.findComposer();
      if (!composer) return null;

      // Claude has a chat-input-grid-container that wraps the input area
      const chatInputContainer = document.querySelector(
        '[data-testid="chat-input-grid-container"]',
      );

      if (chatInputContainer && chatInputContainer.parentElement) {
        return {
          host: chatInputContainer.parentElement,
          referenceNode: chatInputContainer,
        };
      }

      // Fallback to form-based insertion
      const form = composer.closest("form");
      if (form && form.parentElement) {
        return {
          host: form.parentElement,
          referenceNode: form,
        };
      }

      // Last resort: use default behavior
      return null;
    }

    initialize() {
      console.log(
        "[SensitiveDataDetector] Claude platform adapter initialized",
      );
    }
  }

  sg.ClaudePlatform = ClaudePlatform;

  // Self-register when script loads
  if (sg.platformRegistry) {
    sg.platformRegistry.register(ClaudePlatform);
  }
})(typeof window !== "undefined" ? window : globalThis);
