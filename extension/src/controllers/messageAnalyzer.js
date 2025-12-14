(function initMessageAnalyzer(root) {
  const sg = (root.SG = root.SG || {});

  let observer = null;

  function start() {
    if (observer) return;
    observer = new MutationObserver(handleMutations);
    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
      characterData: true,
    });
    handleMutations();
  }

  function handleMutations() {
    // Only ensure the send interceptor is attached once a composer exists
    if (sg.chatSelectors.findComposer()) sg.sendInterceptor.attach();
  }

  sg.messageAnalyzer = {
    start,
    scanExistingMessages() {},
    analyzeMessageNode() {},
  };
})(typeof window !== "undefined" ? window : globalThis);
