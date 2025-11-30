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
      _id: null,
      get id() {
        return this._id;
      },
      set id(value) {
        this._id = value;
        if (value) {
          globalThis.document._elementsById[value] = this;
        }
      },
      textContent: "",
      innerHTML: "",
      style: {},
      children: [],
      _eventListeners: {},
      appendChild: function (child) {
        this.children.push(child);
        child.parentElement = this;
      },
      removeChild: function (child) {
        const index = this.children.indexOf(child);
        if (index > -1) {
          this.children.splice(index, 1);
          child.parentElement = null;
        }
      },
      addEventListener: function (event, callback) {
        if (!this._eventListeners[event]) {
          this._eventListeners[event] = [];
        }
        this._eventListeners[event].push(callback);
      },
      contains: function (child) {
        return this.children.includes(child);
      },
      insertBefore: function (newChild, referenceChild) {
        const index = this.children.indexOf(referenceChild);
        if (index > -1) {
          this.children.splice(index, 0, newChild);
        } else {
          this.children.push(newChild);
        }
        newChild.parentElement = this;
      },
    };
    return element;
  },
  body: {
    appendChild: function (child) {
      this.children = this.children || [];
      this.children.push(child);
    },
  },
  documentElement: {},
  _elementsById: {},
};

globalThis.SG = {
  chatSelectors: {
    findComposer: () => null,
  },
  riskUtils: {
    classifyField: (field) => field.risk || "low",
    compareFieldGroups: (a, b) => {
      const riskOrder = { high: 0, medium: 1, low: 2 };
      return riskOrder[a.risk] - riskOrder[b.risk];
    },
  },
};

// Load the module
require("../src/ui/panel.js");

const { ensure, render, hide, onSendAnyway, onDismiss } = globalThis.SG.panel;

test("ensure creates panel on first call", () => {
  globalThis.document._elementsById = {};
  globalThis.document.body.children = [];

  const panel = ensure();

  assert.ok(panel);
  assert.equal(panel.id, "sg-llm-panel");
  assert.equal(panel.style.display, "none");
  assert.ok(panel._els);
  assert.ok(panel._els.title);
  assert.ok(panel._els.list);
  assert.ok(panel._els.btnSendAnyway);
  assert.ok(panel._els.btnDismiss);
});

test("ensure returns existing panel on subsequent calls", () => {
  const existingPanel = globalThis.document.createElement("div");
  existingPanel.id = "sg-llm-panel";
  existingPanel._els = {
    title: {},
    list: {},
    originBadge: {},
    policy: {},
    actions: {},
    btnSendAnyway: {},
    btnDismiss: {},
  };

  globalThis.document._elementsById = {
    "sg-llm-panel": existingPanel,
  };

  const panel = ensure();

  assert.equal(panel, existingPanel);
});

test("render displays panel with high risk", () => {
  globalThis.document._elementsById = {};
  globalThis.document.body.children = [];

  const result = {
    risk_level: "high",
    detected_fields: [
      { field: "ssn", value: "123-45-6789", risk: "high" },
    ],
    remediation: "Remove sensitive data before sending",
  };

  render(result, "User", "My SSN is 123-45-6789");

  const panel = globalThis.document._elementsById["sg-llm-panel"];
  assert.equal(panel.style.display, "block");
  assert.equal(panel._els.title.textContent, "⚠️ High Risk Detected");
  assert.equal(panel._els.originBadge.textContent, "Source: User");
  assert.ok(panel._els.policy.innerHTML.includes("Remove sensitive data"));
});

test("render displays panel with medium risk", () => {
  globalThis.document._elementsById = {};
  globalThis.document.body.children = [];

  const result = {
    risk_level: "medium",
    detected_fields: [
      { field: "email", value: "user@example.com", risk: "medium" },
    ],
  };

  render(result, "Response", "Contact user@example.com");

  const panel = globalThis.document._elementsById["sg-llm-panel"];
  assert.equal(panel._els.title.textContent, "⚠️ Medium Risk Detected");
  assert.equal(panel._els.originBadge.textContent, "Source: Response");
});

test("render displays panel with low risk", () => {
  globalThis.document._elementsById = {};
  globalThis.document.body.children = [];

  const result = {
    risk_level: "low",
    detected_fields: [],
  };

  render(result, "User", "Some text");

  const panel = globalThis.document._elementsById["sg-llm-panel"];
  assert.equal(panel._els.title.textContent, "⚠️ Low Risk Detected");
});

test("render displays unknown risk", () => {
  globalThis.document._elementsById = {};
  globalThis.document.body.children = [];

  const result = {
    risk_level: "unknown",
    detected_fields: [],
  };

  render(result, "User", "Text");

  const panel = globalThis.document._elementsById["sg-llm-panel"];
  assert.equal(panel._els.title.textContent, "⚠️ Unknown Risk Detected");
});

test("render shows send anyway button for User origin", () => {
  globalThis.document._elementsById = {};
  globalThis.document.body.children = [];

  const result = {
    risk_level: "high",
    detected_fields: [],
  };

  render(result, "User", "Text");

  const panel = globalThis.document._elementsById["sg-llm-panel"];
  assert.equal(panel._els.btnSendAnyway.style.display, "inline-block");
  assert.equal(panel._els.btnDismiss.style.display, "inline-block");
});

test("render hides send anyway button for Response origin", () => {
  globalThis.document._elementsById = {};
  globalThis.document.body.children = [];

  const result = {
    risk_level: "high",
    detected_fields: [],
  };

  render(result, "Response", "Text");

  const panel = globalThis.document._elementsById["sg-llm-panel"];
  // Send anyway button should be removed from actions
  assert.equal(panel._els.btnDismiss.style.display, "inline-block");
  assert.equal(panel._els.btnDismiss.style.flex, "1");
});

