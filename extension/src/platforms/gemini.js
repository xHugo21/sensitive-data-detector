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
      // Gemini typically uses a rich text editor or contenteditable div
      const editable = Array.from(
        document.querySelectorAll(
          '[contenteditable="true"][role="textbox"], [contenteditable="true"]',
        ),
      ).find((el) => {
        return (
          el.offsetParent !== null &&
          el.clientHeight > 0 &&
          !el.closest('[role="dialog"]') &&
          !el.closest('[aria-hidden="true"]')
        );
      });
      if (editable) return editable;

      // Try textarea as fallback
      const textarea = Array.from(document.querySelectorAll("textarea")).find(
        (el) => el.offsetParent !== null && el.clientHeight > 0,
      );
      return textarea || null;
    }

    getComposerText(el) {
      if (!el) return "";
      if (el.tagName === "TEXTAREA") return el.value;
      return (el.textContent || el.innerText || "").replace(/\u00A0/g, " ");
    }

    findSendButton() {
      const composer = this.findComposer();
      if (!composer) return null;

      // Try to find button within the same form or parent container
      const form = composer.closest("form");
      if (form) {
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) return submitButton;
      }

      // Try to find button by aria-label
      const buttons = document.querySelectorAll("button");
      for (const btn of buttons) {
        const ariaLabel = btn.getAttribute("aria-label")?.toLowerCase() || "";
        const title = btn.getAttribute("title")?.toLowerCase() || "";
        if (
          ariaLabel.includes("send") ||
          ariaLabel.includes("submit") ||
          title.includes("send") ||
          title.includes("submit")
        ) {
          if (btn.offsetParent !== null) {
            return btn;
          }
        }
      }

      // Try to find button with specific data attributes
      const dataButton = document.querySelector(
        '[data-test-id*="send"], [data-testid*="send"]',
      );
      if (dataButton) return dataButton;

      // Fallback: find button near composer
      return composer.parentElement?.querySelector("button") || null;
    }

    extractMessageText(node) {
      if (!node) return "";
      return (node.innerText || node.textContent || "").trim();
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

      // Try to infer from context or structure
      const className = (node.className || "").toLowerCase();

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

    get shouldInterceptKeyboard() {
      return true;
    }

    get shouldInterceptClick() {
      return true;
    }

    customSendLogic(composer, button) {
      const targetButton = button || this.findSendButton();
      if (targetButton) {
        targetButton.dataset.sgBypass = "true";
        setTimeout(() => {
          targetButton.click();
          delete targetButton.dataset.sgBypass;
        }, 10);
        return;
      }

      // Fallback: dispatch Enter key event
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

    get fileInputSelector() {
      return 'input[type="file"]';
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
