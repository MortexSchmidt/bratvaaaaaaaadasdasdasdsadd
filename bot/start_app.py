"""
Файл для запуска приложения с ботом и Mini-App
"""
import os
import sys
import threading
import asyncio
from flask import Flask
from bot.run import main as run_bot

# Импортируем Flask-приложение для Mini-App
from bot.app.mini_apps.truth_or_dare.server import app as mini_app

def run_flask():
    """Запуск Flask-приложения для Mini-App"""
    port = int(os.environ.get("PORT", 500))
    mini_app.run(host="0.0.0.0", port=port, debug=False)

def run_bot_async():
    """Запуск бота в отдельном потоке"""
    asyncio.run(run_bot())

if __name__ == "__main__":
    # Запуск Flask-приложения в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Запуск бота в основном потоке
    try:
        run_bot_async()
    except KeyboardInterrupt:
        print("Приложение остановлено")
        sys.exit(0)