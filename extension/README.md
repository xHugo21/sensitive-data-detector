# Browser Extension for LLM Chat Sensitive Data Detection

A browser extension that intercepts messages in LLM chat platforms and detects sensitive data in real-time before submission.

## Supported Platforms

- **ChatGPT** - chat.openai.com, chatgpt.com
- **Claude** - claude.ai
- **Gemini** - gemini.google.com

## Installation

### Prerequisites

The extension requires the backend service to be running:

```bash
cd backend
uv sync
uv run python -m app.main
```

The backend should be accessible at `http://127.0.0.1:8000` (configurable in `src/config.js`).

### Loading the Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" in the top right
3. Click "Load unpacked"
4. Select the `extension/` directory
5. Navigate to a supported platform (ChatGPT, Claude, or Gemini)

## Usage

### Text Detection

1. Navigate to a supported chat platform
2. Type a message containing sensitive data (e.g., "My SSN is 123-45-6789")
3. Click send or press Enter
4. The extension will intercept the message and analyze it
5. A risk panel will appear showing detected sensitive fields
6. Choose to proceed or cancel based on the risk level

### File Detection

1. Upload a file (image, PDF, document) in the chat interface
2. The extension will analyze the file content
3. A risk panel will display detected sensitive data from the file
4. Review the findings before sending

## Adding a New Platform

The extension makes it easy to add support for new LLM chat platforms

- Create Platform Adapter: Create a new file `src/platforms/newplatform.js` that follows the structure of one of the existing ones.
- Update manifest.json: Add both the new platform URL to the `matches` section and script to `js` section.

## Testing

Run the unit tests (requires Node.js)

```bash
node --test .
```

## License

See LICENSE file in the root of the repository.
