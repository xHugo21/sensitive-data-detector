FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS runtime

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

COPY pyproject.toml uv.lock ./
COPY backend backend
COPY multiagent-firewall multiagent-firewall

# Limit syncing to the workspace members the backend depends on.
# `--locked` is omitted here because the lock references other workspace members
# that are intentionally not copied into the image (for example `proxy`).
RUN uv sync --package multiagent-firewall --package backend

ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app/backend

EXPOSE 8000

CMD ["python3", "-m", "app.main", "--host", "0.0.0.0"]
