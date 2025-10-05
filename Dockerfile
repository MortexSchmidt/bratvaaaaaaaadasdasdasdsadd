FROM python:3.12-slim

# ========== Базовые ENV ==========
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Europe/Kyiv

WORKDIR /app

# ========== Системные пакеты (tzdata для zoneinfo) ==========
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

# ========== Зависимости Python ==========
COPY bot/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ========== Исходники ==========
COPY bot /app/bot

# ========== Non-root пользователь ==========
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# ========== Healthcheck ==========
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import sys,os; sys.exit(0 if os.environ.get('BOT_TOKEN') else 1)" || exit 1

# ========== Запуск ==========
CMD ["python", "bot/run.py"]
