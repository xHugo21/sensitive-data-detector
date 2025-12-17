/**
 * Gemini Platform Adapter
 *
 * Implements platform-specific selectors and behaviors for Google Gemini (gemini.google.com).
 */
(function initGeminiPlatform(root) {
  const sg = (root.SG = root.SG || {});

  class GeminiPlatform extends sg.BasePlatform {
    get name() {
      return "gemini";
    }

    get displayName() {
      return "Gemini";
    }

    get urlPatterns() {
      return ["gemini.google.com"];
    }

    findComposer() {
      const composer = document.querySelector(
        'div.ql-editor.textarea.new-input-ui[contenteditable="true"]',
      );
      return composer && composer.offsetParent !== null ? composer : null;
    }

    findSendButton() {
      const buttons = document.querySelectorAll("button.send-button.submit");
      for (const btn of buttons) {
        if (btn.offsetParent === null) continue;
        const aria = btn.getAttribute("aria-label")?.toLowerCase() || "";
        const hasIcon = btn.querySelector(
          'mat-icon[fonticon="send"][data-mat-icon-name="send"]',
        );
        if (aria === "send message" || aria === "enviar mensaje" || hasIcon) {
          return btn;
        }
      }

      return null;
    }

    isMessageNode(n) {
      if (!n || n.nodeType !== 1) return false;
      const el = n;

      // Gemini's messages often have specific data attributes
      if (
        el.hasAttribute?.("data-message-id") ||
        el.hasAttribute?.("data-response-id")
      ) {
        return true;
      }

      // Check for role-based attributes
      if (
        el.getAttribute?.("role") === "article" ||
        el.getAttribute?.("role") === "listitem"
      ) {
        return true;
      }

      // Check for class patterns common in message containers
      const className = el.className || "";
      if (
        typeof className === "string" &&
        (className.includes("message") ||
          className.includes("response") ||
          className.includes("conversation"))
      ) {
        return true;
      }

      return false;
    }

    findAssistantContentEl(host) {
      // Try to find the main content area within the message
      const selectors = [
        "[data-message-content]",
        '[role="article"]',
        ".message-content",
        ".response-content",
        'div[class*="content"]',
        "markdown-element",
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
        node.getAttribute?.("data-message-author");

      if (role === "model" || role === "assistant" || role === "gemini") {
        return "assistant";
      }
      if (role === "user" || role === "human") {
        return "user";
      }

      const className =
        typeof node.className === "string"
          ? node.className.toLowerCase()
          : node.className?.baseVal?.toLowerCase() || "";

      if (
        className.includes("model") ||
        className.includes("assistant") ||
        className.includes("gemini")
      ) {
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

      // Try to find the input-area-container (main container for the entire input area)
      const inputContainer = document.querySelector(".input-area-container");
      if (inputContainer) {
        // Find the input-area-v2 element to insert before
        const inputAreaV2 = inputContainer.querySelector("input-area-v2");
        if (inputAreaV2) {
          return {
            host: inputContainer,
            referenceNode: inputAreaV2,
          };
        }
      }

      // Fallback: Use the default behavior from BasePlatform
      return super.findPanelInsertionPoint();
    }

    initialize() {
      console.log(
        "[SensitiveDataDetector] Gemini platform adapter initialized",
      );
    }
  }

  sg.GeminiPlatform = GeminiPlatform;

  // Self-register when script loads
  if (sg.platformRegistry) {
    sg.platformRegistry.register(GeminiPlatform);
  }
})(typeof window !== "undefined" ? window : globalThis);
