# Platform Architecture

This document describes the platform abstraction layer that makes the Sensitive Data Detector extension work across multiple chatbot platforms (ChatGPT, Claude, Gemini, Grok, etc.).

## Overview

The extension now uses a **platform adapter pattern** that separates platform-specific DOM manipulation from the core detection logic. This makes it easy to add support for new chatbot platforms without modifying the core functionality.

## Architecture Components

### 1. Base Platform Interface (`src/platforms/base.js`)

Defines the abstract interface that all platform adapters must implement. Key methods include:

- `findComposer()` - Locate the text input element
- `getComposerText(element)` - Extract text from the composer
- `findSendButton()` - Locate the send button
- `extractMessageText(node)` - Extract text from a message
- `isMessageNode(node)` - Check if a node is a message container
- `findAssistantContentEl(host)` - Find assistant response content
- `getMessageRole(node)` - Determine if message is from user or assistant
- `customSendLogic(composer, button)` - Handle sending messages

### 2. Platform Registry (`src/platforms/registry.js`)

Central registry that manages all platform adapters:

- Registers platform adapters
- Detects which platform is active based on URL
- Activates the appropriate platform
- Provides access to the active platform

### 3. Platform Adapters

Each chatbot has its own adapter that implements the base interface:

- **ChatGPT** (`src/platforms/chatgpt.js`) - For chat.openai.com and chatgpt.com
- **Claude** (`src/platforms/claude.js`) - For claude.ai
- **Gemini** (`src/platforms/gemini.js`) - For gemini.google.com
- **Grok** (`src/platforms/grok.js`) - For x.com/i/grok

### 4. Chat Selectors (`src/dom/chatSelectors.js`)

Acts as a facade that delegates all DOM operations to the active platform adapter. This allows the rest of the codebase to remain platform-agnostic.

## How It Works

### Initialization Flow

1. **Platform Registration** - All platform adapters are registered with the registry
2. **Platform Detection** - The registry detects which platform matches the current URL
3. **Platform Activation** - The detected platform is initialized and activated
4. **Controllers Attach** - Core controllers (sendInterceptor, messageAnalyzer, fileInterceptor) attach using platform-agnostic methods

### Request Flow

```
User types message
    ↓
sendInterceptor intercepts
    ↓
Calls chatSelectors.findComposer()
    ↓
chatSelectors delegates to active platform
    ↓
Platform adapter returns ChatGPT/Claude/Gemini/Grok-specific element
    ↓
Extension analyzes content
    ↓
Platform adapter handles sending via customSendLogic()
```

## Adding a New Platform

To add support for a new chatbot platform:

### Step 1: Create Platform Adapter

Create a new file `src/platforms/newplatform.js`:

```javascript
(function initNewPlatform(root) {
  const sg = (root.SG = root.SG || {});

  class NewPlatform extends sg.BasePlatform {
    get name() {
      return "newplatform";
    }

    get displayName() {
      return "New Platform";
    }

    get urlPatterns() {
      return ["newplatform.com"];
    }

    findComposer() {
      // Implement platform-specific logic to find composer
      return document.querySelector('[data-composer]');
    }

    getComposerText(el) {
      if (!el) return "";
      return el.textContent || "";
    }

    findSendButton() {
      // Implement platform-specific logic to find send button
      return document.querySelector('[data-send]');
    }

    extractMessageText(node) {
      if (!node) return "";
      return node.innerText || "";
    }

    isMessageNode(n) {
      if (!n || n.nodeType !== 1) return false;
      // Implement platform-specific logic
      return n.hasAttribute('data-message');
    }

    findAssistantContentEl(host) {
      return host.querySelector('.response-content') || host;
    }

    getMessageRole(node) {
      if (!node) return null;
      const role = node.getAttribute('data-role');
      if (role === 'ai') return 'assistant';
      if (role === 'user') return 'user';
      return null;
    }

    customSendLogic(composer, button) {
      const targetButton = button || this.findSendButton();
      if (targetButton) {
        targetButton.dataset.sgBypass = "true";
        setTimeout(() => {
          targetButton.click();
          delete targetButton.dataset.sgBypass;
        }, 10);
      }
    }
  }

  sg.NewPlatform = NewPlatform;
})(typeof window !== "undefined" ? window : globalThis);
```

### Step 2: Register in manifest.json

