(function initConfig(root) {
  const sg = (root.SG = root.SG || {});

  const API_BASE = "http://127.0.0.1:8000";

  sg.config = {
    API_BASE,
  };
})(typeof window !== "undefined" ? window : globalThis);
