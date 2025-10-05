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
        "title": "📚 Помощь — Обзор",
        "text": (
            "<b>Добро пожаловать!</b> Это многостраничная справка.\n\n"
            "Выбирай разделы кнопками ниже. Ключевые команды:\n"
            "• /profile — профиль\n"
            "• /дрочка — ежедневное действие\n"
            "• /truth — Правда или Действие\n"
            "• /tictactoe — Крестики-нолики (если включено)\n"
            "• /лидеры /ачивки — рейтинги и достижения\n"
            "• /set_status — статус в профиле\n\n"
            "Разделы: Профиль, Дрочка, П/Д, Игры, Мафия, Админ." )
    },
    "profile": {
        "title": "👤 Профиль / Экономика",
        "text": (
            "<b>/profile</b> — показывает: уровень, XP, монеты, серию, всего действий, питомца, ELO (позже), статус.\n"
            "<b>Уровень</b>: формула тестовая sqrt(xp/10).\n"
            "<b>XP</b>: растёт за ежедневное действие (1) и бонус (+2 поверх) каждые 10 стрика.\n"
            "<b>Монеты</b>: +1 на каждом дне серии кратном 7.\n"
            "<b>/set_status</b> — установить статус (до 60 символов).\n"
            "<b>/питомец Имя</b> — задать имя питомцу (персонализация)." )
    },
    "drochka": {
        "title": "🔥 Ежедневное действие (дрочка)",
        "text": (
            "<b>/дрочка</b> или словом 'дроч' — засчитывает на сегодня. 1 раз до полуночи (таймзона Europe/Kyiv).\n"
            "<b>Серия (streak)</b> — растёт если каждый день без пропуска. >34ч перерыв — слом серии.\n"
            "<b>Награды</b>: XP +1 (обычно) / +3 (каждый 10-й день серии). Монета: каждый 7-й день серии.\n"
            "Ачивки сейчас: серии 5 / 10 / 30. Скоро расширим (50/100/365 и total 1000/5000).\n"
            "Комбо и квесты — в планах." )
    },
    "tod": {
        "title": "🎭 Правда или Действие",
        "text": (
            "<b>/truth</b> (/tod) — создать лобби в группе.\n"
            "Режимы: По кругу / Кому угодно.\n"
            "Правила: с 1 пасом или бесконечные.\n"
            "В режиме 'По кругу' цель сама выбирает (Правда / Действие / Random / Пас).\n"
            "Секретные задания: спрашивающему в ЛС — пишет, цель получает в ЛС и жмёт 'Задание выполнено'.\n"
            "Кнопка 'Завершить' у создателя. /end_tod — принудительно остановить." )
    },
    "games": {
        "title": "🎮 Игры (прочее)",
        "text": (
            "<b>/tictactoe</b> — крестики-нолики (если включено в боте). Будет ELO, победы/поражения.\n"
            "План: рейтинги, сезонные события, бустеры XP.\n"
            "Мини-игры могут давать XP/монеты (позже)." )
    },
    "mafia": {
        "title": "🕵️ Мафия (основы)",
        "text": (
            "Команды (в группе):\n"
            "/mafia_start — создать\n/join_mafia — вступить\n/start_game_mafia — старт (создатель)\n"
            "/vote @user — дневное голосование\n/kill_mafia @user — ночью (мафия)\n/heal_mafia @user — доктор\n/check_mafia @user — детектив.\n"
            "Роли и логика могут расширяться. XP интеграция — в планах." )
    },
    "admin": {
        "title": "🛠 Админ / Тех",
        "text": (
            "<b>/refresh_commands</b> — пересоздать меню команд (кеш у клиента).\n"
            "<b>/broadcast</b> <текст> — отправка админам (можно адаптировать под всех).\n"
            "Переменные окружения: BOT_TOKEN, TIMEZONE, DB_DIR.\n"
            "БД: SQLite (user_stats, user_achievements).\n"
            "Планы: журналы событий, ручная выдача наград." )
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
