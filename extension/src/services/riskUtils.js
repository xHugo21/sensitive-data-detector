(function initRiskUtils(root) {
  const sg = root.SG = root.SG || {};

  const RISK_ORDER = { high: 0, medium: 1, low: 2 };

  function classifyField(fieldName) {
    if (!fieldName) return "low";
    const upper = String(fieldName).toUpperCase();
    if (sg.config.HIGH_FIELDS.has(upper)) return "high";
    if (sg.config.MEDIUM_FIELDS.has(upper)) return "medium";
    return "low";
  }

  function compareFieldGroups(a, b) {
    const order = RISK_ORDER[a.risk] - RISK_ORDER[b.risk];
    if (order !== 0) return order;
    return (a.minIdx - b.minIdx) || a.field.localeCompare(b.field);
  }

  function shouldBlock(riskLevel) {
    return riskLevel === "High" && !sg.alertStore.isOverrideActive();
  }

  sg.riskUtils = {
    classifyField,
    compareFieldGroups,
    shouldBlock
  };
})(typeof window !== "undefined" ? window : globalThis);
