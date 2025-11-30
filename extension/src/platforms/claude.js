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

    getComposerText(el) {
      if (!el) return "";
      if (el.tagName === "TEXTAREA") return el.value;
      return (el.textContent || el.innerText || "").replace(/\u00A0/g, " ");
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

    extractMessageText(node) {
      if (!node) return "";
      return (node.innerText || node.textContent || "").trim();
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
      const className = (node.className || "").toLowerCase();

      if (className.includes("assistant") || className.includes("claude")) {
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

    findPanelInsertionPoint() {
      const composer = this.findComposer();
      if (!composer) return null;

      // Traverse up to find the main chat input container
      let current = composer;
      let iterations = 0;
      const maxIterations = 10;

      // Walk up the DOM tree to find a suitable container
      // Look for a container that's wide enough and has reasonable positioning
      while (current && current.parentElement && iterations < maxIterations) {
        const parent = current.parentElement;

        // Stop if we hit the body or a main landmark
        if (parent.tagName === "BODY" || parent.tagName === "MAIN") {
          break;
        }

        // Look for a container that seems to be the chat input area
        const computedStyle = window.getComputedStyle(parent);
        const width = parent.offsetWidth;

        // If we find a wide container use its parent
        if (width > 500 && computedStyle.position !== "fixed") {
          const form = current.closest("form");
          if (form && form.parentElement) {
            return {
              host: form.parentElement,
              referenceNode: form,
            };
          }
          return {
            host: parent,
            referenceNode: current,
          };
        }

        current = parent;
        iterations++;
      }

      // Fallback to form-based insertion
      const form = composer.closest("form");
      if (form && form.parentElement) {
        return {
          host: form.parentElement,
          referenceNode: form,
        };
      }

      // Last resort: use a higher-level parent
      return {
        host: composer.parentElement?.parentElement || composer.parentElement,
        referenceNode: composer.parentElement || composer,
      };
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
