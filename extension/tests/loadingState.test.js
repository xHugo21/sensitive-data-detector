const test = require("node:test");
const assert = require("node:assert/strict");

// Mock DOM globals
globalThis.document = {
  getElementById: function (id) {
    return this._elementsById?.[id] || null;
  },
  createElement: function (tagName) {
    return {
      tagName: tagName.toUpperCase(),
      id: null,
      textContent: "",
      style: {},
    };
  },
  head: {
    appendChild: function (el) {
      this.children = this.children || [];
      this.children.push(el);
    },
    children: [],
  },
  _elementsById: {},
};

globalThis.SG = {
  chatSelectors: {
    findSendButton: () => null,
  },
};

// Load the module
require("../src/ui/loadingState.js");

const { show, hide } = globalThis.SG.loadingState;

test("show creates style element on first call", () => {
  globalThis.document.head.children = [];

  const mockButton = {
    dataset: {},
    setAttribute: function (attr, value) {
      this[attr] = value;
    },
  };

  show(mockButton);

  assert.equal(globalThis.document.head.children.length, 1);
  const style = globalThis.document.head.children[0];
  assert.equal(style.tagName, "STYLE");
  assert.equal(style.id, "sg-send-loading-style");
  assert.ok(style.textContent.includes("[data-sg-loading=\"true\"]"));
  assert.ok(style.textContent.includes("@keyframes sg-send-spin"));
});

test("show sets loading attributes on button", () => {
  globalThis.document.head.children = [];

  const mockButton = {
    dataset: {},
    setAttribute: function (attr, value) {
      this[attr] = value;
    },
  };

  show(mockButton);

  assert.equal(mockButton.dataset.sgLoading, "true");
  assert.equal(mockButton["aria-busy"], "true");
});

test("show does nothing when button is null", () => {
  globalThis.document.head.children = [];

  // Should not throw
  show(null);

  // Style might still be added
  assert.ok(true);
});

test("show uses findSendButton when no button provided", () => {
  globalThis.document.head.children = [];

  const mockButton = {
    dataset: {},
    setAttribute: function (attr, value) {
      this[attr] = value;
    },
  };

  globalThis.SG.chatSelectors.findSendButton = () => mockButton;

  show();

  assert.equal(mockButton.dataset.sgLoading, "true");
  assert.equal(mockButton["aria-busy"], "true");
});

test("show uses findSendButton when string is passed", () => {
  globalThis.document.head.children = [];

  const mockButton = {
    dataset: {},
    setAttribute: function (attr, value) {
      this[attr] = value;
    },
  };

  globalThis.SG.chatSelectors.findSendButton = () => mockButton;

  show("some string");

  assert.equal(mockButton.dataset.sgLoading, "true");
  assert.equal(mockButton["aria-busy"], "true");
});

test("hide removes loading attributes from button", () => {
  const mockButton = {
    dataset: {
      sgLoading: "true",
    },
    removeAttribute: function (attr) {
      this[attr] = null;
    },
  };

  hide(mockButton);

  assert.equal(mockButton.dataset.sgLoading, undefined);
  assert.equal(mockButton["aria-busy"], null);
});

test("hide does nothing when button is null", () => {
  // Ensure findSendButton returns null too
  globalThis.SG.chatSelectors.findSendButton = () => null;
  
  // Should not throw
  hide(null);
  assert.ok(true);
});

test("hide uses findSendButton when no button provided", () => {
  const mockButton = {
    dataset: {
      sgLoading: "true",
    },
    removeAttribute: function (attr) {
      this[attr] = null;
    },
  };

  globalThis.SG.chatSelectors.findSendButton = () => mockButton;

  hide();

  assert.equal(mockButton.dataset.sgLoading, undefined);
  assert.equal(mockButton["aria-busy"], null);
});

test("hide handles button without dataset", () => {
  const mockButton = {
    dataset: {},
    removeAttribute: function (attr) {
      this[attr] = null;
    },
  };

  // Should not throw
  hide(mockButton);
  assert.ok(true);
});

test("show and hide work together", () => {
  globalThis.document.head.children = [];

  const mockButton = {
    dataset: {},
    setAttribute: function (attr, value) {
      this[attr] = value;
    },
    removeAttribute: function (attr) {
      delete this[attr];
      delete this.dataset.sgLoading;
    },
  };

  show(mockButton);
  assert.equal(mockButton.dataset.sgLoading, "true");
  assert.equal(mockButton["aria-busy"], "true");

  hide(mockButton);
  assert.equal(mockButton.dataset.sgLoading, undefined);
});

test("show only creates style element once", () => {
  globalThis.document.head.children = [];
  globalThis.document._elementsById = {};

  const mockButton1 = {
    dataset: {},
    setAttribute: function () {},
  };

  const mockButton2 = {
    dataset: {},
    setAttribute: function () {},
  };

  show(mockButton1);
  const lengthAfterFirst = globalThis.document.head.children.length;
  
  // Register the style element by ID so it can be found
  const styleEl = globalThis.document.head.children[0];
  if (styleEl && styleEl.id) {
    globalThis.document._elementsById[styleEl.id] = styleEl;
  }

  show(mockButton2);
  const lengthAfterSecond = globalThis.document.head.children.length;

  assert.equal(lengthAfterSecond, 1);
});

test("show handles button with existing dataset attributes", () => {
  globalThis.document.head.children = [];

  const mockButton = {
    dataset: {
      customAttribute: "existing",
    },
    setAttribute: function (attr, value) {
      this[attr] = value;
    },
  };

  show(mockButton);

  assert.equal(mockButton.dataset.sgLoading, "true");
  assert.equal(mockButton.dataset.customAttribute, "existing");
});

test("style element contains all necessary CSS", () => {
  globalThis.document.head.children = [];
  globalThis.document._elementsById = {};

  const mockButton = {
    dataset: {},
    setAttribute: function () {},
  };

  show(mockButton);

  const style = globalThis.document.head.children[0];
  assert.ok(style.textContent.includes("position: relative"));
  assert.ok(style.textContent.includes("pointer-events: none"));
  assert.ok(style.textContent.includes("border-radius: 999px"));
  assert.ok(style.textContent.includes("animation: sg-send-spin"));
  assert.ok(style.textContent.includes("transform: rotate("));
});
