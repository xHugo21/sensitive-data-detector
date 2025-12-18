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
  assert.equal(shouldBlock({ risk_level: "high" }), true);
  assert.equal(shouldBlock({ risk_level: "medium" }), false);
  store.setOverrideActive(true);
  assert.equal(shouldBlock({ decision: "block" }), false);
  store.setOverrideActive(false);
});

test("shouldWarn detects warn decision", () => {
  const { shouldWarn } = globalThis.SG.riskUtils;
  
  store.setOverrideActive(false);
  assert.equal(shouldWarn({ decision: "warn" }), true);
  assert.equal(shouldWarn({ decision: "block" }), false);
  assert.equal(shouldWarn({ decision: "allow" }), false);
  assert.equal(shouldWarn({ risk_level: "high" }), false);
  assert.equal(shouldWarn({ risk_level: "medium" }), false);
  
  // Override should suppress warnings too
  store.setOverrideActive(true);
  assert.equal(shouldWarn({ decision: "warn" }), false);
  store.setOverrideActive(false);
});