Add URLs to `manifest.json`:

```json
{
  "content_scripts": [
    {
      "matches": [
        "https://chat.openai.com/*",
        "https://chatgpt.com/*",
        "https://claude.ai/*",
        "https://gemini.google.com/*",
        "https://x.com/*",
        "https://twitter.com/*",
        "https://newplatform.com/*"  // Add new platform
      ],
      "js": [
        "src/config.js",
        "src/state/alertStore.js",
        "src/services/detectorClient.js",
        "src/services/riskUtils.js",
        "src/services/fileAnalyzer.js",
        "src/ui/panel.js",
        "src/ui/highlights.js",
        "src/ui/loadingState.js",
        "src/platforms/base.js",
        "src/platforms/chatgpt.js",
        "src/platforms/claude.js",
        "src/platforms/gemini.js",
        "src/platforms/grok.js",
        "src/platforms/newplatform.js",  // Add new platform script
        "src/platforms/registry.js",
        "src/dom/chatSelectors.js",
        "src/controllers/sendInterceptor.js",
        "src/controllers/messageAnalyzer.js",
        "src/controllers/fileInterceptor.js",
        "src/main.js"
      ]
    }
  ]
}
```

### Step 3: Register in main.js

Add registration in `src/main.js`:

```javascript
function initializePlatforms() {
  console.log("[SensitiveDataDetector] Initializing platform system...");
  
  if (sg.ChatGPTPlatform) {
    sg.platformRegistry.register(sg.ChatGPTPlatform);
  }
  if (sg.ClaudePlatform) {
    sg.platformRegistry.register(sg.ClaudePlatform);
  }
  if (sg.GeminiPlatform) {
    sg.platformRegistry.register(sg.GeminiPlatform);
  }
  if (sg.GrokPlatform) {
    sg.platformRegistry.register(sg.GrokPlatform);
  }
  if (sg.NewPlatform) {  // Add this
    sg.platformRegistry.register(sg.NewPlatform);
  }

  console.log("[SensitiveDataDetector] Supported platforms:", sg.platformRegistry.getSupportedPlatforms());
}
```

### Step 4: Test the Platform

1. Load the extension in Chrome
2. Navigate to the new platform's URL
3. Check console for platform detection logs
4. Test message interception and detection

## Platform-Specific Considerations

### DOM Selectors

Each platform uses different DOM structures. Key things to identify:

- **Composer element** - Where users type (contenteditable div, textarea, etc.)
- **Send button** - Button or action that submits the message
- **Message containers** - Elements that hold conversation messages
- **Role identification** - How to distinguish user vs assistant messages

### Debugging Tips

1. **Console Logging** - Each platform logs initialization and detection
2. **Inspect DOM** - Use Chrome DevTools to identify selectors
3. **Test Incrementally** - Implement one method at a time
4. **Fallback Gracefully** - Return null/empty instead of throwing errors

### Performance Considerations

- Use efficient selectors (IDs, data attributes > class names > tag names)
- Cache frequently accessed elements when possible
- Avoid querying entire document tree (`document.querySelectorAll("*")`)
- Use platform's `waitForReady()` to handle async loading

## Backward Compatibility

The refactoring maintains 100% backward compatibility with ChatGPT:

- All original functionality preserved
- Same detection logic and UI
- Same performance characteristics
- Existing tests continue to work

## Testing

When adding a new platform, test:

1. ✅ Platform detection on page load
2. ✅ Message interception (keyboard and click)
3. ✅ Text extraction from messages
4. ✅ Assistant response detection
5. ✅ File upload interception
6. ✅ UI panel display with platform badge
7. ✅ Send override functionality

## Future Enhancements

Potential improvements to the platform system:

- Hot-swapping platforms for SPAs
- Platform-specific configuration
- Dynamic platform loading
- Platform capability detection
- Automated platform testing framework

## Migration Notes

For developers familiar with the old code:

- **Old**: Direct DOM queries in `chatSelectors.js`
- **New**: Platform adapters delegate to platform-specific implementations
- **Impact**: Core controllers unchanged, just use `chatSelectors.*` methods
- **Benefit**: Adding new platforms no longer requires modifying core code

## Support

For questions or issues with the platform system:

1. Check console logs for platform detection issues
2. Verify DOM selectors match actual platform structure
3. Review existing platform adapters for examples
4. Test with minimal implementation first
