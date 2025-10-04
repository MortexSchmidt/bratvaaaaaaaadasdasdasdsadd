from __future__ import annotations
from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command

router = Router(name="tictactoe")

# Constants for game symbols
EMPTY_CELL = 0
PLAYER_X = 1
PLAYER_O = 2
TIE = 3

# Game state storage (in a real application, you would use a database)
active_games = {}  # Stores active games by chat_id

# Game state storage (in a real application, you would use a database)
game_invites = {}  # Stores game invite info

def create_board(board_state):
    """Create an inline keyboard for the Tic Tac Toe board"""
    builder = InlineKeyboardBuilder()
    
    # Add visual styling to the board
    for i in range(3):
        for j in range(3):
            cell_value = board_state[i*3 + j]
            if cell_value == EMPTY_CELL:
                builder.button(text="⬜", callback_data=f"ttt:move:{i}:{j}")
            elif cell_value == PLAYER_X:
                builder.button(text="❌", callback_data=f"ttt:move:{i}:{j}")
            else:
                builder.button(text="⭕", callback_data=f"ttt:move:{i}:{j}")
        builder.adjust(3)
    
    # Add game controls
    builder.button(text="🔄 Новая игра", callback_data="ttt:new")
    builder.button(text="❌ Сдаться", callback_data="ttt:quit")
    builder.adjust(3, 2)
    
    return builder.as_markup()

def get_player_symbol(player_id, game):
    """Get the symbol (X or O) for a player"""
    if player_id == game["player_x"]:
        return PLAYER_X
    elif player_id == game["player_o"]:
        return PLAYER_O
    return None

async def get_user_name_by_id(bot, user_id):
    """Get the user's display name by their ID"""
    try:
        user = await bot.get_chat_member(chat_id=user_id, user_id=user_id)
        user_info = user.user
        if user_info.first_name and user_info.last_name:
            return f"{user_info.first_name} {user_info.last_name}"
        elif user_info.first_name:
            return user_info.first_name
        elif user_info.username:
            return user_info.username
        else:
            return f"Пользователь {user_info.id}"
    except:
        return f"Пользователь {user_id}"

def get_player_link(player_id):
    """Get a link to the player using Telegram's user linking feature"""
    return f'<a href="tg://user?id={player_id}">Пользователь</a>'

def get_player_name(player_symbol, game, player_x_id=None, player_o_id=None):
    """Get the display name for a player symbol"""
    if player_symbol == PLAYER_X and player_x_id:
        return f'<a href="tg://user?id={player_x_id}">Игрок X</a>'
    elif player_symbol == PLAYER_O and player_o_id:
        return f'<a href="tg://user?id={player_o_id}">Игрок O</a>'
    elif player_symbol == PLAYER_X:
        return "Игрок X"
    elif player_symbol == PLAYER_O:
        return "Игрок O"
    return "Неизвестный игрок"

def get_player_mark(player_symbol):
    """Get the display mark for a player symbol"""
    if player_symbol == PLAYER_X:
        return "❌"
    elif player_symbol == PLAYER_O:
        return "⭕"
    return " "

def create_join_button(chat_id):
    """Create a join game button"""
    builder = InlineKeyboardBuilder()
    builder.button(text=" Играть в крестики-нолики", callback_data=f"ttt:join:{chat_id}")
    return builder.as_markup()

def check_winner(board):
    """Check if there's a winner on the board"""
    # Check rows
    for i in range(0, 9, 3):
        if board[i] == board[i+1] == board[i+2] != EMPTY_CELL:
            return board[i]
    
    # Check columns
    for i in range(3):
        if board[i] == board[i+3] == board[i+6] != EMPTY_CELL:
            return board[i]
    
    # Check diagonals
    if board[0] == board[4] == board[8] != EMPTY_CELL:
        return board[0]
    if board[2] == board[4] == board[6] != EMPTY_CELL:
        return board[2]
    
    # Check for tie
    if EMPTY_CELL not in board:
        return TIE  # Tie
    
    return EMPTY_CELL  # No winner yet

def init_board():
    """Initialize a new game board"""
    return [EMPTY_CELL] * 9  # 0 = empty, 1 = X, 2 = O

@router.message(Command(commands=["tictactoe"]))
async def start_tictactoe(message: Message, bot: Bot):
    """Create a new Tic Tac Toe game in chat"""
    chat_id = message.chat.id
    player_id = message.from_user.id
    
    # Check if there's already a game in this chat
    if chat_id in active_games:
        await message.answer("В этом чате уже идет игра! Дождитесь её окончания.")
        return
    
    # Create a new game
    active_games[chat_id] = {
        "board": init_board(),
        "player_x": player_id,
        "player_o": None,
        "current_player": player_id,
        "moves": 0,
        "chat_id": chat_id
    }
    
    player_name = await get_user_name_by_id(message.bot, player_id)
    
    # Send message with join button
    await message.answer(
        f"🎮 {player_name} начал игру в крестики-нолики!\n"
        "Кто хочет сыграть против него?\n\n"
        "❌ - Создатель игры (X)\n"
        "⭕ - Свободно (O)\n\n"
        "Нажмите кнопку ниже, чтобы присоединиться к игре!",
        reply_markup=create_join_button(chat_id)
    )

