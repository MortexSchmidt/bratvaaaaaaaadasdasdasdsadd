from __future__ import annotations
from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from typing import Dict, List, Optional
import json
import random
import os

router = Router(name="truth_or_dare")

# Load game content
CONTENT_FILE = os.path.join(os.path.dirname(__file__), '..', 'truth_or_dare_content.json')
try:
    with open(CONTENT_FILE, 'r', encoding='utf-8') as f:
        GAME_CONTENT = json.load(f)
except FileNotFoundError:
    GAME_CONTENT = {"truths": {"safe": [], "spicy": [], "risky": []}, "dares": {"safe": [], "spicy": [], "risky": []}}

# Constants for game modes
MODE_CLOCKWISE = "clockwise"  # По часовой стрелке
MODE_ANYONE = "anyone"       # Кому угодно
MODE_WITH_RULES = "with"  # С правилами
MODE_WITHOUT_RULES = "without"  # Без правил

# Rule constants
MAX_PASSES_WITH_RULES = 1 # Максимум пасов с правилами
UNLIMITED_PASSES = float('inf')  # Неограниченные пасы без правил

# Game state storage
active_games: Dict[int, Dict] = {}  # Stores active games by chat_id
lobbies: Dict[int, Dict] = {}  # Stores lobbies by chat_id
waiting_for_input: Dict[int, Dict] = {}  # Tracks players waiting to send truth/dare

class TruthOrDareGame:
    def __init__(self, chat_id: int, players: List[int], mode: str, rules_mode: str, player_names: Dict[int, str], player_usernames: Dict[int, str] = None):
        self.chat_id = chat_id
        self.players = players  # List of player IDs
        self.mode = mode  # Game mode: clockwise or anyone
        self.rules_mode = rules_mode # With rules or without rules
        self.player_names = player_names  # Dict of player_id to name
        self.player_usernames = player_usernames or {}  # Dict of player_id to username
        self.current_player_index = 0 # Index of current player
        self.passes_used: Dict[int, int] = {player_id: 0 for player_id in players}  # Track used passes (count)
        self.game_active = True
        self.waiting_for_response = None  # Player currently waiting to respond to truth/dare
        self.expected_responder = None  # Who should respond to the current truth/dare
        
    def get_current_player(self) -> int:
        """Get the current player ID"""
        return self.players[self.current_player_index]
    
    def get_next_player_clockwise(self) -> int:
        """Get the next player in clockwise order"""
        next_index = (self.current_player_index + 1) % len(self.players)
        return self.players[next_index]
    
    def set_current_player(self, player_id: int):
        """Set current player by ID"""
        if player_id in self.players:
            self.current_player_index = self.players.index(player_id)
    
    def use_pass(self, player_id: int):
        """Mark pass as used for a player"""
        if player_id in self.passes_used:
            self.passes_used[player_id] += 1
    
    def can_use_pass(self, player_id: int) -> bool:
        """Check if player can use a pass"""
        if self.rules_mode == MODE_WITH_RULES:
            # With rules: only one pass per player per game
            return self.passes_used.get(player_id, 0) < MAX_PASSES_WITH_RULES
        else:
            # Without rules: unlimited passes
            return True

def create_game_modes_keyboard():
    """Create keyboard for selecting game modes"""
    builder = InlineKeyboardBuilder()
    
    # Game type selection
    builder.button(text="🎯 По часовой стрелке", callback_data="tod:mode:clockwise")
    builder.button(text="🔥 Кому угодно", callback_data="tod:mode:anyone")
    builder.adjust(1, 1)
    
    return builder.as_markup()

def create_rules_modes_keyboard():
    """Create keyboard for selecting rules modes"""
    builder = InlineKeyboardBuilder()
    
    # Rules selection
    builder.button(text="✅ С правилами", callback_data="tod:rules:with")
    builder.button(text="❌ Без правил", callback_data="tod:rules:without")
    builder.adjust(1, 1)
    
    return builder.as_markup()

def create_truth_or_dare_choice_keyboard():
    """Create keyboard for truth or dare choice"""
    builder = InlineKeyboardBuilder()

    builder.button(text="💡 Правда", callback_data="tod:choice:truth")
    builder.button(text="🎭 Действие", callback_data="tod:choice:dare")
    builder.button(text="🎲 Случайное", callback_data="tod:choice:random")
    builder.button(text="⏭️ Пас", callback_data="tod:choice:pass")
    builder.adjust(2, 2)

    return builder.as_markup()

