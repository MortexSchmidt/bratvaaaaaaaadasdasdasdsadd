from __future__ import annotations
from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from typing import Dict, List, Optional

router = Router(name="truth_or_dare")

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
game_invites: Dict[int, Dict] = {}  # Stores game invite info
waiting_for_input: Dict[int, Dict] = {}  # Tracks players waiting to send truth/dare

class TruthOrDareGame:
    def __init__(self, chat_id: int, players: List[int], mode: str, rules_mode: str):
        self.chat_id = chat_id
        self.players = players  # List of player IDs
        self.mode = mode  # Game mode: clockwise or anyone
        self.rules_mode = rules_mode # With rules or without rules
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
    builder.button(text="⏭️ Пас", callback_data="tod:choice:pass")
    builder.adjust(1, 1, 1)
    
    return builder.as_markup()

def create_target_player_keyboard(game: TruthOrDareGame, current_player_id: int):
    """Create keyboard for selecting target player"""
    builder = InlineKeyboardBuilder()
    
    for player_id in game.players:
        if player_id != current_player_id:
            # Get player name for display
            builder.button(text=f"👉 Игрок", callback_data=f"tod:target:{player_id}")
    
    builder.adjust(1) # One button per row for clarity
    
    return builder.as_markup()

def get_player_name_link(player_id: int) -> str:
    """Get a link to the player using Telegram's user linking feature"""
    return f'<a href="tg://user?id={player_id}">Игрок</a>'

@router.message(Command(commands=["truthordare", "tod"]))
async def start_truth_or_dare(message: Message):
    """Start a new Truth or Dare game"""
    chat_id = message.chat.id
    
    # Check if there's already a game in this chat
    if chat_id in active_games:
        await message.answer("В этом чате уже идет игра! Дождитесь её окончания.")
        return
    
    # Initialize game with just the starter
    starter_id = message.from_user.id
    game_invites[chat_id] = {
        "players": [starter_id],
        "starter": starter_id
    }
    
    # Send message asking for game mode selection
    await message.answer(
        "🎮 Начинаем игру 'Правда или действие'!\n\n"
        "Выберите режим игры:",
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
        if chat_id not in game_invites:
            game_invites[chat_id] = {}
        game_invites[chat_id]["mode"] = mode
        
        # Ask for rules mode
        await callback.message.edit_text(
            "🎮 Выберите режим правил:",
            reply_markup=create_rules_modes_keyboard()
        )
        
        await callback.answer()
        
    elif action == "rules":
        # Handle rules mode selection
        rules_mode = data_parts[2]
        
        # Get the mode from stored data
        if chat_id in game_invites and "mode" in game_invites[chat_id]:
            mode = game_invites[chat_id]["mode"]
            players = game_invites[chat_id]["players"]
            
            # Create a new game
            game = TruthOrDareGame(chat_id, players, mode, rules_mode)
            active_games[chat_id] = game
            
            # Notify about game start
            rules_description = ""
            if rules_mode == MODE_WITH_RULES:
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
                f"🎮 Игра 'Правда или действие' началась!\n"
                f"Режим: {'по часовой стрелке' if mode == MODE_CLOCKWISE else 'кому угодно'}\n"
                f"Правила: {'с правилами' if rules_mode == MODE_WITH_RULES else 'без правил'}\n"
                f"{rules_description}"
                f"Ход игрока: {get_player_name_link(game.get_current_player())}\n"
                f"Приглашаем других игроков присоединиться командой /join_tod"
            )
            
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
                    f"⏭️ {get_player_name_link(current_player_id)} использовал пас!\n"
                    f"Ход передан игроку: {get_player_name_link(next_player_id)}"
                )
                
                await callback.answer("Вы использовали пас!")
            else:
                await callback.answer("Вы уже использовали пас в этой игре!", show_alert=True)
        
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
                    f"Введите {'вопрос для "правды"' if choice == 'truth' else 'действие для выполнения'} для игрока {get_player_name_link(target_player_id)}:"
                )
                
                # Also notify the target player that they will receive a message
                await bot.send_message(
                    target_player_id,
                    f"Ожидайте {'вопрос для "правды"' if choice == 'truth' else 'действие для выполнения'} от игрока {get_player_name_link(current_player_id)} в личных сообщениях."
                )
                
                # Update game state to show who is waiting for response
                game.waiting_for_response = current_player_id
                game.expected_responder = target_player_id
                
                await callback.message.edit_text(
                    f"🎮 {get_player_name_link(current_player_id)} составляет {'вопрос' if choice == 'truth' else 'действие'} для {get_player_name_link(target_player_id)}\n"
                    f"Ожидаем отправки в личные сообщения..."
                )
                
            else:  # MODE_ANYONE
                # In "anyone" mode, let the player choose the target
                await callback.message.edit_text(
                    f"🎯 {get_player_name_link(current_player_id)}, выберите игрока для {'вопроса' if choice == 'truth' else 'действия'}:",
                    reply_markup=create_target_player_keyboard(game, current_player_id)
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
                f"🎯 {get_player_name_link(current_player_id)}, выберите для игрока {get_player_name_link(target_player_id)}:",
                reply_markup=create_truth_or_dare_choice_keyboard()
            )
        else:
            # Send to current player instructions to send via PM
            await bot.send_message(
                current_player_id,
                f"Введите {'вопрос для "правды"' if choice_type == 'truth' else 'действие для выполнения'} для игрока {get_player_name_link(target_player_id)}:"
            )
            
            # Also notify the target player that they will receive a message
            await bot.send_message(
                target_player_id,
                f"Ожидайте {'вопрос для "правды"' if choice_type == 'truth' else 'действие для выполнения'} от игрока {get_player_name_link(current_player_id)} в личных сообщениях."
            )
            
            # Update game state to show who is waiting for response
            game.waiting_for_response = current_player_id
            game.expected_responder = target_player_id
            
            await callback.message.edit_text(
                f"🎮 {get_player_name_link(current_player_id)} составляет {'вопрос' if choice_type == 'truth' else 'действие'} для {get_player_name_link(target_player_id)}\n"
                f"Ожидаем отправки в личные сообщения..."
            )
        
        await callback.answer()

