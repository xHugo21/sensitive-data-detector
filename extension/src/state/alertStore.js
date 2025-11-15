(function initAlertStore(root) {
  const sg = root.SG = root.SG || {};

  const state = {
    overrideOnce: false,
    pendingResponseAlert: false,
    suppressUserAlerts: false
  };

  const analyzedNodes = new WeakSet();
  const inFlightAnalyze = new WeakSet();

  sg.alertStore = {
    isOverrideActive() {
      return state.overrideOnce;
    },
    setOverrideActive(value) {
      state.overrideOnce = Boolean(value);
    },
    isResponsePending() {
      return state.pendingResponseAlert;
    },
    setResponsePending(value) {
      state.pendingResponseAlert = Boolean(value);
    },
    consumeResponsePending() {
      const pending = state.pendingResponseAlert;
      state.pendingResponseAlert = false;
      return pending;
    },
    shouldSuppressUserAlerts() {
      return state.suppressUserAlerts;
    },
    setSuppressUserAlerts(value) {
      state.suppressUserAlerts = Boolean(value);
    },
    hasAnalyzed(node) {
      return analyzedNodes.has(node);
    },
    markAnalyzed(node) {
      analyzedNodes.add(node);
    },
    isInFlight(node) {
      return inFlightAnalyze.has(node);
    },
    beginInFlight(node) {
      inFlightAnalyze.add(node);
    },
    endInFlight(node) {
      inFlightAnalyze.delete(node);
    }
  };
})(typeof window !== "undefined" ? window : globalThis);