test("render displays detected fields", () => {
  globalThis.document._elementsById = {};
  globalThis.document.body.children = [];

  const result = {
    risk_level: "high",
    detected_fields: [
      { field: "email", value: "user@example.com", source: "LLM", risk: "low" },
      { field: "ssn", value: "123-45-6789", source: "DLP", risk: "high" },
    ],
  };

  render(result, "User", "email: user@example.com, ssn: 123-45-6789");

  const panel = globalThis.document._elementsById["sg-llm-panel"];
  assert.ok(panel._els.list.children.length > 0);
});

test("render shows empty state when no fields detected", () => {
  globalThis.document._elementsById = {};
  globalThis.document.body.children = [];

  const result = {
    risk_level: "low",
    detected_fields: [],
  };

  render(result, "User", "Clean text");

  const panel = globalThis.document._elementsById["sg-llm-panel"];
  assert.equal(panel._els.list.children.length, 1);
  assert.ok(
    panel._els.list.children[0].textContent.includes("No sensitive fields"),
  );
});

test("render handles missing remediation", () => {
  globalThis.document._elementsById = {};
  globalThis.document.body.children = [];

  const result = {
    risk_level: "high",
    detected_fields: [],
  };

  render(result, "User", "Text");

  const panel = globalThis.document._elementsById["sg-llm-panel"];
  assert.equal(panel._els.policy.innerHTML, "");
});

test("hide hides the panel", () => {
  const mockPanel = globalThis.document.createElement("div");
  mockPanel.id = "sg-llm-panel";
  mockPanel.style.display = "block";
  mockPanel._els = {
    title: {},
    list: {},
    originBadge: {},
    policy: {},
    actions: {},
    btnSendAnyway: {},
    btnDismiss: {},
  };

  globalThis.document._elementsById = {
    "sg-llm-panel": mockPanel,
  };

  hide();

  assert.equal(mockPanel.style.display, "none");
});

test("hide does nothing when panel doesn't exist", () => {
  globalThis.document._elementsById = {};

  // Should not throw
  hide();
  assert.ok(true);
});

test("onSendAnyway registers callback", () => {
  let callbackCalled = false;
  const callback = () => {
    callbackCalled = true;
  };

  onSendAnyway(callback);

  // Create panel and trigger send anyway button
  globalThis.document._elementsById = {};
  globalThis.document.body.children = [];
  const panel = ensure();

  // Simulate button click
  const listeners = panel._els.btnSendAnyway._eventListeners?.["click"] || [];
  listeners.forEach((fn) => fn());

  assert.equal(callbackCalled, true);
});

test("onDismiss registers callback", () => {
  let callbackCalled = false;
  const callback = () => {
    callbackCalled = true;
  };

  onDismiss(callback);

  // Create panel and trigger dismiss button
  globalThis.document._elementsById = {};
  globalThis.document.body.children = [];
  const panel = ensure();

  // Simulate button click
  const listeners = panel._els.btnDismiss._eventListeners?.["click"] || [];
  listeners.forEach((fn) => fn());

  assert.equal(callbackCalled, true);
});

test("onSendAnyway ignores non-function arguments", () => {
  // Should not throw
  onSendAnyway(null);
  onSendAnyway("string");
  onSendAnyway(123);
  assert.ok(true);
});

test("onDismiss ignores non-function arguments", () => {
  // Should not throw
  onDismiss(null);
  onDismiss("string");
  onDismiss(123);
  assert.ok(true);
});

test("render groups duplicate field values", () => {
  globalThis.document._elementsById = {};
  globalThis.document.body.children = [];

  const result = {
    risk_level: "high",
    detected_fields: [
      { field: "email", value: "user@example.com", risk: "low" },
      { field: "email", value: "user@example.com", risk: "low" },
      { field: "email", value: "other@example.com", risk: "low" },
    ],
  };

  render(result, "User", "user@example.com user@example.com other@example.com");

  const panel = globalThis.document._elementsById["sg-llm-panel"];
  // Should group by field type
  assert.equal(panel._els.list.children.length, 1);
});

test("render skips fields with empty values", () => {
  globalThis.document._elementsById = {};
  globalThis.document.body.children = [];

  const result = {
    risk_level: "high",
    detected_fields: [
      { field: "email", value: "", risk: "low" },
      { field: "ssn", value: "   ", risk: "high" },
      { field: "phone", value: "123-456-7890", risk: "medium" },
    ],
  };

  render(result, "User", "phone: 123-456-7890");

  const panel = globalThis.document._elementsById["sg-llm-panel"];
  // Should only show phone field
  assert.equal(panel._els.list.children.length, 1);
});

test("render applies correct border color for high risk", () => {
  globalThis.document._elementsById = {};
  globalThis.document.body.children = [];

  const result = {
    risk_level: "high",
    detected_fields: [],
  };

  render(result, "User", "Text");

  const panel = globalThis.document._elementsById["sg-llm-panel"];
  assert.ok(panel.style.borderLeft.includes("#fa5a5a"));
});

test("render applies correct border color for Response origin", () => {
  globalThis.document._elementsById = {};
  globalThis.document.body.children = [];

  const result = {
    risk_level: "high",
    detected_fields: [],
  };

  render(result, "Response", "Text");

  const panel = globalThis.document._elementsById["sg-llm-panel"];
  assert.ok(panel.style.borderLeft.includes("#82b5ff"));
});
