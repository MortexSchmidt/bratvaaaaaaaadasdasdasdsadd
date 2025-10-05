from __future__ import annotations
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict
from .. import format_user_mention

router = Router(name="drочка")

# Database file - use /app/data for persistent storage on Railway
DB_FILE = os.path.join(os.getenv("DB_DIR", "."), "drochka_data.db")

def init_db():
    """Initialize the database"""
    # Ensure the directory exists
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            last_drочка TEXT,
            total_drочка INTEGER DEFAULT 0,
            current_streak INTEGER DEFAULT 0,
            max_streak INTEGER DEFAULT 0,
            pet_name TEXT
        )
    ''')
    # Миграция: если старый столбец pet_name отсутствует — добавить
    cursor.execute("PRAGMA table_info(user_stats)")
    cols = [r[1] for r in cursor.fetchall()]
    if 'pet_name' not in cols:
        cursor.execute("ALTER TABLE user_stats ADD COLUMN pet_name TEXT")
    conn.commit()
    conn.close()

def load_data() -> Dict:
    """Load user data from database"""
    init_db()  # Ensure DB is initialized
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, last_drочка, total_drочка, current_streak, max_streak, COALESCE(pet_name, "") FROM user_stats')
    rows = cursor.fetchall()
    conn.close()
    
    data = {}
    for row in rows:
        user_id, username, last_drочка, total_drочка, current_streak, max_streak, pet_name = row
        data[user_id] = {
            "username": username,
            "last_drочка": last_drочка,
            "total_drочка": total_drочка,
            "current_streak": current_streak,
            "max_streak": max_streak,
            "pet_name": pet_name or None
        }
    return data

def save_user_data(user_id: str, username: str, last_drочка: str, total_drочка: int, current_streak: int, max_streak: int, pet_name: str | None):
    """Save user data to database"""
    init_db()  # Ensure DB is initialized
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_stats 
        (user_id, username, last_drочка, total_drочка, current_streak, max_streak, pet_name)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, last_drочка, total_drочка, current_streak, max_streak, pet_name))
    conn.commit()
    conn.close()

async def perform_drочка(message: Message):
    """Perform the drочка action"""
    user_id = str(message.from_user.id)
    username = message.from_user.username or message.from_user.full_name or "Аноним"
    
    data = load_data()
    
    # Initialize user data if not exists
    if user_id not in data:
        data[user_id] = {
            "username": username,
            "last_drочка": None,
            "total_drочка": 0,
            "current_streak": 0,
            "max_streak": 0,
            "pet_name": None
        }
    
    user_data = data[user_id]
    
    # Check if user can drочить today
    can_drочить = True
    now = datetime.now()
    today = now.date()
    if user_data["last_drочка"]:
        last_time = datetime.fromisoformat(user_data["last_drочка"])
        last_date = last_time.date()
        if today == last_date:
            can_drочить = False
    
    if can_drочить:
        # Определение разрыва для серии
        if user_data["last_drочка"]:
            if (today - last_time.date()).days == 1:
                # серия продолжается
                pass
            else:
                # пропущен день или впервые — сбрасываем текущую серию
                user_data["current_streak"] = 0
        # Update stats
        user_data["username"] = username
        user_data["last_drочка"] = now.isoformat()
        user_data["total_drочка"] += 1
        user_data["current_streak"] += 1
        
        # Update max streak if needed
        if user_data["current_streak"] > user_data["max_streak"]:
            user_data["max_streak"] = user_data["current_streak"]
        
        # Save to database
        save_user_data(
            user_id,
            username,
            user_data["last_drочка"],
            user_data["total_drочка"],
            user_data["current_streak"],
            user_data["max_streak"],
            user_data.get("pet_name")
        )

        user_mention = format_user_mention(message.from_user)
        flame = "🔥" * min(user_data['current_streak'], 5)
        pet_part = f" на своего '{user_data['pet_name']}'" if user_data.get('pet_name') else ""
        response = f"🔥 {user_mention} подрочил{pet_part}! {flame}\n\n"
        response += "📊 Статистика:\n"
        response += f"Всего дрочков: {user_data['total_drочка']}\n"
        response += f"Текущая серия: {user_data['current_streak']} (макс: {user_data['max_streak']})"
    else:
        last_time = datetime.fromisoformat(user_data["last_drочка"])
        # время до полуночи
        midnight_next = datetime.combine(today + timedelta(days=1), datetime.min.time())
        delta = midnight_next - now
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        user_mention = format_user_mention(message.from_user)
        pet_part = f" своего '{user_data['pet_name']}'" if user_data.get('pet_name') else ""
        response = f"⏳ {user_mention}, ты уже дрочил{pet_part} сегодня!\n"
        response += f"Следующая возможность в 00:00 (через ~ {hours} ч {minutes} мин)"
    
    await message.answer(response)

@router.message(Command(commands=["дрочка", "дрочить", "drochka"]))
async def cmd_drочка(message: Message):
    await perform_drочка(message)

# React to the word "дроч" in messages
@router.message(lambda message: message.text and "дроч" in message.text.lower())
async def word_drоч(message: Message):
    await perform_drочка(message)

@router.message(Command(commands=["статистика_дрочка", "дрочка_статы", "drochka_stats"]))
async def cmd_drочка_stats(message: Message):
    user_id = str(message.from_user.id)
    data = load_data()
    
    if user_id not in data:
        await message.answer("Ты еще ни разу не дрочил! Используй /дрочка чтобы начать.")
        return
    
    user_data = data[user_id]
    user_mention = format_user_mention(message.from_user)

    response = f"📊 Статистика дрочки для {user_mention}:\n\n"
    if user_data.get('pet_name'):
        response += f"Имя дрочика: {user_data['pet_name']}\n"
    response += f"Всего дрочков: {user_data['total_drочка']}\n"
    response += f"Текущая серия: {user_data['current_streak']}\n"
    response += f"Максимальная серия: {user_data['max_streak']}\n"
    
    if user_data["last_drочка"]:
        last_time = datetime.fromisoformat(user_data["last_drочка"])
        response += f"Последний дрочок: {last_time.strftime('%d.%m.%Y %H:%M')}"
    
    await message.answer(response)

@router.message(Command(commands=["дрочик_имя","drochka_name","set_drochka_name"]))
async def cmd_set_pet_name(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("Использование: /дрочик_имя <название> (до 30 символов)")
    pet_name = parts[1].strip()
    if len(pet_name) > 30:
        return await message.answer("Слишком длинно (макс 30)")
    user_id = str(message.from_user.id)
    username = message.from_user.username or message.from_user.full_name or "Аноним"
    data = load_data()
    if user_id not in data:
        # создаём пустую запись
        data[user_id] = {
            "username": username,
            "last_drочка": None,
            "total_drочка": 0,
            "current_streak": 0,
            "max_streak": 0,
            "pet_name": None
        }
    user = data[user_id]
    user['username'] = username
    user['pet_name'] = pet_name
    save_user_data(user_id, username, user['last_drочка'], user['total_drочка'], user['current_streak'], user['max_streak'], user['pet_name'])
    await message.answer(f"Имя дрочика установлено: {pet_name}")