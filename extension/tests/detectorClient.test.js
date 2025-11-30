const test = require("node:test");
const assert = require("node:assert/strict");

// Mock global objects
globalThis.SG = {};
globalThis.FormData = class FormData {
  constructor() {
    this.data = new Map();
  }
  append(key, value) {
    this.data.set(key, value);
  }
  get(key) {
    return this.data.get(key);
  }
};

// Mock fetch
const fetchMock = {
  calls: [],
  responses: [],
  reset() {
    this.calls = [];
    this.responses = [];
  },
  mockResponse(response) {
    this.responses.push(response);
  },
};

globalThis.fetch = async (url, options) => {
  fetchMock.calls.push({ url, options });
  const response = fetchMock.responses.shift();
  if (!response) {
    throw new Error("No mocked response available");
  }
  return response;
};

// Mock MutationObserver
class MockMutationObserver {
  constructor(callback) {
    this.callback = callback;
    this.observing = false;
  }
  observe(target, options) {
    this.observing = true;
    this.target = target;
    this.options = options;
  }
  disconnect() {
    this.observing = false;
  }
}
globalThis.MutationObserver = MockMutationObserver;

// Load the module
require("../src/config.js");
require("../src/services/detectorClient.js");

const { detectText, detectFile, waitForStableContent } =
  globalThis.SG.detectorClient;

test("detectText sends text to API and returns parsed response", async () => {
  fetchMock.reset();
  const expectedResponse = {
    risk_level: "high",
    detected_fields: [{ field: "email", value: "test@example.com" }],
  };

  fetchMock.mockResponse({
    ok: true,
    status: 200,
    json: async () => expectedResponse,
  });

  const result = await detectText("test@example.com");

  assert.equal(fetchMock.calls.length, 1);
  assert.equal(
    fetchMock.calls[0].url,
    "http://127.0.0.1:8000/detect",
  );
  assert.equal(fetchMock.calls[0].options.method, "POST");
  assert.ok(fetchMock.calls[0].options.body instanceof FormData);
  assert.equal(
    fetchMock.calls[0].options.body.get("text"),
    "test@example.com",
  );
  assert.deepEqual(result, expectedResponse);
});

test("detectText throws error on HTTP failure", async () => {
  fetchMock.reset();
  fetchMock.mockResponse({
    ok: false,
    status: 500,
  });

  await assert.rejects(
    async () => await detectText("test"),
    {
      name: "Error",
      message: "Detector HTTP 500",
    },
  );
});

test("detectText handles empty text input", async () => {
  fetchMock.reset();
  const expectedResponse = {
    risk_level: "low",
    detected_fields: [],
  };

  fetchMock.mockResponse({
    ok: true,
    status: 200,
    json: async () => expectedResponse,
  });

  const result = await detectText("");

  assert.equal(fetchMock.calls.length, 1);
  assert.equal(fetchMock.calls[0].options.body.get("text"), "");
  assert.deepEqual(result, expectedResponse);
});

test("detectFile sends file FormData to API", async () => {
  fetchMock.reset();
  const expectedResponse = {
    risk_level: "medium",
    detected_fields: [{ field: "ssn", value: "123-45-6789" }],
  };

  fetchMock.mockResponse({
    ok: true,
    status: 200,
    json: async () => expectedResponse,
  });

  const formData = new FormData();
  formData.append("file", { name: "test.pdf" });

  const result = await detectFile(formData);

  assert.equal(fetchMock.calls.length, 1);
  assert.equal(
    fetchMock.calls[0].url,
    "http://127.0.0.1:8000/detect",
  );
  assert.equal(fetchMock.calls[0].options.method, "POST");
  assert.equal(fetchMock.calls[0].options.body, formData);
  assert.deepEqual(result, expectedResponse);
});

test("detectFile throws error on HTTP failure", async () => {
  fetchMock.reset();
  fetchMock.mockResponse({
    ok: false,
    status: 400,
  });

  const formData = new FormData();
  formData.append("file", { name: "test.pdf" });

  await assert.rejects(
    async () => await detectFile(formData),
    {
      name: "Error",
      message: "Detector HTTP 400",
    },
  );
});

test("waitForStableContent resolves after no mutations for idleMs", async (t) => {
  const mockNode = {
    mutations: [],
  };

  let observerCallback;
  const originalObserver = globalThis.MutationObserver;
  globalThis.MutationObserver = class extends MockMutationObserver {
    constructor(callback) {
      super(callback);
      observerCallback = callback;
    }
  };

  const startTime = Date.now();
  const promise = waitForStableContent(mockNode, 100);

  // Simulate some mutations
  setTimeout(() => observerCallback([{ type: "childList" }]), 10);
  setTimeout(() => observerCallback([{ type: "childList" }]), 50);

  await promise;
  const elapsed = Date.now() - startTime;

  // Should wait at least 100ms after last mutation
  assert.ok(elapsed >= 150);

  globalThis.MutationObserver = originalObserver;
});

test("waitForStableContent disconnects observer after completion", async () => {
  const mockNode = {};
  let observer;

  const originalObserver = globalThis.MutationObserver;
  globalThis.MutationObserver = class extends MockMutationObserver {
    constructor(callback) {
      super(callback);
      observer = this;
    }
  };

  await waitForStableContent(mockNode, 50);

  assert.equal(observer.observing, false);

  globalThis.MutationObserver = originalObserver;
});

test("waitForStableContent observes with correct options", async () => {
  const mockNode = {};
  let capturedOptions;

  const originalObserver = globalThis.MutationObserver;
  globalThis.MutationObserver = class extends MockMutationObserver {
    observe(target, options) {
      super.observe(target, options);
      capturedOptions = options;
    }
  };

  const promise = waitForStableContent(mockNode, 50);
  await promise;

  assert.deepEqual(capturedOptions, {
    childList: true,
    subtree: true,
    characterData: true,
  });

  globalThis.MutationObserver = originalObserver;
});

test("detectText handles network errors gracefully", async () => {
  fetchMock.reset();
  fetchMock.mockResponse(Promise.reject(new Error("Network failure")));

  await assert.rejects(
    async () => await detectText("test"),
    {
      name: "Error",
      message: "Network failure",
    },
  );
});

test("detectText handles malformed JSON response", async () => {
  fetchMock.reset();
  fetchMock.mockResponse({
    ok: true,
    status: 200,
    json: async () => {
      throw new Error("Invalid JSON");
    },
  });

  await assert.rejects(
    async () => await detectText("test"),
    {
      name: "Error",
      message: "Invalid JSON",
    },
  );
});
