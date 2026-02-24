(function initFileAnalyzer(root) {
  const sg = (root.SG = root.SG || {});

  /**
   * Analyze any file by sending to backend.
   * Backend validates file type and returns error if unsupported.
   */
  async function analyzeFile(file) {
    if (!file) {
      throw new Error("No file provided");
    }

    console.log(
      `[SensitiveDataDetectorExtension] Analyzing file: ${file.name} (${file.size} bytes)`,
    );

    const formData = new FormData();
    formData.append("file", file);

    try {
      const result = await sg.detectorClient.detectFile(formData);

      // Backend may return error for unsupported/invalid files
      if (result.error) {
        console.warn(
          `[SensitiveDataDetectorExtension] Backend validation error: ${result.error}`,
        );
      }

      // Add file metadata
      result.fileInfo = {
        name: file.name,
        size: file.size,
      };

      console.log(
        `[SensitiveDataDetectorExtension] Analysis complete for ${file.name}:`,
        {
          riskLevel: result.risk_level,
          fieldsDetected: result.detected_fields?.length || 0,
          hasExtractedText: !!result.extracted_snippet,
          error: result.error,
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
  };
})(typeof window !== "undefined" ? window : globalThis);