def create_target_player_keyboard(game: TruthOrDareGame, current_player_id: int):
    """Create keyboard for selecting target player"""
    builder = InlineKeyboardBuilder()

    for player_id in game.players:
        if player_id != current_player_id:
            # Get player display name for display
            name = get_player_display_name(player_id, game.player_names, game.player_usernames)
            builder.button(text=f"👉 {name}", callback_data=f"tod:target:{player_id}")

    builder.adjust(1) # One button per row for clarity

    return builder.as_markup()

def create_difficulty_keyboard():
    """Create keyboard for selecting difficulty level"""
    builder = InlineKeyboardBuilder()

    builder.button(text="🟢 Безопасно", callback_data="tod:difficulty:safe")
    builder.button(text="🟡 Остро", callback_data="tod:difficulty:spicy")
    builder.button(text="🔴 Рискованно", callback_data="tod:difficulty:risky")
    builder.adjust(1, 1, 1)

    return builder.as_markup()

def create_lobby_keyboard(is_creator: bool = False):
    """Create keyboard for lobby"""
    builder = InlineKeyboardBuilder()

    builder.button(text="🎮 Присоединиться", callback_data="tod:lobby:join")
    if is_creator:
        builder.button(text="🚀 Начать игру", callback_data="tod:lobby:start")
    builder.adjust(2)

    return builder.as_markup()

def get_player_display_name(player_id: int, player_names: Dict[int, str], player_usernames: Dict[int, str] = None) -> str:
    """Get the display name of the player - returns name with optional @username in parentheses"""
    name = player_names.get(player_id, "Игрок")
    if player_usernames and player_id in player_usernames and player_usernames[player_id]:
        return f'<a href="https://t.me/{player_usernames[player_id]}">{name}</a> (@{player_usernames[player_id]})'
    return name

def get_random_content(content_type: str, difficulty: str = None) -> tuple[str, str]:
    """Get random truth or dare content. Returns (content, actual_type)"""
    if content_type == "random":
        content_type = random.choice(["truth", "dare"])

    if content_type not in ["truth", "dare"]:
        return "Неверный тип контента", content_type

    key = "truths" if content_type == "truth" else "dares"

    if difficulty and difficulty in GAME_CONTENT[key]:
        options = GAME_CONTENT[key][difficulty]
    else:
        # Combine all difficulties if no specific difficulty
        options = []
        for diff in GAME_CONTENT[key].values():
            options.extend(diff)

    if not options:
        return "Контент не найден", content_type

    return random.choice(options), content_type

@router.message(Command(commands=["truthordare", "tod"]))
async def start_truth_or_dare(message: Message):
    """Start a new Truth or Dare game"""
    chat_id = message.chat.id

    # Check if there's already a game or lobby in this chat
    if chat_id in active_games or chat_id in lobbies:
        await message.answer("В этом чате уже идет игра или есть активное лобби! Дождитесь окончания или используйте /end_tod.")
        return
    
    # Initialize lobby with just the starter
    starter_id = message.from_user.id
    starter_name = message.from_user.first_name or "Игрок"
    starter_username = message.from_user.username
    lobbies[chat_id] = {
        "players": [starter_id],
        "player_names": {starter_id: starter_name},
        "player_usernames": {starter_id: starter_username}
    }
    
    # Send message asking for game mode selection
    await message.answer(
        "🎉 <b>Добро пожаловать в 'Правда или Действие 2.0'!</b> 🎉\n\n"
        "🌟 <b>Новые возможности:</b>\n"
        "• 🎲 Случайные задания с разными уровнями сложности\n"
        "• 📱 Современные вопросы и действия\n"
        "• 👥 Отображение реальных имен игроков\n\n"
        "🎯 <b>Выберите режим игры:</b>",
        reply_markup=create_game_modes_keyboard()
    )

