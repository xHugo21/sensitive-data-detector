(function initFileInterceptor(root) {
  const sg = (root.SG = root.SG || {});
  let attached = false;

  function attach() {
    if (attached) return;
    attached = true;
    document.addEventListener("change", handleFileChange, true);
  }

  async function handleFileChange(event) {
    const input = event.target;
    if (!input || input.type !== "file" || !input.files?.length) return;
    const file = input.files[0];
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) return;

    try {
      const result = await sg.pdfAnalyzer.analyzePdfFile(file);
      if (!sg.alertStore.shouldSuppressUserAlerts()) {
        sg.panel.render(result, "Usuario", `PDF: ${file.name}`);
      }
      if (result?.extracted_snippet) {
        console.log("[SG-LLM] Snippet PDF extraído:", result.extracted_snippet);
      }
    } catch (err) {
      console.error("[SG-LLM] Error analizando PDF:", err);
    }
  }

  sg.fileInterceptor = { attach };
})(typeof window !== "undefined" ? window : globalThis);
