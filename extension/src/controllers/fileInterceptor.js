(function initFileInterceptor(root) {
  const sg = (root.SG = root.SG || {});
  let attached = false;
  let lastFileIntent = null;

  function now() {
    return (root.performance || {}).now ? performance.now() : Date.now();
  }

  function attach() {
    if (attached) return;
    attached = true;
    document.addEventListener("change", handleFileChange, true);
    sg.panel.onSendAnyway(handleUploadAnyway);
    sg.panel.onDismiss(handleDismiss);
    console.log(
      "[SensitiveDataDetectorExtension] File interceptor attached - monitoring all file uploads",
    );
  }

  function consumeBypassFlag(input) {
    if (!input || !input.dataset) return false;
    if (input.dataset.sgBypass !== "true") return false;
    delete input.dataset.sgBypass;
    return true;
  }

  function allowUpload(input, files) {
    if (!input) return;

    try {
      const dataTransfer = new DataTransfer();
      if (Array.isArray(files)) {
        files.forEach((file) => dataTransfer.items.add(file));
      }
      if (dataTransfer.files?.length) {
        try {
          input.files = dataTransfer.files;
        } catch (err) {
          console.warn(
            "[SensitiveDataDetectorExtension] Could not reset file input files:",
            err,
          );
        }
      }
    } catch (err) {
      console.warn(
        "[SensitiveDataDetectorExtension] Could not rebuild file list:",
        err,
      );
    }

    if (input.dataset) {
      input.dataset.sgBypass = "true";
    }
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function clearInput(input) {
    if (!input) return;
    try {
      input.value = "";
    } catch (err) {
      // Ignore if browser prevents programmatic clearing.
    }
  }

  function shouldBlockFile(result) {
    if (!result) return false;
    const decision = String(result.decision || "").toLowerCase();
    if (decision === "block") return true;
    return result.risk_level === "high";
  }

  function shouldWarnFile(result) {
    if (!result) return false;
    const decision = String(result.decision || "").toLowerCase();
    return decision === "warn";
  }

  async function handleFileChange(event) {
    const input = event.target;
    if (!input || input.type !== "file" || !input.files?.length) return;

    if (consumeBypassFlag(input)) return;

    const files = Array.from(input.files || []);
    if (!files.length) return;

    const supportedFiles = files.filter((file) =>
      sg.fileAnalyzer.isSupportedFile(file.name),
    );

    const inFlight = sg.alertStore.isInFlight(input);
    if (!inFlight && supportedFiles.length === 0) return;

    event.preventDefault();
    event.stopImmediatePropagation();

    if (inFlight) return;

    sg.alertStore.beginInFlight(input);

    const startedAt = now();
    let durationMs = 0;
    let panelShown = false;
    let loadingShown = false;

    try {
      const previewFile = supportedFiles[0];
      const previewInfo = sg.fileAnalyzer.getFileInfo(previewFile.name);
      console.log(
        `[SensitiveDataDetectorExtension] Detected ${previewInfo.label} file upload: ${previewFile.name}`,
      );

      // Show loading state
      sg.loadingState.show({
        message:
          supportedFiles.length > 1
            ? "Analyzing files..."
            : `Analyzing ${previewInfo.label.toLowerCase()}...`,
      });
      loadingShown = true;

      let blocked = null;
      let warned = null;

      for (const file of supportedFiles) {
        const result = await sg.fileAnalyzer.analyzeFile(file);
        if (result?.extracted_snippet) {
          console.log(
            `[SensitiveDataDetectorExtension] Extracted snippet from ${file.name}:`,
            result.extracted_snippet.substring(0, 200) + "...",
          );
        }
        if (result?.detected_fields?.length > 0) {
          console.log(
            `[SensitiveDataDetectorExtension] Detected ${result.detected_fields.length} sensitive fields in ${file.name}:`,
            result.detected_fields.map((f) => f.field),
          );
        }
        if (shouldBlockFile(result)) {
          blocked = { file, result };
          break;
        }
        if (!warned && shouldWarnFile(result)) {
          warned = { file, result };
        }
      }

      durationMs = now() - startedAt;

      const decision = blocked || warned;
      if (decision) {
        const fileInfo = sg.fileAnalyzer.getFileInfo(decision.file.name);
        const displayName = `${fileInfo.label}: ${decision.file.name}`;
        lastFileIntent = {
          input,
          files,
          file: decision.file,
          result: decision.result,
        };
        sg.panel.render(decision.result, displayName, {
          durationMs,
          mode: blocked ? "block" : "warn",
          requireAction: true,
          primaryActionLabel: "Upload anyway",
          hideSanitized: true,
        });
        panelShown = true;
        clearInput(input);
        return;
      }

      allowUpload(input, files);
    } catch (err) {
      durationMs = now() - startedAt;
      const fallbackFile = supportedFiles[0] || files[0];
      const fileInfo = fallbackFile
        ? sg.fileAnalyzer.getFileInfo(fallbackFile.name)
        : { label: "File" };
      console.error(
        `[SensitiveDataDetectorExtension] Error analyzing ${
          fallbackFile?.name || "file"
        }:`,
        err,
      );

      // Optionally show error to user
      sg.panel.render(
        {
          risk_level: "unknown",
          detected_fields: [],
          error: `Failed to analyze file: ${err.message}`,
        },
        fallbackFile
          ? `${fileInfo.label}: ${fallbackFile.name}`
          : "File upload",
        {
          durationMs,
          mode: "warn",
          requireAction: true,
          primaryActionLabel: "Upload anyway",
          hideSanitized: true,
        },
      );
      panelShown = true;
      lastFileIntent = {
        input,
        files,
        file: fallbackFile || null,
        error: err,
      };
      clearInput(input);
    } finally {
      sg.alertStore.endInFlight(input);
      if (loadingShown) {
        sg.loadingState.hide({ durationMs, panelShown });
      }
    }
  }

  function handleUploadAnyway() {
    if (!lastFileIntent) return;
    const { input, files } = lastFileIntent;
    sg.panel.hide();
    allowUpload(input, files);
    lastFileIntent = null;
  }

  function handleDismiss() {
    if (!lastFileIntent) return;
    lastFileIntent = null;
  }

  sg.fileInterceptor = { attach };
})(typeof window !== "undefined" ? window : globalThis);
