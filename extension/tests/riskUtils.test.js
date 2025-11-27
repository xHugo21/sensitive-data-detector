const test = require("node:test");
const assert = require("node:assert/strict");

globalThis.SG = {};
require("../src/config.js");
require("../src/state/alertStore.js");
require("../src/services/riskUtils.js");

const { classifyField, shouldBlock } = globalThis.SG.riskUtils;
const store = globalThis.SG.alertStore;

test("classifyField prefers backend-provided risk and defaults to low", () => {
  assert.equal(classifyField({ field: "anything", risk: "high" }), "high");
  assert.equal(classifyField({ field: "anything", risk: "medium" }), "medium");
  assert.equal(classifyField({ field: "anything", risk: "LOW" }), "low");
  assert.equal(classifyField("unknown-field"), "low");
});

test("shouldBlock respects decision and override flag", () => {
  store.setOverrideActive(false);
  assert.equal(shouldBlock({ decision: "block" }), true);
  assert.equal(shouldBlock({ risk_level: "High" }), true);
  assert.equal(shouldBlock({ risk_level: "Medium" }), false);
  store.setOverrideActive(true);
  assert.equal(shouldBlock({ decision: "block" }), false);
  store.setOverrideActive(false);
});
