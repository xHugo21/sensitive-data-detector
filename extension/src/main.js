(function initMain(root) {
  const sg = (root.SG = root.SG || {});

  /**
   * Initialize platform system by registering all available platforms
   */
  function initializePlatforms() {
    console.log("[SensitiveDataDetector] Initializing platform system...");
    
    // Register all available platform adapters
    if (sg.ChatGPTPlatform) {
      sg.platformRegistry.register(sg.ChatGPTPlatform);
    }
    if (sg.ClaudePlatform) {
      sg.platformRegistry.register(sg.ClaudePlatform);
    }
    if (sg.GeminiPlatform) {
      sg.platformRegistry.register(sg.GeminiPlatform);
    }
    if (sg.GrokPlatform) {
      sg.platformRegistry.register(sg.GrokPlatform);
    }

    console.log("[SensitiveDataDetector] Supported platforms:", sg.platformRegistry.getSupportedPlatforms());
  }

  /**
   * Bootstrap the extension with platform detection
   */
  async function bootstrap() {
    // Initialize platform registry
    initializePlatforms();

    // Detect and activate the appropriate platform
    const platform = await sg.platformRegistry.detectAndActivate();
    
    if (!platform) {
      console.warn("[SensitiveDataDetector] No supported platform detected on this page");
      return;
    }

    console.log(`[SensitiveDataDetector] Successfully initialized on ${platform.displayName}`);

    // Initialize UI components
    sg.panel.ensure();
    sg.highlights.ensureHighlightCSS();

    // Attach controllers
    sg.sendInterceptor.attach();
    sg.messageAnalyzer.start();
    sg.fileInterceptor.attach();
  }

  function startWithDelay() {
    setTimeout(bootstrap, 800);
  }

  if (
    document.readyState === "complete" ||
    document.readyState === "interactive"
  ) {
    startWithDelay();
  } else {
    window.addEventListener("load", startWithDelay);
  }
})(typeof window !== "undefined" ? window : globalThis);
