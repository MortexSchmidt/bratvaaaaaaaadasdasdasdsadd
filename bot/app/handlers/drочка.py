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
import math
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
            profile_status TEXT,
            last_broken_streak INTEGER DEFAULT 0,
            recovery_available INTEGER DEFAULT 0,
            recovery_stored INTEGER DEFAULT 0,
            recovery_expires TEXT
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
        'profile_status': "ALTER TABLE user_stats ADD COLUMN profile_status TEXT",
        'last_broken_streak': "ALTER TABLE user_stats ADD COLUMN last_broken_streak INTEGER DEFAULT 0",
        'recovery_available': "ALTER TABLE user_stats ADD COLUMN recovery_available INTEGER DEFAULT 0",
        'recovery_stored': "ALTER TABLE user_stats ADD COLUMN recovery_stored INTEGER DEFAULT 0",
        'recovery_expires': "ALTER TABLE user_stats ADD COLUMN recovery_expires TEXT"
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
    # Таблица владения титулами
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_titles (
            user_id TEXT,
            code TEXT,
            earned_at TEXT,
            PRIMARY KEY(user_id, code)
        )
    ''')
    # Таблица пользовательских настроек
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_prefs (
            user_id TEXT PRIMARY KEY,
            notify_daily INTEGER DEFAULT 1,
            notify_weekly INTEGER DEFAULT 1,
            notify_recover INTEGER DEFAULT 1,
            last_daily_notify TEXT
        )
    ''')
    # События (аудит)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            type TEXT,
            meta TEXT,
            ts TEXT
        )
    ''')
    # Daily quests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_quests (
            user_id TEXT,
            date TEXT,
            code TEXT,
            progress INTEGER DEFAULT 0,
            target INTEGER DEFAULT 1,
            done INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, date, code)
        )
    ''')
    # Weekly community progress (one row per ISO week)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weekly_progress (
            week_key TEXT PRIMARY KEY,
            total_actions INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weekly_participants (
            week_key TEXT,
            user_id TEXT,
            PRIMARY KEY (week_key, user_id)
        )
    ''')
    conn.commit()
    conn.close()

def load_data() -> Dict:
    """Load user data from database"""
    init_db()  # Ensure DB is initialized
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, last_drочка, total_drочка, current_streak, max_streak, COALESCE(pet_name, ""), break_notified, xp, coins, elo_ttt, ttt_wins, ttt_losses, daily_streak, last_daily, profile_status, last_broken_streak, recovery_available, recovery_stored, recovery_expires FROM user_stats')
    rows = cursor.fetchall()
    conn.close()
    
    data = {}
    for row in rows:
        (user_id, username, last_drочка, total_drочка, current_streak, max_streak, pet_name, break_notified,
         xp, coins, elo_ttt, ttt_wins, ttt_losses, daily_streak, last_daily, profile_status, last_broken_streak, recovery_available, recovery_stored, recovery_expires) = row
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
            "profile_status": profile_status or '',
            "last_broken_streak": last_broken_streak or 0,
            "recovery_available": recovery_available or 0,
            "recovery_stored": recovery_stored or 0,
            "recovery_expires": recovery_expires,
            "active_title": None
        }
    return data

def save_user_data(user_id: str, username: str, last_drочка: str, total_drочка: int, current_streak: int, max_streak: int, pet_name: str | None, break_notified: int = 0,
                   xp: int = 0, coins: int = 0, elo_ttt: int = 1000, ttt_wins: int = 0, ttt_losses: int = 0, daily_streak: int = 0,
                   last_daily: str | None = None, profile_status: str | None = None,
                   last_broken_streak: int = 0, recovery_available: int = 0, recovery_stored: int = 0, recovery_expires: str | None = None):
    """Save user data to database"""
    init_db()  # Ensure DB is initialized
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_stats 
                (user_id, username, last_drочка, total_drочка, current_streak, max_streak, pet_name, break_notified,
                 xp, coins, elo_ttt, ttt_wins, ttt_losses, daily_streak, last_daily, profile_status,
                 last_broken_streak, recovery_available, recovery_stored, recovery_expires)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, last_drочка, total_drочка, current_streak, max_streak, pet_name, break_notified,
                    xp, coins, elo_ttt, ttt_wins, ttt_losses, daily_streak, last_daily, profile_status,
                    last_broken_streak, recovery_available, recovery_stored, recovery_expires))
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
            "profile_status": '',
            "last_broken_streak": 0,
            "recovery_available": 0,
            "recovery_stored": 0,
            "recovery_expires": None
        }
    # ensure active_title column (lazy add) — stored in user_titles ownership; active stored in profile_status extension or separate table (simplified: embed into profile_status if startswith [title])
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
        ud.get('profile_status'),
        ud.get('last_broken_streak',0),
        ud.get('recovery_available',0),
        ud.get('recovery_stored',0),
        ud.get('recovery_expires')
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
    'streak_30': '🏆 Серия 30! Легенда без пропусков.',
    'streak_50': '💪 Серия 50! Полсотни выдержал.',
    'streak_100': '🛡️ Серия 100! Железная дисциплина.',
    'streak_365': '🌍 Серия 365! Целый год без пропусков.',
    'total_1000': '🚀 1000 общих действий! Космос.',
    'total_5000': '🌌 5000 тотал! Ты машина.'
}

# Маппинг ачивка -> титул
ACHIEVEMENT_TITLES = {
    'streak_10': 'Упорный',
    'streak_30': 'Легенда',
    'streak_50': 'Полсотни',
    'streak_100': 'Железный',
    'streak_365': 'Вечный',
    'total_1000': 'Тысячер',
    'total_5000': 'ПятиТысячер'
}

SHOP_ITEMS = {
    'title_flame': { 'type': 'title', 'name': '🔥 Пламенный', 'cost': 25 },
    'title_shadow': { 'type': 'title', 'name': '🌑 Теневой', 'cost': 40 },
    'title_luck': { 'type': 'title', 'name': '🍀 Везучий', 'cost': 55 },
    'freeze_token': { 'type': 'consumable', 'name': '🧊 Заморозка (1 защита серии)', 'cost': 80 }
}

def log_event(user_id: str, etype: str, meta: dict | None = None):
    try:
        init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor()
        cur.execute('INSERT INTO events(user_id,type,meta,ts) VALUES (?,?,?,?)', (user_id, etype, json_dumps(meta or {}), datetime.utcnow().isoformat()))
        conn.commit(); conn.close()
    except Exception:
        pass

def json_dumps(obj):
    import json
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return '{}'

def grant_title(user_id: str, title: str):
    init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor()
    cur.execute('INSERT OR IGNORE INTO user_titles(user_id, code, earned_at) VALUES (?,?,?)', (user_id, title, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()

def list_titles(user_id: str):
    init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor()
    cur.execute('SELECT code FROM user_titles WHERE user_id=? ORDER BY earned_at', (user_id,))
    rows=[r[0] for r in cur.fetchall()]; conn.close(); return rows

def equip_title(user_id: str, title: str):
    titles = list_titles(user_id)
    if title not in titles:
        return False
    # store inside profile_status prefix if not already
    data = load_data(); ud = data.get(user_id)
    if not ud: return False
    base_status = ud.get('profile_status') or ''
    # remove existing [..] prefix
    import re
    base_status_clean = re.sub(r'^\[[^\]]+\]\s*', '', base_status)
    new_status = f"[{title}] {base_status_clean}".strip()
    ud['profile_status'] = new_status
    persist_user(user_id, ud)
    log_event(user_id, 'equip_title', {'title': title})
    return True

def user_has_title(user_id: str, title: str) -> bool:
    return title in list_titles(user_id)

WEEKLY_GOAL = 200  # целевое количество действий на неделю

def current_week_key() -> str:
    dt = now_tz()
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"

def update_weekly_progress(user_id: str):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    week = current_week_key()
    cur.execute('INSERT OR IGNORE INTO weekly_progress(week_key,total_actions) VALUES (?,0)', (week,))
    cur.execute('UPDATE weekly_progress SET total_actions = total_actions + 1 WHERE week_key=?', (week,))
    cur.execute('INSERT OR IGNORE INTO weekly_participants(week_key,user_id) VALUES (?,?)', (week, user_id))
    conn.commit()
    conn.close()

def ensure_daily_quest(user_id: str):
    today = today_key()
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('SELECT done FROM daily_quests WHERE user_id=? AND date=? AND code=?', (user_id, today, 'daily_drochka'))
    row = cur.fetchone()
    if row is None:
        cur.execute('INSERT INTO daily_quests(user_id,date,code,progress,target,done) VALUES (?,?,?,?,?,?)', (user_id, today, 'daily_drochka', 0, 1, 0))
        conn.commit()
    conn.close()

def complete_daily_quest_if_applicable(user_id: str, ud: dict):
    today = today_key()
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('SELECT done FROM daily_quests WHERE user_id=? AND date=? AND code=?', (user_id, today, 'daily_drochka'))
    row = cur.fetchone()
    if row and row[0] == 0:
        # complete quest
        cur.execute('UPDATE daily_quests SET done=1, progress=1 WHERE user_id=? AND date=? AND code=?', (user_id, today, 'daily_drochka'))
        conn.commit()
        conn.close()
        # reward
        add_xp(ud, 2)
        add_coins(ud, 1)
        return True
    conn.close()
    return False

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
                # streak broken; enable recovery quest
                user_data['last_broken_streak'] = user_data.get('current_streak',0)
                user_data['recovery_stored'] = user_data['last_broken_streak']
                user_data['recovery_available'] = 1 if user_data['last_broken_streak'] >= 10 else 0
                user_data['recovery_expires'] = (now + timedelta(days=2)).isoformat()
                user_data['current_streak'] = 0
        user_data["username"] = username
        user_data["last_drочка"] = now.isoformat()
        user_data["total_drочка"] += 1
        user_data["current_streak"] += 1
        user_data['break_notified'] = 0
        if user_data["current_streak"] > user_data["max_streak"]:
            user_data["max_streak"] = user_data["current_streak"]
        # Daily quest ensure & completion
        ensure_daily_quest(user_id)
        quest_completed = complete_daily_quest_if_applicable(user_id, user_data)
        # Reward xp basic logic
        add_xp(user_data, 3 if user_data['current_streak'] % 10 == 0 else 1)
        # Combo coin multiplier on multiples of 7
        if user_data['current_streak'] % 7 == 0:
            mult = max(1, user_data['current_streak']//7)
            add_coins(user_data, mult)  # 7->1,14->2,21->3...
        # update weekly community progress
        update_weekly_progress(user_id)
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
        if quest_completed:
            response += "\n🎯 Daily квест выполнен (+2 XP, +1 монета)"
        streak = user_data['current_streak']
        # Award streak achievements
        for threshold in (5,10,30,50,100,365):
            if streak == threshold:
                code = f"streak_{threshold}"
                if award_achievement(user_id, code):
                    try:
                        await message.bot.send_message(message.from_user.id, f"🏅 Достижение: {ACHIEVEMENTS[code]}")
                    except Exception:
                        pass
                    # титул за ачивку
                    t = ACHIEVEMENT_TITLES.get(code)
                    if t:
                        grant_title(user_id, t)
                        try:
                            await message.bot.send_message(message.from_user.id, f"🎖 Получен титул: {t}")
                        except Exception:
                            pass
        # Total achievements
        for ttot in (1000,5000):
            if user_data['total_drочка'] == ttot:
                code = f"total_{ttot}"
                if award_achievement(user_id, code):
                    try:
                        await message.bot.send_message(message.from_user.id, f"🏅 Достижение: {ACHIEVEMENTS[code]}")
                    except Exception:
                        pass
                    t = ACHIEVEMENT_TITLES.get(code)
                    if t:
                        grant_title(user_id, t)
                        try:
                            await message.bot.send_message(message.from_user.id, f"🎖 Получен титул: {t}")
                        except Exception: pass
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
    level = int(math.sqrt(xp/10)) if xp>0 else 0
    elo = ud.get('elo_ttt',1000)
    streak = ud.get('current_streak',0)
    max_streak = ud.get('max_streak',0)
    coins = ud.get('coins',0)
    pet = ud.get('pet_name') or 'Дрочик'
    status = ud.get('profile_status') or '—'
    ttt_w = ud.get('ttt_wins',0)
    ttt_l = ud.get('ttt_losses',0)
    recovery_info = ''
    if ud.get('recovery_available') and ud.get('recovery_stored',0) > 0:
        # check expiry
        exp_raw = ud.get('recovery_expires')
        if exp_raw:
            try:
                exp_dt = datetime.fromisoformat(exp_raw)
                if exp_dt < now_tz():
                    ud['recovery_available']=0; ud['recovery_stored']=0; ud['recovery_expires']=None; persist_user(uid, ud)
                else:
                    left = exp_dt - now_tz()
                    hrs = int(left.total_seconds()//3600)
                    recovery_info = f"\n♻ Доступно восстановление {ud['recovery_stored']//2} стрика (/recover) ~ {hrs}ч" if ud['recovery_stored']>=10 else ''
            except Exception:
                pass
    response = (
        f"👤 Профиль: {username}\n"
        f"LVL: {level} | XP: {xp}\n"
        f"Монеты: {coins}\n"
        f"Streak: {streak} (max {max_streak})\n"
        f"Дрочков всего: {ud.get('total_drочка',0)}\n"
    f"Дрочик: {pet}\n"
        f"TicTacToe: {ttt_w}W/{ttt_l}L | ELO {elo}\n"
        f"Статус: {status}{recovery_info}"
    )
    await message.answer(response)

@router.message(Command(commands=["top_elo"]))
async def cmd_top_elo(message: Message):
    init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor()
    cur.execute('SELECT username, elo_ttt, ttt_wins, ttt_losses FROM user_stats WHERE elo_ttt IS NOT NULL ORDER BY elo_ttt DESC LIMIT 10')
    rows=cur.fetchall(); conn.close()
    if not rows:
        return await message.answer('Пока нет рейтинга.')
    lines=['🏆 <b>TOP ELO</b>']
    for i,(username, elo, w, l) in enumerate(rows, start=1):
        uname = username or '—'
        lines.append(f"{i}. {uname} — {elo} ({w}W/{l}L)")
    await message.answer('\n'.join(lines), parse_mode='HTML')

@router.message(Command(commands=["top_level","top_xp"]))
async def cmd_top_level(message: Message):
    init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor()
    cur.execute('SELECT username, xp FROM user_stats ORDER BY xp DESC LIMIT 10')
    rows=cur.fetchall(); conn.close()
    if not rows:
        return await message.answer('Нет данных уровней.')
    lines=['🌟 <b>TOP Уровней</b>']
    for i,(username, xp) in enumerate(rows, start=1):
        lvl = int(math.sqrt((xp or 0)/10)) if xp else 0
        lines.append(f"{i}. {username or '—'} — LVL {lvl} ({xp} XP)")
    await message.answer('\n'.join(lines), parse_mode='HTML')

@router.message(Command(commands=["shop","магазин"]))
async def cmd_shop(message: Message):
    text = ['🛒 <b>Магазин</b>']
    for code,item in SHOP_ITEMS.items():
        text.append(f"• {item['name']} — {item['cost']} монет (/buy {code})")
    await message.answer('\n'.join(text), parse_mode='HTML')

@router.message(Command(commands=["buy"]))
async def cmd_buy(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts)<2:
        return await message.answer('Использование: /buy <код>')
    code = parts[1].strip()
    if code not in SHOP_ITEMS:
        return await message.answer('Нет такого товара.')
    item = SHOP_ITEMS[code]
    uid = str(message.from_user.id)
    data = load_data(); ud=data.get(uid) or get_or_init_user(uid, message.from_user.username or '—')
    if ud.get('coins',0) < item['cost']:
        return await message.answer('Недостаточно монет.')
    # deduct
    ud['coins'] -= item['cost']
    persist_user(uid, ud)
    if item['type']=='title':
        grant_title(uid, item['name'])
        await message.answer(f"Получен титул: {item['name']}! /titles чтобы посмотреть.")
    elif item['type']=='consumable':
        # simplistic: store as title-like with prefix 'ITEM:'
        grant_title(uid, f"ITEM:{code}")
        await message.answer(f"Получен предмет: {item['name']} (хранится). Пока без применения.")
    log_event(uid, 'buy', {'code': code})

@router.message(Command(commands=["titles","титулы"]))
async def cmd_titles(message: Message):
    uid = str(message.from_user.id)
    titles = [t for t in list_titles(uid) if not t.startswith('ITEM:')]
    if not titles:
        return await message.answer('Нет титулов. Получай ачивки или покупай в /shop.')
    await message.answer('Твои титулы:\n' + '\n'.join(f"• {t}" for t in titles))

@router.message(Command(commands=["equip"]))
async def cmd_equip(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts)<2:
        return await message.answer('Использование: /equip <точноеНазваниеТитула>')
    title = parts[1].strip()
    uid = str(message.from_user.id)
    if equip_title(uid, title):
        return await message.answer(f"Активирован титул: {title}")
    await message.answer('Нет такого титула или не получен.')

@router.message(Command(commands=["notify_on"]))
async def cmd_notify_on(message: Message):
    uid=str(message.from_user.id); init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor()
    cur.execute('INSERT OR IGNORE INTO user_prefs(user_id) VALUES (?)',(uid,))
    cur.execute('UPDATE user_prefs SET notify_daily=1 WHERE user_id=?',(uid,)); conn.commit(); conn.close()
    await message.answer('Ежедневные напоминания включены.')

@router.message(Command(commands=["notify_off"]))
async def cmd_notify_off(message: Message):
    uid=str(message.from_user.id); init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor()
    cur.execute('INSERT OR IGNORE INTO user_prefs(user_id) VALUES (?)',(uid,))
    cur.execute('UPDATE user_prefs SET notify_daily=0 WHERE user_id=?',(uid,)); conn.commit(); conn.close()
    await message.answer('Ежедневные напоминания отключены.')

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

@router.message(Command(commands=["дрочик_имя","drochka_name","set_drochka_name","питомец"]))
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

@router.message(Command(commands=["drochka_top","drochka_leaders","дрочка_топ","лидеры"]))
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

@router.message(Command(commands=["drochka_achievements","дрочка_ачивки","ачивки"]))
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

@router.message(Command(commands=["recover"]))
async def cmd_recover(message: Message):
    uid = str(message.from_user.id)
    data = load_data()
    if uid not in data:
        return await message.answer("Нет данных.")
    ud = data[uid]
    if not ud.get('recovery_available') or ud.get('recovery_stored',0) < 10:
        return await message.answer("Нет доступного восстановления.")
    # check expiry
    exp_raw = ud.get('recovery_expires')
    if exp_raw:
        try:
            exp_dt = datetime.fromisoformat(exp_raw)
            if exp_dt < now_tz():
                ud['recovery_available']=0; ud['recovery_stored']=0; ud['recovery_expires']=None; persist_user(uid, ud)
                return await message.answer("Срок восстановления истёк.")
        except Exception:
            pass
    restored = max(ud.get('current_streak',0), ud.get('recovery_stored',0)//2)
    if restored <= ud.get('current_streak',0):
        return await message.answer("Нечего восстанавливать.")
    ud['current_streak'] = restored
    if ud['current_streak'] > ud.get('max_streak',0):
        ud['max_streak'] = ud['current_streak']
    ud['recovery_available']=0; ud['recovery_stored']=0; ud['recovery_expires']=None
    persist_user(uid, ud)
    await message.answer(f"♻ Восстановлено! Текущая серия теперь {ud['current_streak']}")

@router.message(Command(commands=["daily","квест"]))
async def cmd_daily(message: Message):
    uid = str(message.from_user.id)
    ensure_daily_quest(uid)
    today = today_key()
    init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor()
    cur.execute('SELECT done FROM daily_quests WHERE user_id=? AND date=? AND code=?', (uid, today, 'daily_drochka'))
    row=cur.fetchone(); conn.close()
    status = '✅ Выполнен (+2 XP, +1 монета)' if row and row[0]==1 else '⏳ Не выполнен — просто сделай /дрочка сегодня'
    await message.answer(f"🎯 Daily квест: 'Сделай ежедневку'\nСтатус: {status}")

@router.message(Command(commands=["week","неделя"]))
async def cmd_week(message: Message):
    week = current_week_key()
    init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor()
    cur.execute('SELECT total_actions FROM weekly_progress WHERE week_key=?', (week,))
    row = cur.fetchone(); total = row[0] if row else 0
    cur.execute('SELECT COUNT(*) FROM weekly_participants WHERE week_key=?', (week,))
    pcount = cur.fetchone()[0]
    conn.close()
    pct = min(100, (total*100)//WEEKLY_GOAL)
    await message.answer(f"📆 Неделя {week}\nОбщий прогресс: {total}/{WEEKLY_GOAL} ({pct}%)\nУчастников: {pcount}\nЦель: делайте ежедневку чтобы дойти до цели недели!")

# ===== ELO Update Helper for other modules (e.g., tictactoe) =====
def update_elo(user_id: str, opponent_id: str, result: float):
    """Update ELO ratings. result: 1=win,0=loss,0.5=draw for user_id perspective."""
    data = load_data()
    if user_id not in data or opponent_id not in data:
        return
    K = 32
    u = data[user_id]; o = data[opponent_id]
    Ru = u.get('elo_ttt',1000); Ro = o.get('elo_ttt',1000)
    Eu = 1/(1+10**((Ro-Ru)/400))
    new_Ru = int(round(Ru + K*(result - Eu)))
    Eo = 1/(1+10**((Ru-Ro)/400))
    new_Ro = int(round(Ro + K*((1-result) - Eo)))
    u['elo_ttt']=new_Ru; o['elo_ttt']=new_Ro
    if result == 1:
        u['ttt_wins']=u.get('ttt_wins',0)+1; o['ttt_losses']=o.get('ttt_losses',0)+1
    elif result == 0:
        o['ttt_wins']=o.get('ttt_wins',0)+1; u['ttt_losses']=u.get('ttt_losses',0)+1
    else:
        # draw doesn't count for wins/losses
        pass
    persist_user(user_id, u); persist_user(opponent_id, o)

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