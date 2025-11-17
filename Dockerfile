FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      poppler-utils \
      tesseract-ocr \
      libtesseract-dev \
      libleptonica-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml .
COPY backend backend
COPY multiagent-firewall multiagent-firewall

RUN uv pip install --system ./multiagent-firewall ./backend

WORKDIR /app/backend

EXPOSE 8000

CMD ["python3", "main.py", "--host", "0.0.0.0"]
