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

// Mock fetch for detectorClient
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

globalThis.MutationObserver = class {
  observe() {}
  disconnect() {}
};

// Load the modules
require("../src/config.js");
require("../src/services/detectorClient.js");
require("../src/services/fileAnalyzer.js");

const {
  analyzeFile,
  isSupportedFile,
  getFileInfo,
  getFileExtension,
  SUPPORTED_EXTENSIONS,
} = globalThis.SG.fileAnalyzer;

test("getFileExtension extracts extension from filename", () => {
  assert.equal(getFileExtension("document.pdf"), "pdf");
  assert.equal(getFileExtension("image.PNG"), "png");
  assert.equal(getFileExtension("file.test.txt"), "txt");
  assert.equal(getFileExtension("script.js"), "js");
  assert.equal(getFileExtension("archive.tar.gz"), "gz");
});

test("getFileExtension handles edge cases", () => {
  assert.equal(getFileExtension(""), "");
  assert.equal(getFileExtension(null), "");
  assert.equal(getFileExtension(undefined), "");
  assert.equal(getFileExtension("noextension"), "");
  assert.equal(getFileExtension(".hiddenfile"), "hiddenfile");
  assert.equal(getFileExtension("file."), "");
});

test("isSupportedFile correctly identifies supported files", () => {
  assert.equal(isSupportedFile("document.pdf"), true);
  assert.equal(isSupportedFile("image.png"), true);
  assert.equal(isSupportedFile("image.JPG"), true);
  assert.equal(isSupportedFile("script.js"), true);
  assert.equal(isSupportedFile("data.csv"), true);
  assert.equal(isSupportedFile("code.py"), true);
  assert.equal(isSupportedFile("markup.html"), true);
  assert.equal(isSupportedFile("config.yaml"), true);
  assert.equal(isSupportedFile("config.yml"), true);
});

test("isSupportedFile correctly identifies unsupported files", () => {
  assert.equal(isSupportedFile("video.mp4"), false);
  assert.equal(isSupportedFile("audio.mp3"), false);
  assert.equal(isSupportedFile("archive.zip"), false);
  assert.equal(isSupportedFile("binary.exe"), false);
  assert.equal(isSupportedFile("noextension"), false);
  assert.equal(isSupportedFile(""), false);
});

test("getFileInfo returns correct info for document files", () => {
  const info = getFileInfo("report.pdf");
  assert.equal(info.type, "document");
  assert.equal(info.label, "PDF");
});

test("getFileInfo returns correct info for image files", () => {
  assert.deepEqual(getFileInfo("photo.png"), { type: "image", label: "Image" });
  assert.deepEqual(getFileInfo("pic.jpg"), { type: "image", label: "Image" });
  assert.deepEqual(getFileInfo("graphic.webp"), {
    type: "image",
    label: "Image",
  });
});

test("getFileInfo returns correct info for text files", () => {
  assert.deepEqual(getFileInfo("notes.txt"), {
    type: "text",
    label: "Text File",
  });
  assert.deepEqual(getFileInfo("README.md"), {
    type: "text",
    label: "Markdown",
  });
  assert.deepEqual(getFileInfo("data.csv"), { type: "text", label: "CSV" });
});

test("getFileInfo returns correct info for code files", () => {
  assert.deepEqual(getFileInfo("app.js"), {
    type: "code",
    label: "JavaScript",
  });
  assert.deepEqual(getFileInfo("script.py"), { type: "code", label: "Python" });
  assert.deepEqual(getFileInfo("Main.java"), { type: "code", label: "Java" });
  assert.deepEqual(getFileInfo("style.css"), { type: "code", label: "CSS" });
  assert.deepEqual(getFileInfo("config.json"), { type: "code", label: "JSON" });
});

test("getFileInfo returns unknown for unsupported files", () => {
  const info = getFileInfo("video.mp4");
  assert.equal(info.type, "unknown");
  assert.equal(info.label, "File");
});

test("analyzeFile throws error when no file provided", async () => {
  await assert.rejects(
    async () => await analyzeFile(null),
    {
      name: "Error",
      message: "No file provided",
    },
  );

  await assert.rejects(
    async () => await analyzeFile(undefined),
    {
      name: "Error",
      message: "No file provided",
    },
  );
});

