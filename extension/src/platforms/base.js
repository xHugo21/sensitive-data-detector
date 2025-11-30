/**
 * Base Platform Adapter Interface
 *
 * Defines the contract that all platform adapters must follow.
 * Each chatbot platform will have its own adapter that extends this base class.
 */
(function initBasePlatform(root) {
  const sg = (root.SG = root.SG || {});

  class BasePlatform {
    constructor() {
      if (new.target === BasePlatform) {
        throw new TypeError(
          "Cannot construct BasePlatform instances directly - must be extended",
        );
      }
    }

    /**
     * Platform identification
     */
    get name() {
      throw new Error("Platform must implement 'name' getter");
    }

    get displayName() {
      throw new Error("Platform must implement 'displayName' getter");
    }

    get urlPatterns() {
      throw new Error("Platform must implement 'urlPatterns' getter");
    }

    /**
     * Check if current URL matches this platform
     * @param {string} url - The URL to check
     * @returns {boolean} True if URL matches this platform
     */
    matches(url) {
      const patterns = this.urlPatterns;
      return patterns.some((pattern) => {
        if (pattern instanceof RegExp) {
          return pattern.test(url);
        }
        return url.includes(pattern);
      });
    }

    /**
     * DOM Selector Methods - Must be implemented by each platform
     */

    /**
     * Find the text input composer element where users type messages
     * @returns {Element|null} The composer element or null if not found
     */
    findComposer() {
      throw new Error("Platform must implement 'findComposer' method");
    }

    /**
     * Extract text content from the composer element
     * @param {Element} element - The composer element
     * @returns {string} The text content
     */
    getComposerText(element) {
      throw new Error("Platform must implement 'getComposerText' method");
    }

    /**
     * Find the send button element
     * @returns {Element|null} The send button or null if not found
     */
    findSendButton() {
      throw new Error("Platform must implement 'findSendButton' method");
    }

    /**
     * Extract text from a message node
     * @param {Node} node - The message node
     * @returns {string} The extracted text
     */
    extractMessageText(node) {
      throw new Error("Platform must implement 'extractMessageText' method");
    }

    /**
     * Check if a node is a message container
     * @param {Node} node - The node to check
     * @returns {boolean} True if node is a message
     */
    isMessageNode(node) {
      throw new Error("Platform must implement 'isMessageNode' method");
    }

    /**
     * Find the assistant response content element within a message container
     * @param {Element} host - The message container element
     * @returns {Element} The content element
     */
    findAssistantContentEl(host) {
      throw new Error(
        "Platform must implement 'findAssistantContentEl' method",
      );
    }

    /**
     * Get the author role of a message node (e.g., "user" or "assistant")
     * @param {Element} node - The message node
     * @returns {string|null} The role ("user", "assistant") or null if unknown
     */
    getMessageRole(node) {
      throw new Error("Platform must implement 'getMessageRole' method");
    }

    /**
     * Platform-specific behavior configuration
     */

    /**
     * Should keyboard events (Enter key) be intercepted?
     * @returns {boolean}
     */
    get shouldInterceptKeyboard() {
      return true;
    }

    /**
     * Should click events on send button be intercepted?
     * @returns {boolean}
     */
    get shouldInterceptClick() {
      return true;
    }

    /**
     * Custom send logic for platforms with special requirements
     * @param {Element} composer - The composer element
     * @param {Element|null} button - The send button (if available)
     */
    customSendLogic(composer, button) {
      // Default implementation: trigger button click or Enter keypress
      if (button) {
        button.click();
        return;
      }

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

    /**
     * Query selector for file input elements (for file upload interception)
     * @returns {string|null} CSS selector for file inputs, or null if not applicable
     */
    get fileInputSelector() {
      return 'input[type="file"]';
    }

    /**
     * Initialize platform-specific event listeners or setup
     * Called when the platform is activated
     */
    initialize() {
      // Default: no additional initialization needed
      console.log(
        `[SensitiveDataDetector] Platform initialized: ${this.displayName}`,
      );
    }

    /**
     * Cleanup platform-specific resources
     * Called when switching platforms or unloading
     */
    cleanup() {
      // Default: no cleanup needed
    }

    /**
     * Wait for platform-specific elements to be ready
     * @returns {Promise<boolean>} Resolves to true when ready
     */
    async waitForReady() {
      // Default: wait for composer to appear
      return new Promise((resolve) => {
        const maxAttempts = 50;
        let attempts = 0;

        const check = () => {
          attempts++;
          if (this.findComposer()) {
            resolve(true);
            return;
          }
          if (attempts >= maxAttempts) {
            console.warn(
              `[SensitiveDataDetector] Platform ${this.displayName} not ready after ${maxAttempts} attempts`,
            );
            resolve(false);
            return;
          }
          setTimeout(check, 200);
        };

        check();
      });
    }
  }

  sg.BasePlatform = BasePlatform;
})(typeof window !== "undefined" ? window : globalThis);
