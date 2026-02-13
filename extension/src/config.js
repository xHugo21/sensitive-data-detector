(function initConfig(root) {
  const sg = (root.SG = root.SG || {});

  const API_BASE = "http://127.0.0.1:8000";

  sg.config = {
    API_BASE,
    MIN_BLOCK_LEVEL: "medium",
  };
})(typeof window !== "undefined" ? window : globalThis);