@router.callback_query(lambda c: c.data and c.data.startswith("tod:"))
async def handle_truth_or_dare_callback(callback: CallbackQuery, bot: Bot):
    """Handle all Truth or Dare callbacks"""
    data_parts = callback.data.split(":")
    action = data_parts[1]
    chat_id = callback.message.chat.id
    
    if action == "mode":
        # Handle mode selection
        mode = data_parts[2]
        
        # Store the selected mode temporarily
        if chat_id not in lobbies:
            lobbies[chat_id] = {}
        lobbies[chat_id]["mode"] = mode
        
        # Ask for rules mode
        await callback.message.edit_text(
            "📜 <b>Выберите режим правил:</b>\n\n"
            "✅ <b>С правилами:</b> Ограниченные пасы, безопасные задания\n"
            "❌ <b>Без правил:</b> Неограниченные пасы, любая сложность",
            reply_markup=create_rules_modes_keyboard()
        )
        
        await callback.answer()
        
    elif action == "rules":
        # Handle rules mode selection
        rules_mode = data_parts[2]
        
        # Get the mode from stored data
        if chat_id in lobbies and "mode" in lobbies[chat_id]:
            mode = lobbies[chat_id]["mode"]
            players = lobbies[chat_id]["players"]
            player_names = lobbies[chat_id].get("player_names", {})
            player_usernames = lobbies[chat_id].get("player_usernames", {})

            # Create lobby instead of game
            lobbies[chat_id] = {
                "mode": mode,
                "rules_mode": rules_mode,
                "creator": players[0],
                "players": players.copy(),
                "player_names": player_names.copy(),
                "player_usernames": player_usernames.copy(),
                "message_id": None  # Will be set when sending lobby message
            }

            # Create lobby message
            rules_description = ""
            if rules_mode == MODE_WITH_RULES:
                rules_description = "С правилами ✅"
            else:
                rules_description = "Без правил ❌"

            lobby_text = (
                f"🎉 <b>Лобби 'Правда или Действие 2.0'</b> 🎉\n\n"
                f"🎯 <b>Режим:</b> {'По часовой стрелке ⏰' if mode == MODE_CLOCKWISE else 'Кому угодно 🎲'}\n"
                f"📜 <b>Правила:</b> {rules_description}\n\n"
                f"👥 <b>Игроки ({len(players)}):</b>\n"
            )

            for player_id in players:
                name = get_player_display_name(player_id, player_names, player_usernames)
                lobby_text += f"• {name}\n"

            lobby_text += "\n🎮 <b>Нажмите 'Играть' чтобы присоединиться!</b>"

            # Send lobby message and store message_id
            lobby_message = await callback.message.edit_text(
                lobby_text,
                reply_markup=create_lobby_keyboard(is_creator=True),
                parse_mode='HTML'
            )
            lobbies[chat_id]["message_id"] = lobby_message.message_id

            await callback.answer()
        else:
            await callback.answer("Ошибка при создании игры!", show_alert=True)
    
    elif action == "choice":
        choice = data_parts[2]
        
        if chat_id not in active_games:
            await callback.answer("Игра не найдена!", show_alert=True)
            return
            
        game = active_games[chat_id]
        current_player_id = callback.from_user.id
        
        # Verify it's the current player's turn
        if current_player_id != game.get_current_player():
            await callback.answer("Сейчас не ваш ход!", show_alert=True)
            return
        
        if choice == "pass":
            # Handle pass
            if game.can_use_pass(current_player_id):
                game.use_pass(current_player_id)
                
                # Move to next player based on mode
                if game.mode == MODE_CLOCKWISE:
                    next_player_id = game.get_next_player_clockwise()
                else:
                    # In "anyone" mode, we need to select next player
                    # For now, go to next player clockwise
                    next_player_id = game.get_next_player_clockwise()
                
                game.set_current_player(next_player_id)
                
                await callback.message.edit_text(
                    f"⏭️ {get_player_display_name(current_player_id, game.player_names, game.player_usernames)} использовал пас!\n"
                    f"Ход передан игроку: {get_player_display_name(next_player_id, game.player_names, game.player_usernames)}",
                    parse_mode='HTML'
                )
                
                await callback.answer("Вы использовали пас!")
            else:
                await callback.answer("Вы уже использовали пас в этой игре!", show_alert=True)
        
        elif choice == "random":
            # Ask for difficulty level
            await callback.message.edit_text(
                f"🎲 <b>Случайное задание!</b>\n\n"
                f"👤 {get_player_display_name(current_player_id, game.player_names, game.player_usernames)}, выберите уровень остроты:\n\n"
                f"🟢 <b>Безопасно:</b> Легкие и веселые задания\n"
                f"🟡 <b>Остро:</b> Более личные вопросы\n"
                f"🔴 <b>Рискованно:</b> Самые смелые задания",
                reply_markup=create_difficulty_keyboard(),
                parse_mode='HTML'
            )

        elif choice in ["truth", "dare"]:
            # Store who is creating the truth/dare
            waiting_for_input[current_player_id] = {
                "type": choice,
                "game_chat_id": chat_id,
                "creator_id": current_player_id
            }

            if game.mode == MODE_CLOCKWISE:
                # In clockwise mode, target is always the next player
                target_player_id = game.get_next_player_clockwise()

                # Send to current player instructions to send via PM
                await bot.send_message(
                    current_player_id,
                    f"📝 <b>Создание задания</b>\n\n"
                    f"Тебе нужно придумать {'вопрос для "правды"' if choice == 'truth' else 'действие для выполнения'} для игрока {get_player_display_name(target_player_id, game.player_names, game.player_usernames)}\n\n"
                    f"✍️ <b>Напиши его прямо здесь, в этом личном сообщении боту.</b>\n\n"
                    f"💡 <i>Пример вопроса:</i> 'Какой твой любимый мем в TikTok?'\n"
                    f"💡 <i>Пример действия:</i> 'Спой куплет песни голосом робота'\n\n"
                    f"После отправки задания, оно будет автоматически доставлено игроку!",
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )

                # Also notify the target player that they will receive a message
                await bot.send_message(
                    target_player_id,
                    f"Ожидайте {'вопрос для "правды"' if choice == 'truth' else 'действие для выполнения'} от игрока {get_player_display_name(current_player_id, game.player_names, game.player_usernames)} в личных сообщениях.",
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )

                # Update game state to show who is waiting for response
                game.waiting_for_response = current_player_id
                game.expected_responder = target_player_id

                await callback.message.edit_text(
                    f"🎮 {get_player_display_name(current_player_id, game.player_names)} составляет {'вопрос' if choice == 'truth' else 'действие'} для {get_player_display_name(target_player_id, game.player_names)}\n\n"
                    f"📩 <b>Важно!</b> {get_player_display_name(current_player_id, game.player_names)}, напиши задание в <b>личные сообщения боту</b>!\n"
                    f"Не пиши в общем чате - задание должно быть секретным! 🤫",
                    parse_mode='HTML'
                )

            else:  # MODE_ANYONE
                # In "anyone" mode, let the player choose the target
                await callback.message.edit_text(
                    f"🎯 {get_player_display_name(current_player_id, game.player_names)}, выберите игрока для {'вопроса' if choice == 'truth' else 'действия'}:",
                    reply_markup=create_target_player_keyboard(game, current_player_id),
                    parse_mode='HTML'
                )
        
        await callback.answer()

    elif action == "difficulty":
        # Handle difficulty selection for random content
        difficulty = data_parts[2]

        if chat_id not in active_games:
            await callback.answer("Игра не найдена!", show_alert=True)
            return

        game = active_games[chat_id]
        current_player_id = callback.from_user.id

        # Verify it's the current player's turn
        if current_player_id != game.get_current_player():
            await callback.answer("Сейчас не ваш ход!", show_alert=True)
            return

        # Generate random content
        random_content, content_type = get_random_content("random", difficulty)

        if game.mode == MODE_CLOCKWISE:
            # In clockwise mode, target is always the next player
            target_player_id = game.get_next_player_clockwise()

            # Send the random content directly
            content_description = "вопрос для 'Правды'" if content_type == "truth" else "действие"
            await bot.send_message(
                target_player_id,
                f"🎲 Вам пришло случайное задание!\n\n{content_description}: {random_content}",
                parse_mode='HTML',
                disable_web_page_preview=True
            )

            # Update game state
            game.waiting_for_response = current_player_id
            game.expected_responder = target_player_id

            await callback.message.edit_text(
                f"🎲 {get_player_display_name(current_player_id, game.player_names)} выбрал случайное задание для {get_player_display_name(target_player_id, game.player_names)}!\n"
                f"Ожидаем выполнения...",
                parse_mode='HTML'
            )

        else:  # MODE_ANYONE
            # Store the random content and ask for target
            waiting_for_input[current_player_id] = {
                "type": content_type,
                "content": random_content,
                "random": True,
                "game_chat_id": chat_id,
                "creator_id": current_player_id
            }

            await callback.message.edit_text(
                f"🎯 {get_player_display_name(current_player_id, game.player_names)}, выберите игрока для случайного задания:",
                reply_markup=create_target_player_keyboard(game, current_player_id),
                parse_mode='HTML'
            )

        await callback.answer()

    elif action == "lobby":
        sub_action = data_parts[2]

        if sub_action == "join":
            # Join lobby
            player_id = callback.from_user.id
            player_name = callback.from_user.first_name or callback.from_user.username or "Игрок"

            if chat_id not in lobbies:
                await callback.answer("Лобби не найдено!", show_alert=True)
                return

            lobby = lobbies[chat_id]
            if player_id in lobby["players"]:
                await callback.answer("Вы уже в лобби!", show_alert=True)
                return

            # Add player to lobby
            lobby["players"].append(player_id)
            lobby["player_names"][player_id] = player_name
            lobby["player_usernames"][player_id] = callback.from_user.username

            # Update lobby message
            mode = lobby["mode"]
            rules_mode = lobby["rules_mode"]
            players = lobby["players"]
            player_names = lobby["player_names"]

            rules_description = "С правилами ✅" if rules_mode == MODE_WITH_RULES else "Без правил ❌"

            lobby_text = (
                f"🎉 <b>Лобби 'Правда или Действие 2.0'</b> 🎉\n\n"
                f"🎯 <b>Режим:</b> {'По часовой стрелке ⏰' if mode == MODE_CLOCKWISE else 'Кому угодно 🎲'}\n"
                f"📜 <b>Правила:</b> {rules_description}\n\n"
                f"👥 <b>Игроки ({len(players)}):</b>\n"
            )

            for pid in players:
                name = get_player_display_name(pid, player_names, player_usernames)
                lobby_text += f"• {name}\n"

            lobby_text += "\n🎮 <b>Нажмите 'Играть' чтобы присоединиться!</b>"

            # Check if joining player is the creator - show start button accordingly
            is_creator = joining_player_id == lobby["creator"]
            # Update the main lobby message in the group chat
            lobby_msg_id = lobbies[chat_id]["message_id"]
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=lobby_msg_id,
                    text=lobby_text,
                    reply_markup=create_lobby_keyboard(is_creator),
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
            except Exception:
                # If message can't be edited, send a new one to the group
                await callback.message.answer(lobby_text, reply_markup=create_lobby_keyboard(is_creator), parse_mode='HTML', disable_web_page_preview=True)
            
            # Notify all lobby members about the new join (except the joining player)
            joining_player_id = callback.from_user.id
            for player_id in lobby["players"]:
                if player_id != joining_player_id:  # Skip the joining player
                    try:
                        await bot.send_message(
                            player_id,
                            f"🎉 <b>{player_name} присоединился к лобби!</b>\n"
                            f"👥 Всего игроков: {len(lobby['players'])}",
                            parse_mode='HTML',
                            disable_web_page_preview=True
                        )
                    except Exception:
                        pass  # User might have blocked the bot

            await callback.answer("Вы успешно присоединились к лобби!", show_alert=False)

        elif sub_action == "start":
            # Start game from lobby
            player_id = callback.from_user.id

            if chat_id not in lobbies:
                await callback.answer("Лобби не найдено!", show_alert=True)
                return

            lobby = lobbies[chat_id]
            if player_id != lobby["creator"]:
                await callback.answer("Только создатель может начать игру!", show_alert=True)
                return

            if len(lobby["players"]) < 2:
                await callback.answer("Нужно минимум 2 игрока!", show_alert=True)
                return

            # Create game from lobby
            game = TruthOrDareGame(chat_id, lobby["players"], lobby["mode"], lobby["rules_mode"], lobby["player_names"], lobby["player_usernames"])
            active_games[chat_id] = game

            # Remove lobby
            del lobbies[chat_id]

            # Notify about game start
            rules_description = ""
            if game.rules_mode == MODE_WITH_RULES:
                rules_description = (
                    "\n📜 <b>Правила игры:</b>\n"
                    "• Никаких сексуальных, насильственных, оскорбительных или опасных заданий\n"
                    "• Запрещено заставлять делать то, что может привести к травме, нарушить закон или задеть чувства человека\n"
                    "• Пас можно использовать 1 раз за игру\n\n"
                )
            else:
                rules_description = (
                    "\n📜 <b>Правила игры:</b>\n"
                    "• Пас можно использовать неограниченное количество раз\n\n"
                )

            await callback.message.edit_text(
                f"🚀 <b>Игра 'Правда или Действие 2.0' началась!</b> 🚀\n\n"
                f"🎯 <b>Режим:</b> {'По часовой стрелке ⏰' if game.mode == MODE_CLOCKWISE else 'Кому угодно 🎲'}\n"
                f"📜 <b>Правила:</b> {'С правилами ✅' if game.rules_mode == MODE_WITH_RULES else 'Без правил ❌'}\n"
                f"{rules_description}\n"
                f"👤 <b>Ход игрока:</b> {get_player_display_name(game.get_current_player(), game.player_names, game.player_usernames)}\n\n"
                f"🎮 <i>Игра началась! Удачи всем участникам!</i>",
                parse_mode='HTML'
            )

            await callback.answer()

    elif action == "target":
        # Handle target player selection (for "anyone" mode)
        target_player_id = int(data_parts[2])
        
        if chat_id not in active_games:
            await callback.answer("Игра не найдена!", show_alert=True)
            return
            
        game = active_games[chat_id]
        current_player_id = callback.from_user.id
        
        # Verify it's the current player's turn
        if current_player_id != game.get_current_player():
            await callback.answer("Сейчас не ваш ход!", show_alert=True)
            return
        
        # Check if this is random content
        if current_player_id in waiting_for_input and waiting_for_input[current_player_id].get("random"):
            # Send the pre-generated random content
            info = waiting_for_input[current_player_id]
            content = info["content"]
            content_type = info["type"]

            content_description = "вопрос для 'Правды'" if content_type == "truth" else "действие"
            await bot.send_message(
                target_player_id,
                f"🎲 Вам пришло случайное задание!\n\n{content_description}: {content}",
                parse_mode='HTML',
                disable_web_page_preview=True
            )

            # Update game state
            game.waiting_for_response = current_player_id
            game.expected_responder = target_player_id

            await callback.message.edit_text(
                f"🎲 {get_player_display_name(current_player_id, game.player_names)} выбрал случайное задание для {get_player_display_name(target_player_id, game.player_names)}!\n"
                f"Ожидаем выполнения...",
                parse_mode='HTML'
            )

            # Remove from waiting list
            del waiting_for_input[current_player_id]

        else:
            # Store who is creating the truth/dare and the target
            if current_player_id in waiting_for_input:
                waiting_for_input[current_player_id]["target_id"] = target_player_id
            else:
                waiting_for_input[current_player_id] = {
                    "type": "pending",  # Will be set when user sends the content
                    "game_chat_id": chat_id,
                    "creator_id": current_player_id,
                    "target_id": target_player_id
                }

            choice_type = waiting_for_input[current_player_id].get("type", "pending")
            if choice_type == "pending":
                # This is from the target selection, need to ask for truth/dare type again
                await callback.message.edit_text(
                    f"🎯 {get_player_display_name(current_player_id, game.player_names)}, выберите для игрока {get_player_display_name(target_player_id, game.player_names)}:",
                    reply_markup=create_truth_or_dare_choice_keyboard(),
                    parse_mode='HTML'
                )
            else:
                # Send to current player instructions to send via PM
                await bot.send_message(
                    current_player_id,
                    f"📝 <b>Создание задания</b>\n\n"
                    f"Тебе нужно придумать {'вопрос для "правды"' if choice_type == 'truth' else 'действие для выполнения'} для игрока {get_player_display_name(target_player_id, game.player_names)}\n\n"
                    f"✍️ <b>Напиши его прямо здесь, в этом личном сообщении боту.</b>\n\n"
                    f"💡 <i>Пример вопроса:</i> 'Какое твое самое неловкое свидание?'\n"
                    f"💡 <i>Пример действия:</i> 'Сделай 20 отжиманий или имитацию'\n\n"
                    f"После отправки задания, оно будет автоматически доставлено игроку!",
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )

                # Also notify the target player that they will receive a message
                await bot.send_message(
                    target_player_id,
                    f"Ожидайте {'вопрос для "правды"' if choice_type == 'truth' else 'действие для выполнения'} от игрока {get_player_display_name(current_player_id, game.player_names)} в личных сообщениях.",
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )

                # Update game state to show who is waiting for response
                game.waiting_for_response = current_player_id
                game.expected_responder = target_player_id

                await callback.message.edit_text(
                    f"🎮 {get_player_display_name(current_player_id, game.player_names)} составляет {'вопрос' if choice_type == 'truth' else 'действие'} для {get_player_display_name(target_player_id, game.player_names)}\n\n"
                    f"📩 <b>Важно!</b> {get_player_display_name(current_player_id, game.player_names)}, напиши задание в <b>личные сообщения боту</b>!\n"
                    f"Не пиши в общем чате - задание должно быть секретным! 🤫",
                    parse_mode='HTML'
                )
        
        await callback.answer()

