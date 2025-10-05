"""
Тестирование генерации аутентификационных параметров для Mini-App
"""
import asyncio
import json
from datetime import datetime
import hashlib
import hmac
import os

# Используем фиктивный токен для тестирования
FAKE_BOT_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"

# Имитация объекта пользователя для тестирования
class MockUser:
    def __init__(self, user_id, first_name, last_name=None, username=None):
        self.id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username

async def generate_mini_app_url(user, bot_token):
    """
    Генерирует безопасную ссылку на Mini-App с аутентификацией
    """
    if not bot_token:
        # Если токен бота не задан, возвращаем базовую ссылку
        return "https://your-bot-domain.onrender.com/mini_apps/truth_or_dare/"
    
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
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
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
    return f"https://your-bot-domain.onrender.com/mini_apps/truth_or_dare/?{query_string}"

async def test_auth_generation():
    """Тестирование генерации аутентификационных параметров"""
    print("Тестирование генерации аутентификационных параметров для Mini-App...")
    
    # Создаем тестового пользователя
    user = MockUser(123456789, "Иван", "Иванов", "ivan_ivanov")
    
    url = await generate_mini_app_url(user, FAKE_BOT_TOKEN)
    print(f"Пользователь: {user.first_name} {user.last_name} (@{user.username})")
    print(f"Ссылка: {url}")
    print(f"Токен: {FAKE_BOT_TOKEN}")
    print("-" * 50)
    
    # Разбор параметров из URL для проверки
    if "?" in url:
        query_params = url.split("?")[1]
        print("Параметры запроса:")
        for param in query_params.split("&"):
            key, value = param.split("=", 1)
            print(f"  {key}: {value}")
    
    print("\nТестирование завершено успешно!")

if __name__ == "__main__":
    asyncio.run(test_auth_generation())