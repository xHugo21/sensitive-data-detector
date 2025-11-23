(function initLoadingState(root) {
  const sg = (root.SG = root.SG || {});

  const STYLE_ID = "sg-send-loading-style";

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      [data-sg-loading="true"] {
        position: relative !important;
        pointer-events: none !important;
        opacity: 0.9;
      }
      [data-sg-loading="true"]::after {
        content: "";
        position: absolute;
        top: 50%;
        left: 50%;
        width: 16px;
        height: 16px;
        margin-top: -8px;
        margin-left: -8px;
        border-radius: 999px;
        border: 2px solid currentColor;
        border-top-color: transparent;
        border-right-color: transparent;
        animation: sg-send-spin 0.8s linear infinite;
        opacity: 0.9;
      }
      [data-sg-loading="true"] > * {
        opacity: 0.35;
      }
      @keyframes sg-send-spin {
        0%   { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    `;
    document.head.appendChild(style);
  }

  function normalizeButton(btn) {
    return btn && typeof btn === "object" ? btn : sg.chatSelectors?.findSendButton?.();
  }

  function show(targetButton) {
    const btn = normalizeButton(targetButton);
    if (!btn) return;
    ensureStyles();
    btn.dataset.sgLoading = "true";
    btn.setAttribute("aria-busy", "true");
  }

  function hide(targetButton) {
    const btn = normalizeButton(targetButton);
    if (!btn) return;
    if (btn.dataset.sgLoading) delete btn.dataset.sgLoading;
    btn.removeAttribute("aria-busy");
  }

  sg.loadingState = {
    show,
    hide,
  };
})(typeof window !== "undefined" ? window : globalThis);
