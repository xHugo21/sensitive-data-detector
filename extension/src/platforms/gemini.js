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
