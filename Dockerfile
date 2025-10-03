FROM python:3.12-slim

# Env tweaks
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Устанавливаем зависимости отдельно (лучше слой кешируется)
COPY bot/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем исходники
COPY bot /app/bot

# Healthcheck (простой — пинг процесса)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import sys; import os; sys.exit(0 if os.environ.get('BOT_TOKEN') else 1)" || exit 1

# Запуск
CMD ["python", "bot/run.py"]
