from __future__ import annotations
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import sqlite3
import os
from datetime import datetime, timedelta
import asyncio
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
            pet_name TEXT,
            break_notified INTEGER DEFAULT 0
        )
    ''')
    # Миграция: если старый столбец pet_name отсутствует — добавить
    cursor.execute("PRAGMA table_info(user_stats)")
    cols = [r[1] for r in cursor.fetchall()]
    if 'pet_name' not in cols:
        cursor.execute("ALTER TABLE user_stats ADD COLUMN pet_name TEXT")
    if 'break_notified' not in cols:
        cursor.execute("ALTER TABLE user_stats ADD COLUMN break_notified INTEGER DEFAULT 0")
    # Таблица достижений
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_achievements (
            user_id TEXT,
            code TEXT,
            earned_at TEXT,
            PRIMARY KEY (user_id, code)
        )
    ''')
    conn.commit()
    conn.close()

def load_data() -> Dict:
    """Load user data from database"""
    init_db()  # Ensure DB is initialized
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, last_drочка, total_drочка, current_streak, max_streak, COALESCE(pet_name, ""), break_notified FROM user_stats')
    rows = cursor.fetchall()
    conn.close()
    
    data = {}
    for row in rows:
        user_id, username, last_drочка, total_drочка, current_streak, max_streak, pet_name, break_notified = row
        data[user_id] = {
            "username": username,
            "last_drочка": last_drочка,
            "total_drочка": total_drочка,
            "current_streak": current_streak,
            "max_streak": max_streak,
            "pet_name": pet_name or None,
            "break_notified": break_notified or 0
        }
    return data

def save_user_data(user_id: str, username: str, last_drочка: str, total_drочка: int, current_streak: int, max_streak: int, pet_name: str | None, break_notified: int = 0):
    """Save user data to database"""
    init_db()  # Ensure DB is initialized
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_stats 
        (user_id, username, last_drочка, total_drочка, current_streak, max_streak, pet_name, break_notified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, last_drочка, total_drочка, current_streak, max_streak, pet_name, break_notified))
    conn.commit()
    conn.close()

def has_achievement(user_id: str, code: str) -> bool:
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('SELECT 1 FROM user_achievements WHERE user_id=? AND code=?', (user_id, code))
    ok = cur.fetchone() is not None
    conn.close()
    return ok

def award_achievement(user_id: str, code: str):
    if has_achievement(user_id, code):
        return False
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO user_achievements(user_id, code, earned_at) VALUES (?,?,?)', (user_id, code, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return True

ACHIEVEMENTS = {
    'streak_5': '🔥 Серия 5! Ты начинаешь привыкать…',
    'streak_10': '⚡ Серия 10! Ты официально упорный.',
    'streak_30': '🏆 Серия 30! Легенда без пропусков.'
}

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
            "pet_name": None,
            "break_notified": 0
        }
    
    user_data = data[user_id]
    
    # Check if user can drочить today
    can_drочить = True
    now = datetime.now()
    today = now.date()
    last_time = None
    if user_data["last_drочка"]:
        last_time = datetime.fromisoformat(user_data["last_drочка"])
        if today == last_time.date():
            can_drочить = False
    
    if can_drочить:
        # Определение разрыва для серии с грацией 34 часа (1 день 10 часов)
        if last_time:
            delta_hours = (now - last_time).total_seconds() / 3600
            # Если уже прошло больше 34 часов со времени последнего — серия сброшена
            if delta_hours > 34:
                user_data['current_streak'] = 0
            # Если прошёл ровно один день или в пределах 34 часов — оставляем серию
            elif delta_hours <= 34 and delta_hours >= 24:
                # это день без пропуска в пределах окна – нет изменений
                pass
            elif delta_hours < 24:
                # это не должно случиться (мы бы заблокировали попытку выше), но на всякий случай
                pass
            else:
                # delta_hours >34 уже поймано, остальные случаи (большой разрыв)
                user_data['current_streak'] = 0
        # Update stats
        user_data["username"] = username
        user_data["last_drочка"] = now.isoformat()
        user_data["total_drочка"] += 1
        user_data["current_streak"] += 1
        user_data['break_notified'] = 0  # сбрасываем флаг
        
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
            user_data.get("pet_name"),
            user_data.get('break_notified',0)
        )

        user_mention = format_user_mention(message.from_user)
        flame = "🔥" * min(user_data['current_streak'], 5)
        pet_part = f" на своего '{user_data['pet_name']}'" if user_data.get('pet_name') else ""
        response = f"🔥 {user_mention} подрочил{pet_part}! {flame}\n\n"
        response += "📊 Статистика:\n"
        response += f"Всего дрочков: {user_data['total_drочка']}\n"
        response += f"Текущая серия: {user_data['current_streak']} (макс: {user_data['max_streak']})"
        # Achievement check
        streak = user_data['current_streak']
        ach_to_check = []
        if streak in (5,10,30):
            ach_to_check.append(f'streak_{streak}')
        for code in ach_to_check:
            if award_achievement(user_id, code):
                try:
                    await message.bot.send_message(message.from_user.id, f"🏅 Достижение: {ACHIEVEMENTS[code]}")
                except Exception:
                    pass
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

