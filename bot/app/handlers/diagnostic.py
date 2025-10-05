from __future__ import annotations
import os, logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router(name="diagnostic")

@router.message(Command(commands=["_ping","_diag"]))
async def cmd_diag(message: Message):
    safe_env = {}
    for k in ("TIMEZONE","DB_DIR"):
        if k in os.environ:
            safe_env[k] = os.environ[k]
    text = ["🩺 DIAG", f"chat={message.chat.id}", f"user={message.from_user.id}"]
    text.append(f"env={safe_env}")
    text.append("Если другие команды молчат, значит update не доходит до нужного роутера или бот не видит сообщения.")
    await message.answer("\n".join(text))

# Fallback для любых неизвестных команд
@router.message()
async def fallback(message: Message):
    if message.text and message.text.startswith('/'):
        # Уже разобранные команды должны быть перехвачены раньше; если мы тут — значит хендлера нет
        await message.answer(f"⁉ Неизвестная команда: {message.text}\nПопробуй /help или /_diag")
        logging.getLogger("fallback").info("Unknown command seen: %s", message.text)
