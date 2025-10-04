from __future__ import annotations
from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from app.config import load_config

router = Router(name="tictactoe")

# Game state storage (in a real application, you would use a database)
active_games = {}  # Stores active games
open_games = []    # Stores game IDs of open games waiting for players
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

def create_join_button(game_id):
    """Create a join game button"""
    builder = InlineKeyboardBuilder()
    builder.button(text=" Играть в крестики-нолики", callback_data=f"ttt:join:{game_id}")
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
    """Create a new Tic Tac Toe game and wait for opponent"""
    player_id = message.from_user.id
    
    # Check if player is already in a game
    for game_id, game in active_games.items():
        if player_id in [game["player_x"], game["player_o"]]:
            await message.answer("Вы уже в игре!")
            return
    
    # Create a new game
    import random
    game_id = f"{random.randint(10000, 99999)}"
    
    active_games[game_id] = {
        "board": init_board(),
        "player_x": player_id,
        "player_o": None,
        "current_player": player_id,
        "moves": 0
    }
    
    open_games.append(game_id)
    
    # Send message with join button
    await message.answer(
        "Крестики-нолики: ожидание второго игрока...",
        reply_markup=create_join_button(game_id)
    )

@router.callback_query(lambda c: c.data and c.data.startswith("ttt:"))
async def handle_tictactoe_callback(callback: CallbackQuery):
    """Handle all Tic Tac Toe callbacks"""
    player_id = callback.from_user.id
    data_parts = callback.data.split(":")
    action = data_parts[1]
    
    if action == "join":
        # Handle joining a game
        game_id = data_parts[2]
        
        # Check if game still exists and is open
        if game_id not in active_games:
            await callback.answer("Игра больше не существует!", show_alert=True)
            return
            
        if game_id not in open_games:
            await callback.answer("Лобби заполнено!", show_alert=True)
            return
            
        game = active_games[game_id]
        
        # Check if player is already in this game
        if player_id in [game["player_x"], game["player_o"]]:
            await callback.answer("Вы уже в этой игре!", show_alert=True)
            return
        
        # Add player as O
        game["player_o"] = player_id
        open_games.remove(game_id)  # Close the lobby
        
        # Notify players
        # Player X (creator)
        await callback.bot.send_message(
            game["player_x"],
            "Игрок присоединился! Вы играете за ❌\nВаш ход",
            reply_markup=create_board(game["board"])
        )
        
        # Player O (joiner)
        await callback.bot.send_message(
            player_id,
            "Вы присоединились к игре! Вы играете за ⭕\nХод соперника...",
            reply_markup=create_board(game["board"])
        )
        
        await callback.answer("Вы присоединились к игре!")
        
    elif action == "move":
        # Handle making a move
        if len(data_parts) < 4:
            await callback.answer("Неверный формат хода!", show_alert=True)
            return
            
        row, col = int(data_parts[2]), int(data_parts[3])
        position = row * 3 + col
        
        # Find game player is in
        game_id = None
        player_symbol = None
        for gid, game in active_games.items():
            if player_id in [game["player_x"], game["player_o"]]:
                game_id = gid
                player_symbol = 1 if player_id == game["player_x"] else 2
                break
                
        if not game_id:
            await callback.answer("Вы не в игре!", show_alert=True)
            return
            
        game = active_games[game_id]
        
        # Check if it's player's turn
        if game["current_player"] != player_id:
            await callback.answer("Сейчас не ваш ход!", show_alert=True)
            return
            
        # Check if cell is already occupied
        if game["board"][position] != 0:
            await callback.answer("Эта клетка уже занята!", show_alert=True)
            return
            
        # Make move
        game["board"][position] = player_symbol
        game["moves"] += 1
        
        # Check for winner
        winner = check_winner(game["board"])
        
        # Determine opponent
        opponent_id = game["player_o"] if player_id == game["player_x"] else game["player_x"]
        opponent_symbol = 2 if player_symbol == 1 else 1
        
        if winner == player_symbol:  # Current player won
            # Notify winner
            await callback.message.edit_text(
                "🎉 Вы выиграли! 🎉", 
                reply_markup=create_board(game["board"])
            )
            
            # Notify opponent
            await callback.bot.send_message(
                opponent_id,
                "💀 Вы проиграли! 💀",
                reply_markup=create_board(game["board"])
            )
            
            # Clean up game
            del active_games[game_id]
            
        elif winner == 3:  # Tie
            # Notify both players
            await callback.message.edit_text(
                "Ничья! 🤝", 
                reply_markup=create_board(game["board"])
            )
            
            await callback.bot.send_message(
                opponent_id,
                "Ничья! 🤝",
                reply_markup=create_board(game["board"])
            )
            
            # Clean up game
            del active_games[game_id]
            
        else:
            # Switch player
            game["current_player"] = opponent_id
            
            # Update boards for both players
            player_mark = "❌" if player_symbol == 1 else "⭕"
            opponent_mark = "⭕" if player_symbol == 1 else "❌"
            
            # Notify current player
            await callback.message.edit_text(
                f"Вы сходили {player_mark}\nХод соперника...",
                reply_markup=create_board(game["board"])
            )
            
            # Notify opponent
            await callback.bot.send_message(
                opponent_id,
                f"Соперник сходил {player_mark}\nВаш ход {opponent_mark}",
                reply_markup=create_board(game["board"])
            )
            
        await callback.answer()
        
    elif action == "new":
        # Handle new game request
        await callback.answer("Для новой игры используйте команду /tictactoe", show_alert=True)
