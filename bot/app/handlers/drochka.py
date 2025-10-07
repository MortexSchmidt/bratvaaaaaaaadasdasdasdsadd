from __future__ import annotations
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import sqlite3
import os
from datetime import datetime, timedelta
try:
	from zoneinfo import ZoneInfo
except ImportError:
	from backports.zoneinfo import ZoneInfo  # type: ignore
import asyncio
from typing import Dict
import math, json, re
from .. import format_user_mention

router = Router(name="drochka")

TIMEZONE_NAME = os.getenv("TIMEZONE", "Europe/Kyiv")
TZ = ZoneInfo(TIMEZONE_NAME)
GRACE_HOURS = 34

def now_tz() -> datetime: return datetime.now(TZ)
def today_key() -> str: return now_tz().date().isoformat()
def next_midnight_delta() -> timedelta:
	now = now_tz(); nm = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0); return nm - now
def parse_saved_ts(ts: str | None) -> datetime | None:
	if not ts: return None
	try:
		dt = datetime.fromisoformat(ts)
		if dt.tzinfo is None: dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(TZ)
		else: dt = dt.astimezone(TZ)
		return dt
	except Exception: return None

def _select_db_dir():
	# 1) Пользователь мог задать DB_DIR явно
	env_dir = os.getenv("DB_DIR")
	candidates = []
	if env_dir:
		candidates.append(env_dir)
	# 2) Текущая папка (может быть read-only на Heroku / Render)
	candidates.append('.')
	# 3) tmp (обычно writable даже на read-only slug)
	candidates.append('/tmp/bratva_data')
	for c in candidates:
		try:
			os.makedirs(c, exist_ok=True)
			test_path = os.path.join(c, '__wtest__')
			with open(test_path, 'w', encoding='utf-8') as f:
				f.write('ok')
			os.remove(test_path)
			return c
		except Exception:
			continue
	# финальный fallback
	return '/tmp'

DB_BASE_DIR = _select_db_dir()
DB_FILE = os.path.join(DB_BASE_DIR, "drochka_data.db")

def init_db():
	os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
	# Попытка исправить read-only файл если он случайно с такими правами
	try:
		if os.path.exists(DB_FILE) and not os.access(DB_FILE, os.W_OK):
			# попробуем chmod если возможно
			try: os.chmod(DB_FILE, 0o664)
			except Exception: pass
	except Exception:
		pass
	conn = sqlite3.connect(DB_FILE); cur = conn.cursor()
	try:
		cur.execute('PRAGMA journal_mode=WAL')
	except Exception:
		pass
	cur.execute('''CREATE TABLE IF NOT EXISTS user_stats (
		user_id TEXT PRIMARY KEY,
		username TEXT,
		last_drochka TEXT,
		total_drochka INTEGER DEFAULT 0,
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
	)''')
	cur.execute("PRAGMA table_info(user_stats)"); cols=[r[1] for r in cur.fetchall()]
	# migrate legacy columns names with кириллица if exist
	if 'last_drочка' in cols and 'last_drochka' not in cols:
		try: cur.execute("ALTER TABLE user_stats ADD COLUMN last_drochka TEXT")
		except Exception: pass
		try: cur.execute("UPDATE user_stats SET last_drochka = last_drочка WHERE last_drочка IS NOT NULL")
		except Exception: pass
	if 'total_drочка' in cols and 'total_drochka' not in cols:
		try: cur.execute("ALTER TABLE user_stats ADD COLUMN total_drochka INTEGER DEFAULT 0")
		except Exception: pass
		try: cur.execute("UPDATE user_stats SET total_drochka = total_drочка")
		except Exception: pass
	# ensure new ascii columns exist
	add_cols = {
		'last_drochka': "ALTER TABLE user_stats ADD COLUMN last_drochka TEXT",
		'total_drochka': "ALTER TABLE user_stats ADD COLUMN total_drochka INTEGER DEFAULT 0"
	}
	for c, stmt in add_cols.items():
		cur.execute("PRAGMA table_info(user_stats)"); cols=[r[1] for r in cur.fetchall()]
		if c not in cols:
			try: cur.execute(stmt)
			except Exception: pass
	# other tables
	cur.execute('''CREATE TABLE IF NOT EXISTS user_achievements (user_id TEXT, code TEXT, earned_at TEXT, PRIMARY KEY(user_id,code))''')
	cur.execute('''CREATE TABLE IF NOT EXISTS user_titles (user_id TEXT, code TEXT, earned_at TEXT, PRIMARY KEY(user_id,code))''')
	cur.execute('''CREATE TABLE IF NOT EXISTS user_prefs (user_id TEXT PRIMARY KEY, notify_daily INTEGER DEFAULT 1, notify_weekly INTEGER DEFAULT 1, notify_recover INTEGER DEFAULT 1, last_daily_notify TEXT)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, type TEXT, meta TEXT, ts TEXT)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS daily_quests (user_id TEXT, date TEXT, code TEXT, progress INTEGER DEFAULT 0, target INTEGER DEFAULT 1, done INTEGER DEFAULT 0, PRIMARY KEY(user_id,date,code))''')
	cur.execute('''CREATE TABLE IF NOT EXISTS weekly_progress (week_key TEXT PRIMARY KEY, total_actions INTEGER DEFAULT 0)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS weekly_participants (week_key TEXT, user_id TEXT, PRIMARY KEY(week_key,user_id))''')
	conn.commit(); conn.close()