@router.message(Command(commands=["end_tod", "stop_tod"]))
async def end_truth_or_dare(message: Message):
    """End the current Truth or Dare game"""
    chat_id = message.chat.id
    
    if chat_id not in active_games:
        await message.answer("В этом чате нет активной игры 'Правда или действие'!")
        return
    
    # Check if the command sender is the game creator or an admin
    game = active_games[chat_id]
    game_creator = game.players[0]  # First player is considered the creator
    sender_id = message.from_user.id
    
    # In a real implementation, we'd also check if sender is an admin
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

# Handler for joining a game
@router.message(Command(commands=["join_tod"]))
async def join_truth_or_dare(message: Message):
    """Allow a player to join an existing game"""
    chat_id = message.chat.id
    player_id = message.from_user.id
    
    if chat_id not in active_games and chat_id not in game_invites:
        await message.answer("В этом чате нет активной игры 'Правда или действие'!")
        return
    
    # Check if it's an active game
    if chat_id in active_games:
        game = active_games[chat_id]
        
        if player_id in game.players:
            await message.answer("Вы уже в этой игре!")
            return
        
        # Add player to the game
        game.players.append(player_id)
        game.passes_used[player_id] = 0  # Initialize pass count
        
        # Notify all players about the new join
        await message.answer(
            f"🎮 {get_player_name_link(player_id)} присоединился к игре!\n"
            f"Всего игроков: {len(game.players)}"
        )
    else:  # Game still being set up invites
        if player_id in game_invites[chat_id]["players"]:
            await message.answer("Вы уже в этой игре!")
            return
        
        game_invites[chat_id]["players"].append(player_id)
        
        await message.answer(
            f"🎮 {get_player_name_link(player_id)} присоединился к игре!\n"
            f"Всего игроков: {len(game_invites[chat_id]['players'])}"
        )

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
            await bot.send_message(
                target_player_id,
                f"🎭 Вам пришло задание '{content_type}' от {get_player_name_link(sender_id)}:\n\n{message.text}"
            )
            
            # Also send a confirmation to the sender
            await message.answer(f"✅ Ваше задание было отправлено игроку {get_player_name_link(target_player_id)}!")
            
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
                    f"🎮 {get_player_name_link(target_player_id)} получил задание!\n"
                    f"Ход теперь передан игроку: {get_player_name_link(game.get_current_player())}"
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
                        f"✅ {get_player_name_link(player_id)} {response_type}!\n"
                        f"Ход передан игроку: {get_player_name_link(next_player_id)}"
                    )
                else:
                    # This is a general message, not a response to a truth/dare
                    pass