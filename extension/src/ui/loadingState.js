(function initLoadingState(root) {
  const sg = (root.SG = root.SG || {});

  const STYLE_ID = "sg-global-loading-style";
  const TOAST_ID = "sg-global-loading-chip";
  const DEFAULT_MESSAGE = "Analyzing message...";
  let activeCount = 0;
  const trackedButtons = new Set();
  const buttonState = new WeakMap();
  let toast = null;
  let textEl = null;

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      #${TOAST_ID} {
        position: fixed;
        right: 16px;
        bottom: 16px;
        display: none;
        align-items: center;
        gap: 8px;
        padding: 10px 14px;
        background: rgba(17, 24, 39, 0.92);
        color: #f8fafc;
        border-radius: 999px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        z-index: 2147483646;
        font-size: 13px;
        line-height: 1.3;
        letter-spacing: 0.01em;
      }
      #${TOAST_ID}[data-sg-visible="true"] {
        display: inline-flex;
      }
      #${TOAST_ID} .sg-loading-spinner {
        width: 14px;
        height: 14px;
        border-radius: 999px;
        border: 2px solid currentColor;
        border-top-color: transparent;
        border-right-color: transparent;
        animation: sg-global-send-spin 0.8s linear infinite;
        opacity: 0.9;
      }
      @keyframes sg-global-send-spin {
        0%   { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    `;
    document.head.appendChild(style);
  }

  function ensureToast() {
    if (toast) return toast;
    const el = document.createElement("div");
    el.id = TOAST_ID;
    el.setAttribute("role", "status");
    el.setAttribute("aria-live", "polite");

    const spinner = document.createElement("span");
    spinner.className = "sg-loading-spinner";
    spinner.setAttribute("aria-hidden", "true");

    textEl = document.createElement("span");
    textEl.className = "sg-loading-text";
    textEl.textContent = DEFAULT_MESSAGE;

    el.appendChild(spinner);
    el.appendChild(textEl);
    document.body.appendChild(el);
    toast = el;
    return toast;
  }

  function normalizeButton(button) {
    if (button && typeof button === "object" && button.tagName === "BUTTON") {
      return button;
    }
    return sg.chatSelectors?.findSendButton?.();
  }

  function disableButton(button) {
    if (!buttonState.has(button)) {
      buttonState.set(button, {
        disabled: button.disabled,
        ariaDisabled: button.getAttribute("aria-disabled"),
        ariaBusy: button.getAttribute("aria-busy"),
      });
    }
    trackedButtons.add(button);
    button.disabled = true;
    button.setAttribute("aria-disabled", "true");
    button.setAttribute("aria-busy", "true");
  }

  function restoreButton(button) {
    const prev = buttonState.get(button);
    if (prev) {
      button.disabled = !!prev.disabled;
      if (prev.ariaDisabled === null) {
        button.removeAttribute("aria-disabled");
      } else {
        button.setAttribute("aria-disabled", prev.ariaDisabled);
      }
      if (prev.ariaBusy === null) {
        button.removeAttribute("aria-busy");
      } else {
        button.setAttribute("aria-busy", prev.ariaBusy);
      }
      buttonState.delete(button);
    } else {
      button.disabled = false;
      button.removeAttribute("aria-disabled");
      button.removeAttribute("aria-busy");
    }
  }

  function show(target = {}) {
    ensureStyles();
    ensureToast();
    const btn = normalizeButton(target.button || target);
    const message =
      typeof target === "string"
        ? target
        : target?.message || DEFAULT_MESSAGE;

    if (textEl) textEl.textContent = message;
    if (toast) toast.dataset.sgVisible = "true";

    if (btn && !trackedButtons.has(btn)) {
      disableButton(btn);
    }

    activeCount += 1;
  }

  function hide() {
    if (activeCount === 0) return;

    activeCount = Math.max(0, activeCount - 1);
    if (activeCount > 0) return;

    trackedButtons.forEach(restoreButton);
    trackedButtons.clear();

    if (toast) {
      toast.dataset.sgVisible = "false";
    }
  }

  sg.loadingState = {
    show,
    hide,
  };
})(typeof window !== "undefined" ? window : globalThis);
