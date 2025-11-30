const test = require("node:test");
const assert = require("node:assert/strict");

// Mock DOM globals
globalThis.document = {
  querySelectorAll: function (selector) {
    return this._elements?.[selector] || [];
  },
  querySelector: function (selector) {
    const results = this.querySelectorAll(selector);
    return results[0] || null;
  },
  _elements: {},
};

globalThis.SG = {};

// Load the module
require("../src/dom/chatSelectors.js");

const {
  findComposer,
  getComposerText,
  findSendButton,
  extractMessageText,
  isMessageNode,
  findAssistantContentEl,
} = globalThis.SG.chatSelectors;

test("getComposerText extracts text from textarea element", () => {
  const mockTextarea = {
    tagName: "TEXTAREA",
    value: "Hello, world!",
  };

  const text = getComposerText(mockTextarea);
  assert.equal(text, "Hello, world!");
});

test("getComposerText extracts textContent from contenteditable", () => {
  const mockDiv = {
    tagName: "DIV",
    textContent: "This is content",
  };

  const text = getComposerText(mockDiv);
  assert.equal(text, "This is content");
});

test("getComposerText replaces non-breaking spaces with regular spaces", () => {
  const mockDiv = {
    tagName: "DIV",
    textContent: "Text\u00A0with\u00A0nbsp",
  };

  const text = getComposerText(mockDiv);
  assert.equal(text, "Text with nbsp");
});

test("getComposerText returns empty string for null element", () => {
  const text = getComposerText(null);
  assert.equal(text, "");
});

test("getComposerText returns empty string for undefined element", () => {
  const text = getComposerText(undefined);
  assert.equal(text, "");
});

test("getComposerText handles empty content", () => {
  const mockTextarea = {
    tagName: "TEXTAREA",
    value: "",
  };

  const text = getComposerText(mockTextarea);
  assert.equal(text, "");
});

test("extractMessageText extracts innerText when available", () => {
  const mockNode = {
    innerText: "Inner text content",
    textContent: "Text content fallback",
  };

  const text = extractMessageText(mockNode);
  assert.equal(text, "Inner text content");
});

test("extractMessageText falls back to textContent", () => {
  const mockNode = {
    textContent: "Text content only",
  };

  const text = extractMessageText(mockNode);
  assert.equal(text, "Text content only");
});

test("extractMessageText trims whitespace", () => {
  const mockNode = {
    innerText: "  Content with spaces  ",
  };

  const text = extractMessageText(mockNode);
  assert.equal(text, "Content with spaces");
});

test("extractMessageText returns empty string for null node", () => {
  const text = extractMessageText(null);
  assert.equal(text, "");
});

test("extractMessageText returns empty string for node with no text", () => {
  const mockNode = {};
  const text = extractMessageText(mockNode);
  assert.equal(text, "");
});

test("isMessageNode identifies node with data-message-author-role", () => {
  const mockNode = {
    nodeType: 1,
    hasAttribute: (attr) => attr === "data-message-author-role",
  };

  assert.equal(isMessageNode(mockNode), true);
});

test("isMessageNode identifies node inside message container", () => {
  const mockNode = {
    nodeType: 1,
    hasAttribute: () => false,
    closest: (sel) => (sel === "[data-message-author-role]" ? {} : null),
  };

  assert.equal(isMessageNode(mockNode), true);
});

test("isMessageNode identifies conversation-turn test id", () => {
  const mockNode = {
    nodeType: 1,
    hasAttribute: () => false,
    closest: () => null,
    matches: (sel) => sel === '[data-testid="conversation-turn"]',
  };

  assert.equal(isMessageNode(mockNode), true);
});

test("isMessageNode returns false for non-element nodes", () => {
  const mockTextNode = {
    nodeType: 3,
  };

  assert.equal(isMessageNode(mockTextNode), false);
});

test("isMessageNode returns false for null", () => {
  assert.equal(isMessageNode(null), false);
});