def load_data() -> Dict:
	init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor()
	# try ascii first else fallback
	try:
		cur.execute('SELECT user_id, username, last_drochka, total_drochka, current_streak, max_streak, COALESCE(pet_name, ""), break_notified, xp, coins, elo_ttt, ttt_wins, ttt_losses, daily_streak, last_daily, profile_status, last_broken_streak, recovery_available, recovery_stored, recovery_expires FROM user_stats')
	except Exception:
		cur.execute('SELECT user_id, username, last_drочка as last_drochka, total_drочка as total_drochka, current_streak, max_streak, COALESCE(pet_name, ""), break_notified, xp, coins, elo_ttt, ttt_wins, ttt_losses, daily_streak, last_daily, profile_status, last_broken_streak, recovery_available, recovery_stored, recovery_expires FROM user_stats')
	rows=cur.fetchall(); conn.close(); data={}
	for row in rows:
		(user_id, username, last_drochka, total_drochka, current_streak, max_streak, pet_name, break_notified, xp, coins, elo_ttt, ttt_wins, ttt_losses, daily_streak, last_daily, profile_status, last_broken_streak, recovery_available, recovery_stored, recovery_expires)=row
		data[user_id]={
			'username': username, 'last_drochka': last_drochka, 'total_drochka': total_drochka,
			'current_streak': current_streak,'max_streak': max_streak,'pet_name': pet_name or None,'break_notified': break_notified or 0,
			'xp': xp or 0,'coins': coins or 0,'elo_ttt': elo_ttt or 1000,'ttt_wins': ttt_wins or 0,'ttt_losses': ttt_losses or 0,
			'daily_streak': daily_streak or 0,'last_daily': last_daily,'profile_status': profile_status or '',
			'last_broken_streak': last_broken_streak or 0,'recovery_available': recovery_available or 0,'recovery_stored': recovery_stored or 0,
			'recovery_expires': recovery_expires
		}
	return data

