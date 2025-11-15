(function initPanel(root) {
  const sg = root.SG = root.SG || {};

  const sendListeners = new Set();
  const dismissListeners = new Set();

  function ensurePanel() {
    let panel = document.getElementById("sg-llm-panel");
    if (panel) {
      if (!panel.dataset.dragInit) {
        primePanelPosition(panel);
        enablePanelDrag(panel);
      }
      return panel;
    }

    panel = document.createElement("div");
    Object.assign(panel.style, {
      position: "fixed",
      bottom: "40px",
      right: "40px",
      zIndex: 999999,
      maxWidth: "680px",
      background: "rgba(20,20,20,.98)",
      color: "#fff",
      borderRadius: "24px",
      boxShadow: "0 16px 50px rgba(0,0,0,.7)",
      padding: "28px",
      fontFamily: "system-ui, sans-serif",
      display: "none",
      fontSize: "18px",
      lineHeight: "1.6",
      borderLeft: "10px solid #666"
    });
    panel.id = "sg-llm-panel";

    const titleRow = document.createElement("div");
    Object.assign(titleRow.style, { display: "flex", justifyContent: "space-between", alignItems: "center" });

    const title = document.createElement("div");
    title.id = "sg-llm-title";
    Object.assign(title.style, { fontWeight: "900", fontSize: "26px", marginBottom: "8px" });
    title.textContent = "⚠️ CUIDADO: Riesgo Detectado";
    titleRow.appendChild(title);

    const originBadge = document.createElement("div");
    originBadge.id = "sg-llm-origin";
    originBadge.textContent = "Origen: Usuario";
    Object.assign(originBadge.style, {
      background: "#2a2a2a", padding: "6px 10px", borderRadius: "999px",
      fontSize: "14px", marginLeft: "12px"
    });
    titleRow.appendChild(originBadge);
    panel.appendChild(titleRow);

    const policy = document.createElement("div");
    policy.id = "sg-llm-policy";
    Object.assign(policy.style, { opacity: "0.95", fontSize: "15px", margin: "6px 0 12px" });
    panel.appendChild(policy);

    const header = document.createElement("div");
    header.id = "sg-llm-header";
    Object.assign(header.style, { fontWeight: "800", margin: "12px 0 6px", fontSize: "18px" });
    header.textContent = "Datos sensibles detectados:";
    panel.appendChild(header);

    const list = document.createElement("div");
    list.id = "sg-llm-list";
    Object.assign(list.style, { fontSize: "16px", maxHeight: "360px", overflow: "auto" });
    panel.appendChild(list);

    const actions = document.createElement("div");
    Object.assign(actions.style, { display: "flex", gap: "12px", marginTop: "16px" });

    const btnSendAnyway = document.createElement("button");
    btnSendAnyway.id = "sg-llm-override";
    btnSendAnyway.textContent = "Enviar de todos modos";
    Object.assign(btnSendAnyway.style, {
      flex: 1, border: "none", borderRadius: "14px", padding: "14px 16px",
      background: "#5a5a5a", color: "#fff", cursor: "pointer", fontSize: "16px", fontWeight: "700"
    });

    const btnDismiss = document.createElement("button");
    btnDismiss.textContent = "Ocultar";
    Object.assign(btnDismiss.style, {
      flex: 0, border: "none", borderRadius: "14px", padding: "14px 16px",
      background: "#2a2a2a", color: "#fff", cursor: "pointer", fontSize: "16px", fontWeight: "700"
    });

    actions.appendChild(btnSendAnyway);
    actions.appendChild(btnDismiss);
    panel.appendChild(actions);
    document.documentElement.appendChild(panel);

    btnDismiss.addEventListener("click", () => {
      hidePanel();
      dismissListeners.forEach(fn => fn());
    });
    btnSendAnyway.addEventListener("click", () => {
      sendListeners.forEach(fn => fn());
    });

    primePanelPosition(panel);
    enablePanelDrag(panel);

    panel._els = { title, list, originBadge, policy, header, actions, btnSendAnyway, btnDismiss };
    return panel;
  }

  function primePanelPosition(panel) {
    const r = panel.getBoundingClientRect();
    panel.style.left = `${Math.max(0, Math.min(window.innerWidth - r.width, r.left))}px`;
    panel.style.top = `${Math.max(0, Math.min(window.innerHeight - r.height, r.top))}px`;
    panel.style.right = "unset";
    panel.style.bottom = "unset";
  }

  function enablePanelDrag(panel) {
    if (panel.dataset.dragInit === "1") return;
    panel.dataset.dragInit = "1";

    try {
      const saved = JSON.parse(localStorage.getItem("sgPanelGeom") || "{}");
      if (typeof saved.x === "number" && typeof saved.y === "number") {
        panel.style.left = saved.x + "px";
        panel.style.top = saved.y + "px";
        panel.style.right = "unset";
        panel.style.bottom = "unset";
        panel.dataset.freed = "1";
      }
    } catch (_) {}

    const handle = panel.querySelector("#sg-llm-title") || panel;
    handle.style.cursor = "grab";

    let dragging = false;
    let offX = 0;
    let offY = 0;
    let raf = null;

    const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
    const saveGeom = () => {
      const rect = panel.getBoundingClientRect();
      localStorage.setItem("sgPanelGeom", JSON.stringify({ x: rect.left, y: rect.top }));
    };

    const onMove = (event) => {
      if (!dragging) return;
      if (raf) cancelAnimationFrame(raf);
      const point = event.touches ? event.touches[0] : event;
      if (!point) return;

      raf = requestAnimationFrame(() => {
        const rect = panel.getBoundingClientRect();
        let nx = point.clientX - offX;
        let ny = point.clientY - offY;
        nx = clamp(nx, 0, Math.max(0, window.innerWidth - rect.width));
        ny = clamp(ny, 0, Math.max(0, window.innerHeight - rect.height));
        Object.assign(panel.style, { left: nx + "px", top: ny + "px", right: "unset", bottom: "unset" });
      });
    };

    const endDrag = () => {
      if (!dragging) return;
      dragging = false;
      document.body.style.userSelect = "";
      handle.style.cursor = "grab";
      saveGeom();
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("touchmove", onMove, { passive: false });
    };

    handle.addEventListener("mousedown", (e) => {
      if (e.button !== 0) return;
      if (e.target.closest("button,a")) return;
      const rect = panel.getBoundingClientRect();
      dragging = true;
      document.body.style.userSelect = "none";
      handle.style.cursor = "grabbing";
      offX = e.clientX - rect.left;
      offY = e.clientY - rect.top;
      panel.dataset.freed = "1";
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", endDrag, { once: true });
    });

    handle.addEventListener("touchstart", (e) => {
      const t = e.touches && e.touches[0];
      if (!t) return;
      const rect = panel.getBoundingClientRect();
      dragging = true;
      document.body.style.userSelect = "none";
      handle.style.cursor = "grabbing";
      offX = t.clientX - rect.left;
      offY = t.clientY - rect.top;
      window.addEventListener("touchmove", onMove, { passive: false });
      window.addEventListener("touchend", endDrag, { once: true });
    });

    window.addEventListener("resize", () => {
      const rect = panel.getBoundingClientRect();
      const nx = clamp(rect.left, 0, Math.max(0, window.innerWidth - rect.width));
      const ny = clamp(rect.top, 0, Math.max(0, window.innerHeight - rect.height));
      Object.assign(panel.style, { left: nx + "px", top: ny + "px", right: "unset", bottom: "unset" });
      saveGeom();
    });
  }

  function renderPanel(result, origin = "Usuario", contextText = "") {
    const panel = ensurePanel();
    const { title, list, originBadge, policy, header, btnSendAnyway, btnDismiss, actions } = panel._els;
    list.innerHTML = "";

    const { risk_level = "Unknown", detected_fields = [] } = result || {};
    const riskEs =
      risk_level === "High" ? "Alto" :
      risk_level === "Medium" ? "Medio" :
      risk_level === "Low" ? "Bajo" : "Desconocido";

    title.textContent = `⚠️ CUIDADO: Riesgo ${riskEs} Detectado`;
    originBadge.textContent = `Origen: ${origin}`;

    const baseText = contextText || "";

    const policyUsuario = `
      <div style="margin-bottom:6px;">
        Según la <b>política de privacidad de OpenAI</b>, tus datos sensibles pueden compartirse con 
        <b>proveedores</b>, <b>afiliadas</b>, <b>autoridades</b> o en <b>transferencias de negocio</b>. 
        También pueden acceder <b>administradores corporativos</b> y los <b>terceros</b> con los que decidas compartir. 
        Parte del contenido puede conservarse y usarse para <b>mejorar los servicios/modelos</b>. 
        Consulta la política completa 
        <a href="https://openai.com/es-ES/policies/row-privacy-policy/" target="_blank" style="color:#3fa9ff;text-decoration:underline;">aquí</a>.
      </div>`;
    const policyRespuesta = `
      <div style="margin-bottom:6px;">
        ⚠️ <b>Se han detectado campos sensibles en la respuesta del modelo.</b><br>
        Si decides usar esta información fuera de ChatGPT, ten en cuenta los riesgos de compartirla. 
        Consulta la <a href="https://openai.com/es-ES/policies/row-privacy-policy/" target="_blank" style="color:#3fa9ff;text-decoration:underline;">política de privacidad aquí</a>.
      </div>`;
    policy.innerHTML = origin === "Respuesta" ? policyRespuesta : policyUsuario;

    const accentRisk =
      risk_level === "High" ? "#ff4d4d" :
      risk_level === "Medium" ? "#ffcc00" :
      risk_level === "Low" ? "#66cc66" : "#666";
    const accentOrigin = origin === "Respuesta" ? "#3fa9ff" : accentRisk;
    panel.style.borderLeft = `10px solid ${accentOrigin}`;

    header.textContent =
      origin === "Respuesta"
        ? "Campos sensibles detectados en la respuesta del modelo:"
        : "Datos sensibles detectados:";

    if (detected_fields.length) {
      const groups = new Map();
      for (const detected of detected_fields) {
        const fieldName = detected.field || "UNKNOWN";
        const value = (detected.value || "").trim();
        if (!value) continue;

        const pos = baseText ? baseText.indexOf(value) : Number.POSITIVE_INFINITY;
        const key = fieldName;
        let group = groups.get(key);
        if (!group) {
          group = { field: fieldName, risk: sg.riskUtils.classifyField(fieldName), _seen: new Map(), minIdx: Number.POSITIVE_INFINITY };
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
        group.minIdx = group.items.length ? group.items[0].pos : Number.POSITIVE_INFINITY;
        delete group._seen;
      }

      const ordered = Array.from(groups.values()).sort(sg.riskUtils.compareFieldGroups);

      for (const group of ordered) {
        const item = document.createElement("div");
        item.style.margin = "12px 0";

        const head = document.createElement("div");
        head.style.fontWeight = "800";
        head.style.fontSize = "18px";
        head.style.textDecoration = "underline";
        head.style.textDecorationThickness = "2px";
        head.style.textUnderlineOffset = "2px";
        head.style.textDecorationColor =
          group.risk === "high" ? "#ff4d4d" : (group.risk === "medium" ? "#ffcc00" : "#66cc66");
        head.style.color = head.style.textDecorationColor;
        head.textContent = group.field;

        const body = document.createElement("div");
        body.style.opacity = "0.98";
        body.style.fontSize = "16px";
        body.style.marginTop = "2px";
        const valuesOrdered = group.items.map(it => it.value);
        body.textContent = valuesOrdered.slice(0, 4).join(", ") + (valuesOrdered.length > 4 ? "…" : "");

        item.appendChild(head);
        item.appendChild(body);
        list.appendChild(item);
      }
    } else {
      const empty = document.createElement("div");
      empty.textContent = "No se detectaron campos sensibles.";
      list.appendChild(empty);
    }

    if (actions && btnDismiss && btnSendAnyway) {
      if (origin === "Usuario") {
        if (!actions.contains(btnSendAnyway)) actions.insertBefore(btnSendAnyway, btnDismiss);
        btnSendAnyway.style.display = "inline-block";
        btnDismiss.style.display = "inline-block";
        btnSendAnyway.style.flex = "1";
        btnDismiss.style.flex = "0";
        actions.style.justifyContent = "flex-start";
        actions.style.gap = "12px";
      } else {
        if (actions.contains(btnSendAnyway)) actions.removeChild(btnSendAnyway);
        btnDismiss.style.display = "inline-block";
        btnDismiss.style.flex = "1";
        actions.style.justifyContent = "stretch";
        actions.style.gap = "0";
      }
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
    onDismiss
  };
})(typeof window !== "undefined" ? window : globalThis);
