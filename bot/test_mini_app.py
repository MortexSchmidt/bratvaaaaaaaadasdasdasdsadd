"""
Тестирование интеграции Mini-App с ботом
"""
import asyncio
import json
from datetime import datetime
import hashlib
import hmac
import os

# Конфигурация
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://your-bot-domain.onrender.com/mini_apps/truth_or_dare/")
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Имитация объекта пользователя для тестирования
class MockUser:
    def __init__(self, user_id, first_name, last_name=None, username=None):
        self.id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username

async def generate_mini_app_url(user):
    """
    Генерирует безопасную ссылку на Mini-App с аутентификацией
    """
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        # Если токен бота не задан, возвращаем базовую ссылку
        return WEB_APP_URL
    
    # Подготовка данных для WebApp
    auth_date = int(datetime.now().timestamp())
    hash_data = [
        f"auth_date={auth_date}",
        f"user={user.id}",
        f"first_name={user.first_name}",
    ]
    
    if user.last_name:
        hash_data.append(f"last_name={user.last_name}")
    if user.username:
        hash_data.append(f"username={user.username}")
    
    # Сортировка по ключам для правильного формата данных
    data_check_arr = sorted(hash_data)
    data_check_string = "\n".join(data_check_arr)
    
    # Создание ключа шифрования
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    # Создание хэша для проверки
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    # Формирование строки параметров
    params = [
        f"auth_date={auth_date}",
        f"user_id={user.id}",
        f"first_name={user.first_name}",
        f"hash={calculated_hash}"
    ]
    
    if user.last_name:
        params.append(f"last_name={user.last_name}")
    if user.username:
        params.append(f"username={user.username}")
    
    query_string = "&".join(params)
    return f"{WEB_APP_URL}?{query_string}"

async def test_mini_app_generation():
    """Тестирование генерации ссылки на Mini-App"""
    print("Тестирование генерации безопасной ссылки на Mini-App...")
    
    # Создаем несколько тестовых пользователей
    test_users = [
        MockUser(123456789, "Иван", "Иванов", "ivan_ivanov"),
        MockUser(987654321, "Мария", "Сидорова", "maria_s"),
        MockUser(456789123, "Алексей", "Петров"),
        MockUser(789123456, "Елена", username="elena_test")
    ]
    
    for user in test_users:
        url = await generate_mini_app_url(user)
        print(f"Пользователь: {user.first_name} {user.last_name or ''} (@{user.username or 'no_username'})")
        print(f"Ссылка: {url}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_mini_app_generation())