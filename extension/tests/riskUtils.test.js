const test = require("node:test");
const assert = require("node:assert/strict");

globalThis.SG = {};
require("../src/config.js");
require("../src/state/alertStore.js");
require("../src/services/riskUtils.js");

const { classifyField, shouldBlock } = globalThis.SG.riskUtils;
const store = globalThis.SG.alertStore;

test("classifyField returns expected risk buckets", () => {
  assert.equal(classifyField("password"), "high");
  assert.equal(classifyField("email"), "medium");
  assert.equal(classifyField("unknown-field"), "low");
});

test("shouldBlock respects override flag", () => {
  store.setOverrideActive(false);
  assert.equal(shouldBlock("High"), true);
  assert.equal(shouldBlock("Medium"), false);
  store.setOverrideActive(true);
  assert.equal(shouldBlock("High"), false);
  store.setOverrideActive(false);
});
