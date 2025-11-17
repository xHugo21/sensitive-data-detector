# 🛡️ LLM Guard 

Detect and prevent private data leakage in user-LLM interactions.

Provides the backend for detecting sensitive information exchange alonside an extension for Chromium based browsers that displays the detected sensitive data and warns users before any information is sent to an LLM.

> [!IMPORTANT]
> This is a fork of the repository [guillecab/SensitiveDataDetector-ChatGPT-Extension](https://github.com/guillecab/SensitiveDataDetector-ChatGPT-Extension).

## ⚡ Exclusive features of this fork
- Proxy server that acts as a MiTM to analyse and block all sensitive LLM API interactions
- Cleaner project structure
- Chromium extension blocks prompt sending until analysed and user explicitly allows it.
- Easier backend server setup via a shared `uv` workspace and Dockerfile
- Unified LiteLLM integration for 100+ providers with simple `.env` overrides
- Local model support through Ollama
- Test suite on every package and CI workflow

---

## 🛠️ Set up and usage

### 1. Clone repository

```bash
git clone https://github.com/xHugo21/sensitive-data-detector.git
cd sensitive-data-detector
```

### 2. Setup .env
Take a look at `backend/.env.example` and copy it to `backend/.env` with desired config options

### 3. Install dependencies and run
Install [uv](https://docs.astral.sh/uv/#installation):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```bash
# Installs dependencies in a virtual environment
uv sync --project backend

# start the API with uv ensuring the env is activated
uv run --project backend python main.py
```

> [!NOTE]
> Alternatively, you can build the backend image using the provided Dockerfile:
> ```bash
> docker build -t sensitive-data-detector .
> docker run -p 8000:8000 --env-file .env sensitive-data-detector
> ```

### 4. Load extension
1. Go to chrome://extensions/
2. Toggle on "Developer mode"
3. Click "Load unpacked" → choose sensitive-data-detector/extension/

> [!IMPORTANT]
> Ensure the host and port used for the extension match the ones defined on the `content.js` of the extension

---

## 🧩 Proxy for LLM API calls

Protect command-line clients, IDEs or applications by routing their HTTP calls through the standalone proxy located in `proxy/`:

1. Run the backend server
2. Set up proxy env varialbes. Copy `proxy/.env.example` to `proxy/.env` and adjust values.
3. Install proxy dependencies and launch it:
   ```bash
   uv sync --project proxy
   uv run --project proxy uvicorn proxy.main:app --host 127.0.0.1 --port 8787
   ```
4. Aim your tool at the proxy. Examples:
   - Replace OpenAI's base URL with `http://127.0.0.1:8787/openai/v1/...`
   - Point GitHub Copilot requests to `http://127.0.0.1:8787/copilot/v1/...`
   - Send Groq traffic to `http://127.0.0.1:8787/groq/openai/v1/...`

Every request is analysed by the backend first. When the configured risk level is reached the proxy returns `403` (with the detected fields in the payload and `X-LLM-Guard-*` headers); otherwise the call is transparently forwarded to the upstream API.

Example Groq request:

```bash
curl http://127.0.0.1:8787/groq/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "model":"groq/llama-3.3-70b-versatile",
        "messages":[{"role":"user","content":"My password is 32141fsaj"}],
        "temperature":0.2,
        "stream":false
      }'
```

---

## 🌐 Supported providers
- Any model reachable through the [LiteLLM](https://github.com/BerriAI/litellm) SDK (100+ vendors)
- See more info in `backend/.env.example`

---

## 🧪 Tests

Each package has its own test suite that can be run with the following commands

```bash
uv sync --project <package> --group test
uv run --project <package> --group test bash -lc "PYTHONPATH=<package> pytest <package>/tests"
```

## 📜 License

This project is under the MIT license.
Check the file LICENSE for more details.
