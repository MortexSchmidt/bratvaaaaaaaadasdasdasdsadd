from __future__ import annotations
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import random
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from .. import format_user_mention, format_user_mention_from_id

router = Router(name="mafia")

class GamePhase(Enum):
    WAITING = "ожидание"
    NIGHT = "ночь"
    DAY = "день"
    VOTING = "голосование"

class Role(Enum):
    MAFIA = "мафия"
    CIVILIAN = "мирный"
    DETECTIVE = "детектив"
    DOCTOR = "доктор"

@dataclass
class Player:
    user_id: int
    username: str
    role: Optional[Role] = None
    alive: bool = True

@dataclass
class MafiaGame:
    chat_id: int
    players: List[Player]
    phase: GamePhase = GamePhase.WAITING
    night_actions: Dict[str, int] = None  # mafia_kill, doctor_heal, detective_check

    def __post_init__(self):
        if self.night_actions is None:
            self.night_actions = {}

games: Dict[int, MafiaGame] = {}

@router.message(Command(commands=["mafia"]))
async def cmd_mafia(message: Message):
    text = (
        "🎭 <b>Мафия</b>\n\n"
        "Игра в мафию - это классическая социальная игра, где игроки делятся на роли:\n"
        "• Мафия - убивает по ночам\n"
        "• Мирные жители - голосуют днем\n"
        "• Детектив - проверяет роли\n"
        "• Доктор - лечит\n\n"
        "Используйте /mafia_start для начала игры в группе."
    )
    await message.answer(text)

@router.message(Command(commands=["mafia_start"]))
async def cmd_mafia_start(message: Message):
    if message.chat.type not in {"group", "supergroup"}:
        return await message.answer("🎭 Игра в мафию доступна только в группах!")

    chat_id = message.chat.id
    if chat_id in games:
        return await message.answer("🎭 Игра уже идет в этом чате!")

    user = message.from_user
    player = Player(user.id, user.username or "Неизвестный")
    game = MafiaGame(chat_id, [player])
    games[chat_id] = game

    player_mention = format_user_mention_from_id(player.user_id, player.username)
    await message.answer(
        "🎭 <b>Игра в мафию начинается!</b>\n\n"
        f"Игрок {player_mention} присоединился.\n"
        "Другие присоединяйтесь с помощью /join_mafia\n"
        "Админ может начать игру с /start_game_mafia"
    )

@router.message(Command(commands=["join_mafia"]))
async def cmd_join_mafia(message: Message):
    chat_id = message.chat.id
    if chat_id not in games:
        return await message.answer("🎭 Нет активной игры. Начните с /mafia_start")

    game = games[chat_id]
    user = message.from_user
    if any(p.user_id == user.id for p in game.players):
        return await message.answer("🎭 Вы уже в игре!")

    player = Player(user.id, user.username or "Неизвестный")
    game.players.append(player)
    player_mention = format_user_mention_from_id(player.user_id, player.username)
    await message.answer(f"🎭 {player_mention} присоединился к игре! Игроков: {len(game.players)}")

@router.message(Command(commands=["start_game_mafia"]))
async def cmd_start_game_mafia(message: Message):
    chat_id = message.chat.id
    if chat_id not in games:
        return await message.answer("🎭 Нет активной игры.")

    game = games[chat_id]
    if len(game.players) < 4:
        return await message.answer("🎭 Нужно минимум 4 игрока!")

    # Распределение ролей
    roles = [Role.MAFIA] * (len(game.players) // 3) + [Role.CIVILIAN] * (len(game.players) - len(game.players) // 3 - 2) + [Role.DETECTIVE, Role.DOCTOR]
    random.shuffle(roles)

    for i, player in enumerate(game.players):
        player.role = roles[i]

    game.phase = GamePhase.NIGHT

    # Отправка ролей в ЛС игрокам
    for player in game.players:
        role_desc = {
            Role.MAFIA: "🌃 Вы мафия! Ночью убивайте с помощью /kill_mafia <номер>",
            Role.CIVILIAN: "🏘️ Вы мирный житель! Голосуйте днем.",
            Role.DETECTIVE: "🔍 Вы детектив! Ночью проверяйте с помощью /check_mafia <номер>",
            Role.DOCTOR: "⚕️ Вы доктор! Ночью лечите с помощью /heal_mafia <номер>"
        }[player.role]

        try:
            await message.bot.send_message(player.user_id, f"🎭 Ваша роль: {role_desc}")
        except:
            pass  # Если не может отправить в ЛС

    await message.answer("🎭 Роли розданы! Наступает ночь. Действуйте в ЛС.")

@router.message(Command(commands=["kill_mafia"]))
async def cmd_kill_mafia(message: Message):
    # Логика убийства мафией
    await message.answer("Эта функция пока не реализована полностью.")

# Остальные команды аналогично