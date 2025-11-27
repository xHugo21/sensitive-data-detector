(function initFileAnalyzer(root) {
  const sg = (root.SG = root.SG || {});

  // Supported file extensions for analysis
  const SUPPORTED_EXTENSIONS = {
    // Documents
    pdf: { type: "document", label: "PDF" },

    // Images (OCR supported by backend)
    png: { type: "image", label: "Image" },
    jpg: { type: "image", label: "Image" },
    jpeg: { type: "image", label: "Image" },
    gif: { type: "image", label: "Image" },
    bmp: { type: "image", label: "Image" },
    webp: { type: "image", label: "Image" },
    tiff: { type: "image", label: "Image" },
    tif: { type: "image", label: "Image" },

    // Text files
    txt: { type: "text", label: "Text File" },
    md: { type: "text", label: "Markdown" },
    csv: { type: "text", label: "CSV" },

    // Code files
    js: { type: "code", label: "JavaScript" },
    py: { type: "code", label: "Python" },
    java: { type: "code", label: "Java" },
    cpp: { type: "code", label: "C++" },
    c: { type: "code", label: "C" },
    html: { type: "code", label: "HTML" },
    css: { type: "code", label: "CSS" },
    json: { type: "code", label: "JSON" },
    xml: { type: "code", label: "XML" },
    yaml: { type: "code", label: "YAML" },
    yml: { type: "code", label: "YAML" },
    sh: { type: "code", label: "Shell Script" },
    sql: { type: "code", label: "SQL" },
  };

  /**
   * Get file extension from filename
   */
  function getFileExtension(filename) {
    if (!filename) return "";
    const parts = filename.toLowerCase().split(".");
    return parts.length > 1 ? parts[parts.length - 1] : "";
  }

  /**
   * Check if file type is supported
   */
  function isSupportedFile(filename) {
    const ext = getFileExtension(filename);
    return ext in SUPPORTED_EXTENSIONS;
  }

  /**
   * Get file type info
   */
  function getFileInfo(filename) {
    const ext = getFileExtension(filename);
    return SUPPORTED_EXTENSIONS[ext] || { type: "unknown", label: "File" };
  }

  /**
   * Analyze any supported file by sending to backend
   */
  async function analyzeFile(file) {
    if (!file) {
      throw new Error("No file provided");
    }

    const ext = getFileExtension(file.name);
    const fileInfo = getFileInfo(file.name);

    console.log(
      `[SensitiveDataDetectorExtension] Analyzing ${fileInfo.label} file: ${file.name} (${file.size} bytes)`,
    );

    // Create FormData to send file to backend
    const formData = new FormData();
    formData.append("file", file);

    try {
      const result = await sg.detectorClient.detectFile(formData);

      // Add file metadata to result
      result.fileInfo = {
        name: file.name,
        size: file.size,
        type: fileInfo.type,
        label: fileInfo.label,
        extension: ext,
      };

      console.log(
        `[SensitiveDataDetectorExtension] Analysis complete for ${file.name}:`,
        {
          riskLevel: result.risk_level,
          fieldsDetected: result.detected_fields?.length || 0,
          hasExtractedText: !!result.extracted_snippet,
        },
      );

      return result;
    } catch (error) {
      console.error(
        `[SensitiveDataDetectorExtension] Error analyzing ${file.name}:`,
        error,
      );
      throw error;
    }
  }

  sg.fileAnalyzer = {
    analyzeFile,
    isSupportedFile,
    getFileInfo,
    getFileExtension,
    SUPPORTED_EXTENSIONS,
  };
})(typeof window !== "undefined" ? window : globalThis);
