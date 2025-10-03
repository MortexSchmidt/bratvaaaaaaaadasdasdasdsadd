from __future__ import annotations
import asyncio
from aiogram import Router, Bot
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
    ENDED = "завершена"

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
    vote_count: int = 0  # for voting

@dataclass
class MafiaGame:
    chat_id: int
    players: List[Player]
    phase: GamePhase = GamePhase.WAITING
    night_actions: Dict[str, Optional[int]] = None  # mafia_kill, doctor_heal, detective_check
    day_votes: Dict[int, int] = None  # voter_id -> target_id
    night_timer: Optional[asyncio.Task] = None
    day_timer: Optional[asyncio.Task] = None

    def __post_init__(self):
        if self.night_actions is None:
            self.night_actions = {"mafia_kill": None, "doctor_heal": None, "detective_check": None}
        if self.day_votes is None:
            self.day_votes = {}

    def get_alive_players(self) -> List[Player]:
        return [p for p in self.players if p.alive]

    def get_mafia_players(self) -> List[Player]:
        return [p for p in self.get_alive_players() if p.role == Role.MAFIA]

    def get_civilian_players(self) -> List[Player]:
        return [p for p in self.get_alive_players() if p.role != Role.MAFIA]

    def check_win_condition(self) -> Optional[str]:
        alive = self.get_alive_players()
        mafia_count = len([p for p in alive if p.role == Role.MAFIA])
        civilian_count = len(alive) - mafia_count

        if mafia_count == 0:
            return "Мирные жители победили!"
        elif mafia_count >= civilian_count:
            return "Мафия победила!"
        return None

games: Dict[int, MafiaGame] = {}

async def start_night_phase(bot: Bot, game: MafiaGame):
    game.phase = GamePhase.NIGHT
    game.night_actions = {"mafia_kill": None, "doctor_heal": None, "detective_check": None}

    alive = game.get_alive_players()
    mafia_list = "\n".join([format_user_mention_from_id(p.user_id, p.username) for p in game.get_mafia_players()])

    # Send night instructions
    for player in alive:
        if player.role == Role.MAFIA:
            await bot.send_message(player.user_id, f"🌃 Ночь наступила!\n\nВы мафия. Ваши союзники:\n{mafia_list}\n\nВыберите жертву: /kill_mafia @username")
        elif player.role == Role.DOCTOR:
            await bot.send_message(player.user_id, "🌃 Ночь наступила!\n\nВы доктор. Выберите кого лечить: /heal_mafia @username")
        elif player.role == Role.DETECTIVE:
            await bot.send_message(player.user_id, "🌃 Ночь наступила!\n\nВы детектив. Выберите кого проверить: /check_mafia @username")
        else:
            await bot.send_message(player.user_id, "🌃 Ночь наступила! Спите спокойно...")

    await bot.send_message(game.chat_id, "🌃 Наступила ночь! Все действия выполняются в ЛС бота.")

    # Start night timer (60 seconds)
    game.night_timer = asyncio.create_task(night_timeout(bot, game))

async def night_timeout(bot: Bot, game: MafiaGame):
    await asyncio.sleep(60)  # 1 minute
    await process_night_results(bot, game)

async def process_night_results(bot: Bot, game: MafiaGame):
    if game.night_timer:
        game.night_timer.cancel()

    actions = game.night_actions
    alive = game.get_alive_players()
    killed = actions.get("mafia_kill")
    healed = actions.get("doctor_heal")
    checked = actions.get("detective_check")

    result_msg = "🌅 Ночь закончилась!\n\n"

    # Detective result
    if checked is not None:
        checked_player = next((p for p in alive if p.user_id == checked), None)
        if checked_player:
            is_mafia = checked_player.role == Role.MAFIA
            detective = next((p for p in alive if p.role == Role.DETECTIVE), None)
            if detective:
                await bot.send_message(detective.user_id, f"🔍 Результат проверки: {checked_player.username} {'мафия' if is_mafia else 'не мафия'}")

    # Killing logic
    if killed is not None and killed != healed:
        killed_player = next((p for p in alive if p.user_id == killed), None)
        if killed_player:
            killed_player.alive = False
            result_msg += f"💀 Убит: {format_user_mention_from_id(killed_player.user_id, killed_player.username)}\n"
        elif healed:
            healed_player = next((p for p in alive if p.user_id == healed), None)
            if healed_player:
                result_msg += f"⚕️ Доктор вылечил: {format_user_mention_from_id(healed_player.user_id, healed_player.username)}\n"

    # Check win condition
    win_msg = game.check_win_condition()
    if win_msg:
        result_msg += f"\n{win_msg}"
        game.phase = GamePhase.ENDED
    else:
        result_msg += "\n🏙️ Наступает день!"
        await start_day_phase(bot, game)

    await bot.send_message(game.chat_id, result_msg)

async def start_day_phase(bot: Bot, game: MafiaGame):
    game.phase = GamePhase.DAY
    game.day_votes = {}

    alive_list = "\n".join([f"{i+1}. {format_user_mention_from_id(p.user_id, p.username)}" for i, p in enumerate(game.get_alive_players())])

    await bot.send_message(game.chat_id, f"🏙️ День наступил!\n\nЖивые игроки:\n{alive_list}\n\nОбсуждайте! Голосование начнется через 2 минуты.")

    # Start day timer (2 minutes)
    game.day_timer = asyncio.create_task(day_timeout(bot, game))

