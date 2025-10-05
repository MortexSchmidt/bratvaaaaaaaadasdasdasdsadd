from __future__ import annotations
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import sqlite3
import os
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:  # python <3.9 fallback if ever
    from backports.zoneinfo import ZoneInfo  # type: ignore
import asyncio
from typing import Dict
from .. import format_user_mention

router = Router(name="drочка")

# ===== Timezone / Midnight Reset =====
TIMEZONE_NAME = os.getenv("TIMEZONE", "Europe/Kyiv")
TZ = ZoneInfo(TIMEZONE_NAME)
GRACE_HOURS = 34  # 1 day 10 hours window to keep streak

def now_tz() -> datetime:
    return datetime.now(TZ)

def today_key() -> str:
    return now_tz().date().isoformat()

def next_midnight_delta() -> timedelta:
    now = now_tz()
    nm = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return nm - now

def parse_saved_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            # трактуем старые значения как UTC и конвертируем в локальную
            dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(TZ)
        else:
            dt = dt.astimezone(TZ)
        return dt
    except Exception:
        return None

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
            break_notified INTEGER DEFAULT 0,
            xp INTEGER DEFAULT 0,
            coins INTEGER DEFAULT 0,
            elo_ttt INTEGER DEFAULT 1000,
            ttt_wins INTEGER DEFAULT 0,
            ttt_losses INTEGER DEFAULT 0,
            daily_streak INTEGER DEFAULT 0,
            last_daily TEXT,
            profile_status TEXT
        )
    ''')
    # Миграция: если старый столбец pet_name отсутствует — добавить
    cursor.execute("PRAGMA table_info(user_stats)")
    cols = [r[1] for r in cursor.fetchall()]
    if 'pet_name' not in cols:
        cursor.execute("ALTER TABLE user_stats ADD COLUMN pet_name TEXT")
    if 'break_notified' not in cols:
        cursor.execute("ALTER TABLE user_stats ADD COLUMN break_notified INTEGER DEFAULT 0")
    # New profile-related columns
    add_cols = {
        'xp': "ALTER TABLE user_stats ADD COLUMN xp INTEGER DEFAULT 0",
        'coins': "ALTER TABLE user_stats ADD COLUMN coins INTEGER DEFAULT 0",
        'elo_ttt': "ALTER TABLE user_stats ADD COLUMN elo_ttt INTEGER DEFAULT 1000",
        'ttt_wins': "ALTER TABLE user_stats ADD COLUMN ttt_wins INTEGER DEFAULT 0",
        'ttt_losses': "ALTER TABLE user_stats ADD COLUMN ttt_losses INTEGER DEFAULT 0",
        'daily_streak': "ALTER TABLE user_stats ADD COLUMN daily_streak INTEGER DEFAULT 0",
        'last_daily': "ALTER TABLE user_stats ADD COLUMN last_daily TEXT",
        'profile_status': "ALTER TABLE user_stats ADD COLUMN profile_status TEXT"
    }
    for col, stmt in add_cols.items():
        if col not in cols:
            cursor.execute(stmt)
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
    cursor.execute('SELECT user_id, username, last_drочка, total_drочка, current_streak, max_streak, COALESCE(pet_name, ""), break_notified, xp, coins, elo_ttt, ttt_wins, ttt_losses, daily_streak, last_daily, profile_status FROM user_stats')
    rows = cursor.fetchall()
    conn.close()
    
    data = {}
    for row in rows:
        (user_id, username, last_drочка, total_drочка, current_streak, max_streak, pet_name, break_notified,
         xp, coins, elo_ttt, ttt_wins, ttt_losses, daily_streak, last_daily, profile_status) = row
        data[user_id] = {
            "username": username,
            "last_drочка": last_drочка,
            "total_drочка": total_drочка,
            "current_streak": current_streak,
            "max_streak": max_streak,
            "pet_name": pet_name or None,
            "break_notified": break_notified or 0,
            "xp": xp or 0,
            "coins": coins or 0,
            "elo_ttt": elo_ttt or 1000,
            "ttt_wins": ttt_wins or 0,
            "ttt_losses": ttt_losses or 0,
            "daily_streak": daily_streak or 0,
            "last_daily": last_daily,
            "profile_status": profile_status or ''
        }
    return data

def save_user_data(user_id: str, username: str, last_drочка: str, total_drочка: int, current_streak: int, max_streak: int, pet_name: str | None, break_notified: int = 0,
                   xp: int = 0, coins: int = 0, elo_ttt: int = 1000, ttt_wins: int = 0, ttt_losses: int = 0, daily_streak: int = 0,
                   last_daily: str | None = None, profile_status: str | None = None):
    """Save user data to database"""
    init_db()  # Ensure DB is initialized
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_stats 
        (user_id, username, last_drочка, total_drочка, current_streak, max_streak, pet_name, break_notified,
         xp, coins, elo_ttt, ttt_wins, ttt_losses, daily_streak, last_daily, profile_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, last_drочка, total_drочка, current_streak, max_streak, pet_name, break_notified,
          xp, coins, elo_ttt, ttt_wins, ttt_losses, daily_streak, last_daily, profile_status))
    conn.commit()
    conn.close()

def get_or_init_user(user_id: str, username: str) -> dict:
    data = load_data()
    if user_id not in data:
        data[user_id] = {
            "username": username,
            "last_drочка": None,
            "total_drочка": 0,
            "current_streak": 0,
            "max_streak": 0,
            "pet_name": "Дрочик",
            "break_notified": 0,
            "xp": 0,
            "coins": 0,
            "elo_ttt": 1000,
            "ttt_wins": 0,
            "ttt_losses": 0,
            "daily_streak": 0,
            "last_daily": None,
            "profile_status": ''
        }
    return data[user_id]

def persist_user(user_id: str, ud: dict):
    save_user_data(
        user_id,
        ud.get('username',''),
        ud.get('last_drочка'),
        ud.get('total_drочка',0),
        ud.get('current_streak',0),
        ud.get('max_streak',0),
        ud.get('pet_name'),
        ud.get('break_notified',0),
        ud.get('xp',0),
        ud.get('coins',0),
        ud.get('elo_ttt',1000),
        ud.get('ttt_wins',0),
        ud.get('ttt_losses',0),
        ud.get('daily_streak',0),
        ud.get('last_daily'),
        ud.get('profile_status')
    )

def add_xp(ud: dict, amount: int):
    ud['xp'] = ud.get('xp',0) + amount
    # simple level calc (optional)
    return ud['xp']

def add_coins(ud: dict, amount: int):
    ud['coins'] = ud.get('coins',0) + amount
    return ud['coins']

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
    """Perform the drочка action (timezone-aware Europe/Kyiv by default)."""
    user_id = str(message.from_user.id)
    username = message.from_user.username or message.from_user.full_name or "Аноним"
    
    user_data = get_or_init_user(user_id, username)
    user_data['username'] = username
    
    # Timezone aware values
    now = now_tz()
    today = now.date()
    last_time = parse_saved_ts(user_data.get("last_drочка"))
    can_drочить = True
    if last_time and last_time.date() == today:
        can_drочить = False
    
    if can_drочить:
        if last_time:
            delta_hours = (now - last_time).total_seconds() / 3600
            if delta_hours > GRACE_HOURS:
                user_data['current_streak'] = 0
        user_data["username"] = username
        user_data["last_drочка"] = now.isoformat()
        user_data["total_drочка"] += 1
        user_data["current_streak"] += 1
        user_data['break_notified'] = 0
        if user_data["current_streak"] > user_data["max_streak"]:
            user_data["max_streak"] = user_data["current_streak"]
        # Reward xp/coins basic logic
        add_xp(user_data, 3 if user_data['current_streak'] % 10 == 0 else 1)
        if user_data['current_streak'] % 7 == 0:
            add_coins(user_data, 1)  # combo coin каждые 7 подряд
        persist_user(user_id, user_data)
        user_mention = format_user_mention(message.from_user)
        flame = "🔥" * min(user_data['current_streak'], 5)
        pet_part = f" на своего '{user_data['pet_name']}'" if user_data.get('pet_name') else ""
        response = (
            f"🔥 {user_mention} подрочил{pet_part}! {flame}\n\n"
            f"📊 Статистика:\n"
            f"Всего дрочков: {user_data['total_drочка']}\n"
            f"Текущая серия: {user_data['current_streak']} (макс: {user_data['max_streak']})"
        )
        streak = user_data['current_streak']
        if streak in (5,10,30):
            code = f"streak_{streak}"
            if award_achievement(user_id, code):
                try:
                    await message.bot.send_message(message.from_user.id, f"🏅 Достижение: {ACHIEVEMENTS[code]}")
                except Exception:
                    pass
    else:
        # Уже сегодня — показываем время до локальной полуночи
        delta = next_midnight_delta()
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        user_mention = format_user_mention(message.from_user)
        pet_part = f" своего '{user_data['pet_name']}'" if user_data.get('pet_name') else ""
        response = (
            f"⏳ {user_mention}, ты уже дрочил{pet_part} сегодня!\n"
            f"Следующая возможность в 00:00 (таймзона {TIMEZONE_NAME}) через ~ {hours} ч {minutes} мин"
        )
    
    await message.answer(response)

@router.message(Command(commands=["profile","профиль"]))
async def cmd_profile(message: Message):
    uid = str(message.from_user.id)
    username = message.from_user.username or message.from_user.full_name or "Аноним"
    ud = get_or_init_user(uid, username)
    # Level formula: lvl = floor(sqrt(xp/10))* (simple)
    xp = ud.get('xp',0)
    import math
    level = int(math.sqrt(xp/10)) if xp>0 else 0
    elo = ud.get('elo_ttt',1000)
    streak = ud.get('current_streak',0)
    max_streak = ud.get('max_streak',0)
    coins = ud.get('coins',0)
    pet = ud.get('pet_name') or 'Дрочик'
    status = ud.get('profile_status') or '—'
    ttt_w = ud.get('ttt_wins',0)
    ttt_l = ud.get('ttt_losses',0)
    response = (
        f"👤 Профиль: {username}\n"
        f"LVL: {level} | XP: {xp}\n"
        f"Монеты: {coins}\n"
        f"Streak: {streak} (max {max_streak})\n"
        f"Дрочков всего: {ud.get('total_drочка',0)}\n"
        f"Pet: {pet}\n"
        f"TicTacToe: {ttt_w}W/{ttt_l}L | ELO {elo}\n"
        f"Статус: {status}"
    )
    await message.answer(response)

@router.message(Command(commands=["set_status","статус"]))
async def cmd_set_status(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("Использование: /set_status <текст>")
    uid = str(message.from_user.id)
    username = message.from_user.username or message.from_user.full_name or "Аноним"
    ud = get_or_init_user(uid, username)
    txt = parts[1][:60]
    ud['profile_status'] = txt
    persist_user(uid, ud)
    await message.answer("Статус обновлён.")

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
        last_time = parse_saved_ts(user_data["last_drочка"])
        if last_time:
            response += f"Последний дрочок: {last_time.strftime('%d.%m.%Y %H:%M')} ({TIMEZONE_NAME})"
    
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
            now = now_tz()
            changed = []
            for uid, last_ts, streak, notified in rows:
                if not last_ts or streak == 0:
                    continue
                lt = parse_saved_ts(last_ts)
                if not lt:
                    continue
                delta_hours = (now - lt).total_seconds()/3600
                if delta_hours > GRACE_HOURS and not notified:
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