@router.message(Command(commands=["end_tod", "stop_tod"]))
async def end_truth_or_dare(message: Message):
    """End the current Truth or Dare game/lobby"""
    chat_id = message.chat.id
    sender_id = message.from_user.id

    if chat_id in active_games:
        # End active game
        game = active_games[chat_id]
        game_creator = game.players[0]  # First player is considered the creator

        if sender_id != game_creator:
            await message.answer("Только создатель игры может завершить игру!")
            return

        # Remove the game
        del active_games[chat_id]

        # Clear any waiting states
        for player_id in list(waiting_for_input.keys()):
            if waiting_for_input[player_id]["game_chat_id"] == chat_id:
                del waiting_for_input[player_id]

        await message.answer("🎮 Игра 'Правда или действие' завершена!")

    elif chat_id in lobbies:
        # End lobby
        lobby = lobbies[chat_id]
        lobby_creator = lobby["creator"]

        if sender_id != lobby_creator:
            await message.answer("Только создатель лобби может его закрыть!")
            return

        # Remove the lobby
        del lobbies[chat_id]

        await message.answer("🎉 Лобби 'Правда или действие' закрыто!")

    else:
        await message.answer("В этом чате нет активной игры или лобби 'Правда или действие'!")

# Handler for joining a game (legacy command, now uses buttons)
@router.message(Command(commands=["join_tod"]))
async def join_truth_or_dare(message: Message, bot: Bot):
    """Allow a player to join an existing lobby/game"""
    chat_id = message.chat.id
    player_id = message.from_user.id

    if chat_id in active_games:
        game = active_games[chat_id]

        if player_id in game.players:
            await message.answer("Вы уже в этой игре!")
            return

        # Add player to the game
        player_name = message.from_user.first_name or message.from_user.username or "Игрок"
        game.players.append(player_id)
        game.player_names[player_id] = player_name
        game.passes_used[player_id] = 0  # Initialize pass count

        # Notify all players about the new join
        await message.answer(
            f"🎉 <b>{player_name} присоединился к игре!</b>\n"
            f"👥 Всего игроков: {len(game.players)}\n\n"
            f"🎮 Продолжаем веселье!",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    elif chat_id in lobbies:
        lobby = lobbies[chat_id]

        if player_id in lobby["players"]:
            await message.answer("Вы уже в лобби!")
            return

        # Add player to lobby
        player_name = message.from_user.first_name or "Игрок"
        player_username = message.from_user.username
        lobby["players"].append(player_id)
        lobby["player_names"][player_id] = player_name
        lobby["player_usernames"][player_id] = player_username

        # Update lobby message if exists
        if lobby.get("message_id"):
            mode = lobby["mode"]
            rules_mode = lobby.get("rules_mode", MODE_WITHOUT_RULES)
            players = lobby["players"]
            player_names = lobby["player_names"]

            rules_description = "С правилами ✅" if rules_mode == MODE_WITH_RULES else "Без правил ❌"

            lobby_text = (
                f"🎉 <b>Лобби 'Правда или Действие 2.0'</b> 🎉\n\n"
                f"🎯 <b>Режим:</b> {'По часовой стрелке ⏰' if mode == MODE_CLOCKWISE else 'Кому угодно 🎲'}\n"
                f"📜 <b>Правила:</b> {rules_description}\n\n"
                f"👥 <b>Игроки ({len(players)}):</b>\n"
            )

            for pid in players:
                name = get_player_display_name(pid, player_names, player_usernames)
                lobby_text += f"• {name}\n"

            lobby_text += "\n🎮 <b>Нажмите 'Играть' чтобы присоединиться!</b>"

            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=lobby["message_id"],
                    text=lobby_text,
                    reply_markup=create_lobby_keyboard(player_id == lobby["creator"]),
                    parse_mode='HTML'
                )
            except:
                pass  # Message might be too old to edit

        await message.answer(
            f"🎉 <b>{player_name} присоединился к лобби!</b>\n"
            f"👥 Всего игроков: {len(lobby['players'])}\n\n"
            f"🎮 Используйте кнопку 'Играть' в лобби!",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    else:
        await message.answer("В этом чате нет активного лобби или игры 'Правда или действие'!\n\nИспользуйте /truthordare чтобы создать лобби.")

# Main handler for all messages
@router.message()
async def handle_all_messages(message: Message, bot: Bot):
    """Handle all messages - PMs for sending truth/dare, group chat for responses"""
    chat_type = message.chat.type
    
    if chat_type == "private":
        # Handle private messages (truth/dare content being sent)
        sender_id = message.from_user.id
        
        # Check if this user is supposed to be sending a truth/dare
        if sender_id in waiting_for_input:
            # Get the stored info about what they're supposed to send
            info = waiting_for_input[sender_id]
            
            if "target_id" in info:
                target_player_id = info["target_id"]
            else:
                # In clockwise mode, get the next player
                game_chat_id = info["game_chat_id"]
                if game_chat_id in active_games:
                    game = active_games[game_chat_id]
                    target_player_id = game.get_next_player_clockwise()
                else:
                    await message.answer("Ошибка: игра не найдена!")
                    return
            
            # Send the truth/dare content to the target player
            content_type = "вопрос для 'Правды'" if info["type"] == "truth" else "действие"
            game = active_games[game_chat_id]
            await bot.send_message(
                target_player_id,
                f"🎭 <b>Вам пришло задание!</b>\n\n"
                f"📝 <b>Тип:</b> {content_type}\n"
                f"👤 <b>От:</b> {get_player_display_name(sender_id, game.player_names)}\n\n"
                f"❓ <b>Задание:</b>\n{message.text}\n\n"
                f"💬 <i>Ответьте в общем чате после выполнения!</i>",
                parse_mode='HTML',
                disable_web_page_preview=True
            )

            # Also send a confirmation to the sender
            await message.answer(f"✅ <b>Отлично!</b> Ваше задание отправлено игроку {get_player_display_name(target_player_id, game.player_names)}!\n\nОжидаем выполнения... 🎉", parse_mode='HTML', disable_web_page_preview=True)
            
            # Update the game state to show it's waiting for the target to respond
            game_chat_id = info["game_chat_id"]
            if game_chat_id in active_games:
                game = active_games[game_chat_id]
                
                # In clockwise mode, after target responds, it's the next player's turn
                # In anyone mode, the target becomes the next player to choose
                if game.mode == MODE_CLOCKWISE:
                    # After target responds, it's next player's turn
                    next_after_target_idx = (game.players.index(target_player_id) + 1) % len(game.players)
                    next_player_id = game.players[next_after_target_idx]
                    game.set_current_player(next_player_id)
                else:
                    # In anyone mode, the target gets to choose next
                    game.set_current_player(target_player_id)
                
                # Update main chat about the new state
                await bot.send_message(
                    game_chat_id,
                    f"📨 <b>{get_player_display_name(target_player_id, game.player_names)} получил задание!</b> 📨\n\n"
                    f"🎯 Следующий ход: {get_player_display_name(game.get_current_player(), game.player_names)}\n\n"
                    f"⏳ <i>Ждем выполнения задания...</i>",
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
            
            # Remove from waiting list
            del waiting_for_input[sender_id]
        else:
            # Check if this is the target player responding to a truth
            # In a real implementation, we'd need to track this differently
            # For now, just acknowledge the message
            await message.answer("Если вы получили задание 'Правда или действие', просто выполните его или ответьте на вопрос в чате.")
    
    else:
        # Handle group chat messages (responses to truth/dare)
        chat_id = message.chat.id
        
        # Only process if this is an active game
        if chat_id in active_games:
            game = active_games[chat_id]
            player_id = message.from_user.id
            
            # Check if this player is expected to respond to a truth/dare
            # For this, we need to track who was given the truth/dare
            # This is complex to track, so we'll create a simple implementation
            # where any player can respond to indicate they've completed the task
            
            # If the message is a response to a truth/dare (not a command)
            if not message.text.startswith('/'):
                # Check if this player is the one who was supposed to respond
                # In our implementation, the "expected_responder" is set when a truth/dare is created
                if game.expected_responder == player_id:
                    # Mark the task as completed and move to next player based on game mode
                    if game.mode == MODE_CLOCKWISE:
                        # Next turn goes to the next player after the one who responded
                        next_player_idx = (game.players.index(player_id) + 1) % len(game.players)
                        next_player_id = game.players[next_player_idx]
                    else:  # MODE_ANYONE
                        # In anyone mode, the responder gets to choose next
                        next_player_id = player_id
                    
                    game.set_current_player(next_player_id)
                    
                    # Reset the expected responder
                    game.expected_responder = None
                    game.waiting_for_response = None
                    
                    # Notify the chat about the response
                    response_type = "ответил на вопрос" if "правду" in message.text.lower() or "вопрос" in message.text.lower() else "выполнил задание"
                    await message.answer(
                        f"✅ <b>Отлично!</b> {get_player_display_name(player_id, game.player_names)} {response_type}! 🎉\n\n"
                        f"🎯 Ход переходит к: {get_player_display_name(next_player_id, game.player_names)}\n\n"
                        f"🔥 <i>Продолжаем игру!</i>",
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                else:
                    # This is a general message, not a response to a truth/dare
                    pass