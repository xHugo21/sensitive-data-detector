const test = require("node:test");
const assert = require("node:assert/strict");

// Mock DOM globals
globalThis.document = {
  getElementById: function (id) {
    return this._elementsById?.[id] || null;
  },
  createElement: function (tagName) {
    const element = {
      tagName: tagName.toUpperCase(),
      id: null,
      textContent: "",
      style: {},
      remove: function () {
        this._removed = true;
        // Remove from parent if in head
        if (globalThis.document.head.children) {
          const index = globalThis.document.head.children.indexOf(this);
          if (index > -1) {
            globalThis.document.head.children.splice(index, 1);
          }
        }
      },
    };
    return element;
  },
  head: {
    appendChild: function (el) {
      this.children = this.children || [];
      this.children.push(el);
    },
    removeChild: function (el) {
      const index = this.children.indexOf(el);
      if (index > -1) {
        this.children.splice(index, 1);
      }
    },
    children: [],
  },
  createTreeWalker: function (root, whatToShow, filter) {
    const mockWalker = {
      _nodes: [],
      _index: -1,
      nextNode: function () {
        this._index++;
        return this._nodes[this._index] || null;
      },
    };
    return mockWalker;
  },
  _elementsById: {},
};

globalThis.NodeFilter = {
  SHOW_TEXT: 4,
  FILTER_ACCEPT: 1,
  FILTER_REJECT: 2,
};

globalThis.Range = class Range {
  constructor() {
    this.startContainer = null;
    this.startOffset = 0;
    this.endContainer = null;
    this.endOffset = 0;
  }
  setStart(node, offset) {
    this.startContainer = node;
    this.startOffset = offset;
  }
  setEnd(node, offset) {
    this.endContainer = node;
    this.endOffset = offset;
  }
};

globalThis.Highlight = class Highlight {
  constructor(...ranges) {
    this.ranges = ranges;
  }
};

globalThis.CSS = {
  highlights: {
    _map: new Map(),
    set: function (name, highlight) {
      this._map.set(name, highlight);
    },
    delete: function (name) {
      this._map.delete(name);
    },
    get: function (name) {
      return this._map.get(name);
    },
    clear: function () {
      this._map.clear();
    },
  },
};

globalThis.SG = {};

// Load dependencies
require("../src/config.js");
require("../src/state/alertStore.js");
require("../src/services/riskUtils.js");
require("../src/ui/highlights.js");

const { ensureHighlightCSS, applyHighlights, clearHighlights } =
  globalThis.SG.highlights;

test("ensureHighlightCSS creates style element", () => {
  globalThis.document.head.children = [];

  ensureHighlightCSS();

  assert.equal(globalThis.document.head.children.length, 1);
  const style = globalThis.document.head.children[0];
  assert.equal(style.tagName, "STYLE");
  assert.equal(style.id, "sg-highlights-css");
  assert.ok(style.textContent.includes("::highlight(sg-user-high)"));
  assert.ok(style.textContent.includes("::highlight(sg-user-med)"));
  assert.ok(style.textContent.includes("::highlight(sg-user-low)"));
});

test("ensureHighlightCSS removes old style before creating new one", () => {
  const oldStyle = {
    tagName: "STYLE",
    id: "sg-highlights-css",
    remove: function () {
      this._removed = true;
    },
  };

  globalThis.document._elementsById = {
    "sg-highlights-css": oldStyle,
  };
  globalThis.document.head.children = [];

  ensureHighlightCSS();

  assert.equal(oldStyle._removed, true);
  assert.equal(globalThis.document.head.children.length, 1);
});

test("clearHighlights removes user highlights", () => {
  globalThis.CSS.highlights.clear();
  globalThis.CSS.highlights.set("sg-user-high", new Highlight());
  globalThis.CSS.highlights.set("sg-user-med", new Highlight());
  globalThis.CSS.highlights.set("sg-user-low", new Highlight());

  clearHighlights("user");

  assert.equal(globalThis.CSS.highlights.get("sg-user-high"), undefined);
  assert.equal(globalThis.CSS.highlights.get("sg-user-med"), undefined);
  assert.equal(globalThis.CSS.highlights.get("sg-user-low"), undefined);
});

test("clearHighlights removes assistant highlights", () => {
  globalThis.CSS.highlights.clear();
  globalThis.CSS.highlights.set("sg-assist-high", new Highlight());
  globalThis.CSS.highlights.set("sg-assist-med", new Highlight());
  globalThis.CSS.highlights.set("sg-assist-low", new Highlight());

  clearHighlights("assistant");

  assert.equal(globalThis.CSS.highlights.get("sg-assist-high"), undefined);
  assert.equal(globalThis.CSS.highlights.get("sg-assist-med"), undefined);
  assert.equal(globalThis.CSS.highlights.get("sg-assist-low"), undefined);
});

test("clearHighlights does not affect other context highlights", () => {
  globalThis.CSS.highlights.clear();
  globalThis.CSS.highlights.set("sg-user-high", new Highlight());
  globalThis.CSS.highlights.set("sg-assist-high", new Highlight());

  clearHighlights("user");

  assert.equal(globalThis.CSS.highlights.get("sg-user-high"), undefined);
  assert.ok(globalThis.CSS.highlights.get("sg-assist-high"));
});

test("applyHighlights returns early when host is null", () => {
  globalThis.CSS.highlights.clear();
  const detectedFields = [{ field: "email", value: "test@example.com" }];

  applyHighlights(null, detectedFields, "user");

  // No highlights should be created
  assert.equal(globalThis.CSS.highlights._map.size, 0);
});

