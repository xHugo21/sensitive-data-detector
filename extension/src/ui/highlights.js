(function initHighlights(root) {
  const sg = root.SG = root.SG || {};

  function ensureHighlightCSS() {
    const old = document.getElementById("sg-highlights-css");
    if (old) old.remove();

    const style = document.createElement("style");
    style.id = "sg-highlights-css";
    style.textContent = `
      ::highlight(sg-user-high)   { background-color: rgba(255, 77, 77, 0.35); }
      ::highlight(sg-user-med)    { background-color: rgba(255, 204, 0, 0.35); }
      ::highlight(sg-user-low)    { background-color: rgba(102, 204, 102, 0.35); }
      ::highlight(sg-assist-high) { background-color: rgba(255, 77, 77, 0.35); }
      ::highlight(sg-assist-med)  { background-color: rgba(255, 204, 0, 0.35); }
      ::highlight(sg-assist-low)  { background-color: rgba(102, 204, 102, 0.35); }
    `;
    document.head.appendChild(style);
  }

  function textNodesIn(root) {
    if (!root) return [];
    const rejectSel = "a, code, pre, style, script";
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent) return NodeFilter.FILTER_REJECT;
        if (parent.closest(rejectSel)) return NodeFilter.FILTER_REJECT;
        return (node.nodeValue && node.nodeValue.trim()) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    const nodes = [];
    let current;
    while ((current = walker.nextNode())) nodes.push(current);
    return nodes;
  }

  function rangesForValue(root, value) {
    const ranges = [];
    const safeValue = value.normalize();
    for (const textNode of textNodesIn(root)) {
      let idx = 0;
      const text = textNode.nodeValue || "";
      if (!text) continue;
      while ((idx = text.indexOf(safeValue, idx)) !== -1) {
        const range = new Range();
        range.setStart(textNode, idx);
        range.setEnd(textNode, idx + safeValue.length);
        ranges.push(range);
        idx += safeValue.length;
      }
    }
    return ranges;
  }

  function clearHighlights(context) {
    if (!root.CSS || !CSS.highlights) return;
    const prefix = context === "assistant" ? "sg-assist" : "sg-user";
    CSS.highlights.delete(`${prefix}-high`);
    CSS.highlights.delete(`${prefix}-med`);
    CSS.highlights.delete(`${prefix}-low`);
  }

  function applyHighlights(host, detectedFields, context) {
    ensureHighlightCSS();
    if (!host || !root.CSS || !CSS.highlights) return;
    clearHighlights(context);
    if (!detectedFields?.length) return;

    const high = [];
    const medium = [];
    const low = [];
    const seen = new Set();

    for (const field of detectedFields) {
      const value = (field.value || "").trim();
      if (!value || value.length < 2) continue;
      const key = `${(field.field || "").toUpperCase()}__${value}`;
      if (seen.has(key)) continue;
      seen.add(key);

      const bucket = sg.riskUtils.classifyField(field.field);
      const target = bucket === "high" ? high : bucket === "medium" ? medium : low;
      target.push(...rangesForValue(host, value));
    }

    const prefix = context === "assistant" ? "sg-assist" : "sg-user";
    if (high.length) CSS.highlights.set(`${prefix}-high`, new Highlight(...high));
    if (medium.length) CSS.highlights.set(`${prefix}-med`, new Highlight(...medium));
    if (low.length) CSS.highlights.set(`${prefix}-low`, new Highlight(...low));
  }

  sg.highlights = {
    ensureHighlightCSS,
    applyHighlights,
    clearHighlights
  };
})(typeof window !== "undefined" ? window : globalThis);
