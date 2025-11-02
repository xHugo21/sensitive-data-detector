// ==== Config ====
const API_BASE = "http://127.0.0.1:8000";
const DEFAULT_MODE = "Zero-shot";

// ==== Categorías ====
const HIGH_FIELDS = new Set([
  "PASSWORD","CREDENTIALS","SSN","DNI","PASSPORTNUMBER","CREDITCARDNUMBER","IP","IPV4","IPV6","MAC",
  "CREDITCARDCVV","ACCOUNTNUMBER","IBAN","PIN","GENETICDATA","BIOMETRICDATA","STREET","VEHICLEVIN",
  "HEALTHDATA","CRIMINALRECORD","CONFIDENTIALDOC","LITECOINADDRESS","BITCOINADDRESS","ETHEREUMADDRESS","PHONEIMEI"
]);
const MEDIUM_FIELDS = new Set([
  "EMAIL","PHONENUMBER","URL","CLIENTDATA","EMPLOYEEDATA","SALARYDETAILS","COMPANYNAME","JOBTITLE","JOBTYPE","JOBAREA",
  "ACCOUNTNAME","PROJECTNAME","CODENAME","EDUCATIONHISTORY","CV","SOCIALMEDIAHANDLE","SECONDARYADDRESS","CITY","STATE",
  "COUNTY","ZIPCODE","BUILDINGNUMBER","USERAGENT","VEHICLEVRM","NEARBYGPSCOORDINATE","BIC","MASKEDNUMBER","AMOUNT",
  "CURRENCY","CURRENCYSYMBOL","CURRENCYNAME","CURRENCYCODE","CREDITCARDISSUER","USERNAME","INFRASTRUCTURE"
]);

// ==== Estado global de control de alertas ====
let overrideOnce = false;            // permitir enviar pese a riesgo alto
let pendingResponseAlert = false;    // mostrar alerta de respuesta solo si el usuario aceptó enviar
let suppressUserAlerts = false;      // silenciar paneles de origen "Usuario" tras enviar hasta terminar análisis de respuesta
const analyzedNodes = new WeakSet();
const inFlightAnalyze = new WeakSet();

// ==== UI panel ====
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

  // --- Título + badge
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

  // --- Texto política + header + lista
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

  // --- Acciones
  const actions = document.createElement("div");
  Object.assign(actions.style, { display: "flex", gap: "12px", marginTop: "16px" });

  // Botón "Enviar de todos modos" (solo debe mostrarse para origen Usuario)
  const btnSendAnyway = document.createElement("button");
  btnSendAnyway.id = "sg-llm-override";
  btnSendAnyway.textContent = "Enviar de todos modos";
  Object.assign(btnSendAnyway.style, {
    flex: 1, border: "none", borderRadius: "14px", padding: "14px 16px",
    background: "#5a5a5a", color: "#fff", cursor: "pointer", fontSize: "16px", fontWeight: "700"
  });

  // Botón "Ocultar"
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

  // Guarda referencias directas en el propio panel
  panel._actions = actions;
  panel._btnSend = btnSendAnyway;
  panel._btnDismiss = btnDismiss;

  // Eventos
  btnDismiss.addEventListener("click", () => { panel.style.display = "none"; });
  btnSendAnyway.addEventListener("click", async () => {
    pendingResponseAlert = true;
    suppressUserAlerts = true;   // silencia paneles de Usuario hasta terminar análisis de respuesta
    overrideOnce = true;
    const composer = findComposer();
    const btn = findSendButton();
    if (btn) btn.click();
    else if (composer) composer.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    setTimeout(() => (overrideOnce = false), 1500);
    panel.style.display = "none";
  });

  // Posición/movimiento
  primePanelPosition(panel);
  enablePanelDrag(panel);

  return panel;
}


