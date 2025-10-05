from __future__ import annotations
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command

router = Router(name="basic")

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("салам пополам я хуеглотка")

HELP_SECTIONS = {
    "main": {
        "title": "📚 <b>Помощь — Обзор</b>",
        "text": (
            "<b>✨ Добро пожаловать!</b> Это интерактивная справка по боту.\n\n"
            "<b>⚡ Самое главное:</b>\n"
            "• <b>/profile</b> — твой профиль (уровень, монеты, ELO, титул, стрик)\n"
            "• <b>/дрочка</b> — ежедневка (ядро прогресса)\n"
            "• <b>/daily</b> — ежедневный квест | <b>/week</b> — общий прогресс недели\n"
            "• <b>/recover</b> — восстановить часть сломанного стрика (если доступно)\n"
            "• <b>/top_elo</b> | <b>/top_level</b> — рейтинги\n"
            "• <b>/shop</b> / <b>/buy</b> — магазин и покупка\n"
            "• <b>/titles</b> / <b>/equip</b> — титулы и экипировка (/equip &lt;точноеНазваниеТитула&gt;)\n"
            "• <b>/notify_on</b> / <b>/notify_off</b> — включить/выключить напоминания\n"
            "• <b>/truth</b> / <b>/tod</b> — Правда/Действие\n"
            "• <b>/tictactoe</b> — игра с ELO\n\n"
            "<b>🗂 Навигация снизу:</b> Профиль • Дрочка • П/Д • Игры • Мафия • Админ" )
    },
    "profile": {
        "title": "👤 <b>Профиль / Экономика</b>",
        "text": (
            "<b>/profile</b> — показывает: <i>LVL • XP • Монеты • Текущий/Макс стрик • Всего действий • Питомец • ELO • Статус • Активный титул</i>.\n"
            "<b>🔢 Уровень:</b> sqrt(xp/10) (временная простая формула).\n"
            "<b>🧬 XP:</b> +1 за ежедневку, +2 бонус на каждом кратном 10 стрике (+3 итого).\n"
            "<b>💰 Монеты:</b> базово 1 на кратных 10 стриках + множитель серии: (стрик // 7).\n"
            "<b>🏷 Титулы:</b> дают стиль, получаютcя за ачивки или в /shop. /titles чтобы увидеть, /equip &lt;название&gt;.\n"
            "<b>📝 /set_status</b> — статус (до 60 символов).\n"
            "<b>🐾 /питомец Имя</b> — имя 'Дрочика'.\n"
            "<b>♻ /recover:</b> половина старого стрика (если был ≥10 и сломался). Окно ~48ч." )
    },
    "drochka": {
        "title": "🔥 <b>Ежедневка (Дрочка)</b>",
        "text": (
            "<b>/дрочка</b> или слово 'дроч' — 1 раз в сутки по таймзоне (Europe/Kyiv).\n"
            "<b>🕛 Ресет:</b> в 00:00; но гибкое окно: если прошло >34ч — стрик сломается.\n"
            "<b>🏅 Ачивки стрика:</b> 5, 10, 30, 50, 100, 365 (с титулами).\n"
            "<b>💯 Ачивки суммарно:</b> 1000, 5000.\n"
            "<b>🎯 /daily:</b> квест (пока базовый) — доп. XP/монеты.\n"
            "<b>🌐 /week:</b> общий командный прогресс недели.\n"
            "<b>♻ Сломалось?</b> /recover если доступно (часть стрика).\n"
            "<b>🔔 Напоминания:</b> /notify_on чтобы не забыть.\n"
            "<b>💡 Совет:</b> держи серию ради множителя монет и титулов." )
    },
    "tod": {
        "title": "🎭 <b>Правда или Действие</b>",
        "text": (
            "<b>/truth</b> / <b>/tod</b> — создать лобби.\n"
            "<b>⚙ Режимы:</b> По кругу ⏱ / Кому угодно 🎯.\n"
            "<b>📏 Правила:</b> 1 пас или бесконечные.\n"
            "<b>🕵 Цель</b> в режиме по кругу сама выбирает тип.\n"
            "<b>🤫 Секретные задания:</b> спрашивающий пишет в ЛС → цель получает в ЛС → жмёт 'Задание выполнено'.\n"
            "<b>🔚 Завершить:</b> кнопка или /end_tod.\n"
            "<b>🎲 Random:</b> случайно Правда/Действие." )
    },
    "games": {
        "title": "🎮 <b>Игры</b>",
        "text": (
            "<b>/tictactoe</b> — крестики-нолики c ELO (старт 1000).\n"
            "<b>/top_elo</b> — топ по ELO, <b>/top_level</b> — топ уровней.\n"
            "<b>ELO:</b> классическая формула ожидания + K=32 (примерно).\n"
            "📌 План: больше мини-игр, бустеры XP, сезонные сбросы." )
    },
    "mafia": {
        "title": "🕵️ <b>Мафия (Базово)</b>",
        "text": (
            "<b>/mafia_start</b> — создать\n<b>/join_mafia</b> — вступить\n<b>/start_game_mafia</b> — старт\n"
            "<b>/vote</b> @user — голос днём\n<b>/kill_mafia</b> @user — мафия ночью\n<b>/heal_mafia</b> @user — доктор\n<b>/check_mafia</b> @user — детектив\n"
            "Дальше: расширение ролей, интеграция XP/монет, сезонные статы." )
    },
    "admin": {
        "title": "🛠 <b>Админ / Тех</b>",
        "text": (
            "<b>/refresh_commands</b> — обновить меню.\n"
            "<b>/broadcast</b> &lt;текст&gt; — рассылка.\n"
            "<b>Логи:</b> events (действия: покупки, ачивки, дрочка и т.п.)\n"
            "<b>ENV:</b> BOT_TOKEN • TIMEZONE • DB_DIR.\n"
            "<b>БД таблицы:</b> user_stats, user_achievements, user_titles, daily_quests, weekly_progress, weekly_participants, user_prefs, events.\n"
            "Планы: авто-выдача наград недели, кроны напоминаний, оптимизация индексов." )
    },
}

