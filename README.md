# 🛡️ LLM Guard 

Browser extension designed to detect and prevent private data leakage in user - LLM interactions.

> [!IMPORTANT]
> This is a fork of the repository [guillecab/SensitiveDataDetector-ChatGPT-Extension](https://github.com/guillecab/SensitiveDataDetector-ChatGPT-Extension).

## ⚡ Exclusive features of this fork
- Cleaner project structure
- Easier backend server setup via `requirements.txt` and virtual environment
- Better model support via API unification and easier to setup local `.env` file.
- Local model support through Ollama

---

## 🛠️ Setting up the extension

### 1. Clone repository

```bash
git clone https://github.com/xHugo21/sensitive-data-detector.git
cd sensitive-data-detector
```

### 2. Install backend dependencies
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Set .env file
Take a look at `backend/.env.example` and copy it to `backend/.env` with desired provider and model

### 4. Run uvicorn
From backend folder run:
```bash
uvicorn server.app:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Load extension
1. Go to chrome://extensions/
2. Toggle on "Developer mode"
3. Click "Load unpacked" → choose sensitive-data-detector/extension/

---

## 🌐 Supported providers
- OpenAI
- Groq
- Ollama

---

## 📜 License

This project is under the MIT license.
Check the file LICENSE for more details.

