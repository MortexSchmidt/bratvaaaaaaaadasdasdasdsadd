from __future__ import annotations
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import json
import os
from datetime import datetime, timedelta
from typing import Dict

router = Router(name="drочка")

# File to store user data
DATA_FILE = "drочка_data.json"

def load_data() -> Dict:
    """Load user data from file"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data: Dict):
    """Save user data to file"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@router.message(Command(commands=["дрочка", "дрочить"]))
async def cmd_drочка(message: Message):
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
            "max_streak": 0
        }
    
    user_data = data[user_id]
    
    # Check if user can drочить today
    can_drочить = True
    current_time = datetime.now()
    
    if user_data["last_drочка"]:
        last_time = datetime.fromisoformat(user_data["last_drочка"])
        if current_time.date() == last_time.date():
            can_drочить = False
    
    if can_drочить:
        # Update stats
        user_data["username"] = username
        user_data["last_drочка"] = current_time.isoformat()
        user_data["total_drочка"] += 1
        user_data["current_streak"] += 1
        
        # Update max streak if needed
        if user_data["current_streak"] > user_data["max_streak"]:
            user_data["max_streak"] = user_data["current_streak"]
        
        save_data(data)
        
        response = f"🔥 {username} только что дрочил!\n\n"
        response += f"📊 Статистика:\n"
        response += f"Всего дрочков: {user_data['total_drочка']}\n"
        response += f"Текущая серия: {user_data['current_streak']}\n"
        response += f"Максимальная серия: {user_data['max_streak']}"
    else:
        last_time = datetime.fromisoformat(user_data["last_drочка"])
        next_time = (last_time + timedelta(days=1)).date()
        time_left = datetime.combine(next_time, datetime.min.time()) - current_time
        
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        response = f"⏳ {username}, ты уже дрочил сегодня!\n"
        response += f"Следующая возможность через: {hours} ч {minutes} мин"
    
    await message.answer(response)

@router.message(Command(commands=["статистика_дрочка", "дрочка_статы"]))
async def cmd_drочка_stats(message: Message):
    user_id = str(message.from_user.id)
    data = load_data()
    
    if user_id not in data:
        await message.answer("Ты еще ни разу не дрочил! Используй /дрочка чтобы начать.")
        return
    
    user_data = data[user_id]
    username = user_data["username"]
    
    response = f"📊 Статистика дрочки для {username}:\n\n"
    response += f"Всего дрочков: {user_data['total_drочка']}\n"
    response += f"Текущая серия: {user_data['current_streak']}\n"
    response += f"Максимальная серия: {user_data['max_streak']}\n"
    
    if user_data["last_drочка"]:
        last_time = datetime.fromisoformat(user_data["last_drочка"])
        response += f"Последний дрочок: {last_time.strftime('%d.%m.%Y %H:%M')}"
    
    await message.answer(response)