test("analyzeFile sends file to backend and returns result with metadata", async () => {
  fetchMock.reset();
  const mockFile = {
    name: "test.pdf",
    size: 1024,
  };

  const backendResponse = {
    risk_level: "high",
    detected_fields: [{ field: "ssn", value: "123-45-6789" }],
    extracted_snippet: "This document contains sensitive data...",
  };

  fetchMock.mockResponse({
    ok: true,
    status: 200,
    json: async () => backendResponse,
  });

  const result = await analyzeFile(mockFile);

  // Verify API call
  assert.equal(fetchMock.calls.length, 1);
  assert.equal(fetchMock.calls[0].options.method, "POST");
  const formData = fetchMock.calls[0].options.body;
  assert.ok(formData instanceof FormData);
  assert.equal(formData.get("file"), mockFile);

  // Verify result includes backend response
  assert.equal(result.risk_level, "high");
  assert.equal(result.detected_fields.length, 1);
  assert.equal(result.extracted_snippet, "This document contains sensitive data...");

  // Verify file metadata was added
  assert.ok(result.fileInfo);
  assert.equal(result.fileInfo.name, "test.pdf");
  assert.equal(result.fileInfo.size, 1024);
  assert.equal(result.fileInfo.type, "document");
  assert.equal(result.fileInfo.label, "PDF");
  assert.equal(result.fileInfo.extension, "pdf");
});

test("analyzeFile handles image files", async () => {
  fetchMock.reset();
  const mockFile = {
    name: "screenshot.png",
    size: 2048,
  };

  const backendResponse = {
    risk_level: "medium",
    detected_fields: [{ field: "email", value: "user@example.com" }],
  };

  fetchMock.mockResponse({
    ok: true,
    status: 200,
    json: async () => backendResponse,
  });

  const result = await analyzeFile(mockFile);

  assert.equal(result.fileInfo.type, "image");
  assert.equal(result.fileInfo.label, "Image");
  assert.equal(result.fileInfo.extension, "png");
});

test("analyzeFile handles code files", async () => {
  fetchMock.reset();
  const mockFile = {
    name: "config.yaml",
    size: 512,
  };

  const backendResponse = {
    risk_level: "low",
    detected_fields: [],
  };

  fetchMock.mockResponse({
    ok: true,
    status: 200,
    json: async () => backendResponse,
  });

  const result = await analyzeFile(mockFile);

  assert.equal(result.fileInfo.type, "code");
  assert.equal(result.fileInfo.label, "YAML");
  assert.equal(result.fileInfo.extension, "yaml");
});

test("analyzeFile handles backend errors", async () => {
  fetchMock.reset();
  const mockFile = {
    name: "test.txt",
    size: 256,
  };

  fetchMock.mockResponse({
    ok: false,
    status: 500,
  });

  await assert.rejects(
    async () => await analyzeFile(mockFile),
    {
      name: "Error",
      message: "Detector HTTP 500",
    },
  );
});

test("analyzeFile handles network errors", async () => {
  fetchMock.reset();
  const mockFile = {
    name: "test.pdf",
    size: 1024,
  };

  fetchMock.mockResponse(Promise.reject(new Error("Network timeout")));

  await assert.rejects(
    async () => await analyzeFile(mockFile),
    {
      name: "Error",
      message: "Network timeout",
    },
  );
});

test("SUPPORTED_EXTENSIONS contains expected file types", () => {
  assert.ok(SUPPORTED_EXTENSIONS.pdf);
  assert.ok(SUPPORTED_EXTENSIONS.png);
  assert.ok(SUPPORTED_EXTENSIONS.jpg);
  assert.ok(SUPPORTED_EXTENSIONS.jpeg);
  assert.ok(SUPPORTED_EXTENSIONS.txt);
  assert.ok(SUPPORTED_EXTENSIONS.md);
  assert.ok(SUPPORTED_EXTENSIONS.csv);
  assert.ok(SUPPORTED_EXTENSIONS.js);
  assert.ok(SUPPORTED_EXTENSIONS.py);
  assert.ok(SUPPORTED_EXTENSIONS.json);
  assert.ok(SUPPORTED_EXTENSIONS.yaml);
  assert.ok(SUPPORTED_EXTENSIONS.yml);
  assert.ok(SUPPORTED_EXTENSIONS.html);
  assert.ok(SUPPORTED_EXTENSIONS.css);
  assert.ok(SUPPORTED_EXTENSIONS.sql);
});

test("analyzeFile handles files with no detected fields", async () => {
  fetchMock.reset();
  const mockFile = {
    name: "clean.txt",
    size: 100,
  };

  const backendResponse = {
    risk_level: "low",
    detected_fields: [],
  };

  fetchMock.mockResponse({
    ok: true,
    status: 200,
    json: async () => backendResponse,
  });

  const result = await analyzeFile(mockFile);

  assert.equal(result.risk_level, "low");
  assert.equal(result.detected_fields.length, 0);
  assert.equal(result.fileInfo.name, "clean.txt");
});