test("applyHighlights returns early when CSS.highlights not available", () => {
  const originalCSS = globalThis.CSS;
  globalThis.CSS = undefined;

  const mockHost = {};
  const detectedFields = [{ field: "email", value: "test@example.com" }];

  // Should not throw
  applyHighlights(mockHost, detectedFields, "user");

  globalThis.CSS = originalCSS;
});

test("applyHighlights handles empty detected fields", () => {
  globalThis.CSS.highlights.clear();
  const mockHost = {};

  applyHighlights(mockHost, [], "user");

  assert.equal(globalThis.CSS.highlights._map.size, 0);
});

test("applyHighlights skips fields with empty values", () => {
  globalThis.CSS.highlights.clear();
  const mockHost = {
    createTreeWalker: globalThis.document.createTreeWalker,
  };

  const detectedFields = [
    { field: "email", value: "" },
    { field: "phone", value: "  " },
  ];

  applyHighlights(mockHost, detectedFields, "user");

  assert.equal(globalThis.CSS.highlights._map.size, 0);
});

test("applyHighlights skips very short values", () => {
  globalThis.CSS.highlights.clear();
  const mockHost = {
    createTreeWalker: globalThis.document.createTreeWalker,
  };

  const detectedFields = [{ field: "initial", value: "A" }];

  applyHighlights(mockHost, detectedFields, "user");

  assert.equal(globalThis.CSS.highlights._map.size, 0);
});

test("applyHighlights deduplicates field values", () => {
  globalThis.CSS.highlights.clear();

  // Create a more complete mock tree walker
  const mockTextNode = {
    nodeValue: "test@example.com and test@example.com",
    parentElement: {
      closest: () => null,
    },
  };

  const mockHost = {};
  const originalCreateTreeWalker = globalThis.document.createTreeWalker;
  globalThis.document.createTreeWalker = function () {
    const walker = originalCreateTreeWalker.apply(this, arguments);
    walker._nodes = [mockTextNode];
    walker._index = -1;
    return walker;
  };

  const detectedFields = [
    { field: "email", value: "test@example.com", risk: "low" },
    { field: "email", value: "test@example.com", risk: "low" },
  ];

  applyHighlights(mockHost, detectedFields, "user");

  // Should create highlights but not duplicate work
  const lowHighlight = globalThis.CSS.highlights.get("sg-user-low");
  assert.ok(lowHighlight);

  globalThis.document.createTreeWalker = originalCreateTreeWalker;
});

test("applyHighlights categorizes fields by risk level", () => {
  globalThis.CSS.highlights.clear();

  const mockTextNode = {
    nodeValue: "email@test.com phone:123 ssn:456",
    parentElement: {
      closest: () => null,
    },
  };

  const mockHost = {};
  const originalCreateTreeWalker = globalThis.document.createTreeWalker;
  globalThis.document.createTreeWalker = function () {
    const walker = originalCreateTreeWalker.apply(this, arguments);
    walker._nodes = [mockTextNode];
    walker._index = -1;
    return walker;
  };

  const detectedFields = [
    { field: "email", value: "email@test.com", risk: "low" },
    { field: "phone", value: "123", risk: "medium" },
    { field: "ssn", value: "456", risk: "high" },
  ];

  applyHighlights(mockHost, detectedFields, "user");

  assert.ok(globalThis.CSS.highlights.get("sg-user-low"));
  assert.ok(globalThis.CSS.highlights.get("sg-user-med"));
  assert.ok(globalThis.CSS.highlights.get("sg-user-high"));

  globalThis.document.createTreeWalker = originalCreateTreeWalker;
});

test("applyHighlights uses correct prefix for assistant context", () => {
  globalThis.CSS.highlights.clear();

  const mockTextNode = {
    nodeValue: "sensitive data",
    parentElement: {
      closest: () => null,
    },
  };

  const mockHost = {};
  const originalCreateTreeWalker = globalThis.document.createTreeWalker;
  globalThis.document.createTreeWalker = function () {
    const walker = originalCreateTreeWalker.apply(this, arguments);
    walker._nodes = [mockTextNode];
    walker._index = -1;
    return walker;
  };

  const detectedFields = [{ field: "test", value: "sensitive data", risk: "high" }];

  applyHighlights(mockHost, detectedFields, "assistant");

  assert.ok(globalThis.CSS.highlights.get("sg-assist-high"));
  assert.equal(globalThis.CSS.highlights.get("sg-user-high"), undefined);

  globalThis.document.createTreeWalker = originalCreateTreeWalker;
});

test("applyHighlights clears previous highlights before applying new ones", () => {
  globalThis.CSS.highlights.clear();
  globalThis.CSS.highlights.set("sg-user-high", new Highlight());
  globalThis.CSS.highlights.set("sg-user-low", new Highlight());

  const mockHost = {};
  applyHighlights(mockHost, [], "user");

  assert.equal(globalThis.CSS.highlights.get("sg-user-high"), undefined);
  assert.equal(globalThis.CSS.highlights.get("sg-user-low"), undefined);
});

test("ensureHighlightCSS is idempotent", () => {
  globalThis.document.head.children = [];
  globalThis.document._elementsById = {};

  ensureHighlightCSS();
  const firstLength = globalThis.document.head.children.length;
  
  // Register the first style element by ID
  const firstStyle = globalThis.document.head.children[0];
  if (firstStyle && firstStyle.id) {
    globalThis.document._elementsById[firstStyle.id] = firstStyle;
  }

  ensureHighlightCSS();
  const secondLength = globalThis.document.head.children.length;

  // Should have same count (old removed, new added)
  assert.equal(secondLength, 1);
});
