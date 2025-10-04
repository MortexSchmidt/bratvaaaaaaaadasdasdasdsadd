from __future__ import annotations
from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from app.config import load_config

router = Router(name="tictactoe")

# Game state storage (in a real application, you would use a database)
active_games = {}  # Stores active games by chat_id
game_invites = {}  # Stores game invite info

def create_board(board_state):
    """Create an inline keyboard for the Tic Tac Toe board"""
    builder = InlineKeyboardBuilder()
    
    for i in range(3):
        for j in range(3):
            cell_value = board_state[i*3 + j]
            if cell_value == 0:
                builder.button(text=" ", callback_data=f"ttt:move:{i}:{j}")
            elif cell_value == 1:
                builder.button(text="❌", callback_data=f"ttt:move:{i}:{j}")
            else:
                builder.button(text="⭕", callback_data=f"ttt:move:{i}:{j}")
        builder.adjust(3)
    
    builder.button(text="🔄 Новая игра", callback_data="ttt:new")
    builder.adjust(3, 3, 3, 1)
    
    return builder.as_markup()

def create_join_button(chat_id):
    """Create a join game button"""
    builder = InlineKeyboardBuilder()
    builder.button(text=" Играть в крестики-нолики", callback_data=f"ttt:join:{chat_id}")
    return builder.as_markup()

def check_winner(board):
    """Check if there's a winner on the board"""
    # Check rows
    for i in range(0, 9, 3):
        if board[i] == board[i+1] == board[i+2] != 0:
            return board[i]
    
    # Check columns
    for i in range(3):
        if board[i] == board[i+3] == board[i+6] != 0:
            return board[i]
    
    # Check diagonals
    if board[0] == board[4] == board[8] != 0:
        return board[0]
    if board[2] == board[4] == board[6] != 0:
        return board[2]
    
    # Check for tie
    if 0 not in board:
        return 3  # Tie
    
    return 0  # No winner yet

def init_board():
    """Initialize a new game board"""
    return [0] * 9  # 0 = empty, 1 = X, 2 = O

@router.message(Command(commands=["tictactoe"]))
async def start_tictactoe(message: Message):
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
    
    # Send message with join button
    await message.answer(
        f"<a href='tg://user?id={player_id}'>Игрок</a> начал игру в крестики-нолики!\n"
        "Кто хочет сыграть против него?\n\n"
        "❌ - Создатель игры\n"
        "⭕ - Свободно",
        reply_markup=create_join_button(chat_id)
    )

@router.callback_query(lambda c: c.data and c.data.startswith("ttt:"))
async def handle_tictactoe_callback(callback: CallbackQuery):
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
        
        await callback.message.edit_text(
            f"<a href='tg://user?id={player_x_id}'>Игрок X</a> против "
            f"<a href='tg://user?id={player_id}'>Игрока O</a>\n\n"
            "Игра началась! Ходит ❌",
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
        if game["board"][position] != 0:
            await callback.answer("Эта клетка уже занята!", show_alert=True)
            return
            
        # Determine player symbol
        player_symbol = 1 if player_id == game["player_x"] else 2
        
        # Make move
        game["board"][position] = player_symbol
        game["moves"] += 1
        
        # Check for winner
        winner = check_winner(game["board"])
        
        if winner == player_symbol:  # Current player won
            player_mark = "❌" if player_symbol == 1 else "⭕"
            winner_name = "Игрок X" if player_symbol == 1 else "Игрок O"
            winner_id = game["player_x"] if player_symbol == 1 else game["player_o"]
            
            # Notify about win
            await callback.message.edit_text(
                f"<a href='tg://user?id={winner_id}'>{winner_name}</a> ({player_mark}) победил! 🎉",
                reply_markup=create_board(game["board"])
            )
            
            # Clean up game
            del active_games[chat_id]
            
        elif winner == 3:  # Tie
            player_x_id = game["player_x"]
            player_o_id = game["player_o"]
            
            # Notify about tie
            await callback.message.edit_text(
                f"<a href='tg://user?id={player_x_id}'>Игрок X</a> и "
                f"<a href='tg://user?id={player_o_id}'>Игрок O</a> сыграли вничью! 🤝",
                reply_markup=create_board(game["board"])
            )
            
            # Clean up game
            del active_games[chat_id]
            
        else:
            # Switch player
            game["current_player"] = game["player_o"] if player_id == game["player_x"] else game["player_x"]
            
            # Update board for players
            player_mark = "❌" if player_symbol == 1 else "⭕"
            next_mark = "⭕" if player_symbol == 1 else "❌"
            next_player_name = "Игрок O" if player_symbol == 1 else "Игрок X"
            next_player_id = game["player_o"] if player_symbol == 1 else game["player_x"]
            
            await callback.message.edit_text(
                f"<a href='tg://user?id={player_id}'>Игрок</a> сходил {player_mark}\n"
                f"Ходит <a href='tg://user?id={next_player_id}'>{next_player_name}</a> ({next_mark})",
                reply_markup=create_board(game["board"])
            )
            
        await callback.answer()
        
    elif action == "new":
        # Handle new game request
        await callback.answer("Для новой игры используйте команду /tictactoe", show_alert=True)
