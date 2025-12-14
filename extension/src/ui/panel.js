(function initPanel(root) {
  const sg = (root.SG = root.SG || {});

  const sendListeners = new Set();
  const dismissListeners = new Set();

  function ensurePanel() {
    let panel = document.getElementById("sg-llm-panel");
    if (panel) {
      mountPanel(panel);
      return panel;
    }

    panel = document.createElement("div");
    Object.assign(panel.style, {
      position: "relative",
      zIndex: 10,
      width: "100%",
      maxWidth: "760px",
      background: "rgba(32,33,35,0.97)",
      color: "#ECECF1",
      borderRadius: "18px",
      boxShadow: "0 12px 35px rgba(0,0,0,0.35)",
      padding: "20px 22px 24px",
      fontFamily:
        '"Sohne", "GT Walsheim", "Helvetica Neue", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      display: "none",
      fontSize: "16px",
      lineHeight: "1.55",
      border: "1px solid rgba(255,255,255,0.08)",
      borderLeft: "4px solid #c5c5d2",
      boxSizing: "border-box",
      backdropFilter: "blur(6px)",
    });
    panel.id = "sg-llm-panel";

    const titleRow = document.createElement("div");
    Object.assign(titleRow.style, {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
    });

    const title = document.createElement("div");
    title.id = "sg-llm-title";
    Object.assign(title.style, {
      fontWeight: "700",
      fontSize: "20px",
      marginBottom: "4px",
      letterSpacing: "-0.01em",
    });
    title.textContent = "⚠️ Risk Detected";
    titleRow.appendChild(title);

    panel.appendChild(titleRow);

    const policy = document.createElement("div");
    policy.id = "sg-llm-policy";
    Object.assign(policy.style, {
      opacity: "0.9",
      fontSize: "14px",
      margin: "6px 0 12px",
      color: "#C5C5D2",
      textAlign: "left",
    });
    panel.appendChild(policy);

    const metrics = document.createElement("div");
    metrics.id = "sg-llm-metrics";
    Object.assign(metrics.style, {
      opacity: "0.9",
      fontSize: "13px",
      margin: "0 0 12px",
      color: "#AEB0C3",
    });
    panel.appendChild(metrics);

    const list = document.createElement("div");
    list.id = "sg-llm-list";
    Object.assign(list.style, {
      fontSize: "15px",
      maxHeight: "360px",
      overflow: "auto",
    });
    panel.appendChild(list);

    const actions = document.createElement("div");
    Object.assign(actions.style, {
      display: "flex",
      gap: "10px",
      marginTop: "16px",
      flexWrap: "wrap",
    });

    const btnSendAnyway = document.createElement("button");
    btnSendAnyway.id = "sg-llm-override";
    btnSendAnyway.textContent = "Send anyway";
    btnSendAnyway.dataset.sgPanelButton = "true";
    Object.assign(btnSendAnyway.style, {
      flex: 1,
      border: "none",
      borderRadius: "12px",
      padding: "10px 16px",
      background: "linear-gradient(120deg,#fa5555,#f23f5d)",
      color: "#fff",
      cursor: "pointer",
      fontSize: "15px",
      fontWeight: "600",
      boxShadow: "0 6px 18px rgba(242,63,93,0.35)",
    });

    const btnDismiss = document.createElement("button");
    btnDismiss.textContent = "Dismiss";
    btnDismiss.dataset.sgPanelButton = "true";
    Object.assign(btnDismiss.style, {
      flex: 0,
      borderRadius: "12px",
      padding: "10px 16px",
      background: "transparent",
      color: "#ECECF1",
      cursor: "pointer",
      fontSize: "15px",
      fontWeight: "600",
      border: "1px solid rgba(255,255,255,0.12)",
    });

    actions.appendChild(btnSendAnyway);
    actions.appendChild(btnDismiss);
    panel.appendChild(actions);

    btnDismiss.addEventListener("click", () => {
      hidePanel();
      dismissListeners.forEach((fn) => fn());
    });
    btnSendAnyway.addEventListener("click", () => {
      sendListeners.forEach((fn) => fn());
    });

    mountPanel(panel);

    panel._els = {
      title,
      list,
      policy,
      metrics,
      actions,
      btnSendAnyway,
      btnDismiss,
    };
    return panel;
  }

  function applyInlinePanelStyles(panel) {
    Object.assign(panel.style, {
      position: "relative",
      margin: "0 auto",
      width: "100%",
      maxWidth: "760px",
      left: "unset",
      right: "unset",
      top: "unset",
      bottom: "unset",
    });
  }

  function applyFloatingPanelStyles(panel) {
    Object.assign(panel.style, {
      position: "fixed",
      bottom: "40px",
      right: "40px",
      margin: "0",
      width: "auto",
      maxWidth: "680px",
      left: "unset",
      top: "unset",
    });
  }

  function mountPanel(panel) {
    const fallbackParent = document.body || document.documentElement;

    // Use platform-specific insertion point if available
    const platform = sg.platformRegistry?.getActive?.();
    if (platform && typeof platform.findPanelInsertionPoint === "function") {
      const insertionPoint = platform.findPanelInsertionPoint();

      if (!insertionPoint || !insertionPoint.host) {
        // Fallback to floating panel if no insertion point found
        if (!panel.parentElement) fallbackParent.appendChild(panel);
        applyFloatingPanelStyles(panel);
        return;
      }

      const { host, referenceNode } = insertionPoint;

      // Check if we need to move the anchor
      let anchor = document.getElementById("sg-llm-panel-anchor");
      if (anchor && anchor.parentElement && anchor.parentElement !== host) {
        anchor.parentElement.removeChild(anchor);
        anchor = null;
      } else if (anchor && !anchor.parentElement) {
        anchor = null;
      }

      if (!anchor) {
        anchor = document.createElement("div");
        anchor.id = "sg-llm-panel-anchor";
        Object.assign(anchor.style, {
          width: "100%",
          display: "flex",
          justifyContent: "center",
          marginBottom: "16px",
          marginTop: "4px",
          padding: "0 8px",
          boxSizing: "border-box",
        });
        host.insertBefore(anchor, referenceNode);
      }

      if (panel.parentElement !== anchor) {
        anchor.appendChild(panel);
      }
      applyInlinePanelStyles(panel);
      return;
    }

    // Fallback to old logic if platform doesn't have findPanelInsertionPoint
    const composer = sg.chatSelectors?.findComposer?.();
    if (!composer || !composer.parentElement) {
      if (!panel.parentElement) fallbackParent.appendChild(panel);
      applyFloatingPanelStyles(panel);
      return;
    }

    const form = composer.closest?.("form");
    const host = form?.parentElement || composer.parentElement;
    if (!host) {
      if (!panel.parentElement) fallbackParent.appendChild(panel);
      applyFloatingPanelStyles(panel);
      return;
    }

    let anchor = document.getElementById("sg-llm-panel-anchor");
    if (anchor && anchor.parentElement && anchor.parentElement !== host) {
      anchor.parentElement.removeChild(anchor);
      anchor = null;
    } else if (anchor && !anchor.parentElement) {
      anchor = null;
    }
    if (!anchor) {
      anchor = document.createElement("div");
      anchor.id = "sg-llm-panel-anchor";
      Object.assign(anchor.style, {
        width: "100%",
        display: "flex",
        justifyContent: "center",
        marginBottom: "16px",
        marginTop: "4px",
        padding: "0 8px",
        boxSizing: "border-box",
      });
      host.insertBefore(anchor, form || composer);
    }

    if (panel.parentElement !== anchor) {
      anchor.appendChild(panel);
    }
    applyInlinePanelStyles(panel);
  }

  function renderPanel(result, contextText = "", meta = {}) {
    const panel = ensurePanel();
    mountPanel(panel);
    const {
      title,
      list,
      policy,
      metrics,
      btnSendAnyway,
      btnDismiss,
      actions,
    } = panel._els;
    list.innerHTML = "";

    const { risk_level = "unknown", detected_fields = [] } = result || {};
    const riskLabel =
      risk_level === "high"
        ? "High"
        : risk_level === "medium"
          ? "Medium"
          : risk_level === "low"
            ? "Low"
            : "Unknown";

    title.textContent = `⚠️ ${riskLabel} Risk Detected`;

    const baseText = contextText || "";

    // Display remediation message from backend
    const remediation = result?.remediation || "";
    policy.innerHTML = remediation
      ? `<div style="margin-bottom:6px;">${remediation}</div>`
      : "";

    // Show timing if provided
    const durationMs = meta?.durationMs;
    if (typeof durationMs === "number" && isFinite(durationMs)) {
      const formatted =
        durationMs >= 1000
          ? `${(durationMs / 1000).toFixed(1)}s`
          : `${Math.round(durationMs)}ms`;
      metrics.textContent = `Analysis completed in ${formatted}`;
      metrics.style.display = "block";
    } else {
      metrics.textContent = "";
      metrics.style.display = "none";
    }

    const accentRisk =
      risk_level === "high"
        ? "#fa5a5a"
        : risk_level === "medium"
          ? "#ffd369"
          : risk_level === "low"
            ? "#10a37f"
            : "#c5c5d2";
    panel.style.borderLeft = `4px solid ${accentRisk}`;

    if (detected_fields.length) {
      const groups = new Map();
      for (const detected of detected_fields) {
        const fieldName = detected.field || "UNKNOWN";
        const value = (detected.value || "").trim();
        if (!value) continue;

        const pos = baseText
          ? baseText.indexOf(value)
          : Number.POSITIVE_INFINITY;
        const key = fieldName;
        let group = groups.get(key);
        if (!group) {
          group = {
            field: fieldName,
            source: detected.source || "Unknown",
            risk: sg.riskUtils.classifyField(detected),
            _seen: new Map(),
            minIdx: Number.POSITIVE_INFINITY,
          };
          groups.set(key, group);
        }

        const prev = group._seen.get(value);
        const minPos = pos === -1 ? Number.POSITIVE_INFINITY : pos;
        if (prev === undefined || minPos < prev) {
          group._seen.set(value, minPos);
        }
      }

      for (const group of groups.values()) {
        group.items = Array.from(group._seen.entries())
          .map(([value, pos]) => ({ value, pos }))
          .sort((a, b) => a.pos - b.pos);
        group.minIdx = group.items.length
          ? group.items[0].pos
          : Number.POSITIVE_INFINITY;
        delete group._seen;
      }

      const ordered = Array.from(groups.values()).sort(
        sg.riskUtils.compareFieldGroups,
      );

      for (const group of ordered) {
        const item = document.createElement("div");
        item.style.margin = "10px 0";
        item.style.padding = "10px 12px";
        item.style.borderRadius = "12px";
        item.style.background = "rgba(255,255,255,0.02)";

        const head = document.createElement("div");
        head.style.display = "flex";
        head.style.justifyContent = "space-between";
        head.style.alignItems = "center";
        head.style.fontWeight = "600";
        head.style.fontSize = "15px";
        const accent =
          group.risk === "high"
            ? "#ff8c8c"
            : group.risk === "medium"
              ? "#ffd666"
              : "#7de6a3";

        const fieldName = document.createElement("span");
        fieldName.style.color = accent;
        fieldName.textContent = group.field;

        const sourceLabel = document.createElement("span");
        sourceLabel.style.color = "#9fa0b3";
        sourceLabel.style.fontWeight = "400";
        sourceLabel.style.fontSize = "13px";
        sourceLabel.style.marginLeft = "8px";
        sourceLabel.textContent = `Source: ${group.source}`;

        head.appendChild(fieldName);
        head.appendChild(sourceLabel);

        const body = document.createElement("div");
        body.style.opacity = "0.9";
        body.style.fontSize = "14px";
        body.style.marginTop = "4px";
        body.style.color = "#ECECF1";
        body.style.textAlign = "left";
        const valuesOrdered = group.items.map((it) => it.value);
        body.textContent =
          valuesOrdered.slice(0, 4).join(", ") +
          (valuesOrdered.length > 4 ? "…" : "");

        item.appendChild(head);
        item.appendChild(body);
        list.appendChild(item);
      }
    } else {
      const empty = document.createElement("div");
      empty.textContent = "No sensitive fields detected.";
      empty.style.padding = "12px";
      empty.style.borderRadius = "10px";
      empty.style.background = "rgba(255,255,255,0.02)";
      empty.style.color = "#9fa0b3";
      list.appendChild(empty);
    }

    if (actions && btnDismiss && btnSendAnyway) {
      if (!actions.contains(btnSendAnyway))
        actions.insertBefore(btnSendAnyway, btnDismiss);
      btnSendAnyway.style.display = "inline-block";
      btnDismiss.style.display = "inline-block";
      btnSendAnyway.style.flex = "1";
      btnDismiss.style.flex = "0";
      actions.style.justifyContent = "flex-start";
      actions.style.gap = "12px";
    }

    panel.style.display = "block";
  }

  function hidePanel() {
    const panel = document.getElementById("sg-llm-panel");
    if (panel) panel.style.display = "none";
  }

  function onSendAnyway(callback) {
    if (typeof callback === "function") sendListeners.add(callback);
  }

  function onDismiss(callback) {
    if (typeof callback === "function") dismissListeners.add(callback);
  }

  sg.panel = {
    ensure: ensurePanel,
    render: renderPanel,
    hide: hidePanel,
    onSendAnyway,
    onDismiss,
  };
})(typeof window !== "undefined" ? window : globalThis);
