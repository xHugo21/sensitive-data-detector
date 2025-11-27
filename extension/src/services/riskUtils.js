(function initRiskUtils(root) {
  const sg = (root.SG = root.SG || {});

  const RISK_ORDER = { high: 0, medium: 1, low: 2 };

  function normalizeRisk(value) {
    if (!value) return null;
    const v = String(value).toLowerCase();
    if (v === "high" || v === "medium" || v === "low") return v;
    return null;
  }

  function classifyField(field) {
    const isObj = field && typeof field === "object";
    const riskHint = isObj ? normalizeRisk(field.risk) : null;
    const fieldName = isObj ? field.field || field.type : field;

    if (riskHint) return riskHint;
    return "low";
  }

  function compareFieldGroups(a, b) {
    const order = RISK_ORDER[a.risk] - RISK_ORDER[b.risk];
    if (order !== 0) return order;
    return a.minIdx - b.minIdx || a.field.localeCompare(b.field);
  }

  function shouldBlock(result) {
    if (!result || sg.alertStore.isOverrideActive()) return false;
    const decision = String(result.decision || "").toLowerCase();
    if (decision === "block") return true;
    return result.risk_level === "high";
  }

  sg.riskUtils = {
    classifyField,
    compareFieldGroups,
    shouldBlock,
  };
})(typeof window !== "undefined" ? window : globalThis);
