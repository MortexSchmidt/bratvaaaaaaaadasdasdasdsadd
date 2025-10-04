from __future__ import annotations
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command

router = Router(name="tictactoe")

# Game state storage (in a real application, you would use a database)
games = {}

def create_board(board_state):
    """Create an inline keyboard for the Tic Tac Toe board"""
    builder = InlineKeyboardBuilder()
    
    for i in range(3):
        for j in range(3):
            cell_value = board_state[i*3 + j]
            if cell_value == 0:
                builder.button(text=" ", callback_data=f"ttt:{i}:{j}")
            elif cell_value == 1:
                builder.button(text="❌", callback_data=f"ttt:{i}:{j}")
            else:
                builder.button(text="⭕", callback_data=f"ttt:{i}:{j}")
        builder.adjust(3)
    
    builder.button(text="🔄 Новая игра", callback_data="ttt:new")
    builder.adjust(3, 3, 3, 1)
    
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
    """Start a new Tic Tac Toe game"""
    board = init_board()
    games[message.chat.id] = {
        "board": board,
        "current_player": 1,  # 1 = X, 2 = O
        "moves": 0
    }
    
    await message.answer("Игра Крестики-Нолики началась!\n\nТвой ход: ❌", reply_markup=create_board(board))

@router.callback_query(lambda c: c.data and c.data.startswith("ttt:"))
async def handle_tictactoe_move(callback: CallbackQuery):
    """Handle Tic Tac Toe moves"""
    chat_id = callback.message.chat.id
    
    if chat_id not in games:
        await callback.answer("Игра не найдена. Начните новую игру с помощью /tictactoe", show_alert=True)
        return
    
    game = games[chat_id]
    
    if callback.data == "ttt:new":
        # Start a new game
        board = init_board()
        games[chat_id] = {
            "board": board,
            "current_player": 1,
            "moves": 0
        }
        await callback.message.edit_text("Игра Крестики-Нолики началась!\n\nТвой ход: ❌", reply_markup=create_board(board))
        await callback.answer()
        return
    
    # Parse move data
    _, row, col = callback.data.split(":")
    row, col = int(row), int(col)
    position = row * 3 + col
    
    # Check if cell is already occupied
    if game["board"][position] != 0:
        await callback.answer("Эта клетка уже занята!", show_alert=True)
        return
    
    # Make move
    game["board"][position] = game["current_player"]
    game["moves"] += 1
    
    # Check for winner
    winner = check_winner(game["board"])
    
    if winner == 1:
        await callback.message.edit_text("🎉 Победили Крестики! 🎉", reply_markup=create_board(game["board"]))
        del games[chat_id]
    elif winner == 2:
        await callback.message.edit_text("🎉 Победили Нолики! 🎉", reply_markup=create_board(game["board"]))
        del games[chat_id]
    elif winner == 3:
        await callback.message.edit_text("Ничья! 🤝", reply_markup=create_board(game["board"]))
        del games[chat_id]
    else:
        # Switch player
        game["current_player"] = 2 if game["current_player"] == 1 else 1
        player_symbol = "❌" if game["current_player"] == 1 else "⭕"
        await callback.message.edit_text(f"Игра Крестики-Нолики\n\nТвой ход: {player_symbol}", reply_markup=create_board(game["board"]))
    
    await callback.answer()