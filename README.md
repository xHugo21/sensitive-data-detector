# 🛡️ LLM Guard 

Browser extension designed to detect and prevent private data leakage in user - LLM interactions.

> [!IMPORTANT]
> This is a fork of the repository [guillecab/SensitiveDataDetector-ChatGPT-Extension](https://github.com/guillecab/SensitiveDataDetector-ChatGPT-Extension).

## ⚡ Exclusive features of this fork
- Cleaner project structure
- Chromium extension blocks prompt sending until analysed and user explicitly allows it.
- Easier backend server setup via `requirements.txt` and Dockerfile
- Unified LiteLLM integration for 100+ providers with simple `.env` overrides
- Local model support through Ollama

---

## 🛠️ Setting up the extension

### 1. Clone repository

```bash
git clone https://github.com/xHugo21/sensitive-data-detector.git
cd sensitive-data-detector
```

### 2. Setup .env
Take a look at `backend/.env.example` and copy it to `backend/.env` with desired config options

### 3. Install dependencies and run
```bash
cd backend

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3 main.py
```

> [!NOTE]
> Alternatively, you can run the backend using the `Dockerfile`
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

## 🌐 Supported providers
- Any model reachable through the [LiteLLM](https://github.com/BerriAI/litellm) SDK (100+ vendors)
- See more info in `backend/.env.example`

---

## 📜 License

This project is under the MIT license.
Check the file LICENSE for more details.
