const test = require("node:test");
const assert = require("node:assert/strict");

globalThis.SG = {};
require("../src/state/alertStore.js");
const store = globalThis.SG.alertStore;

test("override flag toggles", () => {
  store.setOverrideActive(false);
  assert.equal(store.isOverrideActive(), false);
  store.setOverrideActive(true);
  assert.equal(store.isOverrideActive(), true);
  store.setOverrideActive(false);
  assert.equal(store.isOverrideActive(), false);
});

test("node tracking works via WeakSets", () => {
  const node = {};
  assert.equal(store.hasAnalyzed(node), false);
  store.markAnalyzed(node);
  assert.equal(store.hasAnalyzed(node), true);

  assert.equal(store.isInFlight(node), false);
  store.beginInFlight(node);
  assert.equal(store.isInFlight(node), true);
  store.endInFlight(node);
  assert.equal(store.isInFlight(node), false);
});
