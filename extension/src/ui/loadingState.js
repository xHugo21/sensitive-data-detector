(function initLoadingState(root) {
  const sg = (root.SG = root.SG || {});

  const STYLE_ID = "sg-global-loading-style";
  const TOAST_ID = "sg-global-loading-chip";
  const PROGRESS_TOAST_ID = "sg-global-progress-chip";
  const DEFAULT_MESSAGE = "Analyzing message...";
  const DEFAULT_BG = "rgba(17, 24, 39, 0.92)";
  const SUCCESS_BG = "#16a34a";
  const ERROR_BG = "#dc2626";
  const PROGRESS_BG = "rgba(30, 41, 59, 0.92)";
  const DEFAULT_ERROR_MESSAGE = "Analysis failed - Backend Unreachable";
  let activeCount = 0;
  const trackedButtons = new Set();
  const buttonState = new WeakMap();
  let toast = null;
  let textEl = null;
  let spinnerEl = null;
  let hideTimer = null;
  let progressToast = null;
  let progressTextEl = null;
  let progressTimer = null;

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

      #${PROGRESS_TOAST_ID} {
        position: fixed;
        right: 16px;
        bottom: 56px;
        display: none;
        align-items: center;
        gap: 6px;
        padding: 8px 12px;
        background: ${PROGRESS_BG};
        color: #f8fafc;
        border-radius: 999px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        z-index: 2147483646;
        font-size: 12px;
        line-height: 1.3;
        letter-spacing: 0.01em;
        opacity: 0;
        transform: translateY(6px);
      }
      #${PROGRESS_TOAST_ID}[data-sg-visible="true"] {
        display: inline-flex;
      }
      #${PROGRESS_TOAST_ID}.sg-progress-animate {
        animation: sg-progress-toast 1.6s ease forwards;
      }
      @keyframes sg-progress-toast {
        0%   { opacity: 0; transform: translateY(6px); }
        18%  { opacity: 1; transform: translateY(0); }
        80%  { opacity: 1; transform: translateY(0); }
        100% { opacity: 0; transform: translateY(-6px); }
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
    spinner.style.display = "inline-block";

    textEl = document.createElement("span");
    textEl.className = "sg-loading-text";
    textEl.textContent = DEFAULT_MESSAGE;

    el.appendChild(spinner);
    el.appendChild(textEl);
    document.body.appendChild(el);
    toast = el;
    spinnerEl = spinner;
    return toast;
  }

  function ensureProgressToast() {
    if (progressToast) return progressToast;
    const el = document.createElement("div");
    el.id = PROGRESS_TOAST_ID;
    el.setAttribute("role", "status");
    el.setAttribute("aria-live", "polite");

    progressTextEl = document.createElement("span");
    progressTextEl.className = "sg-progress-text";
    progressTextEl.textContent = "Step finished";

    el.appendChild(progressTextEl);
    document.body.appendChild(el);
    progressToast = el;
    return progressToast;
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
    if (hideTimer) {
      clearTimeout(hideTimer);
      hideTimer = null;
    }
    const btn = normalizeButton(target.button || target);
    const message =
      typeof target === "string" ? target : target?.message || DEFAULT_MESSAGE;

    if (toast) {
      toast.style.background = DEFAULT_BG;
    }
    if (spinnerEl) {
      spinnerEl.style.display = "inline-block";
    }
    if (textEl) textEl.textContent = message;
    if (toast) toast.dataset.sgVisible = "true";

    if (btn && !trackedButtons.has(btn)) {
      disableButton(btn);
    }

    activeCount += 1;
  }

  function update(message) {
    if (!message || activeCount === 0) return;
    ensureStyles();
    ensureToast();
    if (hideTimer) {
      clearTimeout(hideTimer);
      hideTimer = null;
    }
    if (toast) {
      toast.style.background = DEFAULT_BG;
      toast.dataset.sgVisible = "true";
    }
    if (spinnerEl) {
      spinnerEl.style.display = "inline-block";
    }
    if (textEl) textEl.textContent = message;
  }

  function flashProgress(message, opts = {}) {
    if (!message || activeCount === 0) return;
    ensureStyles();
    ensureProgressToast();
    if (progressTimer) {
      clearTimeout(progressTimer);
      progressTimer = null;
    }
    if (progressToast) {
      progressToast.dataset.sgVisible = "true";
      progressToast.classList.remove("sg-progress-animate");
      void progressToast.offsetHeight;
      progressToast.classList.add("sg-progress-animate");
    }
    if (progressTextEl) progressTextEl.textContent = message;
    const durationMs =
      typeof opts.durationMs === "number" && isFinite(opts.durationMs)
        ? opts.durationMs
        : 1600;
    progressTimer = setTimeout(() => {
      if (progressToast) {
        progressToast.dataset.sgVisible = "false";
      }
    }, durationMs);
  }

  function getErrorMessage(error) {
    if (!error) return DEFAULT_ERROR_MESSAGE;
    if (typeof error === "string") return error;
    if (
      typeof error.displayMessage === "string" &&
      error.displayMessage.trim()
    ) {
      return error.displayMessage;
    }
    if (typeof error.message === "string" && error.message.trim()) {
      const raw = error.message.trim();
      return raw.startsWith("Analysis") ? raw : `Analysis failed - ${raw}`;
    }
    return DEFAULT_ERROR_MESSAGE;
  }

  function hide(opts = {}) {
    if (activeCount === 0) return;

    activeCount = Math.max(0, activeCount - 1);
    if (activeCount > 0) return;

    trackedButtons.forEach(restoreButton);
    trackedButtons.clear();

    if (toast) {
      const { message, durationMs, panelShown, error } = opts || {};
      const showCompletion = !panelShown;
      const hasError = !!error;

      let finalMessage = message;
      if (
        showCompletion &&
        !finalMessage &&
        typeof durationMs === "number" &&
        isFinite(durationMs)
      ) {
        finalMessage =
          durationMs >= 1000
            ? `Analysis completed in ${(durationMs / 1000).toFixed(1)}s`
            : `Analysis completed in ${Math.round(durationMs)}ms`;
      }

      if (hasError && textEl) {
        textEl.textContent = getErrorMessage(error);
        if (spinnerEl) spinnerEl.style.display = "none";
        toast.style.background = ERROR_BG;
        toast.dataset.sgVisible = "true";
        const persistMs = opts.persistMs ?? 3000;
        hideTimer = setTimeout(() => {
          toast.dataset.sgVisible = "false";
          toast.style.background = DEFAULT_BG;
          if (spinnerEl) spinnerEl.style.display = "inline-block";
        }, persistMs);
      } else if (showCompletion && finalMessage && textEl) {
        textEl.textContent = finalMessage;
        if (spinnerEl) spinnerEl.style.display = "none";
        toast.style.background = SUCCESS_BG;
        toast.dataset.sgVisible = "true";
        const persistMs = opts.persistMs ?? 2200;
        hideTimer = setTimeout(() => {
          toast.dataset.sgVisible = "false";
          toast.style.background = DEFAULT_BG;
          if (spinnerEl) spinnerEl.style.display = "inline-block";
        }, persistMs);
      } else {
        toast.dataset.sgVisible = "false";
        toast.style.background = DEFAULT_BG;
        if (spinnerEl) spinnerEl.style.display = "inline-block";
      }
    }
  }

  sg.loadingState = {
    show,
    update,
    flashProgress,
    hide,
  };
})(typeof window !== "undefined" ? window : globalThis);