// Convierte posición inicial anclada a bottom/right en coordenadas left/top
function primePanelPosition(panel) {
  const r = panel.getBoundingClientRect();
  panel.style.left   = `${Math.max(0, Math.min(window.innerWidth  - r.width,  r.left))}px`;
  panel.style.top    = `${Math.max(0, Math.min(window.innerHeight - r.height, r.top ))}px`;
  panel.style.right  = "unset";
  panel.style.bottom = "unset";
}

// Solo mover (drag), sin resize
function enablePanelDrag(panel) {
  if (panel.dataset.dragInit === "1") return;
  panel.dataset.dragInit = "1";

  // Restaurar posición guardada (si existe)
  try {
    const saved = JSON.parse(localStorage.getItem("sgPanelGeom") || "{}");
    if (typeof saved.x === "number" && typeof saved.y === "number") {
      panel.style.left   = saved.x + "px";
      panel.style.top    = saved.y + "px";
      panel.style.right  = "unset";
      panel.style.bottom = "unset";
      panel.dataset.freed = "1";
    }
  } catch {}

  const handle = panel.querySelector("#sg-llm-title") || panel;
  handle.style.cursor = "grab";

  let dragging = false;
  let offX = 0, offY = 0;
  let raf = null;

  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const saveGeom = () => {
    const r = panel.getBoundingClientRect();
    localStorage.setItem("sgPanelGeom", JSON.stringify({ x: r.left, y: r.top }));
  };

  const onMove = (e) => {
    if (!dragging) return;
    if (raf) cancelAnimationFrame(raf);
    const p = e.touches ? e.touches[0] : e;
    if (!p) return;

    raf = requestAnimationFrame(() => {
      const r = panel.getBoundingClientRect();
      let nx = p.clientX - offX;
      let ny = p.clientY - offY;
      nx = clamp(nx, 0, Math.max(0, window.innerWidth  - r.width));
      ny = clamp(ny, 0, Math.max(0, window.innerHeight - r.height));
      panel.style.left   = nx + "px";
      panel.style.top    = ny + "px";
      panel.style.right  = "unset";
      panel.style.bottom = "unset";
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
    if (e.target.closest("button,a")) return; // no arrastrar si clic en botones/enlaces del título
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

  // Soporte táctil
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

  // Mantener dentro del viewport si cambia el tamaño de la ventana
  window.addEventListener("resize", () => {
    const r = panel.getBoundingClientRect();
    const nx = clamp(r.left, 0, Math.max(0, window.innerWidth  - r.width));
    const ny = clamp(r.top,  0, Math.max(0, window.innerHeight - r.height));
    panel.style.left = nx + "px";
    panel.style.top  = ny + "px";
    panel.style.right  = "unset";
    panel.style.bottom = "unset";
    saveGeom();
  });
}

function renderPanel(result, origin = "Usuario", contextText = null) {
  if (origin === "Usuario" && suppressUserAlerts) return;

  const panel = ensurePanel();
  const title = panel.querySelector("#sg-llm-title");
  const list = panel.querySelector("#sg-llm-list");
  const originBadge = panel.querySelector("#sg-llm-origin");
  const policy = panel.querySelector("#sg-llm-policy");
  const header = panel.querySelector("#sg-llm-header");
  list.innerHTML = "";

  const { risk_level = "Unknown", detected_fields = [] } = result || {};
  const riskEs =
    risk_level === "High"   ? "Alto" :
    risk_level === "Medium" ? "Medio" :
    risk_level === "Low"    ? "Bajo"  : "Desconocido";

  title.textContent = `⚠️ CUIDADO: Riesgo ${riskEs} Detectado`;
  originBadge.textContent = `Origen: ${origin}`;

  // Texto base para ordenar por aparición
  let baseText = contextText || "";
  if (!baseText && origin === "Usuario") {
    const comp = findComposer();
    baseText = comp ? getComposerText(comp) : "";
  }
  baseText = baseText || "";

  // Política breve
  const policyHTMLUsuario = `
    <div style="margin-bottom:6px;">
      Según la <b>política de privacidad de OpenAI</b>, tus datos sensibles pueden compartirse con 
      <b>proveedores</b>, <b>afiliadas</b>, <b>autoridades</b> o en <b>transferencias de negocio</b>. 
      También pueden acceder <b>administradores corporativos</b> y los <b>terceros</b> con los que decidas compartir. 
      Parte del contenido puede conservarse y usarse para <b>mejorar los servicios/modelos</b>. 
      Consulta la política completa 
      <a href="https://openai.com/es-ES/policies/row-privacy-policy/" target="_blank" style="color:#3fa9ff;text-decoration:underline;">aquí</a>.
    </div>`;
  const policyHTMLRespuesta = `
    <div style="margin-bottom:6px;">
      ⚠️ <b>Se han detectado campos sensibles en la respuesta del modelo.</b><br>
      Si decides usar esta información fuera de ChatGPT, ten en cuenta los riesgos de compartirla. 
      Consulta la <a href="https://openai.com/es-ES/policies/row-privacy-policy/" target="_blank" style="color:#3fa9ff;text-decoration:underline;">política de privacidad aquí</a>.
    </div>`;
  policy.innerHTML = origin === "Respuesta" ? policyHTMLRespuesta : policyHTMLUsuario;

  // Colores de acento
  const accentRisk =
    risk_level === "High"   ? "#ff4d4d" :
    risk_level === "Medium" ? "#ffcc00" :
    risk_level === "Low"    ? "#66cc66" : "#666";
  const accentOrigin = origin === "Respuesta" ? "#3fa9ff" : accentRisk;
  panel.style.borderLeft = `10px solid ${accentOrigin}`;

  header.textContent =
    origin === "Respuesta"
      ? "Campos sensibles detectados en la respuesta del modelo:"
      : "Datos sensibles detectados:";

  // Renderizar lista de campos detectados
  if (detected_fields.length) {
    const groups = new Map();
    const riskOrder = { high: 0, medium: 1, low: 2 };

    for (const f of detected_fields) {
      const field = f.field || "UNKNOWN";
      const value = (f.value || "").trim();
      if (!value) continue;

      const upper = field.toUpperCase();
      const risk  = HIGH_FIELDS.has(upper) ? "high" : (MEDIUM_FIELDS.has(upper) ? "medium" : "low");

      let pos = Number.POSITIVE_INFINITY;
      if (baseText) {
        const idx = baseText.indexOf(value);
        if (idx !== -1) pos = idx;
      }

      let g = groups.get(field);
      if (!g) {
        g = { field, risk, _seen: new Map(), items: [], minIdx: Number.POSITIVE_INFINITY };
        groups.set(field, g);
      }
      const prev = g._seen.get(value);
      if (prev === undefined || pos < prev) g._seen.set(value, pos);
    }

    for (const g of groups.values()) {
      g.items = Array.from(g._seen.entries())
        .map(([value, pos]) => ({ value, pos }))
        .sort((a, b) => a.pos - b.pos);
      g.minIdx = g.items.length ? g.items[0].pos : Number.POSITIVE_INFINITY;
      delete g._seen;
    }

    const ordered = Array.from(groups.values()).sort((a, b) => {
      const r = riskOrder[a.risk] - riskOrder[b.risk];
      if (r !== 0) return r;
      return (a.minIdx - b.minIdx) || a.field.localeCompare(b.field);
    });

    for (const g of ordered) {
      const item = document.createElement("div");
      item.style.margin = "12px 0";

      const head = document.createElement("div");
      head.style.fontWeight = "800";
      head.style.fontSize = "18px";
      head.style.textDecoration = "underline";
      head.style.textDecorationThickness = "2px";
      head.style.textUnderlineOffset = "2px";
      head.style.textDecorationColor =
        g.risk === "high" ? "#ff4d4d" : (g.risk === "medium" ? "#ffcc00" : "#66cc66");
      head.style.color = head.style.textDecorationColor;
      head.textContent = g.field;

      const body = document.createElement("div");
      body.style.opacity = "0.98";
      body.style.fontSize = "16px";
      body.style.marginTop = "2px";
      const valuesOrdered = g.items.map(it => it.value);
      body.textContent = valuesOrdered.slice(0, 4).join(", ") + (valuesOrdered.length > 4 ? "…" : "");

      item.appendChild(head);
      item.appendChild(body);
      list.appendChild(item);
    }
  } else {
    const p = document.createElement("div");
    p.textContent = "No se detectaron campos sensibles.";
    list.appendChild(p);
  }

  // Resaltado en el editor si es Usuario
  if (origin === "Usuario") {
    const comp = findComposer();
    if (comp) applyHighlights(comp, detected_fields, "user");
  }

  // --- Mostrar/ocultar botones según el origen ---
  const actions    = panel._actions;
  const btnSend    = panel._btnSend;
  const btnDismiss = panel._btnDismiss;

  if (actions && btnDismiss && btnSend) {
    if (origin === "Usuario") {
      if (!actions.contains(btnSend)) actions.insertBefore(btnSend, btnDismiss);
      btnSend.style.display = "inline-block";
      btnDismiss.style.display = "inline-block";
      btnSend.style.flex = "1";
      btnDismiss.style.flex = "0";
      actions.style.justifyContent = "flex-start";
      actions.style.gap = "12px";
    } else {
      if (actions.contains(btnSend)) actions.removeChild(btnSend);
      btnDismiss.style.display = "inline-block";
      btnDismiss.style.flex = "1";
      actions.style.justifyContent = "stretch";
      actions.style.gap = "0";
    }
  }

  panel.style.display = "block";
}







// ==== CSS Custom Highlight API (resaltado/ subrayado sin overlays) ====
function ensureHighlightCSS() {
  const old = document.getElementById("sg-highlights-css");
  if (old) old.remove(); // por si tenías la versión con subrayado

  const s = document.createElement("style");
  s.id = "sg-highlights-css";
  s.textContent = `
    /* Usuario: resaltado tipo marcador (fondo) */
    ::highlight(sg-user-high)   { background-color: rgba(255, 77, 77, 0.35); }
    ::highlight(sg-user-med)    { background-color: rgba(255, 204, 0, 0.35); }
    ::highlight(sg-user-low)    { background-color: rgba(102, 204, 102, 0.35); }

    /* Respuesta: ahora también marcador (mismos colores) */
    ::highlight(sg-assist-high) { background-color: rgba(255, 77, 77, 0.35); }
    ::highlight(sg-assist-med)  { background-color: rgba(255, 204, 0, 0.35); }
    ::highlight(sg-assist-low)  { background-color: rgba(102, 204, 102, 0.35); }
  `;
  document.head.appendChild(s);
}


// Devuelve todos los nodos de texto dentro de root (excluye <a>, <code>, <pre>, etc.)
function textNodesIn(root) {
  if (!root) return [];
  const rejectSel = "a, code, pre, style, script";
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(n) {
      const p = n.parentElement;
      if (!p) return NodeFilter.FILTER_REJECT;
      if (p.closest(rejectSel)) return NodeFilter.FILTER_REJECT;
      return (n.nodeValue && n.nodeValue.trim()) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
    }
  });
  const out = [];
  let n;
  while ((n = walker.nextNode())) out.push(n);
  return out;
}

// Crea rangos para todas las coincidencias exactas dentro de cada nodo de texto
function rangesForValue(root, value) {
  const ranges = [];
  const safe = value.normalize();
  for (const tn of textNodesIn(root)) {
    let idx = 0;
    const txt = tn.nodeValue || "";
    if (!txt) continue;
    while ((idx = txt.indexOf(safe, idx)) !== -1) {
      const r = new Range();
      r.setStart(tn, idx);
      r.setEnd(tn, idx + safe.length);
      ranges.push(r);
      idx += safe.length;
    }
  }
  return ranges;
}

// Aplica highlights por nivel y contexto (user/assistant)
function applyHighlights(root, detected_fields, context /* 'user' | 'assistant' */) {
  ensureHighlightCSS();
  if (!root || !window.CSS || !CSS.highlights) return;

  // Limpia previos de ese contexto
  if (context === "user") {
    CSS.highlights.delete("sg-user-high");
    CSS.highlights.delete("sg-user-med");
    CSS.highlights.delete("sg-user-low");
  } else {
    CSS.highlights.delete("sg-assist-high");
    CSS.highlights.delete("sg-assist-med");
    CSS.highlights.delete("sg-assist-low");
  }

  if (!detected_fields || !detected_fields.length) return;

  const hi = [], med = [], low = [];
  const seen = new Set();

  for (const f of detected_fields) {
    const val = (f.value || "").trim();
    if (!val || val.length < 2) continue; // evita falsos positivos muy cortos
    const key = `${(f.field||"").toUpperCase()}__${val}`;
    if (seen.has(key)) continue;
    seen.add(key);

    const up = (f.field||"").toUpperCase();
    const bucket = HIGH_FIELDS.has(up) ? hi : MEDIUM_FIELDS.has(up) ? med : low;

    bucket.push(...rangesForValue(root, val));
  }

  if (context === "user") {
    if (hi.length)  CSS.highlights.set("sg-user-high",  new Highlight(...hi));
    if (med.length) CSS.highlights.set("sg-user-med",   new Highlight(...med));
    if (low.length) CSS.highlights.set("sg-user-low",   new Highlight(...low));
  } else {
    if (hi.length)  CSS.highlights.set("sg-assist-high", new Highlight(...hi));
    if (med.length) CSS.highlights.set("sg-assist-med",  new Highlight(...med));
    if (low.length) CSS.highlights.set("sg-assist-low",  new Highlight(...low));
  }
}

// ==== Editor ====
function findComposer() {
  const ce = Array.from(document.querySelectorAll('[contenteditable="true"][role="textbox"], div[contenteditable="true"]'))
    .find(el => el.offsetParent !== null && el.clientHeight > 0);
  if (ce) return ce;
  const ta = Array.from(document.querySelectorAll("textarea"))
    .find(el => el.offsetParent !== null && el.clientHeight > 0);
  return ta || null;
}
function getComposerText(el) {
  if (!el) return "";
  if (el.tagName === "TEXTAREA") return el.value;
  return (el.textContent || "").replace(/\u00A0/g, " ");
}

// ==== DOM utils ====
function findSendButton() {
  const composer = findComposer();
  if (!composer) return null;
  return (
    composer.closest("form")?.querySelector('button[type="submit"]') ||
    document.querySelector('[data-testid="send-button"]') ||
    composer.parentElement?.querySelector("button")
  );
}
function extractMessageText(node) {
  if (!node) return "";
  return (node.innerText || node.textContent || "").trim();
}
function isMessageNode(n) {
  if (!n || n.nodeType !== 1) return false;
  const el = n;
  if (el.hasAttribute?.("data-message-author-role")) return true;
  if (el.closest?.('[data-message-author-role]')) return true;
  if (el.matches && el.matches('[data-testid="conversation-turn"]')) return true;
  return false;
}

// ==== API ====
async function callDetector(text, mode = DEFAULT_MODE) {
  const resp = await fetch(`${API_BASE}/detect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, mode })
  });
  if (!resp.ok) throw new Error(`Detector HTTP ${resp.status}`);
  return await resp.json();
}

// ==== Bloqueo de envío ====
function shouldBlock(risk) { return risk === "High" && !overrideOnce; }

// ==== Esperar fin de streaming ====
function waitForStableContent(node, idleMs = 800) {
  return new Promise((resolve) => {
    let timer = setTimeout(done, idleMs);
    const obs = new MutationObserver(() => {
      clearTimeout(timer);
      timer = setTimeout(done, idleMs);
    });
    function done() { obs.disconnect(); resolve(); }
    obs.observe(node, { childList: true, subtree: true, characterData: true });
  });
}

// ==== Enganche compositor + mensajes ====
let attached = false;
function attachOnce() {
  if (attached) return;
  const composer = findComposer();
  if (!composer) return;
  attached = true;

  ensurePanel();
  ensureHighlightCSS();

  // Pre-análisis con debounce (USUARIO) + resaltado tipo marcador
  let typingTimer;
  const onInput = () => {
    clearTimeout(typingTimer);
    typingTimer = setTimeout(async () => {
      if (suppressUserAlerts) return; // no relanzar panel de Usuario mientras esperamos la respuesta
      const text = getComposerText(composer);
      if (!text) { applyHighlights(composer, [], "user"); return; }
      try {
        const result = await callDetector(text);
        applyHighlights(composer, result?.detected_fields || [], "user");
        if (["Medium", "High"].includes(result?.risk_level)) renderPanel(result, "Usuario");
      } catch {
        applyHighlights(composer, [], "user");
      }
    }, 450);
  };
  composer.addEventListener("input", onInput);
  composer.addEventListener("keyup", onInput);

  // Intercepta Enter
  composer.addEventListener("keydown", async (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      clearTimeout(typingTimer);
      const text = getComposerText(composer);
      if (!text) return;
      try {
        const result = await callDetector(text);
        applyHighlights(composer, result?.detected_fields || [], "user");
        if (shouldBlock(result?.risk_level)) {
          e.preventDefault(); e.stopPropagation();
          renderPanel(result, "Usuario");
        } else {
          pendingResponseAlert = true;
          suppressUserAlerts = true;   // silencia paneles de Usuario hasta terminar análisis de respuesta
          setTimeout(() => applyHighlights(composer, [], "user"), 50);
        }
      } catch {}
    }
  }, true);

  // Intercepta botón enviar
  const sendBtn = findSendButton();
  if (sendBtn) {
    sendBtn.addEventListener("click", async (e) => {
      clearTimeout(typingTimer);
      const text = getComposerText(composer);
      if (!text) return;
      try {
        const result = await callDetector(text);
        applyHighlights(composer, result?.detected_fields || [], "user");
        if (shouldBlock(result?.risk_level)) {
          e.preventDefault(); e.stopImmediatePropagation();
          renderPanel(result, "Usuario");
        } else {
          pendingResponseAlert = true;
          suppressUserAlerts = true;   // silencia paneles de Usuario hasta terminar análisis de respuesta
          setTimeout(() => applyHighlights(composer, [], "user"), 50);
        }
      } catch {}
    }, true);
  }
}

function findAssistantContentEl(host) {
  // Prueba varios selectores usados por ChatGPT a lo largo del tiempo
  const sels = [
    ".markdown",
    ".prose",
    '[data-message-author-role="assistant"] .markdown',
    '[data-message-author-role="assistant"] .prose',
    '[data-message-author-role="assistant"] [class*="whitespace-pre-wrap"]',
    '[data-message-author-role="assistant"] [data-testid="assistant-response"]',
  ];
  for (const sel of sels) {
    const el = host.querySelector?.(sel);
    if (el && el.innerText?.trim()) return el;
  }
  // Fallback: si el propio host tiene texto, úsalo
  return host;
}


// ==== Analizar mensajes (usuario y respuesta) ====
async function analyzeMessageNode(node, originGuess = "Desconocido") {
  if (!node) return;

  const host = node.closest?.('[data-message-author-role]') || node;
  if (analyzedNodes.has(host) || inFlightAnalyze.has(host)) return;

  const roleAttr = host.getAttribute?.("data-message-author-role");
  const isAssistant = roleAttr === "assistant";
  const isUser      = roleAttr === "user";

  // --- RESPUESTA DEL MODELO ---
  if (isAssistant) {
    if (!pendingResponseAlert) return; // solo si el usuario decidió enviar
    inFlightAnalyze.add(host);

    await waitForStableContent(host, 1200); // un poco más de margen para streaming

    const contentEl = findAssistantContentEl(host);
    if (!contentEl) { inFlightAnalyze.delete(host); return; }

    const text = extractMessageText(contentEl).trim();
    if (!text || text.length < 10) {
      inFlightAnalyze.delete(host); return;
    }

    try {
      const result = await callDetector(text);
      if (["Medium", "High"].includes(result?.risk_level)) {
        renderPanel(result, "Respuesta", text);
        applyHighlights(contentEl, result?.detected_fields || [], "assistant"); // subrayado
      }
    } catch (e) {
      console.warn("[SG-LLM] analyze assistant error:", e);
    } finally {
      analyzedNodes.add(host);
      inFlightAnalyze.delete(host);
      pendingResponseAlert = false;  // consumido
      suppressUserAlerts = false;    // reactivar para siguiente turno
    }
    return;
  }

  // --- MENSAJE DEL USUARIO (para historial existente) ---
  if (isUser || originGuess === "Usuario") {
    if (suppressUserAlerts) return; // evita panel viejo justo tras enviar
    const textUser = extractMessageText(host);
    if (!textUser) return;
    try {
      const result = await callDetector(textUser);
      if (["Medium", "High"].includes(result?.risk_level)) {
        renderPanel(result, "Usuario", textUser);
      }
      analyzedNodes.add(host);
    } catch (e) {
      console.warn("[SG-LLM] analyze user error:", e);
    }
  }
}

function attachFileInterceptor() {
  document.addEventListener("change", async (e) => {
    const input = e.target;
    if (input.type === "file" && input.files?.length) {
      const file = input.files[0];
      if (file.name.toLowerCase().endsWith(".pdf")) {
        console.log("[SG-LLM] PDF detectado:", file.name);
        await analyzePDF(file);
      }
    }
  }, true);
}

async function analyzePDF(file) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("mode", DEFAULT_MODE);

  try {
    const resp = await fetch(`${API_BASE}/detect_file`, { method: "POST", body: formData });
    const result = await resp.json();

    // Render panel igual que con texto de usuario
    renderPanel(result, "Usuario", `PDF: ${file.name}`);

    // Además, log snippet en consola
    if (result.extracted_snippet) {
      console.log("[SG-LLM] Snippet PDF extraído:", result.extracted_snippet);
    }
  } catch (err) {
    console.error("[SG-LLM] Error analizando PDF:", err);
  }
}


function scanExistingMessages() {
  const nodes = document.querySelectorAll(
    '[data-message-author-role], [data-testid="conversation-turn"], .markdown'
  );
  nodes.forEach(n => analyzeMessageNode(n, "Respuesta"));
}

// ==== Observador global ====
const mo = new MutationObserver((muts) => {
  if (findComposer() && !document.getElementById("sg-llm-panel")) {
    ensurePanel(); ensureHighlightCSS(); attachOnce();
  }
  for (const m of muts) {
    // Analiza nodos añadidos
    m.addedNodes && m.addedNodes.forEach(n => {
      if (isMessageNode(n)) analyzeMessageNode(n, "Respuesta");
      if (n.querySelectorAll) {
        n.querySelectorAll('[data-message-author-role]').forEach(h => analyzeMessageNode(h, "Respuesta"));
      }
    });

    // Si estamos esperando respuesta, reintenta analizar el último turno del asistente
    if (pendingResponseAlert) {
      const lastAssistant = [...document.querySelectorAll('[data-message-author-role="assistant"]')].pop();
      if (lastAssistant) analyzeMessageNode(lastAssistant, "Respuesta");
    }
  }
});
mo.observe(document.documentElement, { childList: true, subtree: true, characterData: true });


window.addEventListener("load", () => {
  setTimeout(() => {
    ensurePanel(); ensureHighlightCSS(); attachOnce(); scanExistingMessages();attachFileInterceptor(); 
  }, 800);
});