async def day_timeout(bot: Bot, game: MafiaGame):
    await asyncio.sleep(120)  # 2 minutes
    await start_voting_phase(bot, game)

async def start_voting_phase(bot: Bot, game: MafiaGame):
    game.phase = GamePhase.VOTING

    alive = game.get_alive_players()
    if len(alive) <= 1:
        return

    await bot.send_message(game.chat_id, "🗳️ Голосование за казнь!\n\nГолосуйте: /vote @username\n\nУ вас 1 минута!")

    await asyncio.sleep(60)  # 1 minute voting
    await process_voting_results(bot, game)

async def process_voting_results(bot: Bot, game: MafiaGame):
    if game.day_timer:
        game.day_timer.cancel()

    # Count votes
    vote_counts = {}
    for target_id in game.day_votes.values():
        vote_counts[target_id] = vote_counts.get(target_id, 0) + 1

    if not vote_counts:
        await bot.send_message(game.chat_id, "🗳️ Никто не проголосовал. Ночь наступает...")
        await start_night_phase(bot, game)
        return

    # Find player with most votes
    max_votes = max(vote_counts.values())
    candidates = [pid for pid, votes in vote_counts.items() if votes == max_votes]

    if len(candidates) > 1:
        await bot.send_message(game.chat_id, "🗳️ Ничья в голосовании. Ночь наступает...")
        await start_night_phase(bot, game)
        return

    executed_id = candidates[0]
    executed_player = next((p for p in game.get_alive_players() if p.user_id == executed_id), None)

    if executed_player:
        executed_player.alive = False
        result_msg = f"⚔️ Казнен: {format_user_mention_from_id(executed_player.user_id, executed_player.username)}\n"
        result_msg += f"Он был: {executed_player.role.value}\n\n"

        win_msg = game.check_win_condition()
        if win_msg:
            result_msg += win_msg
            game.phase = GamePhase.ENDED
        else:
            result_msg += "🌃 Ночь наступает..."
            await start_night_phase(bot, game)

        await bot.send_message(game.chat_id, result_msg)

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

    await message.answer("🎭 Роли розданы! Игра начинается...")

    # Start night phase
    await start_night_phase(message.bot, game)

@router.message(Command(commands=["kill_mafia"]))
async def cmd_kill_mafia(message: Message):
    chat_id = message.chat.id
    if chat_id not in games or games[chat_id].phase != GamePhase.NIGHT:
        return

    game = games[chat_id]
    user = message.from_user
    player = next((p for p in game.players if p.user_id == user.id), None)

    if not player or not player.alive or player.role != Role.MAFIA:
        return await message.answer("❌ Вы не можете использовать эту команду!")

    # Parse target
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Использование: /kill_mafia @username")

    target_username = args[1].lstrip('@')
    target = next((p for p in game.get_alive_players() if p.username.lower() == target_username.lower()), None)

    if not target:
        return await message.answer("❌ Игрок не найден!")

    if target.role == Role.MAFIA:
        return await message.answer("❌ Нельзя убивать своих!")

    game.night_actions["mafia_kill"] = target.user_id
    await message.answer("✅ Выбор сделан!")

@router.message(Command(commands=["heal_mafia"]))
async def cmd_heal_mafia(message: Message):
    chat_id = message.chat.id
    if chat_id not in games or games[chat_id].phase != GamePhase.NIGHT:
        return

    game = games[chat_id]
    user = message.from_user
    player = next((p for p in game.players if p.user_id == user.id), None)

    if not player or not player.alive or player.role != Role.DOCTOR:
        return await message.answer("❌ Вы не можете использовать эту команду!")

    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Использование: /heal_mafia @username")

    target_username = args[1].lstrip('@')
    target = next((p for p in game.get_alive_players() if p.username.lower() == target_username.lower()), None)

    if not target:
        return await message.answer("❌ Игрок не найден!")

    game.night_actions["doctor_heal"] = target.user_id
    await message.answer("✅ Выбор сделан!")

@router.message(Command(commands=["check_mafia"]))
async def cmd_check_mafia(message: Message):
    chat_id = message.chat.id
    if chat_id not in games or games[chat_id].phase != GamePhase.NIGHT:
        return

    game = games[chat_id]
    user = message.from_user
    player = next((p for p in game.players if p.user_id == user.id), None)

    if not player or not player.alive or player.role != Role.DETECTIVE:
        return await message.answer("❌ Вы не можете использовать эту команду!")

    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Использование: /check_mafia @username")

    target_username = args[1].lstrip('@')
    target = next((p for p in game.get_alive_players() if p.username.lower() == target_username.lower()), None)

    if not target:
        return await message.answer("❌ Игрок не найден!")

    game.night_actions["detective_check"] = target.user_id
    await message.answer("✅ Выбор сделан!")

@router.message(Command(commands=["vote"]))
async def cmd_vote(message: Message):
    chat_id = message.chat.id
    if chat_id not in games or games[chat_id].phase != GamePhase.VOTING:
        return

    game = games[chat_id]
    user = message.from_user
    player = next((p for p in game.players if p.user_id == user.id), None)

    if not player or not player.alive:
        return await message.answer("❌ Вы не можете голосовать!")

    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Использование: /vote @username")

    target_username = args[1].lstrip('@')
    target = next((p for p in game.get_alive_players() if p.username.lower() == target_username.lower()), None)

    if not target:
        return await message.answer("❌ Игрок не найден!")

    game.day_votes[user.id] = target.user_id
    await message.answer("✅ Ваш голос учтен!")