@router.message(Command(commands=["drochka_top","drochka_leaders","дрочка_топ"]))
async def cmd_drochka_top(message: Message):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('SELECT user_id, username, current_streak, max_streak, total_drочка FROM user_stats ORDER BY current_streak DESC, max_streak DESC, total_drочка DESC LIMIT 10')
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return await message.answer("Пока пусто.")
    lines = ["🏆 ТОП 10 по текущей серии:"]
    for i,(uid, username, cur_st, max_st, total) in enumerate(rows, start=1):
        uname = username or uid
        lines.append(f"{i}. {uname} — {cur_st}🔥 (макс {max_st}, всего {total})")
    await message.answer("\n".join(lines))

@router.message(Command(commands=["drochka_achievements","дрочка_ачивки"]))
async def cmd_drochka_achievements(message: Message):
    user_id = str(message.from_user.id)
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('SELECT code, earned_at FROM user_achievements WHERE user_id=? ORDER BY earned_at', (user_id,))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return await message.answer("Пока нет достижений. Дрочь каждый день, чтобы открыть! 🔥")
    lines=["🏅 Твои достижения:"]
    for code, ts in rows:
        desc = ACHIEVEMENTS.get(code, code)
        lines.append(f"• {desc}")
    await message.answer("\n".join(lines))

async def check_breaks_and_notify(bot):
    """Периодическая проверка: у кого междрочечный перерыв >34ч — сбрасываем серию и уведомляем."""
    while True:
        try:
            init_db()
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute('SELECT user_id, last_drочка, current_streak, break_notified FROM user_stats')
            rows = cur.fetchall()
            now = datetime.utcnow()
            changed = []
            for uid, last_ts, streak, notified in rows:
                if not last_ts or streak == 0:
                    continue
                try:
                    lt = datetime.fromisoformat(last_ts)
                except Exception:
                    continue
                delta_hours = (now - lt).total_seconds()/3600
                if delta_hours > 34 and not notified:
                    # сброс серии
                    changed.append(uid)
                    try:
                        await bot.send_message(int(uid), "💤 Серия прервана. Ты пропустил слишком долго (>34ч). Начни заново! 🔄")
                    except Exception:
                        pass
            if changed:
                for uid in changed:
                    cur.execute('UPDATE user_stats SET current_streak=0, break_notified=1 WHERE user_id=?', (uid,))
                conn.commit()
            conn.close()
        except Exception:
            # просто пропускаем один цикл если что-то сломалось
            pass
        await asyncio.sleep(3600)  # раз в час