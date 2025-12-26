const test = require("node:test");
const assert = require("node:assert/strict");

function setup({ progressEvents }) {
  const listeners = new Map();
  const composerListeners = new Map();
  const updates = [];
  const sendButton = {
    tagName: "BUTTON",
    disabled: false,
    setAttribute: () => {},
    removeAttribute: () => {},
  };
  const composer = {
    tagName: "TEXTAREA",
    addEventListener: (type, handler) => {
      composerListeners.set(type, handler);
    },
  };

  globalThis.document = {
    addEventListener: (type, handler) => {
      listeners.set(type, handler);
    },
  };

  globalThis.SG = {};
  delete require.cache[require.resolve("../src/state/alertStore.js")];
  require("../src/state/alertStore.js");

  globalThis.SG.panel = {
    ensure: () => {},
    onSendAnyway: () => {},
    onSendSanitized: () => {},
    render: () => {},
    hide: () => {},
  };

  globalThis.SG.highlights = {
    ensureHighlightCSS: () => {},
    applyHighlights: () => {},
    clearHighlights: () => {},
  };

  globalThis.SG.settings = {
    isDetectionEnabled: () => true,
  };

  globalThis.SG.loadingState = {
    show: () => {},
    hide: () => {},
    update: (message) => {
      updates.push(message);
    },
  };

  globalThis.SG.riskUtils = {
    shouldBlock: () => false,
    shouldWarn: () => false,
  };

  globalThis.SG.platformRegistry = {
    getActive: () => ({
      isSendButton: () => true,
    }),
  };

  globalThis.SG.chatSelectors = {
    findComposer: () => composer,
    findSendButton: () => sendButton,
    getComposerText: () => "hello",
    triggerSend: () => {},
  };

  globalThis.SG.detectorClient = {
    detectTextStream: async (text, onProgress) => {
      progressEvents.forEach((event) => {
        onProgress(event.message, event);
      });
      return { detected_fields: [], risk_level: "none" };
    },
  };

  delete require.cache[require.resolve("../src/controllers/sendInterceptor.js")];
  require("../src/controllers/sendInterceptor.js");
  globalThis.SG.sendInterceptor.attach();

  const keydownHandler = composerListeners.get("keydown");

  return {
    updates,
    keydownHandler,
  };
}

test("updates loading toast with detection counts", async () => {
  const env = setup({
    progressEvents: [
      { message: "normalize", detected_count: 0 },
      { message: "merge dlp ner", detected_count: 2 },
    ],
  });

  env.keydownHandler({
    key: "Enter",
    shiftKey: false,
    preventDefault: () => {},
    stopPropagation: () => {},
  });

  await new Promise((resolve) => setTimeout(resolve, 10));

  assert.equal(
    env.updates[0],
    "Analyzing message - Running normalize - No detections yet",
  );
  assert.equal(
    env.updates[1],
    "Analyzing message - Running merge dlp ner - Detected 2",
  );
});