test("isMessageNode returns false for undefined", () => {
  assert.equal(isMessageNode(undefined), false);
});

test("isMessageNode returns false for regular divs", () => {
  const mockNode = {
    nodeType: 1,
    hasAttribute: () => false,
    closest: () => null,
    matches: () => false,
  };

  assert.equal(isMessageNode(mockNode), false);
});

test("findAssistantContentEl finds markdown element", () => {
  const mockMarkdown = {
    innerText: "Content here",
  };

  const mockHost = {
    querySelector: (sel) => (sel === ".markdown" ? mockMarkdown : null),
  };

  const result = findAssistantContentEl(mockHost);
  assert.equal(result, mockMarkdown);
});

test("findAssistantContentEl finds prose element", () => {
  const mockProse = {
    innerText: "Prose content",
  };

  const mockHost = {
    querySelector: (sel) => (sel === ".prose" ? mockProse : null),
  };

  const result = findAssistantContentEl(mockHost);
  assert.equal(result, mockProse);
});

test("findAssistantContentEl returns host as fallback", () => {
  const mockHost = {
    querySelector: () => null,
  };

  const result = findAssistantContentEl(mockHost);
  assert.equal(result, mockHost);
});

test("findAssistantContentEl skips elements with no innerText", () => {
  const mockEmptyElement = {
    innerText: "",
  };

  const mockValidElement = {
    innerText: "Valid content",
  };

  let queryCalls = 0;
  const mockHost = {
    querySelector: (sel) => {
      queryCalls++;
      if (queryCalls === 1) return mockEmptyElement;
      if (sel === ".prose") return mockValidElement;
      return null;
    },
  };

  const result = findAssistantContentEl(mockHost);
  assert.equal(result, mockValidElement);
});

test("findComposer returns null when no composer found", () => {
  globalThis.document._elements = {};
  const result = findComposer();
  assert.equal(result, null);
});

test("findComposer finds visible contenteditable element", () => {
  const mockComposer = {
    offsetParent: {},
    clientHeight: 100,
  };

  globalThis.document._elements = {
    '[contenteditable="true"][role="textbox"], div[contenteditable="true"]': [
      mockComposer,
    ],
  };

  const result = findComposer();
  assert.equal(result, mockComposer);
});

test("findComposer skips hidden contenteditable elements", () => {
  const mockHiddenComposer = {
    offsetParent: null,
    clientHeight: 0,
  };

  const mockVisibleTextarea = {
    offsetParent: {},
    clientHeight: 50,
  };

  globalThis.document._elements = {
    '[contenteditable="true"][role="textbox"], div[contenteditable="true"]': [
      mockHiddenComposer,
    ],
    textarea: [mockVisibleTextarea],
  };

  const result = findComposer();
  assert.equal(result, mockVisibleTextarea);
});

test("findSendButton returns null when no composer exists", () => {
  globalThis.document._elements = {};
  const result = findSendButton();
  assert.equal(result, null);
});

test("findSendButton finds submit button in form", () => {
  const mockButton = { type: "submit" };
  const mockForm = {
    querySelector: (sel) =>
      sel === 'button[type="submit"]' ? mockButton : null,
  };

  const mockComposer = {
    offsetParent: {},
    clientHeight: 100,
    closest: (sel) => (sel === "form" ? mockForm : null),
  };

  globalThis.document._elements = {
    '[contenteditable="true"][role="textbox"], div[contenteditable="true"]': [
      mockComposer,
    ],
  };

  const result = findSendButton();
  assert.equal(result, mockButton);
});

test("findSendButton finds button by data-testid", () => {
  const mockButton = { testId: "send-button" };
  const mockComposer = {
    offsetParent: {},
    clientHeight: 100,
    closest: () => null,
  };

  globalThis.document._elements = {
    '[contenteditable="true"][role="textbox"], div[contenteditable="true"]': [
      mockComposer,
    ],
    '[data-testid="send-button"]': [mockButton],
  };

  const result = findSendButton();
  assert.equal(result, mockButton);
});
