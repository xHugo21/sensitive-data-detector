const test = require("node:test");
const assert = require("node:assert/strict");

function setup({ resultFactory }) {
  const listeners = new Map();
  const dispatched = [];
  let renderCall = null;
  let sendAnywayHandler = null;

  globalThis.document = {
    addEventListener: (type, handler) => {
      listeners.set(type, handler);
    },
  };

  globalThis.Event = class Event {
    constructor(type, init = {}) {
      this.type = type;
      this.bubbles = Boolean(init.bubbles);
    }
  };

  globalThis.DataTransfer = class DataTransfer {
    constructor() {
      this._items = [];
      this.items = {
        add: (file) => {
          this._items.push(file);
          this.files = this._items.slice();
        },
      };
      this.files = [];
    }
  };

  globalThis.SG = {};
  delete require.cache[require.resolve("../src/state/alertStore.js")];
  require("../src/state/alertStore.js");

  globalThis.SG.panel = {
    render: (result, context, meta) => {
      renderCall = { result, context, meta };
    },
    onSendAnyway: (fn) => {
      sendAnywayHandler = fn;
    },
    onDismiss: () => {},
    hide: () => {},
  };

  globalThis.SG.loadingState = {
    show: () => {},
    hide: () => {},
  };

  const analyzeCalls = [];
  globalThis.SG.fileAnalyzer = {
    isSupportedFile: () => true,
    getFileInfo: () => ({ type: "text", label: "Text File" }),
    analyzeFile: async (file) => {
      analyzeCalls.push(file);
      return resultFactory(file);
    },
  };

  delete require.cache[require.resolve("../src/controllers/fileInterceptor.js")];
  require("../src/controllers/fileInterceptor.js");
  globalThis.SG.fileInterceptor.attach();

  const handler = listeners.get("change");

  function createInput(files) {
    return {
      type: "file",
      files,
      dataset: {},
      value: "original",
      dispatchEvent: (evt) => {
        dispatched.push(evt);
      },
    };
  }

  return {
    handler,
    createInput,
    analyzeCalls,
    dispatched,
    get renderCall() {
      return renderCall;
    },
    get sendAnywayHandler() {
      return sendAnywayHandler;
    },
  };
}

test("warn auto-allows upload and shows dismiss-only panel", async () => {
  const env = setup({
    resultFactory: () => ({
      decision: "warn",
      risk_level: "low",
      detected_fields: [],
    }),
  });

  const input = env.createInput([{ name: "note.txt", size: 12 }]);
  let prevented = false;
  let stopped = false;

  await env.handler({
    target: input,
    preventDefault: () => {
      prevented = true;
    },
    stopImmediatePropagation: () => {
      stopped = true;
    },
  });

  assert.equal(prevented, true);
  assert.equal(stopped, true);
  assert.equal(env.analyzeCalls.length, 1);
  assert.equal(env.dispatched.length, 1);
  assert.equal(input.dataset.sgBypass, "true");
  assert.equal(input.value, "original");
  assert.equal(env.renderCall.meta.mode, "warn");
  assert.equal(env.renderCall.meta.requireAction, false);
});

test("block gates upload until user action", async () => {
  const env = setup({
    resultFactory: () => ({
      decision: "block",
      risk_level: "high",
      detected_fields: [],
    }),
  });

  const input = env.createInput([{ name: "secret.txt", size: 42 }]);
  let prevented = false;
  let stopped = false;

  await env.handler({
    target: input,
    preventDefault: () => {
      prevented = true;
    },
    stopImmediatePropagation: () => {
      stopped = true;
    },
  });

  assert.equal(prevented, true);
  assert.equal(stopped, true);
  assert.equal(env.dispatched.length, 0);
  assert.equal(input.value, "");
  assert.equal(env.renderCall.meta.mode, "block");
  assert.equal(env.renderCall.meta.requireAction, true);
  assert.equal(env.renderCall.meta.primaryActionLabel, "Upload anyway");

  assert.equal(typeof env.sendAnywayHandler, "function");
  env.sendAnywayHandler();
  assert.equal(env.dispatched.length, 1);
  assert.equal(input.dataset.sgBypass, "true");
});
