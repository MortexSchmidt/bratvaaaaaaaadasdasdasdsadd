# Bratva Fan Telegram Bot

Инфраструктурные файлы для фан-бота (папка `bot/`).

## Содержимое
- `bot/` — исходный код бота (см. подробный `bot/README.md`)
- `Dockerfile` — образ для деплоя (Railway / любой контейнер)
- `.dockerignore` — исключения для сборки образа
- `Procfile` — процессный файл (опционально)

## Быстрый старт локально
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r bot/requirements.txt
copy bot/.env.example bot/.env  # и вставьте токен
python bot/run.py
```

## Деплой
См. `bot/README.md` раздел "Деплой на Railway".

## Безопасность
Не коммить `.env` и реальные токены.