def persist_user(user_id: str, ud: dict):
	init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor()
	cur.execute('''INSERT OR REPLACE INTO user_stats (user_id, username, last_drochka, total_drochka, current_streak, max_streak, pet_name, break_notified, xp, coins, elo_ttt, ttt_wins, ttt_losses, daily_streak, last_daily, profile_status, last_broken_streak, recovery_available, recovery_stored, recovery_expires) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
				(user_id, ud.get('username'), ud.get('last_drochka'), ud.get('total_drochka',0), ud.get('current_streak',0), ud.get('max_streak',0), ud.get('pet_name'), ud.get('break_notified',0), ud.get('xp',0), ud.get('coins',0), ud.get('elo_ttt',1000), ud.get('ttt_wins',0), ud.get('ttt_losses',0), ud.get('daily_streak',0), ud.get('last_daily'), ud.get('profile_status'), ud.get('last_broken_streak',0), ud.get('recovery_available',0), ud.get('recovery_stored',0), ud.get('recovery_expires')))
	conn.commit(); conn.close()

def get_or_init_user(user_id: str, username: str) -> dict:
	data = load_data()
	if user_id not in data:
		data[user_id] = {
			'username': username,'last_drochka': None,'total_drochka': 0,'current_streak': 0,'max_streak': 0,'pet_name': 'Дрочик','break_notified': 0,
			'xp':0,'coins':0,'elo_ttt':1000,'ttt_wins':0,'ttt_losses':0,'daily_streak':0,'last_daily':None,'profile_status':'','last_broken_streak':0,'recovery_available':0,'recovery_stored':0,'recovery_expires':None
		}
	return data[user_id]

def add_xp(ud: dict, amount: int): ud['xp']=ud.get('xp',0)+amount; return ud['xp']
def add_coins(ud: dict, amount: int): ud['coins']=ud.get('coins',0)+amount; return ud['coins']

def has_achievement(user_id: str, code: str)->bool:
	init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute('SELECT 1 FROM user_achievements WHERE user_id=? AND code=?',(user_id,code)); ok=cur.fetchone() is not None; conn.close(); return ok
def award_achievement(user_id: str, code: str):
	if has_achievement(user_id, code): return False
	init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute('INSERT OR REPLACE INTO user_achievements(user_id,code,earned_at) VALUES (?,?,?)',(user_id,code,datetime.utcnow().isoformat())); conn.commit(); conn.close(); return True

ACHIEVEMENTS = {
	'streak_5':'🔥 Серия 5! Ты начинаешь привыкать…', 'streak_10':'⚡ Серия 10! Ты официально упорный.', 'streak_30':'🏆 Серия 30! Легенда без пропусков.', 'streak_50':'💪 Серия 50! Полсотни выдержал.', 'streak_100':'🛡️ Серия 100! Железная дисциплина.', 'streak_365':'🌍 Серия 365! Целый год без пропусков.', 'total_1000':'🚀 1000 общих действий! Космос.', 'total_5000':'🌌 5000 тотал! Ты машина.'}
ACHIEVEMENT_TITLES = {'streak_10':'Упорный','streak_30':'Легенда','streak_50':'Полсотни','streak_100':'Железный','streak_365':'Вечный','total_1000':'Тысячер','total_5000':'ПятиТысячер'}
SHOP_ITEMS={'title_flame':{'type':'title','name':'🔥 Пламенный','cost':25},'title_shadow':{'type':'title','name':'🌑 Теневой','cost':40},'title_luck':{'type':'title','name':'🍀 Везучий','cost':55},'freeze_token':{'type':'consumable','name':'🧊 Заморозка (1 защита серии)','cost':80}}

def log_event(user_id:str, etype:str, meta:dict|None=None):
	try: init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute('INSERT INTO events(user_id,type,meta,ts) VALUES (?,?,?,?)',(user_id,etype,json.dumps(meta or {},ensure_ascii=False),datetime.utcnow().isoformat())); conn.commit(); conn.close()
	except Exception: pass

def grant_title(user_id:str, title:str): init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute('INSERT OR IGNORE INTO user_titles(user_id,code,earned_at) VALUES (?,?,?)',(user_id,title,datetime.utcnow().isoformat())); conn.commit(); conn.close()
def list_titles(user_id:str): init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute('SELECT code FROM user_titles WHERE user_id=? ORDER BY earned_at',(user_id,)); rows=[r[0] for r in cur.fetchall()]; conn.close(); return rows
def equip_title(user_id:str,title:str):
	titles = list_titles(user_id)
	if title not in titles:
		return False
	data = load_data()
	ud = data.get(user_id)
	if not ud:
		return False
	base_status = ud.get('profile_status') or ''
	base_status_clean = re.sub(r'^\[[^\]]+\]\s*', '', base_status)
	ud['profile_status'] = f"[{title}] {base_status_clean}".strip()
	persist_user(user_id, ud)
	log_event(user_id, 'equip_title', {'title': title})
	return True
def user_has_title(user_id:str,title:str)->bool: return title in list_titles(user_id)

WEEKLY_GOAL=200
def current_week_key()->str: iso=now_tz().isocalendar(); return f"{iso.year}-W{iso.week:02d}"
def update_weekly_progress(user_id:str): init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); wk=current_week_key(); cur.execute('INSERT OR IGNORE INTO weekly_progress(week_key,total_actions) VALUES (?,0)',(wk,)); cur.execute('UPDATE weekly_progress SET total_actions=total_actions+1 WHERE week_key=?',(wk,)); cur.execute('INSERT OR IGNORE INTO weekly_participants(week_key,user_id) VALUES (?,?)',(wk,user_id)); conn.commit(); conn.close()

def ensure_daily_quest(user_id:str):
	today=today_key(); init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); inserted=False
	try:
		cur.execute('SELECT done FROM daily_quests WHERE user_id=? AND date=? AND code=?',(user_id,today,'daily_drochka'))
		row=cur.fetchone()
		if row is None:
			cur.execute('INSERT INTO daily_quests(user_id,date,code,progress,target,done) VALUES (?,?,?,?,?,?)',(user_id,today,'daily_drochka',0,1,0))
			inserted=True
			conn.commit()
	finally:
		try: conn.close()
		except Exception: pass
	return inserted
def complete_daily_quest_if_applicable(user_id:str, ud:dict):
	today=today_key(); init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute('SELECT done FROM daily_quests WHERE user_id=? AND date=? AND code=?',(user_id,today,'daily_drochka')); row=cur.fetchone();
	if row and row[0]==0:
		cur.execute('UPDATE daily_quests SET done=1, progress=1 WHERE user_id=? AND date=? AND code=?',(user_id,today,'daily_drochka')); conn.commit(); conn.close(); add_xp(ud,2); add_coins(ud,1); return True
	conn.close(); return False

async def perform_drochka(message:Message):
	user_id=str(message.from_user.id); username=message.from_user.username or message.from_user.full_name or 'Аноним'; ud=get_or_init_user(user_id, username); ud['username']=username
	now=now_tz(); today=now.date(); last_time=parse_saved_ts(ud.get('last_drochka')); can=True
	if last_time and last_time.date()==today: can=False
	if can:
		if last_time:
			delta_hours=(now-last_time).total_seconds()/3600
			if delta_hours>GRACE_HOURS:
				ud['last_broken_streak']=ud.get('current_streak',0); ud['recovery_stored']=ud['last_broken_streak']; ud['recovery_available']=1 if ud['last_broken_streak']>=10 else 0; ud['recovery_expires']=(now+timedelta(days=2)).isoformat(); ud['current_streak']=0
		ud['last_drochka']=now.isoformat(); ud['total_drochka']=ud.get('total_drochka',0)+1; ud['current_streak']=ud.get('current_streak',0)+1; ud['break_notified']=0
		if ud['current_streak']>ud.get('max_streak',0): ud['max_streak']=ud['current_streak']
		ensure_daily_quest(user_id); quest_done=complete_daily_quest_if_applicable(user_id, ud)
		add_xp(ud, 3 if ud['current_streak']%10==0 else 1)
		if ud['current_streak']%7==0: mult=max(1, ud['current_streak']//7); add_coins(ud, mult)
		update_weekly_progress(user_id); persist_user(user_id, ud)
		# Перезагружаем данные пользователя после обновления
		ud=get_or_init_user(user_id, username)
		mention=format_user_mention(message.from_user); flame="🔥"*min(ud['current_streak'],5); pet_part=f" на своего '{ud['pet_name']}'" if ud.get('pet_name') else ''
		resp=(f"🔥 {mention} подрочил{pet_part}! {flame}\n\n📊 Статистика:\nВсего дрочков: {ud['total_drochka']}\nТекущая серия: {ud['current_streak']} (макс: {ud['max_streak']})")
		if quest_done: resp+="\n🎯 Daily квест выполнен (+2 XP, +1 монета)"
		streak=ud['current_streak']
		for th in (5,10,30,50,100,365):
			if streak==th:
				code=f"streak_{th}";
				if award_achievement(user_id, code):
					try: await message.bot.send_message(message.from_user.id, f"🏅 Достижение: {ACHIEVEMENTS[code]}")
					except Exception: pass
					t=ACHIEVEMENT_TITLES.get(code);
					if t: grant_title(user_id,t)
		for tot in (1000,5000):
			if ud['total_drochka']==tot:
				code=f"total_{tot}";
				if award_achievement(user_id, code):
					try: await message.bot.send_message(message.from_user.id, f"🏅 Достижение: {ACHIEVEMENTS[code]}")
					except Exception: pass
					t=ACHIEVEMENT_TITLES.get(code);
					if t: grant_title(user_id,t)
		await message.answer(resp)
	else:
		# Перезагружаем данные пользователя перед выводом сообщения, чтобы убедиться, что отображаются актуальные данные
		ud=get_or_init_user(user_id, username)
		delta=next_midnight_delta(); hours,remainder=divmod(int(delta.total_seconds()),3600); minutes,_=divmod(remainder,60); mention=format_user_mention(message.from_user); pet_part=f" своего '{ud['pet_name']}'" if ud.get('pet_name') else ''
		resp=(f"⏳ {mention}, ты уже дрочил{pet_part} сегодня!\nСледующая возможность в 00:00 (таймзона {TIMEZONE_NAME}) через ~ {hours} ч {minutes} мин")
		await message.answer(resp)

@router.message(Command(commands=["profile","профиль"]))
async def cmd_profile(message:Message):
	uid=str(message.from_user.id); username=message.from_user.username or message.from_user.full_name or 'Аноним'; ud=get_or_init_user(uid, username)
	xp=ud.get('xp',0); level=int(math.sqrt(xp/10)) if xp>0 else 0; elo=ud.get('elo_ttt',1000); streak=ud.get('current_streak',0); max_streak=ud.get('max_streak',0); coins=ud.get('coins',0); pet=ud.get('pet_name') or 'Дрочик'; status=ud.get('profile_status') or '—'; tw=ud.get('ttt_wins',0); tl=ud.get('ttt_losses',0)
	rec_info='' 
	if ud.get('recovery_available') and ud.get('recovery_stored',0)>0:
		exp_raw=ud.get('recovery_expires')
		if exp_raw:
			try:
				exp_dt=datetime.fromisoformat(exp_raw)
				if exp_dt<now_tz(): ud['recovery_available']=0; ud['recovery_stored']=0; ud['recovery_expires']=None; persist_user(uid,ud)
				else:
					left=exp_dt-now_tz(); hrs=int(left.total_seconds()//3600)
					rec_info=f"\n♻ Доступно восстановление {ud['recovery_stored']//2} стрика (/recover) ~ {hrs}ч" if ud['recovery_stored']>=10 else ''
			except Exception: pass
	resp=(f"👤 Профиль: {username}\nLVL: {level} | XP: {xp}\nМонеты: {coins}\nStreak: {streak} (max {max_streak})\nДрочков всего: {ud.get('total_drochka',0)}\nДрочик: {pet}\nTicTacToe: {tw}W/{tl}L | ELO {elo}\nСтатус: {status}{rec_info}")
	await message.answer(resp)

@router.message(Command(commands=["top_elo"]))
async def cmd_top_elo(message:Message):
	init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute('SELECT username, elo_ttt, ttt_wins, ttt_losses FROM user_stats WHERE elo_ttt IS NOT NULL ORDER BY elo_ttt DESC LIMIT 10'); rows=cur.fetchall(); conn.close()
	if not rows: return await message.answer('Пока нет рейтинга.')
	lines=['🏆 <b>TOP ELO</b>'];
	for i,(username, elo, w, l) in enumerate(rows, start=1): lines.append(f"{i}. {username or '—'} — {elo} ({w}W/{l}L)")
	await message.answer('\n'.join(lines), parse_mode='HTML')

@router.message(Command(commands=["top_level","top_xp"]))
async def cmd_top_level(message:Message):
	init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute('SELECT username, xp FROM user_stats ORDER BY xp DESC LIMIT 10'); rows=cur.fetchall(); conn.close()
	if not rows: return await message.answer('Нет данных уровней.')
	lines=['🌟 <b>TOP Уровней</b>']
	for i,(username, xp) in enumerate(rows, start=1): lvl=int(math.sqrt((xp or 0)/10)) if xp else 0; lines.append(f"{i}. {username or '—'} — LVL {lvl} ({xp} XP)")
	await message.answer('\n'.join(lines), parse_mode='HTML')

@router.message(Command(commands=["shop","магазин"]))
async def cmd_shop(message:Message):
	text=['🛒 <b>Магазин</b>']
	for code,item in SHOP_ITEMS.items(): text.append(f"• {item['name']} — {item['cost']} монет (/buy {code})")
	await message.answer('\n'.join(text), parse_mode='HTML')

@router.message(Command(commands=["buy"]))
async def cmd_buy(message:Message):
	parts=message.text.split(maxsplit=1)
	if len(parts)<2: return await message.answer('Использование: /buy <код>')
	code=parts[1].strip()
	if code not in SHOP_ITEMS: return await message.answer('Нет такого товара.')
	item=SHOP_ITEMS[code]; uid=str(message.from_user.id); data=load_data(); ud=data.get(uid) or get_or_init_user(uid, message.from_user.username or '—')
	if ud.get('coins',0)<item['cost']: return await message.answer('Недостаточно монет.')
	ud['coins']-=item['cost']; persist_user(uid,ud)
	if item['type']=='title': grant_title(uid,item['name']); await message.answer(f"Получен титул: {item['name']}! /titles чтобы посмотреть.")
	elif item['type']=='consumable': grant_title(uid,f"ITEM:{code}"); await message.answer(f"Получен предмет: {item['name']} (хранится). Пока без применения.")
	log_event(uid,'buy',{'code':code})

@router.message(Command(commands=["titles","титулы"]))
async def cmd_titles(message:Message):
	uid=str(message.from_user.id); titles=[t for t in list_titles(uid) if not t.startswith('ITEM:')]
	if not titles: return await message.answer('Нет титулов. Получай ачивки или покупай в /shop.')
	await message.answer('Твои титулы:\n'+'\n'.join(f"• {t}" for t in titles))

@router.message(Command(commands=["equip"]))
async def cmd_equip(message:Message):
	parts=message.text.split(maxsplit=1)
	if len(parts)<2: return await message.answer('Использование: /equip &lt;точноеНазваниеТитула&gt;')
	title=parts[1].strip(); uid=str(message.from_user.id)
	if equip_title(uid,title): return await message.answer(f"Активирован титул: {title}")
	await message.answer('Нет такого титула или не получен.')

@router.message(Command(commands=["notify_on"]))
async def cmd_notify_on(message:Message):
	uid=str(message.from_user.id); init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute('INSERT OR IGNORE INTO user_prefs(user_id) VALUES (?)',(uid,)); cur.execute('UPDATE user_prefs SET notify_daily=1 WHERE user_id=?',(uid,)); conn.commit(); conn.close(); await message.answer('Ежедневные напоминания включены.')

@router.message(Command(commands=["notify_off"]))
async def cmd_notify_off(message:Message):
	uid=str(message.from_user.id); init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute('INSERT OR IGNORE INTO user_prefs(user_id) VALUES (?)',(uid,)); cur.execute('UPDATE user_prefs SET notify_daily=0 WHERE user_id=?',(uid,)); conn.commit(); conn.close(); await message.answer('Ежедневные напоминания отключены.')

@router.message(Command(commands=["set_status","статус"]))
async def cmd_set_status(message:Message):
	parts=message.text.split(maxsplit=1)
	if len(parts)<2: return await message.answer("Использование: /set_status <текст>")
	uid=str(message.from_user.id); username=message.from_user.username or message.from_user.full_name or 'Аноним'; ud=get_or_init_user(uid, username); txt=parts[1][:60]; ud['profile_status']=txt; persist_user(uid,ud); await message.answer('Статус обновлён.')

@router.message(Command(commands=["дрочка","дрочить","drochka"]))
async def cmd_drochka(message:Message): await perform_drochka(message)

@router.message(lambda m: m.text and "дроч" in m.text.lower())
async def word_droch(message:Message): await perform_drochka(message)

@router.message(Command(commands=["статистика_дрочка","дрочка_статы","drochka_stats","drochka_stat","drochka_stats" ]))
async def cmd_drochka_stats(message:Message):
	uid=str(message.from_user.id); data=load_data();
	if uid not in data: return await message.answer("Ты еще ни разу не дрочил! Используй /дрочка чтобы начать.")
	ud=data[uid]; mention=format_user_mention(message.from_user); resp=f"📊 Статистика дрочки для {mention}:\n\n"; 
	if ud.get('pet_name'): resp+=f"Имя дрочика: {ud['pet_name']}\n"; resp+=f"Всего дрочков: {ud['total_drochka']}\nТекущая серия: {ud['current_streak']}\nМаксимальная серия: {ud['max_streak']}\n"; 
	if ud.get('last_drochka'):
		lt=parse_saved_ts(ud['last_drochka']);
		if lt: resp+=f"Последний дрочок: {lt.strftime('%d.%m.%Y %H:%M')} ({TIMEZONE_NAME})"; await message.answer(resp)

@router.message(Command(commands=["дрочик_имя","drochka_name","set_drochka_name","питомец","pet"]))
async def cmd_set_pet_name(message:Message):
	parts=message.text.split(maxsplit=1)
	if len(parts)<2: return await message.answer("Использование: /дрочик_имя <название> (до 30 символов)")
	pet_name=parts[1].strip()
	if len(pet_name)>30: return await message.answer('Слишком длинно (макс 30)')
	uid=str(message.from_user.id); username=message.from_user.username or message.from_user.full_name or 'Аноним'; data=load_data();
	if uid not in data: data[uid]={'username':username,'last_drochka':None,'total_drochka':0,'current_streak':0,'max_streak':0,'pet_name':None}
	ud=data[uid]; ud['username']=username; ud['pet_name']=pet_name; persist_user(uid,ud); await message.answer(f"Имя дрочика установлено: {pet_name}")

@router.message(Command(commands=["drochka_top","drochka_leaders","дрочка_топ","лидеры","leaders"]))
async def cmd_drochka_top(message:Message):
	init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute('SELECT user_id, username, current_streak, max_streak, total_drochka FROM user_stats ORDER BY current_streak DESC, max_streak DESC, total_drochka DESC LIMIT 10'); rows=cur.fetchall(); conn.close()
	if not rows: return await message.answer('Пока пусто.')
	lines=["🏆 ТОП 10 по текущей серии:"]
	for i,(uid,username,cur_st,max_st,total) in enumerate(rows,start=1): lines.append(f"{i}. {username or uid} — {cur_st}🔥 (макс {max_st}, всего {total})")
	await message.answer('\n'.join(lines))

@router.message(Command(commands=["drochka_achievements","дрочка_ачивки","ачивки","achievements"]))
async def cmd_drochka_achievements(message:Message):
	uid=str(message.from_user.id); init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute('SELECT code, earned_at FROM user_achievements WHERE user_id=? ORDER BY earned_at',(uid,)); rows=cur.fetchall(); conn.close()
	if not rows: return await message.answer('Пока нет достижений. Дрочь каждый день, чтобы открыть! 🔥')
	lines=['🏅 Твои достижения:']
	for code,ts in rows: lines.append(f"• {ACHIEVEMENTS.get(code, code)}")
	await message.answer('\n'.join(lines))

@router.message(Command(commands=["recover"]))
async def cmd_recover(message:Message):
	uid=str(message.from_user.id); data=load_data();
	if uid not in data: return await message.answer('Нет данных.')
	ud=data[uid]
	if not ud.get('recovery_available') or ud.get('recovery_stored',0)<10: return await message.answer('Нет доступного восстановления.')
	exp_raw=ud.get('recovery_expires')
	if exp_raw:
		try:
			exp_dt=datetime.fromisoformat(exp_raw)
			if exp_dt<now_tz(): ud['recovery_available']=0; ud['recovery_stored']=0; ud['recovery_expires']=None; persist_user(uid,ud); return await message.answer('Срок восстановления истёк.')
		except Exception: pass
	restored=max(ud.get('current_streak',0), ud.get('recovery_stored',0)//2)
	if restored<=ud.get('current_streak',0): return await message.answer('Нечего восстанавливать.')
	ud['current_streak']=restored; 
	if ud['current_streak']>ud.get('max_streak',0): ud['max_streak']=ud['current_streak']
	ud['recovery_available']=0; ud['recovery_stored']=0; ud['recovery_expires']=None; persist_user(uid,ud); await message.answer(f"♻ Восстановлено! Текущая серия теперь {ud['current_streak']}")

@router.message(Command(commands=["daily","квест"]))
async def cmd_daily(message:Message):
	uid=str(message.from_user.id); ensure_daily_quest(uid); today=today_key(); init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute('SELECT done FROM daily_quests WHERE user_id=? AND date=? AND code=?',(uid,today,'daily_drochka')); row=cur.fetchone(); conn.close(); status='✅ Выполнен (+2 XP, +1 монета)' if row and row[0]==1 else '⏳ Не выполнен — просто сделай /дрочка сегодня'; await message.answer(f"🎯 Daily квест: 'Сделай ежедневку'\nСтатус: {status}")

@router.message(Command(commands=["week","неделя"]))
async def cmd_week(message:Message):
	wk=current_week_key(); init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute('SELECT total_actions FROM weekly_progress WHERE week_key=?',(wk,)); row=cur.fetchone(); total=row[0] if row else 0; cur.execute('SELECT COUNT(*) FROM weekly_participants WHERE week_key=?',(wk,)); pcount=cur.fetchone()[0]; conn.close(); pct=min(100,(total*100)//WEEKLY_GOAL); await message.answer(f"📆 Неделя {wk}\nОбщий прогресс: {total}/{WEEKLY_GOAL} ({pct}%)\nУчастников: {pcount}\nЦель: делайте ежедневку чтобы дойти до цели недели!")

def update_elo(user_id:str, opponent_id:str, result:float):
	data=load_data();
	if user_id not in data or opponent_id not in data: return
	K=32; u=data[user_id]; o=data[opponent_id]; Ru=u.get('elo_ttt',1000); Ro=o.get('elo_ttt',1000); Eu=1/(1+10**((Ro-Ru)/400)); new_Ru=int(round(Ru+K*(result-Eu))); Eo=1/(1+10**((Ru-Ro)/400)); new_Ro=int(round(Ro+K*((1-result)-Eo))); u['elo_ttt']=new_Ru; o['elo_ttt']=new_Ro
	if result==1: u['ttt_wins']=u.get('ttt_wins',0)+1; o['ttt_losses']=o.get('ttt_losses',0)+1
	elif result==0: o['ttt_wins']=o.get('ttt_wins',0)+1; u['ttt_losses']=u.get('ttt_losses',0)+1
	persist_user(user_id,u); persist_user(opponent_id,o)

async def check_breaks_and_notify(bot):
	while True:
		try:
			init_db(); conn=sqlite3.connect(DB_FILE); cur=conn.cursor(); cur.execute('SELECT user_id, last_drochka, current_streak, break_notified FROM user_stats'); rows=cur.fetchall(); now=now_tz(); changed=[]
			for uid,last_ts,streak,notified in rows:
				if not last_ts or streak==0: continue
				lt=parse_saved_ts(last_ts); 
				if not lt: continue
				delta_hours=(now-lt).total_seconds()/3600
				if delta_hours>GRACE_HOURS and not notified:
					changed.append(uid)
					try: await bot.send_message(int(uid), '💤 Серия прервана. Ты пропустил слишком долго (>34ч). Начни заново! 🔄')
					except Exception: pass
			if changed:
				for uid in changed: cur.execute('UPDATE user_stats SET current_streak=0, break_notified=1 WHERE user_id=?',(uid,))
				conn.commit()
			conn.close()
		except Exception: pass
		await asyncio.sleep(3600)