def build_help_keyboard(active_key: str) -> InlineKeyboardMarkup:
    buttons = []
    row1 = [
        InlineKeyboardButton(text=("📚" if active_key=="main" else "Меню"), callback_data="help:sec:main"),
        InlineKeyboardButton(text=("👤" if active_key=="profile" else "Профиль"), callback_data="help:sec:profile"),
        InlineKeyboardButton(text=("🔥" if active_key=="drochka" else "Дрочка"), callback_data="help:sec:drochka"),
    ]
    row2 = [
        InlineKeyboardButton(text=("🎭" if active_key=="tod" else "П/Д"), callback_data="help:sec:tod"),
        InlineKeyboardButton(text=("🎮" if active_key=="games" else "Игры"), callback_data="help:sec:games"),
        InlineKeyboardButton(text=("🕵️" if active_key=="mafia" else "Мафия"), callback_data="help:sec:mafia"),
    ]
    row3 = [
        InlineKeyboardButton(text=("🛠" if active_key=="admin" else "Админ"), callback_data="help:sec:admin"),
        InlineKeyboardButton(text="✖ Закрыть", callback_data="help:close"),
    ]
    buttons.extend([row1,row2,row3])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def render_help_section(key: str) -> str:
    sec = HELP_SECTIONS.get(key, HELP_SECTIONS['main'])
    return f"{sec['title']}\n\n{sec['text']}"

@router.message(Command(commands=["help"]))
async def cmd_help(message: Message):
    text = render_help_section('main')
    await message.answer(text, parse_mode="HTML", reply_markup=build_help_keyboard('main'))

@router.callback_query(F.data.startswith("help:"))
async def help_callbacks(cb: CallbackQuery):
    if not cb.data:
        return await cb.answer()
    parts = cb.data.split(":")
    if len(parts) < 2:
        return await cb.answer()
    action = parts[1]
    if action == 'close':
        try:
            await cb.message.edit_text("Закрыто.")
        except Exception:
            pass
        return await cb.answer("Закрыто")
    if action == 'sec':
        if len(parts) < 3:
            return await cb.answer()
        key = parts[2]
        text = render_help_section(key)
        try:
            await cb.message.edit_text(text, parse_mode="HTML", reply_markup=build_help_keyboard(key))
        except Exception:
            # fallback отправим новое сообщение
            await cb.message.answer(text, parse_mode="HTML", reply_markup=build_help_keyboard(key))
        return await cb.answer()
    await cb.answer()

@router.message(Command(commands=["ping"]))
async def cmd_ping(message: Message):
    await message.answer("pong")

@router.message(Command(commands=["whoami", "id"]))
async def cmd_whoami(message: Message):
    user = message.from_user
    chat = message.chat
    await message.answer(
        f"<b>User ID:</b> <code>{user.id}</code>\n" \
        f"<b>Chat ID:</b> <code>{chat.id}</code>\n" \
        f"Тип чата: {chat.type}\n" \
        "Если бот не ловит сообщения в группе — отключи privacy у BotFather."
    )

@router.message(Command(commands=["echo"]))
async def cmd_echo(message: Message):
    # удаляем саму команду
    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        await message.answer("Нужно передать текст: /echo <текст>")
    else:
        await message.answer(text[1])

@router.message(F.text.contains("бот"))
async def mention_react(message: Message):
    if message.from_user and not message.from_user.is_bot:
        try:
            # Get all chat members and mention them
            if message.chat.type in {"group", "supergroup"}:
                members = []
                async for member in message.bot.get_chat_members(message.chat.id):
                    members.append(member.user.id)
                mentions = " ".join([f"<a href='tg://user?id={user_id}'>‌</a>" for user_id in members])
                await message.reply(f"сука быстрее все сюда нахуй{mentions}", parse_mode="HTML")
            else:
                await message.reply("сука быстрее все сюда нахуй")
        except Exception:
            # Fallback to @all
            await message.reply("сука быстрее все сюда нахуй @all")
