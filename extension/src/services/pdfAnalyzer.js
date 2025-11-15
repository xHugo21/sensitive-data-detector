(function initPdfAnalyzer(root) {
  const sg = (root.SG = root.SG || {});

  async function analyzePdfFile(file) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("mode", sg.config.MODE);
    return sg.detectorClient.detectFile(formData);
  }

  sg.pdfAnalyzer = { analyzePdfFile };
})(typeof window !== "undefined" ? window : globalThis);
