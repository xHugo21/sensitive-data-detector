(function initFileInterceptor(root) {
  const sg = (root.SG = root.SG || {});
  let attached = false;

  function now() {
    return (root.performance || {}).now ? performance.now() : Date.now();
  }

  function attach() {
    if (attached) return;
    attached = true;
    document.addEventListener("change", handleFileChange, true);
    console.log(
      "[SensitiveDataDetectorExtension] File interceptor attached - monitoring all file uploads",
    );
  }

  async function handleFileChange(event) {
    const input = event.target;
    if (!input || input.type !== "file" || !input.files?.length) return;

    let panelShown = false;
    const file = input.files[0];
    if (!file) return;

    // Check if file type is supported
    if (!sg.fileAnalyzer.isSupportedFile(file.name)) {
      console.log(
        `[SensitiveDataDetectorExtension] Skipping unsupported file: ${file.name}`,
      );
      return;
    }

    const fileInfo = sg.fileAnalyzer.getFileInfo(file.name);
    console.log(
      `[SensitiveDataDetectorExtension] Detected ${fileInfo.label} file upload: ${file.name}`,
    );

    const startedAt = now();

    try {
      // Show loading state
      sg.loadingState.show({
        message: `Analyzing ${fileInfo.label.toLowerCase()}...`,
      });

      // Analyze file through backend
      const result = await sg.fileAnalyzer.analyzeFile(file);
      const durationMs = now() - startedAt;

      // Only display panel if blocked
      if (sg.riskUtils.shouldBlock(result)) {
        const displayName = `${fileInfo.label}: ${file.name}`;
        sg.panel.render(result, displayName, { durationMs });
        panelShown = true;
      }

      // Hide loading state after panel decision so the toast behaves correctly
      sg.loadingState.hide({ durationMs, panelShown });

      // Log extracted text snippet if available
      if (result?.extracted_snippet) {
        console.log(
          `[SensitiveDataDetectorExtension] Extracted snippet from ${file.name}:`,
          result.extracted_snippet.substring(0, 200) + "...",
        );
      }

      // Log detection summary
      if (result?.detected_fields?.length > 0) {
        console.log(
          `[SensitiveDataDetectorExtension] Detected ${result.detected_fields.length} sensitive fields in ${file.name}:`,
          result.detected_fields.map((f) => f.field),
        );
      }
    } catch (err) {
      const durationMs = now() - startedAt;
      sg.loadingState.hide({ durationMs, panelShown: true });
      console.error(
        `[SensitiveDataDetectorExtension] Error analyzing ${file.name}:`,
        err,
      );

      // Optionally show error to user
      sg.panel.render(
        {
          risk_level: "unknown",
          detected_fields: [],
          error: `Failed to analyze file: ${err.message}`,
        },
        `${fileInfo.label}: ${file.name}`,
        { durationMs },
      );
    }
  }

  sg.fileInterceptor = { attach };
})(typeof window !== "undefined" ? window : globalThis);
