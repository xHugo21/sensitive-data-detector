(function initMain(root) {
  const sg = root.SG = root.SG || {};

  function bootstrap() {
    sg.panel.ensure();
    sg.highlights.ensureHighlightCSS();
    sg.sendInterceptor.attach();
    sg.messageAnalyzer.scanExistingMessages();
    sg.messageAnalyzer.start();
    sg.fileInterceptor.attach();
  }

  function startWithDelay() {
    setTimeout(bootstrap, 800);
  }

  if (document.readyState === "complete" || document.readyState === "interactive") {
    startWithDelay();
  } else {
    window.addEventListener("load", startWithDelay);
  }
})(typeof window !== "undefined" ? window : globalThis);