@router.callback_query(lambda c: c.data and c.data.startswith("ttt:"))
async def handle_tictactoe_callback(callback: CallbackQuery, bot):
    """Handle all Tic Tac Toe callbacks"""
    player_id = callback.from_user.id
    chat_id = callback.message.chat.id
    data_parts = callback.data.split(":")
    action = data_parts[1]
    
    if action == "join":
        # Handle joining a game
        game_chat_id = int(data_parts[2])
        
        # Check if game still exists
        if game_chat_id not in active_games:
            await callback.answer("Игра больше не существует!", show_alert=True)
            return
            
        game = active_games[game_chat_id]
        
        # Check if player is already in this game
        if player_id in [game["player_x"], game["player_o"]]:
            await callback.answer("Вы уже в этой игре!", show_alert=True)
            return
            
        # Check if second player is already set
        if game["player_o"] is not None:
            await callback.answer("К игре уже присоединился другой игрок!", show_alert=True)
            return
        
        # Add player as O
        game["player_o"] = player_id
        
        # Notify players
        player_x_id = game["player_x"]
        
        player_x_name = await get_user_name_by_id(bot, game["player_x"])
        player_o_name = await get_user_name_by_id(bot, game["player_o"])
        
        await callback.message.edit_text(
            f"🎮 {player_x_name} против {player_o_name}\n\n"
            "Игра началась! Ходит ❌\n\n"
            "Для сдачи нажмите кнопку 'Сдаться' под полем.",
            reply_markup=create_board(game["board"])
        )
        
        await callback.answer("Вы присоединились к игре!")
        
    elif action == "move":
        # Handle making a move
        if len(data_parts) < 4:
            await callback.answer("Неверный формат хода!", show_alert=True)
            return
            
        # Check if there's a game in this chat
        if chat_id not in active_games:
            await callback.answer("В этом чате нет активной игры!", show_alert=True)
            return
            
        game = active_games[chat_id]
        
        # Check if player is in this game
        if player_id not in [game["player_x"], game["player_o"]]:
            await callback.answer("Вы не участвуете в этой игре!", show_alert=True)
            return
            
        row, col = int(data_parts[2]), int(data_parts[3])
        position = row * 3 + col
        
        # Check if it's player's turn
        if game["current_player"] != player_id:
            await callback.answer("Сейчас не ваш ход!", show_alert=True)
            return
            
        # Check if cell is already occupied
        if game["board"][position] != EMPTY_CELL:
            await callback.answer("Эта клетка уже занята!", show_alert=True)
            return
            
        # Determine player symbol
        player_symbol = get_player_symbol(player_id, game)
        
        # Make move
        game["board"][position] = player_symbol
        game["moves"] += 1
        
        # Check for winner
        winner = check_winner(game["board"])
        
        if winner == player_symbol:  # Current player won
            player_mark = get_player_mark(player_symbol)
            winner_id = game["player_x"] if player_symbol == PLAYER_X else game["player_o"]
            winner_name = await get_user_name_by_id(bot, winner_id)
            
            # Notify about win
            await callback.message.edit_text(
                f"🎉 Победа! 🎉\n"
                f"{winner_name} ({player_mark}) выиграл!\n\n"
                f"Сыграно ходов: {game['moves']}",
                reply_markup=create_board(game["board"])
            )
            
            # Clean up game
            del active_games[chat_id]
            
        elif winner == TIE:  # Tie
            player_x_name = await get_user_name_by_id(bot, game["player_x"])
            player_o_name = await get_user_name_by_id(bot, game["player_o"])
            
            # Notify about tie
            await callback.message.edit_text(
                f"🤝 Ничья! 🤝\n"
                f"{player_x_name} и {player_o_name} сыграли вничью!\n\n"
                f"Сыграно ходов: {game['moves']}",
                reply_markup=create_board(game["board"])
            )
            
            # Clean up game
            del active_games[chat_id]
            
        else:
            # Switch player
            game["current_player"] = game["player_o"] if player_id == game["player_x"] else game["player_x"]
            
            # Update board for players
            current_player_name = await get_user_name_by_id(bot, player_id)
            next_player_id = game["player_o"] if player_id == game["player_x"] else game["player_x"]
            next_player_name = await get_user_name_by_id(bot, next_player_id)
            player_mark = get_player_mark(player_symbol)
            next_mark = get_player_mark(PLAYER_O if player_symbol == PLAYER_X else PLAYER_X)
            
            await callback.message.edit_text(
                f"🎮 Ход #{game['moves'] + 1}\n"
                f"{current_player_name} сходил {player_mark}\n"
                f"Ходит {next_player_name} ({next_mark})",
                reply_markup=create_board(game["board"])
            )
            
        await callback.answer()
        
    elif action == "new":
        # Handle new game request
        await callback.answer("Для новой игры используйте команду /tictactoe", show_alert=True)
        
    elif action == "quit":
        # Handle surrender request
        if chat_id not in active_games:
            await callback.answer("В этом чате нет активной игры!", show_alert=True)
            return
            
        game = active_games[chat_id]
        
        # Check if player is in this game
        if player_id not in [game["player_x"], game["player_o"]]:
            await callback.answer("Вы не участвуете в этой игре!", show_alert=True)
            return
            
        # Determine who is surrendering and who wins
        surrenderer_name = await get_user_name_by_id(bot, player_id)
        winner_id = game["player_o"] if player_id == game["player_x"] else game["player_x"]
        winner_name = await get_user_name_by_id(bot, winner_id)
            
        # Notify about surrender
        await callback.message.edit_text(
            f"🏳️ {surrenderer_name} сдался!\n"
            f"{winner_name} выигрывает!",
            reply_markup=create_board(game["board"])
        )
        
        # Clean up game
        del active_games[chat_id]
        
        await callback.answer("Вы сдались в игре.")
